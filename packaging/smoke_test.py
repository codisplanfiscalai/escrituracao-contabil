"""Real process + HTTP smoke test, using only disposable fictitious data."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import uuid
from contextlib import closing
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time


def request(port, path, *, token=None, data=None, origin=None, session=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    headers = {}
    if token:
        headers["X-Local-Token"] = token
    if session and session.get("cookie"):
        headers["Cookie"] = session["cookie"]
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers.update({"Content-Type": "application/json", "Origin": origin or f"http://127.0.0.1:{port}"})
    try:
        conn.request("POST" if data is not None else "GET", path, body, headers)
        response = conn.getresponse()
        if session is not None and response.getheader("Set-Cookie"):
            session["cookie"] = response.getheader("Set-Cookie").split(";",1)[0]
        return response.status, response.read()
    finally:
        conn.close()


def stop(process):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None
    if process.poll() is None:
        if os.name == "nt":
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.SetEvent.argtypes = [wintypes.HANDLE]
            assert kernel.SetEvent(process._stop_event), "Cannot signal GUI shutdown"
        else:
            process.send_signal(signal.SIGINT)
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise AssertionError("Application did not stop within 15 seconds") from None
    if os.name == "nt":
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(process._stop_event)
    if process.returncode != 0:
        raise AssertionError(f"Exit status {process.returncode}: {stdout!r} {stderr!r}")


def run(command, *, server=False):
    with tempfile.TemporaryDirectory(prefix="escrituracao-smoke-") as directory:
        root = Path(directory)
        database = root / "private-data" / "synthetic.sqlite3"
        old_token = None
        for iteration in range(2):
            # Pick a fresh local port: closed TCP sessions may remain in TIME_WAIT.
            with socket.socket() as reserve:
                reserve.bind(("127.0.0.1", 0))
                port = reserve.getsockname()[1]
            environment = os.environ.copy()
            if server:
                environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
            if os.name == "nt":
                kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
                kernel.CreateEventW.restype = wintypes.HANDLE
                event_name = "Local\\EscrituraSmoke_" + uuid.uuid4().hex
                stop_event = kernel.CreateEventW(None, True, False, event_name)
                assert stop_event
                environment["ESCRITURA_SMOKE_STOP_EVENT"] = event_name
                status_file = root / f"gui-status-{iteration}.json"
                environment["ESCRITURA_SMOKE_STATUS_FILE"] = str(status_file)
            process = subprocess.Popen(
                [*command, "--database", str(database), "--port", str(port)],
                cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            if os.name == "nt": process._stop_event = stop_event
            try:
                deadline = time.monotonic() + 45
                while True:
                    if process.poll() is not None:
                        raise AssertionError(f"Application exited before HTTP became ready: {process.communicate()!r}")
                    try:
                        status, html = request(port, "/")
                        if status == 200:
                            break
                    except (OSError, http.client.HTTPException):
                        pass
                    if time.monotonic() >= deadline:
                        raise AssertionError("HTTP startup timed out")
                    time.sleep(0.1)
                if os.name == "nt":
                    while not status_file.exists() and time.monotonic() < deadline: time.sleep(0.1)
                    gui = json.loads(status_file.read_text(encoding="utf-8"))
                    assert gui["tk_window"] and gui["tray_window"] and gui["backend_running"], gui
                    if gui["frozen"]: assert not gui["console_window"], "A GUI executable must not create a console"
                assert b'/portal/app.js' in html, 'Corporate portal missing'
                session = {}
                if iteration == 0:
                    setup_token = (database.parent / 'identity' / 'setup.token').read_text().strip()
                    code, body = request(port, '/api/v1/setup', data={'token':setup_token, 'name':'Operador sintético', 'email':'smoke@example.test', 'password':'synthetic-password-2026'}, session=session)
                    assert code == 200, body
                code, body = request(port, '/api/v1/auth/login', data={'email':'smoke@example.test','password':'synthetic-password-2026'}, session=session)
                assert code == 200, body
                token = json.loads(body)['data']['csrf']
                for asset in ('/portal/app.js','/portal/app.css','/portal/render.js','/portal/vendor/vue.js','/app.js','/posting_math.js','/posting_editor.js','/integrated_workspace.js','/style.css','/assets/symbol.svg','/assets/icon.svg',
                              *(f'/assets/icon-{size}.png' for size in (16,24,32,48,64,128,256,512))):
                    code, content = request(port, asset)
                    assert code == 200 and content, asset
                assert request(port, '/api/companies')[0] == 401
                assert request(port, '/api/companies', token=token, data={}, origin='https://example.invalid',session=session)[0] == 403
                assert request(port, '/api/companies', data={},session=session)[0] == 403
                if iteration == 0:
                    code, body = request(port, '/api/companies', token=token, data={'name':'Empresa ficticia de empacotamento','prosoft_company_code':'SYNTHETIC','prosoft_plan_code':'TEST'},session=session)
                    assert code == 200, body
                else:
                    assert token != old_token, 'New login must issue a new session'
                code, body = request(port, '/api/companies',token=token,session=session)
                assert code == 200 and len(json.loads(body)['data']) == 1, body
                code, workspace = request(port, '/workspace',session=session)
                assert code == 200 and token.encode() in workspace, 'Authenticated workspace missing'
                code, body = request(port, '/api/v1/auth/logout',data={},token=token,session=session)
                assert code == 200, body
                assert request(port, '/api/companies',token=token,session=session)[0] == 401
                old_token = token
            finally:
                stop(process)
            assert database.is_file(), "SQLite was not written outside the installation"
            # sqlite3's own context manager commits/rolls back but does NOT close.
            # Windows cannot delete the temporary database while this handle lives.
            with closing(sqlite3.connect(database)) as connection:
                assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            with socket.socket() as probe:
                assert probe.connect_ex(("127.0.0.1", port)) != 0, "Listener survived process shutdown"
        mode = "Windows GUI/tray" if os.name == "nt" else ("server entrypoint" if server else "launcher")
        print(f"PASS: corporate login, logout, CSRF/origin, Vue assets, synthetic POST, external SQLite, {mode}, restart/persistence")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--server", action="store_true", help="Testar o entrypoint real do contêiner")
    options = parser.parse_args()
    command = [str(options.executable.resolve())] if options.executable else [sys.executable, str(Path(__file__).with_name("launcher.py").resolve())]
    if options.server:
        if options.executable: parser.error("Escolha --server ou --executable")
        command = [sys.executable, "-m", "src.server.runtime"]
    run(command, server=options.server)
