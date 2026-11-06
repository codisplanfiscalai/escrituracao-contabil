"""Visibility, modal windows, queued tray actions and explicit process shutdown."""
import os
from pathlib import Path
import queue
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import Mock, patch
import uuid

from desktop_lifecycle import DesktopLifecycle, load_settings, save_settings, start_minimized
from windows_app import Tray
from src import local_app


class DesktopPreferenceTests(unittest.TestCase):
    def test_visible_by_default_and_explicit_switches_override_saved_preference(self):
        for config in ({}, {'auto_start':True}, {'start_minimized':False}, {'start_minimized':'false'}):
            self.assertFalse(start_minimized(config))
            self.assertTrue(start_minimized(config, background=True))
        self.assertTrue(start_minimized({'start_minimized':True}))
        self.assertFalse(start_minimized({'start_minimized':True}, show_window=True))

    def test_preferences_round_trip_preserves_other_values_and_never_moves_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'desktop.json'
            database = Path(directory) / 'private.sqlite3'
            database.write_bytes(b'synthetic bytes, never opened')
            values = save_settings(path, {'future_preference':'preserved'}, database=database,
                port=8765, auto_start=True, minimized=True)
            self.assertEqual(load_settings(path), values)
            self.assertEqual(values['future_preference'], 'preserved')
            self.assertTrue(start_minimized(load_settings(path)))
            self.assertEqual(database.read_bytes(), b'synthetic bytes, never opened')
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_invalid_or_non_object_settings_recover_to_visible_start(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'desktop.json'
            self.assertEqual(load_settings(path), {})
            for text in ('[]','null','true','"text"','{broken'):
                path.write_text(text)
                self.assertFalse(start_minimized(load_settings(path)))


class DesktopLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.root = Mock()
        self.backend = Mock()
        self.error = Mock()
        self.lifecycle = DesktopLifecycle(self.root, self.backend, self.error)
        self.lifecycle.tray = Mock(available=True)

    def test_close_window_only_hides_and_restore_does_not_restart_backend(self):
        self.lifecycle.hide()
        self.root.withdraw.assert_called_once()
        self.lifecycle.show()
        self.root.deiconify.assert_called_once()
        self.backend.stop.assert_not_called()
        self.root.destroy.assert_not_called()

    def test_tray_unavailable_minimizes_to_taskbar_without_losing_window(self):
        self.lifecycle.tray.available = False
        self.lifecycle.hide()
        self.root.iconify.assert_called_once()
        self.root.withdraw.assert_not_called()
        self.root.destroy.assert_not_called()

    def test_browser_success_failure_and_exception_never_stop_application(self):
        for result in (True, False, OSError('Synthetic shell failure')):
            with patch('desktop_lifecycle.webbrowser.open', side_effect=result if isinstance(result, Exception) else None,
                       return_value=result):
                self.assertEqual(self.lifecycle.open_url('http://127.0.0.1:8765'), result is True)
        self.assertEqual(self.error.call_count, 2)
        self.backend.stop.assert_not_called()
        self.lifecycle.tray.close.assert_not_called()
        self.root.destroy.assert_not_called()

    def test_explicit_quit_is_idempotent_and_ignores_later_restore_callbacks(self):
        self.lifecycle.quit(); self.lifecycle.quit(); self.lifecycle.show(); self.lifecycle.hide()
        self.backend.stop.assert_called_once()
        self.lifecycle.tray.close.assert_called_once()
        self.root.destroy.assert_called_once()
        self.root.deiconify.assert_not_called()
        self.root.withdraw.assert_not_called()

    def test_shutdown_still_cleans_tray_and_window_if_backend_stop_raises(self):
        self.backend.stop.side_effect = OSError('Synthetic stop failure')
        self.lifecycle.quit()
        self.error.assert_called_once()
        self.lifecycle.tray.close.assert_called_once()
        self.root.destroy.assert_called_once()


class TrayQueueTests(unittest.TestCase):
    def setUp(self):
        self.tray = object.__new__(Tray)
        self.tray.root = Mock()
        self.tray.pending = queue.SimpleQueue()
        self.tray.closed = False
        self.tray.taskbar_created = 0xC123
        self.callback = Mock()
        self.tray.callbacks = {1:('Restore',self.callback)}

    def test_native_notifications_only_enqueue_without_calling_tcl(self):
        self.tray.handle(None, 0x8002, 0, 0)
        self.tray.handle(None, 0x8001, 0, 0x0203)
        self.tray.root.after.assert_not_called()
        self.callback.assert_not_called()
        self.tray.pump()
        self.assertEqual(self.callback.call_count, 2)
        self.tray.root.after.assert_called_once()

    def test_failed_action_is_reported_and_next_action_still_runs(self):
        self.tray.callbacks[2] = ('Failure',Mock(side_effect=OSError('Synthetic action failure')))
        self.tray.pending.put((2,None)); self.tray.pending.put((1,None))
        self.tray.pump()
        self.tray.root.report_callback_exception.assert_called_once()
        self.callback.assert_called_once()
        self.tray.root.after.assert_called_once()

    def test_quit_from_tray_does_not_call_tcl_again_or_run_later_actions(self):
        backend = Mock()
        lifecycle = DesktopLifecycle(self.tray.root, backend, Mock())
        lifecycle.tray = self.tray
        self.tray.close = Mock(side_effect=lambda: setattr(self.tray, 'closed', True))
        self.tray.callbacks[6] = ('Quit', lifecycle.quit)
        self.tray.pending.put((6,None)); self.tray.pending.put((1,None))
        self.tray.pump()
        backend.stop.assert_called_once()
        self.tray.root.destroy.assert_called_once()
        self.tray.root.after.assert_not_called()
        self.callback.assert_not_called()

    def test_native_callback_exception_is_queued_instead_of_escaping_wndproc(self):
        self.tray.user = Mock()
        self.tray.user.DefWindowProcW.side_effect = OSError('Synthetic native callback error')
        self.assertEqual(self.tray.handle(None, 0, 0, 0), 0)
        self.tray.root.report_callback_exception.assert_not_called()
        self.tray.pump()
        self.tray.root.report_callback_exception.assert_called_once()


@unittest.skipUnless(os.name == 'nt', 'Requires native Windows/Tk and its message queue')
class NativeDesktopLifecycleTests(unittest.TestCase):
    def test_native_tray_restore_modal_popup_escape_and_explicit_shutdown(self):
        root = tk.Tk()
        def cleanup_root():
            try: root.destroy()
            except tk.TclError: pass
        self.addCleanup(cleanup_root)
        root.title('Synthetic Escritura lifecycle test')
        backend, error = Mock(), Mock()
        lifecycle = DesktopLifecycle(root, backend, error)
        tray = Tray(root, local_app.WEB_ROOT / 'assets/icon.ico', {1:('Restore',lifecycle.show)}, uuid.uuid4().hex)
        lifecycle.tray = tray
        self.addCleanup(tray.close)
        root.protocol('WM_DELETE_WINDOW', lifecycle.hide)
        root.update()
        lifecycle.hide()
        tray.user.PostMessageW(tray.window, 0x8002, 0, 0)
        deadline = time.monotonic()+5
        while root.state() != 'normal' and time.monotonic()<deadline:
            root.update(); time.sleep(.01)
        self.assertEqual(root.state(), 'normal')
        popup = tk.Toplevel(root); popup.transient(root); popup.grab_set()
        root.after(80, popup.destroy)
        root.wait_window(popup)
        root.event_generate('<Escape>'); root.update()
        self.assertEqual(root.state(), 'normal')
        backend.stop.assert_not_called()
        self.assertTrue(root.winfo_exists())
        error.assert_not_called()
        lifecycle.quit()
        backend.stop.assert_called_once()
