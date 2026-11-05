"""Persistent work tabs are actor scoped; clients cannot use fiscal writers."""
import unittest
from server import test_identity_portal as helpers
class FiscalHTTPTests(unittest.TestCase):
    setUp=helpers.PortalTests.setUp
    tearDown=helpers.PortalTests.tearDown
    post=helpers.PortalTests.post
    create_company=helpers.PortalTests.create_company
    other_client=helpers.PortalTests.other_client
    def test_incomplete_tab_actor_scope_and_retired_fiscal_writer(self):
        company=self.create_company()
        cycle=self.client.post('/api/work-cycles',json={'company_id':company,'competence':'2026-09','reference_competence':'2026-08','reason':'Teste'},headers=self.headers).json()['data']['id']
        self.post('users',{'name':'Operador sintético','email':'operator@example.test','password':self.password,'role':'accountant','companies':[company]})
        operator,headers=self.other_client('operator@example.test');self.addCleanup(operator.close)
        scope={'company_id':company,'cycle_id':cycle}
        response=operator.post('/api/work-tabs',json={**scope,'title':'Ficha incompleta','data':{'payload':{'fiscal':{'number':'Sintético'}}}},headers=headers)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.client.get('/api/work-tabs',params=scope).json()['data'],[])
        self.assertEqual(len(operator.get('/api/work-tabs',params=scope).json()['data']),1)
        for route in ['fiscal-entries','fiscal-workspaces']:
            self.assertEqual(operator.post('/api/'+route,json={'company_id':company},headers=headers).status_code,410)
    def test_client_cannot_write_fiscal_register_or_participants(self):
        company=self.create_company()
        self.post('users',{'name':'Cliente sintético','email':'client@example.test','password':self.password,'role':'client','companies':[company]})
        client,headers=self.other_client();self.addCleanup(client.close)
        for route in ['work-operations','work-review','work-post','work-tabs','source-organize','work-policies']:
            self.assertEqual(client.post('/api/'+route,json={'company_id':company},headers=headers).status_code,403,route)
            self.assertEqual(client.post('/api/v1/client/'+route,json={'company_id':company},headers=headers).status_code,404,route)
