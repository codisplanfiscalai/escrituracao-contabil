"""Window visibility and explicit shutdown, independent of the native tray API."""
from __future__ import annotations

import json
from pathlib import Path
import webbrowser


def load_settings(path):
    try:
        value = Path(path).read_text(encoding='utf-8')
        value = json.loads(value)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def start_minimized(config, *, background=False, show_window=False):
    if show_window:
        return False
    return background or config.get('start_minimized') is True


def save_settings(path, previous, *, database, port, auto_start, minimized):
    """Preserve existing preferences; never move or open the selected database."""
    values = {**previous, 'database': str(database), 'port': port,
              'auto_start': bool(auto_start), 'start_minimized': bool(minimized)}
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)
    return values


class DesktopLifecycle:
    def __init__(self, root, backend, report_error):
        self.root = root
        self.backend = backend
        self.report_error = report_error
        self.tray = None
        self.closing = False

    def show(self):
        if self.closing:
            return
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        if self.closing:
            return
        if self.tray and self.tray.available:
            self.root.withdraw()
        else:
            self.root.iconify()

    def open_url(self, url):
        try:
            if not webbrowser.open(url):
                raise OSError('O Windows não confirmou a abertura do navegador padrão.')
        except Exception as error:
            self.report_error('Não foi possível abrir o navegador. O aplicativo continua ativo.', error)
            return False
        return True

    def quit(self):
        if self.closing:
            return
        self.closing = True
        try:
            self.backend.stop()
        except Exception as error:
            self.report_error('Falha ao interromper o serviço local.', error)
        finally:
            try:
                if self.tray:
                    self.tray.close()
            finally:
                self.root.destroy()
