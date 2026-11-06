"""Tax batch routes preserve company scope, CSRF and write/review separation."""
import unittest
from fastapi.testclient import TestClient
from server import test_company_profiles_http as fixtures


class TaxBatchHTTPTests(unittest.TestCase):
    setUp=fixtures.RegistrationHTTPTests.setUp
    post=fixtures.RegistrationHTTPTests.post

    def setup_data(self):
        company=self.post('/api/companies',{'name':'Lote sintético'})['id']
        cycle=self.post('/api/work-cycles',{'company_id':company,'competence':'2026-09','reference_competence':'2026-08','reason':'Teste'})['id']
        scope={'company_id':company,'cycle_id':cycle}
        self.post('/api/tax-rules',{'company_id':company,'rule_key':'test','label':'Regra sintética','state':'aprovada','expected_version':0,'reason':'Teste',
            'spec':{'tax':'ICMS','rate':'2.5','base_field':'total','effect':'debito','operation':'entrada','valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Sem validade legal'}})
        ids=[]
        for n in (1,2):
            payload=self.client.get('/api/work-prepare',params={**scope,'operation':'entrada'}).json()['data']
            payload['reference']='Documento sintético '+str(n);payload['fiscal'].update(total='100.00',model='55',number=str(n),issued_date='2026-09-15',posting_date='2026-09-15')
            row=self.post('/api/work-operations',{**scope,'payload':payload,'reason':'Teste','request_key':'operation-'+str(n)})
            ids.append(row['operation_id'])
        return scope,ids

    def test_preview_apply_retry_history_and_original_versions(self):
        scope,ids=self.setup_data()
        preview=self.post('/api/tax-batch-preview',{**scope,'operation_ids':ids})
        request={**scope,'operation_ids':ids,'snapshot_hash':preview['snapshot_hash'],'request_key':'batch','reason':'Teste'}
        self.assertEqual(self.client.post('/api/tax-batch-apply',json=request,headers=self.headers).status_code,400)
        first=self.post('/api/tax-batch-apply',{**request,'confirmed':True})
        again=self.post('/api/tax-batch-apply',{**request,'confirmed':True})
        self.assertTrue(again['duplicate']);self.assertEqual(first['snapshot'],again['snapshot'])
        history=self.client.get('/api/tax-batches',params=scope).json()['data']
        self.assertEqual(history['total'],1);self.assertEqual(history['items'][0]['count'],2)
        detail=self.client.get('/api/tax-batch',params={'company_id':scope['company_id'],'batch_id':first['id']}).json()['data']
        self.assertEqual(len(detail['calculations']),2)
        self.assertTrue(all(item['output_version']==2 for item in detail['snapshot']['items']))
        for operation in ids:
            row=self.client.get('/api/work-operation',params={'company_id':scope['company_id'],'operation_id':operation}).json()['data']
            self.assertEqual(row['state'],'rascunho')

    def test_reader_cannot_calculate_and_other_company_is_inaccessible(self):
        scope,ids=self.setup_data();other=self.post('/api/companies',{'name':'Outra sintética'})['id']
        role=self.post('/api/v1/roles',{'name':'Leitor sintético','permissions':['workspace.read']})
        self.post('/api/v1/users',{'name':'Leitor de lotes','email':'batch@example.test','password':self.password,'role':role['id'],'companies':[str(scope['company_id'])],'active':True})
        client=TestClient(self.app,base_url='http://127.0.0.1:8765');self.addCleanup(client.close)
        login=client.post('/api/v1/auth/login',json={'email':'batch@example.test','password':self.password},headers={'Origin':'http://127.0.0.1:8765'}).json()['data']
        headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':login['csrf']}
        self.assertEqual(client.get('/api/tax-batches',params=scope).status_code,200)
        self.assertEqual(client.get('/api/tax-batches',params={**scope,'company_id':other}).status_code,403)
        for route in ('preview','apply'):
            self.assertEqual(client.post('/api/tax-batch-'+route,json={**scope,'operation_ids':ids},headers=headers).status_code,403)
        self.assertEqual(self.client.post('/api/tax-batch-preview',json={**scope,'operation_ids':ids},headers={'Origin':'http://127.0.0.1:8765'}).status_code,403)


if __name__=='__main__':unittest.main()
