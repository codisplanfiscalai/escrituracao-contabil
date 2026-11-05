"""Client intake has no period dependency and cannot organize or post."""
import base64
import unittest
from server import test_identity_portal as helpers
from test_batch_import import zip_bytes
from test_persistence import fake_xml

class BatchHTTPTests(unittest.TestCase):
    setUp=helpers.PortalTests.setUp
    tearDown=helpers.PortalTests.tearDown
    post=helpers.PortalTests.post
    create_company=helpers.PortalTests.create_company
    other_client=helpers.PortalTests.other_client
    def test_client_receives_original_retry_and_company_isolation(self):
        company=self.create_company()
        self.post('users',{'name':'Cliente sintético','email':'client@example.test','password':self.password,'role':'client','companies':[company]})
        client,headers=self.other_client();self.addCleanup(client.close)
        packed=zip_bytes([('ok.xml',fake_xml()),('bad.xml',b'broken')])
        body={'company_id':company,'request_key':'client-receipt','inputs':[{'filename':'pack.zip','content_base64':base64.b64encode(packed).decode()}]}
        r=client.post('/api/v1/client/source-receive',json=body,headers=headers);self.assertEqual(r.status_code,200,r.text)
        receipt=r.json()['data'];self.assertEqual(len(receipt['items']),3)
        self.assertTrue(client.post('/api/v1/client/source-receive',json=body,headers=headers).json()['data']['duplicate'])
        source=next(s for s in receipt['items'] if s['filename']=='pack.zip');params={'company_id':company,'input_id':source['input_id']}
        r=client.get('/api/v1/client/source-original',params=params);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.content,packed)
        self.assertIn('no-store',r.headers['cache-control']);self.assertIn('attachment;',r.headers['content-disposition'])
        self.assertEqual(client.get('/api/v1/client/periods',params={'company_id':company}).json()['data'],[])
        self.assertEqual(client.post('/api/v1/client/source-receive',json=body,headers={'Origin':headers['Origin']}).status_code,403)
        for route in ['source-organize','work-operations','work-post']:
            self.assertEqual(client.post('/api/'+route,json=body,headers=headers).status_code,403)
            self.assertEqual(client.post('/api/v1/client/'+route,json=body,headers=headers).status_code,404)
        other=self.create_company('Outra sintética');self.assertEqual(client.get('/api/v1/client/source-original',params={**params,'company_id':other}).status_code,403)
