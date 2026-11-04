"""Escopo por empresa e separação de permissões de escrita/revisão contábil."""
import unittest
from server import test_identity_portal as helpers
from test_persistence import fake_accounts


class AccountingPortalTests(unittest.TestCase):
    setUp=helpers.PortalTests.setUp
    tearDown=helpers.PortalTests.tearDown
    post=helpers.PortalTests.post
    create_company=helpers.PortalTests.create_company
    other_client=helpers.PortalTests.other_client

    def test_operator_writes_reviewer_closes_and_download_requires_company_scope(self):
        company=self.create_company()
        def admin_post(route,body):
            response=self.client.post('/api/'+route,json={'company_id':company,**body},headers=self.headers)
            self.assertEqual(response.status_code,200,response.text)
            return response.json()['data']
        period=admin_post('periods',{'reference_competence':'2026-08','processing_competence':'2026-09'})['id']
        plan=admin_post('plans',{'label':'Plano fictício','accounts':fake_accounts()})['id']
        accounts=self.client.get('/api/accounts',params={'company_id':company,'plan_id':plan}).json()['data']
        ids={row['code']:row['id'] for row in accounts}
        self.post('users',{'name':'Operador fictício','email':'operator@example.test','password':self.password,'role':'accountant','companies':[company]})
        operator,headers=self.other_client('operator@example.test');self.addCleanup(operator.close)
        lines=[dict(date='2026-09-15',group='ficticio',side=side,amount='10.00',account_id=ids[code],memo='Histórico fictício')
               for side,code in (('D','1.1.1'),('C','2.1'))]
        body={'company_id':company,'period_id':period,'plan_id':plan,'entries':lines,'reference':'Ref fictícia','reason':'Teste','request_key':'portal-1'}
        response=operator.post('/api/manual-journals',json=body,headers=headers)
        self.assertEqual(response.status_code,200,response.text);revision=response.json()['data']
        review={'journal_id':revision['journal_id'],'snapshot_hash':revision['snapshot_hash'],'reason':'Teste'}
        for route in ('manual-review','manual-close'):
            self.assertEqual(operator.post('/api/'+route,json={'company_id':company,**review},headers=headers).status_code,403)
            admin_post(route,review)
        params={'company_id':company,'period_id':period,'plan_id':plan}
        books=operator.get('/api/accounting-books',params=params).json()['data']
        body={**params,'book_hash':books['book_hash'],'reason':'Teste'}
        self.assertEqual(operator.post('/api/accounting-book-exports',json=body,headers=headers).status_code,403)
        export=admin_post('accounting-book-exports',body)
        file_params={'company_id':company,'export_id':export['id'],'name':'books.json'}
        downloaded=operator.get('/api/accounting-book-file',params=file_params)
        self.assertEqual(downloaded.status_code,200,downloaded.text)
        self.assertEqual(downloaded.json()['book_hash'],books['book_hash'])
        self.assertIn('attachment;',downloaded.headers['content-disposition'])
        other=self.create_company('Outra fictícia')
        self.assertEqual(operator.get('/api/accounting-book-file',params={**file_params,'company_id':other}).status_code,403)
        self.assertEqual(operator.post('/api/manual-journals',json=body,headers={'Origin':headers['Origin']}).status_code,403)
        self.post('users',{'name':'Cliente fictício','email':'client@example.test','password':self.password,'role':'client','companies':[company]})
        client,client_headers=self.other_client();self.addCleanup(client.close)
        for route in ('manual-journals','accounting-books','accounting-book-exports','accounting-book-file'):
            self.assertEqual(client.get('/api/'+route,params=file_params).status_code,403)
            self.assertEqual(client.get('/api/v1/client/'+route,params=file_params).status_code,404)


if __name__ == '__main__':unittest.main()
