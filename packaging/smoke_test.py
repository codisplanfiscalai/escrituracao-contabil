"""Real process + HTTP smoke test, using only disposable fictitious data."""
from __future__ import annotations

import argparse
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


def request(port, path, *, token=None, data=None, origin=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    headers = {}
    if token:
        headers["X-Local-Token"] = token
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers.update({"Content-Type": "application/json", "Origin": origin or f"http://127.0.0.1:{port}"})
    try:
        conn.request("POST" if data is not None else "GET", path, body, headers)
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


def stop(process):
    if process.poll() is None:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
    try:
        stdout, stderr = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise AssertionError("Application did not stop within 15 seconds") from None
    if process.returncode != 0:
        raise AssertionError(f"Exit status {process.returncode}: {stdout!r} {stderr!r}")


def run(command):
    with tempfile.TemporaryDirectory(prefix="escrituracao-smoke-") as directory:
        root = Path(directory)
        database = root / "private-data" / "synthetic.sqlite3"
        old_token = None
        for iteration in range(2):
            # Pick a fresh local port: closed TCP sessions may remain in TIME_WAIT.
            with socket.socket() as reserve:
                reserve.bind(("127.0.0.1", 0))
                port = reserve.getsockname()[1]
            process = subprocess.Popen(
                [*command, "--database", str(database), "--port", str(port)],
                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
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
                match = re.search(rb'<meta name="local-token" content="([^"]+)"', html)
                assert match and b"__LOCAL_TOKEN__" not in html, "Missing injected session token"
                token = match.group(1).decode("ascii")
                for asset in ("/app.js", "/style.css", "/assets/symbol.svg", "/assets/icon.svg", "/favicon.ico",
                              *(f"/assets/icon-{size}.png" for size in (16, 24, 32, 48, 64, 128, 256, 512))):
                    code, content = request(port, asset)
                    assert code == 200 and content, asset
                assert request(port, "/api/companies")[0] == 403
                assert request(port, "/api/companies", token=token, data={}, origin="https://example.invalid")[0] == 403
                if iteration == 0:
                    code, body = request(port, "/api/companies", token=token, data={
                        "name": "Empresa ficticia de empacotamento", "prosoft_company_code": "SYNTHETIC", "prosoft_plan_code": "TEST",
                    })
                    assert code == 201, body
                else:
                    assert token != old_token, "Token must rotate after restart"
                    assert request(port, "/api/companies", token=old_token)[0] == 403
                code, body = request(port, "/api/companies", token=token)
                assert code == 200 and len(json.loads(body)["data"]) == 1, body
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
        print("PASS: static HTTP, token/origin protection, synthetic POST, external SQLite, graceful stop, restart/persistence")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path)
    options = parser.parse_args()
    command = [str(options.executable.resolve())] if options.executable else [sys.executable, str(Path(__file__).with_name("launcher.py").resolve())]
    run(command)
