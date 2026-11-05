import base64
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.server.app import create_app
from src.server.identity import IdentityError, digest, otp

class PortalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=create_app(self.temp.name, 'http://127.0.0.1:8765',worker=False)
        self.identity=self.app.state.identity
        self.client=TestClient(self.app,base_url='http://127.0.0.1:8765')
        self.headers={'Origin':'http://127.0.0.1:8765'}
        self.password='correct-horse-battery-2026'
        r=self.post('setup',{'token':self.identity.setup_secret,'name':'Administrador','email':'admin@example.test','password':self.password})
        self.assertEqual(r.status_code,200,r.text)
        r=self.post('auth/login',{'email':'admin@example.test','password':self.password})
        self.assertEqual(r.status_code,200,r.text)
        self.user=r.json()['data']['user'];self.headers['X-CSRF-Token']=r.json()['data']['csrf']
    def tearDown(self):self.client.close();self.temp.cleanup()
    def post(self,path,data,client=None,headers=None):
        return (client or self.client).post('/api/v1/'+path,json=data,headers=self.headers if headers is None else headers)
    def create_company(self,name='Empresa de teste'):
        r=self.client.post('/api/companies',json={'name':name,'prosoft_company_code':'1','prosoft_plan_code':'1'},headers=self.headers)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()['data']['id']
    def create_client(self,companies):
        r=self.post('users',{'name':'Cliente','email':'client@example.test','password':self.password,'role':'client','companies':companies})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()['data']
    def other_client(self,email='client@example.test'):
        client=TestClient(self.app,base_url='http://127.0.0.1:8765')
        r=client.post('/api/v1/auth/login',json={'email':email,'password':self.password},headers={'Origin':'http://127.0.0.1:8765'})
        self.assertEqual(r.status_code,200,r.text)
        return client,{'Origin':'http://127.0.0.1:8765','X-CSRF-Token':r.json()['data']['csrf']}

    def test_auth_boundaries_and_static_assets(self):
        outsider=TestClient(self.app,base_url='http://127.0.0.1:8765')
        for path in ('/api/companies','/api/v1/users','/workspace','/api/v1/dashboard'):
            self.assertEqual(outsider.get(path).status_code,401,path)
        self.assertEqual(outsider.get('/').status_code,200)
        self.assertEqual(outsider.get('/workbench.js?name=../../identity.sqlite3').status_code,200)
        self.assertIn('const clone',outsider.get('/workbench.js?name=../../identity.sqlite3').text)
        self.assertEqual(outsider.get('/api/v1/status',headers={'Host':'evil.example'}).status_code,403)
        self.assertEqual(self.post('auth/logout',{},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.post('auth/logout',{},headers={'Origin':'http://127.0.0.1:8765'}).status_code,403)
        cookie=self.client.cookies.get('escritura_session')
        with self.identity.connect() as db:self.assertIsNotNone(db.execute('SELECT token FROM sessions WHERE token=?',(digest(cookie),)).fetchone())
        self.assertNotIn(cookie,Path(self.identity.path).read_bytes().decode('latin1'))
        self.assertNotIn('unsafe-eval',outsider.get('/').headers['content-security-policy'])
        outsider.close()

    def test_bootstrap_single_use_and_last_admin(self):
        r=self.post('setup',{'token':self.identity.setup_secret,'name':'Other','email':'other@example.test','password':self.password})
        self.assertEqual(r.status_code,409)
        r=self.post('users',{**self.user,'active':False})
        self.assertEqual(r.status_code,409)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code,200)

    def test_evidence_download_preserves_bytes_headers_and_company_scope(self):
        company=self.create_company();other=self.create_company('Outra empresa')
        self.create_client([str(company)])
        client,_=self.other_client()
        artifact={'content':b'conta,valor\r\n1,123.45\r\n','media_type':'text/csv','name':'postings.csv'}
        with patch('src.server.app.dispatch',return_value=artifact) as dispatch:
            response=client.get('/api/v1/client/accounting-evidence-file',params={'company_id':company,'export_id':'1','name':'postings.csv'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.content,artifact['content'])
            self.assertEqual(response.headers['content-disposition'],'attachment; filename="postings.csv"')
            self.assertTrue(response.headers['content-type'].startswith('text/csv'))
            self.assertEqual(client.get('/api/v1/client/accounting-evidence-file',params={'company_id':other,'export_id':'1','name':'postings.csv'}).status_code,403)
            self.assertEqual(dispatch.call_count,1)
        client.close()

    def test_company_scope_and_client_cannot_use_internal_operations(self):
        first=self.create_company();second=self.create_company('Outra empresa')
        self.create_client([str(first)])
        client,headers=self.other_client()
        companies=client.get('/api/v1/client/companies').json()['data']
        self.assertEqual([c['id'] for c in companies],[first])
        self.assertEqual(client.get('/api/v1/client/documents',params={'company_id':second}).status_code,403)
        self.assertEqual(client.get('/api/companies').status_code,403)
        self.assertEqual(client.get('/api/v1/users').status_code,403)
        self.assertEqual(client.get('/workspace').status_code,403)
        self.assertEqual(client.post('/api/accounting-close',json={},headers=headers).status_code,403)
        self.assertEqual(client.get('/api/v1/client/documents',params={'company_id':first}).status_code,200)
        client.close()

    def test_role_change_revokes_existing_sessions_and_keeps_audit_actor(self):
        company=self.create_company();user=self.create_client([str(company)])
        client,headers=self.other_client()
        r=self.post('users',{**user,'name':'Renomeado','active':False})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(client.get('/api/v1/dashboard').status_code,401)
        audit=self.client.get('/api/v1/audit').json()['data']
        self.assertEqual(audit[0]['actor'],self.user['id'])
        domain=self.client.get('/api/audit',params={'company_id':company}).json()['data']
        self.assertIn(self.user['id'],json.dumps(domain))
        client.close()

    def test_totp_enrollment_login_replay_and_recovery_consumption(self):
        enroll=self.post('mfa/begin',{'password':self.password}).json()['data']
        counter=int(time.time())//30
        r=self.post('mfa/confirm',{'token':enroll['token'],'code':otp(enroll['secret'],counter)})
        self.assertEqual(r.status_code,200,r.text)
        codes=r.json()['data']['recovery_codes'];self.assertEqual(len(codes),8)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code,401)
        login=self.post('auth/login',{'email':'admin@example.test','password':self.password}).json()['data']
        self.assertTrue(login['mfa_required'])
        self.assertEqual(self.post('auth/mfa',{'challenge':login['challenge'],'code':otp(enroll['secret'],counter)}).status_code,401)
        verified=self.post('auth/mfa',{'challenge':login['challenge'],'code':codes[0]})
        self.assertEqual(verified.status_code,200,verified.text)
        self.assertEqual(self.post('auth/mfa',{'challenge':login['challenge'],'code':codes[1]}).status_code,401)
        second=self.post('auth/login',{'email':'admin@example.test','password':self.password}).json()['data']
        self.assertEqual(self.post('auth/mfa',{'challenge':second['challenge'],'code':codes[0]}).status_code,401)
        with self.identity.connect() as db:
            row=db.execute('SELECT mfa FROM users WHERE id=?',(self.user['id'],)).fetchone()
            self.assertNotIn(enroll['secret'],row[0]);self.assertNotEqual(row[0],enroll['secret'])
            self.assertEqual(db.execute('SELECT count(*) FROM recovery').fetchone()[0],7)

    def test_reset_is_single_use_delivered_by_outbox_and_revokes_sessions(self):
        settings={'host':'smtp.example.test','port':587,'mode':'starttls','sender':'support@example.test','username':'mailer','password':'smtp-secret'}
        self.assertEqual(self.post('settings',{'smtp':settings}).status_code,200)
        configured=self.client.get('/api/v1/settings').json()['data']['smtp']
        self.assertNotIn('password',configured);self.assertTrue(configured['has_password'])
        r=self.post('auth/forgot',{'email':'admin@example.test'});self.assertEqual(r.status_code,200)
        messages=[]
        self.assertTrue(self.identity.deliver_one(lambda config,message:messages.append(message)))
        text=messages[0].get_content();token=text.split('/#/reset/')[1].split()[0]
        r=self.post('auth/reset',{'token':token,'password':'new-password-for-test-2026'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code,401)
        self.assertEqual(self.post('auth/reset',{'token':token,'password':self.password}).status_code,400)
        self.assertEqual(self.identity.outbox()[0]['status'],'sent')
        with self.identity.connect() as db:self.assertEqual(db.execute('SELECT payload FROM outbox').fetchone()[0],'')

    def test_rate_limit_persists_after_failed_password(self):
        for _ in range(9):
            self.assertEqual(self.post('auth/login',{'email':'admin@example.test','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('auth/login',{'email':'admin@example.test','password':'wrong'}).status_code,429)

    def test_sessions_can_only_be_revoked_by_owner(self):
        company=self.create_company();self.create_client([str(company)])
        client,headers=self.other_client()
        own=self.client.get('/api/v1/sessions').json()['data'][0]
        client.post('/api/v1/sessions/revoke',json={'id':own['id']},headers=headers)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code,200)
        self.post('sessions/revoke',{'id':own['id']})
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code,401)
        client.close()

    def test_custom_roles_and_revocation(self):
        r=self.post('roles',{'name':'Consulta documental','permissions':['client.read']})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.post('roles',{'name':'Invalid','permissions':['system.shell']}).status_code,400)
        self.assertEqual(self.post('roles',{'id':'admin','name':'Override','permissions':[]}).status_code,400)

    def test_accounting_database_survives_portal_restart(self):
        company=self.create_company()
        app=create_app(self.temp.name,'http://127.0.0.1:8765',worker=False)
        other=TestClient(app,base_url='http://127.0.0.1:8765');other.cookies.update(self.client.cookies)
        self.assertEqual(other.get('/api/companies').json()['data'][0]['id'],company)
        other.close()

    def test_network_url_requires_https(self):
        with self.assertRaises(ValueError):create_app(Path(self.temp.name)/'other','http://192.0.2.1:8765',worker=False)

    def test_totp_rfc_vector(self):
        secret=base64.b32encode(b'12345678901234567890').decode()
        self.assertEqual(otp(secret,1),'287082')

if __name__=='__main__':unittest.main()
