"""Financial writers retired; title creation belongs to reviewed operations."""
import unittest
from server import test_identity_portal as helpers

class FinancePortalTests(unittest.TestCase):
    setUp=helpers.PortalTests.setUp
    tearDown=helpers.PortalTests.tearDown
    post=helpers.PortalTests.post
    create_company=helpers.PortalTests.create_company
    other_client=helpers.PortalTests.other_client
    def test_old_financial_writers_retired_and_cycle_scoped(self):
        company=self.create_company();other=self.create_company('Outra sintética')
        self.post('users',{'name':'Operador sintético','email':'finance@example.test','password':self.password,'role':'accountant','companies':[company]})
        operator,headers=self.other_client('finance@example.test');self.addCleanup(operator.close)
        for route in ['finance-titles','finance-settlements']:
            self.assertEqual(operator.post('/api/'+route,json={'company_id':company},headers=headers).status_code,410)
            self.assertEqual(operator.post('/api/'+route,json={'company_id':company}).status_code,403)
        r=self.client.post('/api/work-cycles',json={'company_id':company,'competence':'2026-09','reference_competence':'2026-08','reason':'Teste'},headers=self.headers)
        cycle=r.json()['data']['id']
        self.assertEqual(operator.get('/api/work-finance',params={'company_id':company,'cycle_id':cycle}).json()['data'],[])
        self.assertEqual(operator.get('/api/work-finance',params={'company_id':other,'cycle_id':cycle}).status_code,403)
        self.assertEqual(operator.post('/api/work-policies',json={'company_id':company},headers=headers).status_code,403)
