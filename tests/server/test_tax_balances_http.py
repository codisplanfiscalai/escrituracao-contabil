"""Authenticated adjustment review; all values and identities are synthetic."""
import unittest
from fastapi.testclient import TestClient
from server import test_company_profiles_http as fixtures


class TaxBalanceHTTPTests(unittest.TestCase):
    setUp=fixtures.RegistrationHTTPTests.setUp
    post=fixtures.RegistrationHTTPTests.post

    def test_preview_review_history_cancel_and_stale_assessment(self):
        company=self.post('/api/companies',{'name':'Ajuste sintético'})['id']
        cycle=self.post('/api/work-cycles',{'company_id':company,'competence':'2026-09','reference_competence':'2026-08','reason':'Teste'})['id']
        scope={'company_id':company,'cycle_id':cycle}
        spec={'kind':'manual','date':'2026-09-15','component_key':'ICMS','revenue_code':'','effect':'credito','amount':'10.00','description':'Teste','reference':'Sem validade legal'}
        preview=self.post('/api/tax-assessment-adjustment-preview',{**scope,'spec':spec})
        payload={**scope,'spec':spec,'snapshot_hash':preview['snapshot_hash'],'request_key':'apply','reason':'Teste','review_reference':'Conferência sintética'}
        self.assertEqual(self.client.post('/api/tax-assessment-adjustment-apply',json=payload,headers=self.headers).status_code,400)
        payload['confirmed']=True;row=self.post('/api/tax-assessment-adjustment-apply',payload)
        self.assertEqual(row,self.post('/api/tax-assessment-adjustment-apply',payload))
        before=self.client.get('/api/tax-assessment-preview',params=scope).json()['data']
        self.assertEqual(before['snapshot']['totals'][0]['saldo_aritmetico'],'-10.00')
        self.assertEqual(self.client.get('/api/tax-balance-sources',params=scope).json()['data'],[])
        self.post('/api/tax-assessment-adjustment-cancel',{**scope,'adjustment_id':row['id'],'snapshot_hash':row['snapshot_hash'],'request_key':'cancel','reason':'Teste','review_reference':'Revisão','confirmed':True})
        history=self.client.get('/api/tax-assessment-adjustments',params=scope).json()['data']
        self.assertEqual([r['state'] for r in history],['cancelada','aprovada'])
        self.assertEqual(self.client.post('/api/tax-assessments',json={**scope,'snapshot_hash':before['snapshot_hash'],'request_key':'stale','reason':'Teste'},headers=self.headers).status_code,400)

    def test_read_permission_cannot_apply_and_other_company_is_inaccessible(self):
        company=self.post('/api/companies',{'name':'Autorizada sintética'})['id']
        other=self.post('/api/companies',{'name':'Segregada sintética'})['id']
        cycle=self.post('/api/work-cycles',{'company_id':company,'competence':'2026-09','reference_competence':'2026-08','reason':'Teste'})['id']
        role=self.post('/api/v1/roles',{'name':'Leitura sintética','permissions':['workspace.read']})
        self.post('/api/v1/users',{'name':'Leitor sintético','email':'balances@example.test','password':self.password,'role':role['id'],'companies':[str(company)],'active':True})
        client=TestClient(self.app,base_url='http://127.0.0.1:8765');self.addCleanup(client.close)
        login=client.post('/api/v1/auth/login',json={'email':'balances@example.test','password':self.password},headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':login['csrf']}
        self.assertEqual(client.get('/api/tax-assessment-adjustments',params={'company_id':company,'cycle_id':cycle}).status_code,200)
        self.assertEqual(client.get('/api/tax-assessment-adjustments',params={'company_id':other,'cycle_id':cycle}).status_code,403)
        for route in ('preview','apply','cancel'):
            self.assertEqual(client.post('/api/tax-assessment-adjustment-'+route,json={'company_id':company,'cycle_id':cycle},headers=headers).status_code,403)


if __name__=='__main__':unittest.main()
