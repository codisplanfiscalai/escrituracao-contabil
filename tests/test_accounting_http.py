"""Fluxo contábil sintético pela API HTTP local, incluindo arquivos binários."""
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

    def test_manual_edit_review_close_books_export_and_download(self):
        company=self.company()['id']
        period=self.api('periods',{'company_id':company,'reference_competence':'2026-08','processing_competence':'2026-09'})['id']
        plan=self.api('plans',{'company_id':company,'label':'Plano sintético','accounts':fake_accounts()})['id']
        accounts=self.api(f'accounts?company_id={company}&plan_id={plan}')
        ids={row['code']:row['id'] for row in accounts}
        lines=[dict(date='2026-09-15',group='grupo',side=side,amount='10.00',account_id=ids[code],memo='Histórico sintético')
               for side,code in (('D','1.1.1'),('C','2.1'))]
        body={'company_id':company,'period_id':period,'plan_id':plan,'entries':lines,'reference':'Ref sintética','reason':'Teste','request_key':'http-1'}
        first=self.api('manual-journals',body)
        self.assertEqual(len(self.api(f'manual-journals?company_id={company}&period_id={period}')),1)
        transition={'company_id':company,'journal_id':first['journal_id'],'snapshot_hash':first['snapshot_hash'],'reason':'Teste'}
        self.assertEqual(self.request('/api/manual-close','POST',transition)[0],400)
        self.assertEqual(self.request('/api/manual-review','POST',transition,headers={'X-Local-Token':None})[0],403)
        self.api('manual-review',transition);self.api('manual-close',transition)
        query=f'company_id={company}&period_id={period}&plan_id={plan}'
        book=self.api('accounting-books?'+query)
        export=self.api('accounting-book-exports',{'company_id':company,'period_id':period,'plan_id':plan,'book_hash':book['book_hash'],'reason':'Teste'})
        for artifact in export['artifacts']:
            status,headers,content=self.request(f'/api/accounting-book-file?company_id={company}&export_id={export["id"]}&name={artifact["name"]}')
            self.assertEqual(status,200,content)
            self.assertIn('attachment;',headers['Content-Disposition'])
            self.assertEqual(len(content),artifact['size'])
            self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(len(self.api(f'accounting-book-exports?company_id={company}')),1)
        other=self.company()['id']
        self.assertEqual(self.request(f'/api/accounting-book-file?company_id={other}&export_id={export["id"]}&name=books.json')[0],400)
        self.assertEqual(self.request(f'/api/accounting-book-file?company_id={company}&export_id={export["id"]}&name=../private')[0],400)
        bad={**body,'company_id':True}
        self.assertEqual(self.request('/api/manual-journals','POST',bad)[0],400)


if __name__ == '__main__':unittest.main()
