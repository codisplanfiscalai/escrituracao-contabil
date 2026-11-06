"""Synthetic loopback HTTP coverage; no real fiscal or company information."""
import base64
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from src.local_app import LocalServer, MAX_BODY


class LocalApplicationTests(unittest.TestCase):
    def test_tax_configuration_is_available_in_private_mode_without_legal_defaults(self):
        company = self.company()
        result = self.api(f"tax-config?company_id={company['id']}")
        self.assertEqual(result['rules'], [])
        self.assertEqual(result['catalog'], [])
        self.assertFalse(result['legal_defaults_loaded'])
        self.assertTrue(all(not model['spec']['rate'] for model in result['structural_models']))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "synthetic.sqlite3"
        self.start_server()

    def start_server(self):
        self.server = LocalServer(self.database, 0)
        self.port = self.server.server_port
        self.origin = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def tearDown(self):
        self.stop_server()
        self.directory.cleanup()

    def request(self, path, method="GET", data=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        request_headers = {"X-Local-Token": self.server.token, "Origin": self.origin}
        if data is not None:
            raw = json.dumps(data).encode()
            request_headers["Content-Type"] = "application/json"
        for name, value in (headers or {}).items():
            if value is None:
                request_headers.pop(name, None)
            else:
                request_headers[name] = value
        try:
            connection.request(method, path, body=raw, headers=request_headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def api(self, route, data=None):
        status, _, body = self.request("/api/" + route, "POST" if data is not None else "GET", data)
        self.assertEqual(status, 201 if data is not None else 200, body)
        return json.loads(body)["data"]

    def company(self):
        return self.api("companies", {"name": "Empresa Sintética <script>",
                                     "prosoft_company_code": "TEST-01", "prosoft_plan_code": "PL-01"})



    def test_static_allowlist_token_injection_and_headers(self):
        status, headers, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(self.server.token.encode(), body)
        self.assertNotIn(b"__LOCAL_TOKEN__", body)
        self.assertTrue(headers["Cache-Control"].startswith("no-store"))
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for path in ("/workbench.js", "/workbench_render.js", "/workbench.css", "/portal/vendor/vue.js"):
            self.assertEqual(self.request(path)[0], 200)
        for path in ("/../persistence.py", "/src/persistence.py", "/web/index.html", "/.git/config", "/api/nope"):
            self.assertEqual(self.request(path)[0], 404, path)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_host_origin_token_and_cross_site_restrictions(self):
        for headers in ({"Host": "evil.example"},
                        {"Origin": "http://evil.example"},
                        {"Origin": "null"},
                        {"X-Local-Token": "incorrect"},
                        {"X-Local-Token": None},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.request("/api/companies", headers=headers)[0], 403, headers)
        self.assertEqual(self.request("/api/companies", "POST", {}, headers={"Origin": None})[0], 403)
        self.assertEqual(self.request("/api/companies", "POST", {}, headers={"Origin": ""})[0], 403)
        status, headers, _ = self.request("/api/companies", headers={"X-Local-Token": "bad"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_identity_assets_are_local_and_allowlisted(self):
        for path, media, signature in (
            ("/assets/symbol.svg", "image/svg+xml", b"<svg"),
            ("/assets/icon.svg", "image/svg+xml", b"<svg"),
            ("/favicon.ico", "image/x-icon", b"\x00\x00\x01\x00"),
            ("/assets/icon-256.png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ):
            status, headers, content = self.request(path)
            self.assertEqual(status, 200, path)
            self.assertEqual(headers["Content-Type"], media)
            self.assertTrue(content.startswith(signature), path)
            self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        for path in ("/assets/../persistence.py", "/assets/icon-999.png", "/assets/", "/assets/manifest.json"):
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request("/favicon.ico", headers={"Origin":"https://foreign.invalid"})[0],403)

    def test_invalid_bodies_and_limits(self):
        for raw in (b"[]", b"{", b'{"value": NaN}', b"\xff"):
            self.assertEqual(self.request("/api/companies", "POST", raw=raw,
                                         headers={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("/api/companies", "POST", raw=b"{}",
                                      headers={"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("/api/companies", "POST", raw=b"",
                                      headers={"Content-Type": "application/json",
                                               "Content-Length": str(MAX_BODY + 1)})[0], 413)
        self.assertEqual(self.request("/api/periods?company_id=1&company_id=2")[0], 400)
        self.assertEqual(self.request("/api/companies?name=x", "POST", {})[0], 400)



    def test_new_session_retains_sqlite_and_rotates_token(self):
        self.company()
        old_token = self.server.token
        self.stop_server()
        self.start_server()
        self.assertNotEqual(self.server.token, old_token)
        self.assertEqual(len(self.api("companies")), 1)
        self.assertEqual(self.request("/api/companies", headers={"X-Local-Token": old_token})[0], 403)












if __name__ == "__main__":
    unittest.main()
