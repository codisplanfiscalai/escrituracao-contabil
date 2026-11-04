"""Synthetic loopback HTTP coverage; no real fiscal or company information."""
import base64
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from src.local_app import LocalServer, MAX_BODY


class LocalApplicationTests(unittest.TestCase):
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
        for path in ("/app.js", "/style.css"):
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

    def test_end_to_end_synthetic_flow_and_statuses(self):
        company = self.company()
        cid = company["id"]
        period = self.api("periods", {"company_id": cid, "reference_competence": "2026-04",
                                     "processing_competence": "2026-05"})
        self.assertNotEqual(period["reference_competence"], period["processing_competence"])
        plan = self.api("plans", {"company_id": cid, "label": "Plano sintético", "accounts": [
            {"code": "1", "description": "Ativo", "kind": "sintetica", "nature": "devedora"},
            {"code": "1.1", "description": "Caixa", "parent_code": "1", "kind": "analitica", "nature": "devedora"}]})
        mapping = self.api("mappings", {"company_id": cid, "plan_id": plan["id"],
                                       "source_account": "caixa-local", "target_code": "1.1", "valid_from": "2026-05"})
        self.assertEqual(mapping["state"], "rascunho")
        upload = {"company_id": cid, "period_id": period["id"], "filename": "synthetic.txt", "kind": "SPED",
                  "content_base64": base64.b64encode(b"|0000|TESTE|\n").decode()}
        self.assertEqual(self.api("files", upload)["status"], "pendente")
        self.assertTrue(self.api("files", upload)["duplicate"])
        upload.update(filename="synthetic.xml", kind="XML", content_base64=base64.b64encode(b"<invalid/>").decode())
        self.assertEqual(self.api("files", upload)["status"], "rejeitado")
        for route in ("periods", "plans", "accounts", "mappings", "files", "documents", "audit"):
            query = f"{route}?company_id={cid}" + (f'&plan_id={plan["id"]}' if route == "accounts" else "")
            self.assertIsInstance(self.api(query), list)
        self.assertEqual(len(self.api(f"files?company_id={cid}")), 2)
        self.assertEqual(self.api(f"documents?company_id={cid}&period_id={period['id']}"), [])
        self.assertGreaterEqual(len(self.api(f"audit?company_id={cid}")), 7)

    def test_bad_base64_filename_and_company_isolation(self):
        first, second = self.company(), self.company()
        period = self.api("periods", {"company_id": first["id"], "reference_competence": "2026-04",
                                     "processing_competence": "2026-05"})
        upload = {"company_id": first["id"], "period_id": period["id"], "filename": "synthetic.txt",
                  "kind": "SPED", "content_base64": "!bad"}
        self.assertEqual(self.request("/api/files", "POST", upload)[0], 400)
        upload.update(content_base64="dGVzdA==", filename="../secret")
        self.assertEqual(self.request("/api/files", "POST", upload)[0], 400)
        upload.update(filename="synthetic.txt", company_id=second["id"])
        self.assertEqual(self.request("/api/files", "POST", upload)[0], 400)
        self.assertEqual(self.request(f'/api/documents?company_id={second["id"]}&period_id={period["id"]}')[0], 400)

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
