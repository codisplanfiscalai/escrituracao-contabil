"""Preparation and observed XML routes, synthetic inputs only."""
import base64
import unittest
from fastapi.testclient import TestClient
from server import test_company_profiles_http as fixtures
from test_persistence import fake_accounts,BUYER
from test_document_preparation import item_xml


class PreparationHTTPTests(unittest.TestCase):
    setUp=fixtures.RegistrationHTTPTests.setUp
    post=fixtures.RegistrationHTTPTests.post

    def setup_data(self):
        company=self.post('/api/companies',{'name':'Preparação sintética','cnpj':BUYER})['id']
        plan=self.post('/api/plans',{'company_id':company,'label':'Plano sintético','accounts':fake_accounts()})['id']
        cycle=self.post('/api/work-cycles',{'company_id':company,'plan_id':plan,'reference_competence':'2026-08','competence':'2026-09','reason':'Teste'})['id']
        accounts={r['code']:r['id'] for r in self.client.get('/api/accounts',params={'company_id':company,'plan_id':plan}).json()['data']}
        policy=self.post('/api/work-policies',{'company_id':company,'plan_id':plan,'operation':'entrada','reference_competence':'2026-08','label':'Política sintética',
            'debit_account_id':accounts['1.1.1'],'credit_account_id':accounts['2.1'],'reason':'Teste','approved':True})
        source=self.post('/api/source-receive',{'company_id':company,'request_key':'source','inputs':[{'filename':'synthetic.xml','content_base64':base64.b64encode(item_xml()).decode()}]})['items'][0]
        organized=self.post('/api/source-organize',{'company_id':company,'cycle_id':cycle,'input_id':source['input_id'],'snapshot_hash':source['snapshot_hash'],'reason':'Teste'})
        return {'company_id':company,'cycle_id':cycle},[{'document_id':organized['evidence']['document_ids'][0],'observation_id':None}],{'operation':'entrada','policy_id':policy['id'],'posting_date':'2026-09-20','item_mode':'propor_itens_xml','total_source':'vProd','copy_bases':['icms_base']}

    def test_confirmed_preparation_and_readonly_observation(self):
        scope,docs,config=self.setup_data()
        preview=self.post('/api/document-preparation-preview',{**scope,'documents':docs,'config':config})
        item=preview['snapshot']['items'][0]
        observed=self.client.get('/api/document-item-values',params={'company_id':scope['company_id'],'document_id':docs[0]['document_id'],'observation_id':item['observation_id']}).json()['data']
        self.assertEqual(observed['snapshot']['values']['items'][0]['fields']['prod/vProd']['raw'],'60.00')
        request={**scope,'documents':docs,'config':config,'snapshot_hash':preview['snapshot_hash'],'request_key':'apply','reason':'Teste','review_reference':'Conferência sintética'}
        self.assertEqual(self.client.post('/api/document-preparation-apply',json=request,headers=self.headers).status_code,400)
        row=self.post('/api/document-preparation-apply',{**request,'confirmed':True})
        self.assertEqual(row['operations'][0]['state'],'rascunho')
        self.assertTrue(self.post('/api/document-preparation-apply',{**request,'confirmed':True})['duplicate'])
        self.assertEqual(len(self.client.get('/api/document-preparations',params=scope).json()['data']),1)

    def test_reader_cannot_prepare_and_company_scope_is_enforced(self):
        scope,docs,config=self.setup_data();other=self.post('/api/companies',{'name':'Outra sintética'})['id']
        role=self.post('/api/v1/roles',{'name':'Leitor sintético','permissions':['workspace.read']})
        self.post('/api/v1/users',{'name':'Leitor sintético','email':'prepare@example.test','password':self.password,'role':role['id'],'companies':[str(scope['company_id'])],'active':True})
        client=TestClient(self.app,base_url='http://127.0.0.1:8765');self.addCleanup(client.close)
        login=client.post('/api/v1/auth/login',json={'email':'prepare@example.test','password':self.password},headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':login['csrf']}
        self.assertEqual(client.get('/api/document-preparations',params=scope).status_code,200)
        self.assertEqual(client.get('/api/document-preparations',params={**scope,'company_id':other}).status_code,403)
        self.assertEqual(client.post('/api/document-preparation-preview',json={**scope,'documents':docs,'config':config},headers=headers).status_code,403)
        self.assertEqual(self.client.post('/api/document-preparation-preview',json={**scope,'documents':docs,'config':config},headers={'Origin':'http://127.0.0.1:8765'}).status_code,403)


if __name__=='__main__':unittest.main()
