"""Authenticated batch boundaries with purely synthetic source bytes."""
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

    def test_client_upload_download_retry_and_cross_company_isolation(self):
        company=self.create_company()
        period=self.client.post('/api/periods',json={'company_id':company,'reference_competence':'2026-09','processing_competence':'2026-09'},headers=self.headers).json()['data']['id']
        self.post('users',{'name':'Cliente fictício','email':'client@example.test','password':self.password,'role':'client','companies':[company]})
        client,headers=self.other_client();self.addCleanup(client.close)
        packed=zip_bytes([('sub/ficticio.xml',fake_xml()),('ruim.xml',b'broken')])
        body={'company_id':company,'period_id':period,'request_key':'http-ficticio','inputs':[{'filename':'ficticio.zip','content_base64':base64.b64encode(packed).decode()}]}
        response=client.post('/api/v1/client/import-batches',json=body,headers=headers)
        self.assertEqual(response.status_code,200,response.text)
        batch=response.json()['data'];self.assertEqual(batch['counts']['rejeitado'],1)
        self.assertTrue(client.post('/api/v1/client/import-batches',json=body,headers=headers).json()['data']['duplicate'])
        params={'company_id':company,'item_id':batch['items'][0]['id']}
        response=client.get('/api/v1/client/import-original',params=params)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.content,packed)
        self.assertIn('attachment;',response.headers['content-disposition'])
        self.assertIn('no-store',response.headers['cache-control'])
        self.assertEqual(client.post('/api/v1/client/import-batches',json=body,headers={'Origin':headers['Origin']}).status_code,403)
        self.assertEqual(client.get('/api/v1/client/products',params={'company_id':company}).status_code,404)
        other=self.create_company('Outra fictícia')
        self.assertEqual(client.get('/api/v1/client/import-original',params={**params,'company_id':other}).status_code,403)
        self.assertEqual(self.client.get('/api/import-original',params={**params,'company_id':other}).status_code,400)
        self.assertEqual(client.post('/api/product-review',json={'company_id':company},headers=headers).status_code,403)
        self.assertEqual(client.post('/api/v1/client/product-review',json={'company_id':company},headers=headers).status_code,404)
