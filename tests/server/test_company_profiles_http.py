"""Authentication, scope and persistence for synthetic client registrations."""
import tempfile
import unittest
from fastapi.testclient import TestClient
from src.server.app import create_app


class RegistrationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app(self.temp.name, worker=False)
        self.client = TestClient(self.app, base_url='http://127.0.0.1:8765')
        self.addCleanup(self.client.close)
        identity = self.app.state.identity
        self.password = 'synthetic-registration-password'
        identity.setup({'token': identity.setup_secret, 'name':'Operador sintético', 'email':'admin@example.test', 'password':self.password}, 'local')
        response = self.client.post('/api/v1/auth/login', json={'email':'admin@example.test', 'password':self.password}, headers={'Origin':'http://127.0.0.1:8765'})
        self.headers = {'Origin':'http://127.0.0.1:8765', 'X-CSRF-Token':response.json()['data']['csrf']}

    def post(self, path, data):
        response = self.client.post(path, json=data, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['data']

    def test_admin_profiles_organization_history_and_no_period_search(self):
        company = self.post('/api/companies', {'name':'Cliente sintético'})['id']
        saved = self.post('/api/company-profile', {'company_id':company, 'data':{'general':{'contact_name':'Contato sintético'}}, 'version':0, 'reason':'Teste'})
        self.assertEqual(saved['data']['general']['contact_name'], 'Contato sintético')
        self.assertEqual(self.client.get('/api/company-profile-history', params={'company_id':company}).json()['data'][0]['version'], 1)
        office = self.post('/api/v1/organization', {'data':{'name':'Escritório sintético', 'cnpj':'', 'profile':{}}, 'version':0, 'reason':'Teste'})
        self.assertEqual(office['version'], 1)
        self.assertEqual(len(self.client.get('/api/companies').json()['data']), 1)
        self.assertEqual(self.client.get('/api/source-search', params={'company_id':company,'query':'x'}).json()['data']['total'], 0)
        self.assertEqual(self.client.get('/api/work-cycles', params={'company_id':company}).json()['data'], [])
        conflict = self.client.post('/api/company-profile', json={'company_id':company, 'data':{}, 'version':0, 'reason':'stale'}, headers=self.headers)
        self.assertEqual(conflict.status_code, 400)
        self.assertEqual(self.client.post('/api/v1/organization', json={}, headers={'Origin':'http://127.0.0.1:8765'}).status_code, 403)

    def test_custom_profile_manager_cannot_read_other_clients_or_write_global_identity(self):
        company = self.post('/api/companies', {'name':'Autorizada sintética'})['id']
        other = self.post('/api/companies', {'name':'Segregada sintética'})['id']
        role = self.post('/api/v1/roles', {'name':'Consulta cadastral sintética', 'permissions':['workspace.read','companies.manage']})
        self.post('/api/v1/users', {'name':'Consulta sintética','email':'reader@example.test','password':self.password,'role':role['id'],'companies':[str(company)],'active':True})
        reader = TestClient(self.app, base_url='http://127.0.0.1:8765')
        self.addCleanup(reader.close)
        login = reader.post('/api/v1/auth/login', json={'email':'reader@example.test','password':self.password}, headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers = {'Origin':'http://127.0.0.1:8765', 'X-CSRF-Token':login['csrf']}
        self.assertEqual(reader.get('/api/company-profile', params={'company_id':company}).status_code, 200)
        for route in ('company-profile','company-profile-history','source-search'):
            self.assertEqual(reader.get('/api/'+route, params={'company_id':other}).status_code, 403)
        self.assertEqual(reader.get('/api/v1/organization').status_code, 403)
        self.assertEqual(reader.get('/api/v1/organization-history').status_code, 403)
        self.assertEqual(reader.post('/api/company-profile', json={'company_id':company,'data':{},'version':0,'reason':'Teste'}, headers=headers).status_code, 403)
        self.assertEqual(reader.post('/api/v1/organization', json={}, headers=headers).status_code, 403)

    def test_independent_module_closure_http_contract(self):
        company = self.post('/api/companies', {'name':'Módulos sintéticos'})['id']
        cycle = self.post('/api/work-cycles', {'company_id':company, 'reference_competence':'2026-08', 'competence':'2026-09', 'reason':'Configuração'})
        rows = self.client.get('/api/work-module-state', params={'company_id':company,'cycle_id':cycle['id']}).json()['data']
        fiscal = next(r for r in rows if r['state']['module']=='fiscal')
        payload = {'company_id':company, 'cycle_id':cycle['id'], 'module':'fiscal', 'target':'encerrada',
                   'snapshot_hash':fiscal['snapshot_hash'], 'reason':'Conferência', 'checks':{key:True for key in fiscal['required_checks']},
                   'evidence_reference':'Apuração externa sintética conferida'}
        result = self.post('/api/work-module-state', payload)
        self.assertEqual(result['state']['state'], 'encerrada')
        rows = self.client.get('/api/work-module-state', params={'company_id':company,'cycle_id':cycle['id']}).json()['data']
        self.assertEqual(next(r for r in rows if r['state']['module']=='contabil')['state']['state'], 'aberta')
        self.assertEqual(self.client.post('/api/work-module-state', json=payload, headers={'Origin':'http://127.0.0.1:8765'}).status_code, 403)


if __name__ == '__main__':
    unittest.main()
