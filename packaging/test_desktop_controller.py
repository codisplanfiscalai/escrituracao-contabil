"""Lifecycle real do serviço controlado pela interface, com dados descartáveis."""
from pathlib import Path
import socket
import tempfile
import unittest
from windows_app import BackendController
from src import local_app


class DesktopControllerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'private' / 'test.sqlite3'
        self.controller = BackendController(); self.addCleanup(self.controller.stop)
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0)); self.port = reserve.getsockname()[1]
    def test_start_is_idempotent_and_stop_releases_listener(self):
        self.controller.start(self.path, self.port); first = self.controller.server
        self.controller.start(self.path, self.port)
        self.assertIs(self.controller.server, first); self.assertTrue(self.controller.running)
        self.controller.stop(); self.controller.stop(); self.assertFalse(self.controller.running)
        with socket.socket() as probe: self.assertNotEqual(probe.connect_ex(('127.0.0.1', self.port)),0)
    def test_restart_preserves_database(self):
        self.controller.start(self.path, self.port)
        with local_app.open_store(self.path) as store: store.create_company('Empresa fictícia', 'TEST', 'TEST')
        self.controller.stop(); self.controller.start(self.path, self.port)
        with local_app.open_store(self.path) as store: self.assertEqual(len(store.list_companies()),1)
    def test_bad_port_and_installation_database_are_rejected(self):
        with self.assertRaises(ValueError): self.controller.start(self.path,80)
        with self.assertRaises(ValueError): self.controller.start(local_app.PROJECT_ROOT / 'data.sqlite3',self.port)
        self.assertFalse(self.path.exists()); self.assertFalse(self.controller.running)
    def test_occupied_port_does_not_claim_running_state(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1',self.port)); occupied.listen()
            with self.assertRaises(OSError): self.controller.start(self.path,self.port)
        self.assertFalse(self.controller.running)


if __name__ == '__main__': unittest.main()
