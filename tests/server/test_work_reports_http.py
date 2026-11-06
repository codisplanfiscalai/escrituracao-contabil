"""Reports retain existing authenticated portal company authorization."""
import unittest
from server import test_identity_portal as helpers
from test_persistence import fake_accounts


class ReportsPortalTests(unittest.TestCase):
    setUp = helpers.PortalTests.setUp
    tearDown = helpers.PortalTests.tearDown
    post = helpers.PortalTests.post
    create_company = helpers.PortalTests.create_company
    other_client = helpers.PortalTests.other_client

    def test_authenticated_company_scoped_reports_and_no_write_permission(self):
        company = self.create_company()
        def admin(route, body):
            response = self.client.post('/api/'+route, json={'company_id':company, **body}, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()['data']
        plan = admin('plans', {'label':'Plano sintético','accounts':fake_accounts()})['id']
        cycle = admin('work-cycles', {'reference_competence':'2026-08','competence':'2026-09','plan_id':plan,'reason':'Teste'})['id']
        self.post('users', {'name':'Contador sintético','email':'reports@example.test','password':self.password,'role':'accountant','companies':[company]})
        operator, headers = self.other_client('reports@example.test')
        self.addCleanup(operator.close)
        params = dict(company_id=company, cycle_id=cycle, plan_id=plan, include_zero='true', level='sintetico')
        response = operator.get('/api/accounting-report', params=params)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()['data']['rows']), 3)
        self.assertEqual(operator.post('/api/accounting-report',json=params,headers=headers).status_code,404)
        other = self.create_company('Outra sintética')
        self.assertEqual(operator.get('/api/accounting-report',params={**params,'company_id':other}).status_code,403)
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/accounting-report', params=params).status_code,401)
