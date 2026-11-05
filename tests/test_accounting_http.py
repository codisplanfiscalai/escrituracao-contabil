"""Replacement ledger through the private HTTP boundary; frozen downloads and scope."""
import unittest
import test_local_app as helpers
from test_persistence import fake_accounts

class AccountingHTTPTests(unittest.TestCase):
    setUp=helpers.LocalApplicationTests.setUp
    tearDown=helpers.LocalApplicationTests.tearDown
    start_server=helpers.LocalApplicationTests.start_server
    stop_server=helpers.LocalApplicationTests.stop_server
    request=helpers.LocalApplicationTests.request
    api=helpers.LocalApplicationTests.api
    company=helpers.LocalApplicationTests.company

    def fixture(self):
        company=self.company()['id']
        plan=self.api('plans',{'company_id':company,'label':'Plano sintético','accounts':fake_accounts()})['id']
        cycle=self.api('work-cycles',{'company_id':company,'reference_competence':'2026-08','competence':'2026-09','plan_id':plan,'reason':'Teste'})['id']
        accounts={r['code']:r['id'] for r in self.api(f'accounts?company_id={company}&plan_id={plan}')}
        p=self.api(f'work-prepare?company_id={company}&cycle_id={cycle}')
        p['reference']='Sintético';p['fiscal'].update(posting_date='2026-09-15',total='10.00')
        for l,code in zip(p['entries'],['1.1.1','2.1']):l.update(account_id=accounts[code],amount='10.00',date='2026-09-15',memo='Sintético')
        return company,cycle,p

    def test_manual_review_post_export_scope_and_restart(self):
        company,cycle,p=self.fixture();scope={'company_id':company,'cycle_id':cycle}
        draft=self.api('work-operations',{**scope,'payload':p,'reason':'Teste','request_key':'http-1'})
        transition={'company_id':company,'operation_id':draft['operation_id'],'snapshot_hash':draft['snapshot_hash'],'reason':'Teste'}
        self.assertEqual(self.request('/api/work-post','POST',transition)[0],400)
        self.assertEqual(self.request('/api/work-review','POST',transition,headers={'X-Local-Token':None})[0],403)
        self.api('work-review',transition);posted=self.api('work-post',transition)
        self.assertTrue(posted['validation']['ready'])
        book=self.api(f'work-books?company_id={company}&cycle_id={cycle}')
        export=self.api('work-exports',{**scope,'snapshot_hash':book['snapshot_hash'],'reason':'Teste'})
        import hashlib
        for f in export['files']:
            status,headers,content=self.request(f'/api/work-export-file?company_id={company}&export_id={export["id"]}&name={f["name"]}')
            self.assertEqual(status,200,content);self.assertEqual(hashlib.sha256(content).hexdigest(),f['sha256'])
            self.assertIn('attachment;',headers['Content-Disposition'])
        self.stop_server();self.start_server()
        self.assertEqual(self.api(f'work-operation?company_id={company}&operation_id={draft["operation_id"]}')['state'],'escriturado')
        other=self.company()['id']
        self.assertEqual(self.request(f'/api/work-export-file?company_id={other}&export_id={export["id"]}&name=escrituracao.json')[0],400)
        self.assertEqual(self.request(f'/api/work-export-file?company_id={company}&export_id={export["id"]}&name=../private')[0],400)

    def test_old_writers_retired_without_removing_history(self):
        company=self.company()['id']
        from src.work_api import RETIRED_WRITES
        for route in RETIRED_WRITES:
            self.assertEqual(self.request('/api/'+route,'POST',{'company_id':company})[0],410,route)
        for route in ['files','import-batches','manual-journals','fiscal-entries','finance-titles','accounting-batches']:
            self.assertEqual(self.api(route+'?company_id='+str(company)),[],route)

    def test_durable_operator_tab_isolation_and_cas(self):
        company,cycle,_=self.fixture();scope={'company_id':company,'cycle_id':cycle}
        tab=self.api('work-tabs',{**scope,'title':'Ficha incompleta','data':{'payload':{'reference':'Rascunho'}}})
        self.stop_server();self.start_server()
        self.assertEqual(self.api(f'work-tabs?company_id={company}&cycle_id={cycle}')[0]['data']['payload']['reference'],'Rascunho')
        self.assertEqual(self.request('/api/work-tabs','POST',{**scope,'tab_id':tab['id'],'expected_version':0,'title':'Conflito','data':{}})[0],400)
