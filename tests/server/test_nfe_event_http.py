"""Event intake/review authorization, scoped synthetic originals only."""
import base64
import unittest
from fastapi.testclient import TestClient
from server import test_company_profiles_http as fixtures
from test_nfe_events import event_xml


class EventHTTPTests(unittest.TestCase):
    setUp=fixtures.RegistrationHTTPTests.setUp
    post=fixtures.RegistrationHTTPTests.post

    def source(self):
        company=self.post('/api/companies',{'name':'Eventos sintéticos'})['id']
        source=self.post('/api/source-receive',{'company_id':company,'request_key':'event','inputs':[{'filename':'evento.xml','content_base64':base64.b64encode(event_xml()).decode()}]})['items'][0]
        return company,source

    def test_event_intake_preview_and_annotation_need_no_cycle(self):
        company,source=self.source();scope={'company_id':company,'input_id':source['input_id']}
        preview=self.client.get('/api/nfe-event-preview',params=scope).json()['data']
        self.assertFalse(preview['snapshot']['event']['authorization_verified'])
        self.assertEqual(self.client.get('/api/nfe-events',params={'company_id':company}).json()['data']['total'],1)
        data={**scope,'snapshot_hash':preview['snapshot_hash'],'decision':'pendente','reason':'Teste','review_reference':'Referência sintética','request_key':'review','confirmed':True}
        first=self.post('/api/nfe-event-review',data)
        self.assertTrue(self.post('/api/nfe-event-review',data)['duplicate'])
        history=self.client.get('/api/nfe-event-history',params=scope).json()['data'];self.assertEqual(history[0]['snapshot_hash'],first['snapshot_hash'])
        self.assertEqual(self.client.get('/api/work-cycles',params={'company_id':company}).json()['data'],[])

    def test_scope_csrf_and_review_permission(self):
        company,source=self.source();other=self.post('/api/companies',{'name':'Outra sintética'})['id']
        role=self.post('/api/v1/roles',{'name':'Leitor eventos','permissions':['workspace.read','workspace.write']})
        self.post('/api/v1/users',{'name':'Leitor eventos','email':'event@example.test','password':self.password,'role':role['id'],'companies':[str(company)],'active':True})
        client=TestClient(self.app,base_url='http://127.0.0.1:8765');self.addCleanup(client.close)
        login=client.post('/api/v1/auth/login',json={'email':'event@example.test','password':self.password},headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':login['csrf']};scope={'company_id':company,'input_id':source['input_id']}
        preview=client.get('/api/nfe-event-preview',params=scope).json()['data']
        request={**scope,'snapshot_hash':preview['snapshot_hash'],'decision':'pendente','reason':'Teste','review_reference':'Teste','request_key':'review','confirmed':True}
        self.assertEqual(client.post('/api/nfe-event-review',json=request,headers=headers).status_code,403)
        self.assertEqual(client.get('/api/nfe-event-preview',params={**scope,'company_id':other}).status_code,403)
        self.assertEqual(self.client.post('/api/nfe-event-review',json=request,headers={'Origin':'http://127.0.0.1:8765'}).status_code,403)


if __name__=='__main__':unittest.main()
