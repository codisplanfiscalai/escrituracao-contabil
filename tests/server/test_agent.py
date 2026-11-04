import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid
from fastapi.testclient import TestClient
from src.agent import create_agent,DockerServices
from src.server.identity import IdentityError

IDENT='a'*64
class FakeDocker:
    def __init__(self):self.commands=[]
    def services(self):return [{'id':IDENT,'name':'api','state':'running','status':'Up','image':'synthetic'}]
    def require(self,ident):
        if ident!=IDENT:raise IdentityError('Não autorizado',403)
    def command(self,ident,action):self.require(ident);self.commands.append((ident,action));return {'completed':True}
    def logs(self,ident):self.require(ident);return {'text':'synthetic log'}

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.docker=FakeDocker();self.app=create_agent(self.temp.name,self.docker)
        self.client=TestClient(self.app);self.headers={'Authorization':'Bearer '+self.app.state.token,'Idempotency-Key':str(uuid.uuid4())}
    def tearDown(self):self.client.close();self.temp.cleanup()
    def test_requires_agent_token(self):
        self.assertEqual(self.client.get('/v1/services').status_code,401)
        self.assertEqual(self.client.get('/v1/services',headers=self.headers).status_code,200)
    def test_commands_are_allowlisted_scoped_and_idempotent(self):
        path=f'/v1/services/{IDENT}/restart'
        for _ in range(2):self.assertEqual(self.client.post(path,headers=self.headers).status_code,200)
        self.assertEqual(self.docker.commands,[(IDENT,'restart')])
        self.assertEqual(self.client.post(f'/v1/services/{IDENT}/stop',headers=self.headers).status_code,409)
        self.assertEqual(self.client.post('/v1/services/'+('b'*64)+'/start',headers=self.headers).status_code,403)
        self.assertEqual(self.client.post(f'/v1/services/{IDENT}/exec',headers=self.headers).status_code,400)
    def test_pending_result_not_blindly_retried(self):
        with patch.object(self.docker,'command',side_effect=IdentityError('Docker timeout',502)):
            self.assertEqual(self.client.post(f'/v1/services/{IDENT}/restart',headers=self.headers).status_code,502)
        self.assertEqual(self.client.post(f'/v1/services/{IDENT}/restart',headers=self.headers).status_code,409)
    def test_labels_checked_even_when_runtime_returns_unrelated_container(self):
        service=DockerServices('/tmp/unconnected.sock','escritura')
        data=[{'Id':IDENT,'State':'running','Labels':{'io.escritura.installation':'other','io.escritura.managed':'true'}}]
        with patch.object(service,'request',return_value=json.dumps(data).encode()):
            self.assertEqual(service.services(),[])
            with self.assertRaises(IdentityError):service.require(IDENT)
    def test_docker_logs_demultiplexed(self):
        service=DockerServices('/tmp/unconnected.sock','escritura');payload=b'hello\n';raw=b'\x01\0\0\0'+len(payload).to_bytes(4,'big')+payload
        with patch.object(service,'require'),patch.object(service,'request',return_value=raw):self.assertEqual(service.logs(IDENT)['text'],'hello\n')

if __name__=='__main__':unittest.main()
