"""Papéis separados sobre a mesma operação, livros e exportação preservada."""
import unittest
from server import test_identity_portal as helpers
from test_persistence import fake_accounts

class AccountingPortalTests(unittest.TestCase):
    setUp=helpers.PortalTests.setUp
    tearDown=helpers.PortalTests.tearDown
    post=helpers.PortalTests.post
    create_company=helpers.PortalTests.create_company
    other_client=helpers.PortalTests.other_client

    def test_operator_drafts_reviewer_posts_and_scoped_download(self):
        company=self.create_company()
        def admin(route,body):
            r=self.client.post('/api/'+route,json={'company_id':company,**body},headers=self.headers)
            self.assertEqual(r.status_code,200,r.text);return r.json()['data']
        plan=admin('plans',{'label':'Plano sintético','accounts':fake_accounts()})['id']
        cycle=admin('work-cycles',{'reference_competence':'2026-08','competence':'2026-09','plan_id':plan,'reason':'Teste'})['id']
        ids={r['code']:r['id'] for r in self.client.get('/api/accounts',params={'company_id':company,'plan_id':plan}).json()['data']}
        self.post('users',{'name':'Operador sintético','email':'operator@example.test','password':self.password,'role':'accountant','companies':[company]})
        operator,headers=self.other_client('operator@example.test');self.addCleanup(operator.close)
        scope={'company_id':company,'cycle_id':cycle}
        p=operator.get('/api/work-prepare',params=scope).json()['data'];p['reference']='Ajuste sintético';p['fiscal'].update(total='10.00',posting_date='2026-09-15')
        for l,code in zip(p['entries'],['1.1.1','2.1']):l.update(account_id=ids[code],amount='10.00',date='2026-09-15',memo='Sintético')
        body={**scope,'payload':p,'reason':'Teste','request_key':'portal-work-1'}
        response=operator.post('/api/work-operations',json=body,headers=headers)
        self.assertEqual(response.status_code,200,response.text);o=response.json()['data']
        transition={'operation_id':o['operation_id'],'snapshot_hash':o['snapshot_hash'],'reason':'Teste'}
        for route in ['work-review','work-post']:
            self.assertEqual(operator.post('/api/'+route,json={'company_id':company,**transition},headers=headers).status_code,403)
            admin(route,transition)
        book=operator.get('/api/work-books',params=scope).json()['data']
        export=admin('work-exports',{'cycle_id':cycle,'snapshot_hash':book['snapshot_hash'],'reason':'Teste'})
        params={'company_id':company,'export_id':export['id'],'name':'escrituracao.json'}
        response=operator.get('/api/work-export-file',params=params)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['snapshot_hash'],book['snapshot_hash'])
        self.assertIn('attachment;',response.headers['content-disposition'])
        other=self.create_company('Outra sintética');self.assertEqual(operator.get('/api/work-export-file',params={**params,'company_id':other}).status_code,403)
        self.assertEqual(operator.post('/api/work-operations',json=body,headers={'Origin':headers['Origin']}).status_code,403)
        self.assertEqual(operator.post('/api/manual-journals',json={'company_id':company},headers=headers).status_code,410)
