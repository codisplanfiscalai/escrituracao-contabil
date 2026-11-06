"""Company scope, CSRF and exact original download for synthetic catalogues."""
import base64
import unittest
from fastapi.testclient import TestClient
from server import test_company_profiles_http as fixtures
import test_tax_catalog_import as catalogs


class CatalogImportHTTPTests(unittest.TestCase):
    setUp=fixtures.RegistrationHTTPTests.setUp
    post=fixtures.RegistrationHTTPTests.post

    def test_import_preview_apply_and_exact_download_without_period(self):
        company=self.post('/api/companies',{'name':'Catálogos sintéticos'})['id']
        raw=catalogs.json_bytes([catalogs.record()])
        receipt=self.post('/api/tax-catalog-imports',{'company_id':company,'filename':'synthetic.json','content_base64':base64.b64encode(raw).decode(),
            'metadata':catalogs.meta(),'request_key':'receive','reason':'Teste'})['import']
        params={'company_id':company,'import_id':receipt['id']}
        download=self.client.get('/api/tax-catalog-original',params=params)
        self.assertEqual(download.status_code,200);self.assertEqual(download.content,raw)
        self.assertIn(f'cadastro-{receipt["id"]}.json',download.headers['content-disposition'])
        self.assertEqual(self.client.get('/api/work-cycles',params={'company_id':company}).json()['data'],[])
        payload={**params,'codes':['1102'],'application_from':'2026-09-01'}
        self.assertEqual(self.client.post('/api/tax-catalog-preview',json=payload,headers={'Origin':'http://127.0.0.1:8765'}).status_code,403)
        preview=self.post('/api/tax-catalog-preview',payload)
        result=self.post('/api/tax-catalog-apply',{**payload,'snapshot_hash':preview['snapshot_hash'],'request_key':'apply','reason':'Teste','review_reference':'Revisão sintética','confirmed':True})
        self.assertEqual(result['snapshot']['versions'][0]['code'],'1102')
        config=self.client.get('/api/tax-config',params={'company_id':company}).json()['data']
        self.assertEqual(config['catalog'][0]['data']['import_origin']['import_id'],receipt['id'])
        self.assertFalse(config['legal_defaults_loaded'])

    def test_imports_and_originals_enforce_company_scope_and_review_permission(self):
        first=self.post('/api/companies',{'name':'Primeira sintética'})['id'];second=self.post('/api/companies',{'name':'Segunda sintética'})['id']
        receipt=self.post('/api/tax-catalog-imports',{'company_id':first,'filename':'synthetic.json','content_base64':base64.b64encode(catalogs.json_bytes([catalogs.record()])).decode(),
            'metadata':catalogs.meta(),'request_key':'receive','reason':'Teste'})['import']
        params={'company_id':first,'import_id':receipt['id'],'codes':['1102'],'application_from':'2026-09-01'}
        preview=self.post('/api/tax-catalog-preview',params)
        application=self.post('/api/tax-catalog-apply',{**params,'snapshot_hash':preview['snapshot_hash'],'request_key':'apply','reason':'Teste','review_reference':'Revisão','confirmed':True})
        role=self.post('/api/v1/roles',{'name':'Leitor de catálogos','permissions':['workspace.read']})
        self.post('/api/v1/users',{'name':'Leitor sintético','email':'catalogs@example.test','password':self.password,'role':role['id'],'companies':[str(first)],'active':True})
        reader=TestClient(self.app,base_url='http://127.0.0.1:8765');self.addCleanup(reader.close)
        login=reader.post('/api/v1/auth/login',json={'email':'catalogs@example.test','password':self.password},headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':login['csrf']}
        for route in ('tax-catalog-import','tax-catalog-original','tax-catalog-applications'):
            self.assertEqual(reader.get('/api/'+route,params={'company_id':first,'import_id':receipt['id']}).status_code,200)
            self.assertEqual(reader.get('/api/'+route,params={'company_id':second,'import_id':receipt['id']}).status_code,403)
        self.assertEqual(reader.post('/api/tax-catalog-imports',json={'company_id':first},headers=headers).status_code,403)
        self.assertEqual(reader.post('/api/tax-catalog-preview',json={'company_id':first,'import_id':receipt['id'],'codes':['1102'],'application_from':'2026-09-01'},headers=headers).status_code,403)
        self.assertEqual(reader.get('/api/tax-catalog-application',params={'company_id':first,'application_id':application['id']}).status_code,200)
        self.assertEqual(reader.get('/api/tax-catalog-application',params={'company_id':second,'application_id':application['id']}).status_code,403)
        self.assertEqual(self.client.get('/api/tax-catalog-original',params={'company_id':second,'import_id':receipt['id']}).status_code,400)

    def test_invalid_encoding_rejects_without_receipt(self):
        company=self.post('/api/companies',{'name':'Base64 sintético'})['id']
        response=self.client.post('/api/tax-catalog-imports',json={'company_id':company,'filename':'x.json','content_base64':'??','metadata':catalogs.meta(),'request_key':'bad','reason':'Teste'},headers=self.headers)
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.get('/api/tax-catalog-imports',params={'company_id':company}).json()['data'],[])


if __name__=='__main__':unittest.main()
