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

    def test_batch_loopback_results_original_download_and_catalog_routes(self):
        from test_batch_import import zip_bytes
        from test_persistence import fake_xml
        company=self.company()['id']
        period=self.api('periods',{'company_id':company,'reference_competence':'2026-09','processing_competence':'2026-09'})['id']
        packed=zip_bytes([('ficticio.xml',fake_xml())])
        batch=self.api('import-batches',{'company_id':company,'period_id':period,'request_key':'local-ficticio','inputs':[{'filename':'pacote.zip','content_base64':base64.b64encode(packed).decode()}]})
        self.assertEqual(batch['status'],'concluido')
        self.assertEqual(len(self.api('import-batches?company_id='+str(company))),1)
        route=f"/api/import-original?company_id={company}&item_id={batch['items'][0]['id']}"
        status,headers,content=self.request(route)
        self.assertEqual(status,200);self.assertEqual(content,packed)
        self.assertIn('attachment;',headers['Content-Disposition'])
        self.assertEqual(self.request(route,headers={'X-Local-Token':None})[0],403)
        self.assertEqual(self.api('products?company_id='+str(company)),[])
        self.assertTrue(self.api('participants?company_id='+str(company)))

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

    def test_browser_text_ids_keep_equivalent_xml_as_two_sources_without_conflict(self):
        from test_persistence import fake_xml, ISSUER
        from xml.etree import ElementTree as ET
        company=self.api("companies",{"name":"Empresa fictícia HTTP","prosoft_company_code":"TEST","prosoft_plan_code":"TEST","cnpj":ISSUER})
        cid=str(company["id"])
        period=self.api("periods",{"company_id":cid,"reference_competence":"2026-08","processing_competence":"2026-09"})
        original=fake_xml()
        for index,content in enumerate((original,ET.tostring(ET.fromstring(original)))):
            imported=self.api("files",{"company_id":cid,"period_id":str(period["id"]),"filename":f"ficticio-{index}.xml","kind":"XML","content_base64":base64.b64encode(content).decode()})
            self.assertEqual(imported["status"],"validado")
        docs=self.api(f"documents?company_id={cid}")
        self.assertEqual(len(docs),1)
        self.assertEqual([s["conflict"] for s in docs[0]["sources"]],[0,0])

    def test_logical_removal_requires_current_preview_reason_confirmation_and_company(self):
        company,other=self.company(),self.company()
        cid=company["id"]
        period=self.api("periods",{"company_id":cid,"reference_competence":"2026-08","processing_competence":"2026-09"})
        imported=self.api("files",{"company_id":cid,"period_id":period["id"],"filename":"ficticio.txt","kind":"SPED","content_base64":base64.b64encode(b"|0000|TESTE|\n").decode()})
        preview=self.api(f"file-preview?company_id={cid}&file_id={imported['id']}")
        data={"company_id":cid,"file_id":imported["id"],"reason":"Remoção fictícia","confirmed":True,"preview_token":preview["preview_token"]}
        for change in ({"preview_token":""},{"preview_token":"stale"},{"reason":""},{"confirmed":False},{"confirmed":"true"},{"company_id":other["id"]}):
            self.assertEqual(self.request("/api/file-removal","POST",{**data,**change})[0],400)
        self.assertEqual(self.request(f"/api/file-preview?company_id={other['id']}&file_id={imported['id']}")[0],400)
        self.assertEqual(self.api(f"files?company_id={cid}")[0]["status"],"pendente")
        self.api("file-removal",data)
        self.assertEqual(self.api(f"files?company_id={cid}")[0]["status"],"excluido")
        self.assertEqual(self.api(f"audit?company_id={cid}")[0]["action"],"arquivo_removido_logicamente")
        self.assertEqual(self.request("/api/file-removal","POST",data)[0],400)

    def test_partial_reconciliation_and_saved_source_analysis_over_http(self):
        from test_persistence import fake_xml, ISSUER
        from test_reconciliation import fake_sped
        from src.reconciliation import SPED_PROFILE
        company=self.api("companies",{"name":"Empresa fictícia da conciliação","prosoft_company_code":"TEST","prosoft_plan_code":"TEST","cnpj":ISSUER})
        cid=company["id"]
        period=self.api("periods",{"company_id":cid,"reference_competence":"2026-08","processing_competence":"2026-09"})
        for kind,content in (("XML",fake_xml()),("SPED",fake_sped())):
            imported=self.api("files",{"company_id":str(cid),"period_id":str(period["id"]),"filename":"ficticio."+kind.lower(),"kind":kind,"content_base64":base64.b64encode(content).decode()})
        self.assertEqual(self.api(f"reconciliation?company_id={cid}")[0]["state"],"somente_xml")
        analysis={"company_id":cid,"file_id":str(imported["id"]),"profile":SPED_PROFILE}
        self.assertFalse(self.api("file-analysis",analysis)["duplicate"])
        self.assertTrue(self.api("file-analysis",analysis)["duplicate"])
        reconciled=self.api(f"reconciliation?company_id={cid}&period_id={period['id']}")
        self.assertEqual(len(reconciled),1)
        self.assertEqual(reconciled[0]["state"],"coincidente_no_recorte")
        self.assertEqual(len(reconciled[0]["invoices"][0]["installments"]),2)
        self.assertFalse(reconciled[0]["ready_for_export"])
        rows=self.api(f"observations?company_id={cid}")
        self.assertTrue(any(row["locator"]=="linha:3" for row in rows))
        other=self.company()["id"]
        self.assertEqual(self.api(f"reconciliation?company_id={other}"),[])
        self.assertEqual(self.request("/api/file-analysis","POST",{**analysis,"company_id":other})[0],400)
        self.assertEqual(self.request(f"/api/observations?company_id={other}&period_id={period['id']}")[0],400)
        self.assertEqual(self.request("/api/file-analysis","POST",{**analysis,"profile":"inventado"})[0],400)

    def test_explicit_partial_sped_import_and_pending_records_over_http(self):
        from test_persistence import ISSUER
        from test_reconciliation import fake_sped
        from src.reconciliation import SPED_PROFILE
        company=self.api("companies",{"name":"Empresa fictícia do perfil","prosoft_company_code":"TEST","prosoft_plan_code":"TEST","cnpj":ISSUER})
        cid=company["id"]
        period=self.api("periods",{"company_id":cid,"reference_competence":"2026-08","processing_competence":"2026-09"})
        imported=self.api("files",{"company_id":cid,"period_id":period["id"],"filename":"ficticio.txt","kind":"SPED","sped_profile":SPED_PROFILE,"content_base64":base64.b64encode(fake_sped(key="")).decode()})
        self.assertEqual(imported["status"],"pendente")
        self.assertTrue(imported["analyses"])
        self.assertEqual(self.api(f"reconciliation?company_id={cid}"),[])
        rows=self.api(f"observations?company_id={cid}")
        self.assertTrue(any(row["issues"] for row in rows))


    def accounting_fixture(self):
        from test_persistence import fake_xml, fake_accounts, ISSUER
        cid=self.api('companies',{'name':'Contábil fictícia','prosoft_company_code':'T','prosoft_plan_code':'T','cnpj':ISSUER})['id']
        period=self.api('periods',{'company_id':cid,'reference_competence':'2026-08','processing_competence':'2026-09'})['id']
        plan=self.api('plans',{'company_id':cid,'label':'Plano fictício','accounts':fake_accounts()})['id']
        mappings=[self.api('mappings',{'company_id':cid,'plan_id':plan,'source_account':str(index),'target_code':code,'valid_from':'2026-09','state':'aprovado','reason':'Fictício'})['id'] for index,code in enumerate(('1.1.1','2.1'))]
        self.api('files',{'company_id':cid,'period_id':period,'filename':'ficticio.xml','kind':'XML','content_base64':base64.b64encode(fake_xml()).decode()})
        doc=self.api(f'reconciliation?company_id={cid}')[0]
        review={'company_id':str(cid),'period_id':str(period),'document_id':str(doc['document_id']),'chosen_observation_id':str(doc['sources'][0]['id']),'expected_fingerprint':doc['source_fingerprint'],'reason':'Conferência fictícia'}
        entries=[{'document_id':doc['document_id'],'observation_id':doc['sources'][0]['id'],'group':'doc','date':'2026-09-15','side':side,'amount':'100.30','mapping_id':mapping,'memo':'Histórico fictício'} for side,mapping in zip(('D','C'),mappings)]
        batch={'company_id':str(cid),'period_id':str(period),'plan_id':str(plan),'request_key':'ficticio-1','entries':entries,'reason':'Prévia fictícia'}
        return cid,review,batch

    def test_document_review_accounting_close_and_snapshot_over_http(self):
        cid,review,batch_data=self.accounting_fixture()
        self.assertTrue(self.api('document-reviews',review)['readiness_for_accounting'])
        history=self.api(f'document-reviews?company_id={cid}&document_id={review["document_id"]}')
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['actor'],'operador-local')
        batch=self.api('accounting-batches',batch_data)
        self.assertEqual(self.api('accounting-batches',batch_data)['id'],batch['id'])
        transition={'company_id':str(cid),'batch_id':str(batch['id']),'snapshot_hash':batch['snapshot_hash'],'reason':'Conferência fictícia'}
        self.assertEqual(self.request('/api/accounting-close','POST',transition)[0],400)
        self.assertEqual(self.api('accounting-review',transition)['status'],'revisado')
        closed=self.api('accounting-close',transition)
        self.assertEqual(closed['status'],'fechado')
        self.assertEqual(closed['snapshot'],batch['snapshot'])
        rows=self.api(f'accounting-batches?company_id={cid}')
        self.assertEqual(len(rows),1)
        self.assertFalse(rows[0]['ready_for_export'])
        self.assertEqual(rows[0]['current_blockers'],[])
        self.stop_server();self.start_server()
        self.assertEqual(self.api(f'accounting-batches?company_id={cid}')[0]['snapshot_hash'],batch['snapshot_hash'])

    def test_accounting_routes_require_tokens_origin_fingerprint_and_company(self):
        cid,review,batch_data=self.accounting_fixture()
        for update in ({'expected_fingerprint':'stale'},{'expected_fingerprint':''},{'chosen_observation_id':True},{'reason':''}):
            self.assertEqual(self.request('/api/document-reviews','POST',{**review,**update})[0],400)
        self.api('document-reviews',review)
        batch=self.api('accounting-batches',batch_data)
        transition={'company_id':cid,'batch_id':batch['id'],'snapshot_hash':batch['snapshot_hash'],'reason':'Teste fictício'}
        for route,data in (('document-reviews',review),('accounting-batches',batch_data),('accounting-review',transition),('accounting-close',transition)):
            for headers in ({'X-Local-Token':None},{'Origin':'http://other.invalid'}):
                self.assertEqual(self.request('/api/'+route,'POST',data,headers=headers)[0],403)
        other=self.company()['id']
        for route,data in (('document-reviews',review),('accounting-batches',batch_data),('accounting-review',transition),('accounting-close',transition)):
            self.assertEqual(self.request('/api/'+route,'POST',{**data,'company_id':other})[0],400)
        self.assertEqual(self.api(f'accounting-batches?company_id={other}'),[])
        self.assertEqual(self.api(f'document-reviews?company_id={other}'),[])
        self.assertEqual(self.request('/api/accounting-review','POST',{**transition,'snapshot_hash':''})[0],400)

    def test_closed_accounting_evidence_download_and_isolation(self):
        cid, review, batch_data = self.accounting_fixture()
        self.api('document-reviews', review)
        batch = self.api('accounting-batches', batch_data)
        transition = {'company_id':cid, 'batch_id':batch['id'],
                      'snapshot_hash':batch['snapshot_hash'], 'reason':'Evidência fictícia'}
        self.assertEqual(self.request('/api/accounting-evidence','POST',transition)[0],400)
        self.api('accounting-review', transition)
        self.assertEqual(self.request('/api/accounting-evidence-file', 'POST', transition)[0],404)
        self.assertEqual(self.api(f'accounting-batches?company_id={cid}')[0]['status'],'revisado')
        self.api('accounting-close', transition)
        export = self.api('accounting-evidence', transition)
        self.assertEqual(export['profile'], 'accounting-evidence-v1')
        self.assertEqual(self.api('accounting-evidence',transition)['id'], export['id'])
        self.assertEqual(len(self.api(f'accounting-evidence?company_id={cid}')),1)
        for artifact in export['artifacts']:
            url = f"/api/accounting-evidence-file?company_id={cid}&export_id={export['id']}&name={artifact['name']}"
            status, headers, content = self.request(url)
            self.assertEqual(status,200)
            self.assertEqual(headers['Content-Type'], artifact['media_type'])
            self.assertIn('attachment;', headers['Content-Disposition'])
            self.assertEqual(hashlib.sha256(content).hexdigest(), artifact['sha256'])
            self.assertEqual(len(content), artifact['size'])
            self.assertEqual(self.request(url,headers={'X-Local-Token':None})[0],403)
        other = self.company()['id']
        self.assertEqual(self.api(f'accounting-evidence?company_id={other}'),[])
        for owner, name in ((other,'evidence.json'), (cid,'../persistence.py'), (cid,'evidence.json%0d%0aInjected')):
            self.assertEqual(self.request(f"/api/accounting-evidence-file?company_id={owner}&export_id={export['id']}&name={name}")[0],400)
        self.assertEqual(self.request('/api/accounting-evidence','POST',{**transition,'company_id':other})[0],400)
        self.stop_server(); self.start_server()
        self.assertEqual(self.api(f'accounting-evidence?company_id={cid}')[0]['manifest_sha256'],export['manifest_sha256'])

    def test_billing_association_preview_confirmation_and_document_review(self):
        from test_persistence import fake_xml, edit_xml
        cid, review, batch_data = self.accounting_fixture()
        self.api('document-reviews',review)
        content=edit_xml(fake_xml(),'cobr/fat/nFat','OUTRO-TITULO-FICTICIO')
        file=self.api('files',{'company_id':cid,'period_id':batch_data['period_id'],
                    'filename':'ficticio-associacao.xml','kind':'XML','content_base64':base64.b64encode(content).decode()})
        doc=self.api(f'reconciliation?company_id={cid}')[0]
        self.assertFalse(doc['readiness_for_accounting'])
        invoice=doc['invoices'][0]
        observations=[s for s in doc['sources'] if s['file_id']==file['id'] and s['entity_kind']=='parcela']
        proposal={'company_id':cid,'document_id':doc['document_id'],'period_id':doc['period_id'],
                  'file_id':file['id'],'invoice_id':invoice['id'],
                  'installment_links':[{'observation_id':s['id'],'installment_id':p['id']} for s,p in zip(observations,invoice['installments'])]}
        preview=self.api('billing-association-preview',proposal)
        save={**proposal,'expected_fingerprint':preview['expected_fingerprint'],'reason':'Conferência fictícia','confirmed':True}
        for change in ({'confirmed':False},{'confirmed':'true'},{'reason':''},{'expected_fingerprint':'stale'}):
            self.assertEqual(self.request('/api/billing-associations','POST',{**save,**change})[0],400)
        other=self.company()['id']
        self.assertEqual(self.request('/api/billing-association-preview','POST',{**proposal,'company_id':other})[0],400)
        self.assertEqual(self.request('/api/billing-associations','POST',save,headers={'X-Local-Token':None})[0],403)
        self.assertTrue(self.api('billing-associations',save)['valid'])
        self.assertEqual(self.request('/api/billing-associations','POST',save)[0],400)
        self.assertEqual(self.api(f'billing-associations?company_id={other}'),[])
        self.assertEqual(len(self.api(f'billing-associations?company_id={cid}')),1)
        resolved=self.api(f'reconciliation?company_id={cid}')[0]
        self.assertFalse(resolved['review']['valid'])
        self.assertTrue(any(s.get('billing_resolution') for s in resolved['sources']))
        self.assertTrue(self.api('document-reviews',{**review,'expected_fingerprint':resolved['source_fingerprint']})['readiness_for_accounting'])
        self.assertEqual(self.api('accounting-batches',batch_data)['status'],'previa')
        self.stop_server();self.start_server()
        self.assertTrue(self.api(f'billing-associations?company_id={cid}')[0]['valid'])


if __name__ == "__main__":
    unittest.main()
