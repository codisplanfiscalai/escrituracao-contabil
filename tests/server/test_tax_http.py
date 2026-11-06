"""Tax permissions and cross-company template boundaries with synthetic rules."""
import unittest
from fastapi.testclient import TestClient
from server import test_company_profiles_http as fixtures


class TaxHTTPTests(unittest.TestCase):
    setUp = fixtures.RegistrationHTTPTests.setUp
    post = fixtures.RegistrationHTTPTests.post

    def test_item_profiles_roundtrip_and_invalid_formula_is_rejected_by_http(self):
        company=self.post('/api/companies',{'name':'Itens sintéticos'})['id']
        spec={'tax':'ICMS_ST','rate':'10','base_field':'total','effect':'debito','operation':'entrada',
              'valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Teste sem validade legal',
              'calculation':{'scope':'item','method':'st','reduction_percent':'0','base_rounding':'centavos_antes_da_taxa',
                             'margin_percent':'50','deduction_field':'st_deduction','negative_policy':'bloquear'}}
        payload={'company_id':company,'rule_key':'st','label':'ST declarada','state':'aprovada','expected_version':0,'reason':'Teste','spec':spec}
        result=self.post('/api/tax-rules',payload)
        self.assertEqual(result['spec']['calculation'],spec['calculation'])
        config=self.client.get('/api/tax-config',params={'company_id':company}).json()['data']
        self.assertIn('ICMS_DIFAL',config['supported_taxes'])
        self.assertFalse(config['legal_defaults_loaded'])
        payload['expected_version']=1
        spec['calculation']['formula']='execute()'
        response=self.client.post('/api/tax-rules',json=payload,headers=self.headers)
        self.assertEqual(response.status_code,400)
        self.assertEqual(len(self.client.get('/api/tax-config',params={'company_id':company}).json()['data']['rules']),1)

    def test_models_require_access_to_both_companies_and_copy_unapproved(self):
        first = self.post('/api/companies',{'name':'Origem sintética'})['id']
        second = self.post('/api/companies',{'name':'Destino sintético'})['id']
        rule = self.post('/api/tax-rules',{'company_id':first,'rule_key':'test','label':'Regra sintética','state':'aprovada','expected_version':0,'reason':'Teste',
            'spec':{'tax':'ICMS','rate':'2.5','base_field':'total','effect':'debito','operation':'entrada','valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Revisão sintética'}})
        template = self.post('/api/tax-templates',{'company_id':first,'rule_id':rule['id'],'rule_hash':rule['snapshot_hash'],'label':'Modelo sintético','expected_version':0,'reason':'Teste'})
        copied = self.post('/api/tax-template-copy',{'company_id':second,'source_company_id':first,'template_id':template['id'],'template_hash':template['snapshot_hash'],'rule_key':'copy','label':'Cópia sintética','reason':'Teste'})
        self.assertEqual(copied['state'],'rascunho')
        self.assertEqual(copied['spec']['validation_reference'],'')
        role = self.post('/api/v1/roles',{'name':'Revisor restrito','permissions':['workspace.read','workspace.review']})
        self.post('/api/v1/users',{'name':'Revisor sintético','email':'tax@example.test','password':self.password,'role':role['id'],'companies':[str(second)],'active':True})
        client = TestClient(self.app,base_url='http://127.0.0.1:8765')
        self.addCleanup(client.close)
        login = client.post('/api/v1/auth/login',json={'email':'tax@example.test','password':self.password},headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers = {'Origin':'http://127.0.0.1:8765','X-CSRF-Token':login['csrf']}
        self.assertEqual(client.get('/api/tax-config',params={'company_id':first}).status_code,403)
        self.assertEqual(client.post('/api/tax-template-copy',json={'company_id':second,'source_company_id':first,'template_id':template['id'],'template_hash':template['snapshot_hash'],'rule_key':'unauthorized','label':'Não copiar','reason':'Teste'},headers=headers).status_code,403)
        config = client.get('/api/tax-config',params={'company_id':second}).json()['data']
        self.assertEqual(len(config['rules']),1)
        self.assertEqual(client.post('/api/tax-codes',json={'company_id':second},headers={'Origin':'http://127.0.0.1:8765'}).status_code,403)


if __name__=='__main__':unittest.main()
