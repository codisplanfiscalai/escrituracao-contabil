"""Source intake without a period, immutable originals and explicit organizing."""
import base64
import unittest
import test_accounting_http as helpers
from test_persistence import fake_xml
from test_batch_import import zip_bytes

class IntakeLocalTests(unittest.TestCase):
    for method in ['setUp','tearDown','start_server','stop_server','request','api','company']:
        locals()[method]=getattr(helpers.AccountingHTTPTests,method)

    def test_receive_retry_bad_base64_original_and_decision(self):
        company=self.company()['id'];content=zip_bytes([('ok.xml',fake_xml()),('bad.xml',b'broken')])
        body={'company_id':company,'request_key':'synthetic-receipt','inputs':[{'filename':'pack.zip','content_base64':base64.b64encode(content).decode()}]}
        receipt=self.api('source-receive',body)
        self.assertEqual(self.api(f'periods?company_id={company}'),[])
        self.assertEqual(len(receipt['items']),3)
        self.assertTrue(self.api('source-receive',body)['duplicate'])
        package=next(r for r in receipt['items'] if r['filename']=='pack.zip')
        status,headers,original=self.request(f'/api/source-original?company_id={company}&input_id={package["input_id"]}')
        self.assertEqual(status,200);self.assertEqual(original,content);self.assertIn('attachment;',headers['Content-Disposition'])
        body['inputs'][0]['content_base64']='@@@'
        self.assertEqual(self.request('/api/source-receive','POST',body)[0],400)
        source=next(r for r in receipt['items'] if r['filename']=='ok.xml')
        cycle=self.api('work-cycles',{'company_id':company,'reference_competence':'2026-08','competence':'2026-09','reason':'Teste'})
        self.api('source-organize',{'company_id':company,'input_id':source['input_id'],'cycle_id':cycle['id'],'snapshot_hash':source['snapshot_hash'],'reason':'Identificado e organizado'})
        self.assertEqual(len(self.api(f'documents?company_id={company}')),1)
        impact=self.api(f'source-impact?company_id={company}&input_id={source["input_id"]}')
        self.assertEqual(impact['protected'],[])
        self.api('source-remove',{'company_id':company,'input_id':source['input_id'],'impact_hash':impact['impact_hash'],'reason':'Correção sintética','confirmed':True})
        self.assertEqual(self.api(f'source-inbox?company_id={company}')[1]['evidence']['state'],'descartado')
