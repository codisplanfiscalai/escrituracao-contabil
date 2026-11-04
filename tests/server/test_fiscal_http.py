import unittest
from server import test_identity_portal as helpers


class FiscalHTTPTests(unittest.TestCase):
    setUp=helpers.PortalTests.setUp
    tearDown=helpers.PortalTests.tearDown
    post=helpers.PortalTests.post
    create_company=helpers.PortalTests.create_company
    other_client=helpers.PortalTests.other_client

    def test_scoped_roles_manual_entry_and_operator_tabs(self):
        company=self.create_company()
        r=self.client.post('/api/periods',json={'company_id':company,'reference_competence':'2026-08','processing_competence':'2026-09'},headers=self.headers)
        period=r.json()['data']['id']
        r=self.post('users',{'name':'Operador fictício','email':'operator@example.test','password':self.password,'role':'accountant','companies':[company]})
        self.assertEqual(r.status_code,200,r.text)
        operator,headers=self.other_client('operator@example.test');self.addCleanup(operator.close)
        fields={'model':'55','number':'1','series':'1','operation':'entrada','issued_date':'2026-08-01','entry_date':'2026-09-01','posting_date':'2026-09-01','total':'100.00'}
        body={'company_id':company,'period_id':period,'data':fields,'reason':'Somente teste','request_key':'HTTP-FICTICIO'}
        response=operator.post('/api/fiscal-entries',json=body,headers=headers)
        self.assertEqual(response.status_code,200,response.text);revision=response.json()['data']
        review={'company_id':company,'entry_id':revision['entry_id'],'snapshot_hash':revision['snapshot_hash'],'reason':'Conferência','acknowledged':True}
        self.assertEqual(operator.post('/api/fiscal-review',json=review,headers=headers).status_code,403)
        self.assertEqual(self.client.post('/api/fiscal-review',json=review,headers=self.headers).status_code,200)
        self.assertEqual(operator.post('/api/fiscal-entries',json=body,headers={'Origin':headers['Origin']}).status_code,403)
        other=self.create_company('Outra fictícia')
        self.assertEqual(operator.get('/api/fiscal-entries',params={'company_id':other}).status_code,403)
        workspace={'company_id':company,'period_id':period,'title':'Guia fictícia','data':fields,'request_key':'tab-http'}
        r=operator.post('/api/fiscal-workspaces',json=workspace,headers=headers)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/fiscal-workspaces',params={'company_id':company,'period_id':period}).json()['data'],[])
        self.assertEqual(len(operator.get('/api/fiscal-workspaces',params={'company_id':company,'period_id':period}).json()['data']),1)

    def test_client_cannot_write_fiscal_register_or_participants(self):
        company=self.create_company()
        self.post('users',{'name':'Cliente fictício','email':'client@example.test','password':self.password,'role':'client','companies':[company]})
        client,headers=self.other_client();self.addCleanup(client.close)
        for route in ('fiscal-entries','fiscal-workspaces','participants','fiscal-review','fiscal-period','participant-review'):
            self.assertEqual(client.post('/api/'+route,json={'company_id':company},headers=headers).status_code,403,route)
            self.assertEqual(client.post('/api/v1/client/'+route,json={'company_id':company},headers=headers).status_code,404,route)
