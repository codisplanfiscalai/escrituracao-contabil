"""Agente de operação isolado: somente contêineres rotulados desta instalação."""
import argparse
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import time
from urllib.parse import quote, urlencode, urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .server.identity import private_file, IdentityError

class UnixConnection(http.client.HTTPConnection):
    def __init__(self,path):super().__init__('localhost',timeout=15);self.path=path
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(self.timeout);self.sock.connect(self.path)

class DockerServices:
    def __init__(self,socket_path,installation):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',installation):raise ValueError('Instalação inválida.')
        self.socket_path=socket_path;self.installation=installation
    def request(self,method,path):
        connection=UnixConnection(self.socket_path)
        try:
            connection.request(method,path,headers={'Content-Length':'0'} if method=='POST' else {})
            response=connection.getresponse();body=response.read(2*1024*1024)
            if response.status not in (200,204,304):raise IdentityError('O runtime Docker recusou a operação.',502)
            return body
        finally:connection.close()
    def services(self):
        filters=json.dumps({'label':['io.escritura.installation='+self.installation,'io.escritura.managed=true']})
        rows=json.loads(self.request('GET','/containers/json?'+urlencode({'all':'1','filters':filters})))
        # Reconfere os rótulos retornados antes de permitir qualquer comando.
        return [{'id':r['Id'],'name':r.get('Labels',{}).get('com.docker.compose.service',r.get('Names',['serviço'])[0].lstrip('/')),'state':r['State'],'status':r.get('Status',''),'image':r.get('Image','')} for r in rows if r.get('Labels',{}).get('io.escritura.installation')==self.installation and r.get('Labels',{}).get('io.escritura.managed')=='true']
    def require(self,ident):
        if not re.fullmatch(r'[a-f0-9]{64}',ident) or not any(s['id']==ident for s in self.services()):raise IdentityError('Serviço fora desta instalação.',403)
    def command(self,ident,action):
        if action not in ('start','stop','restart'):raise IdentityError('Comando não permitido.',400)
        self.require(ident)
        self.request('POST',f'/containers/{ident}/{action}?t=10')
        return {'id':ident,'action':action,'completed':True}
    def logs(self,ident):
        self.require(ident)
        raw=self.request('GET',f'/containers/{ident}/logs?stdout=1&stderr=1&tail=100&timestamps=1')
        # Docker multiplexa stdout/stderr com cabeçalho de 8 bytes.
        pieces=[];offset=0
        while offset+8<=len(raw) and raw[offset] in (0,1,2) and raw[offset+1:offset+4]==b'\0\0\0':
            size=int.from_bytes(raw[offset+4:offset+8],'big');pieces.append(raw[offset+8:offset+8+size]);offset+=8+size
        text=(b''.join(pieces) if pieces else raw).decode('utf-8',errors='replace')
        return {'text':re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)[-50000:]}


def create_agent(directory,docker=None,installation='escritura',token_file=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    import secrets
    token=private_file(Path(token_file) if token_file else directory/'agent.token',secrets.token_urlsafe(48).encode()).decode()
    if len(token)<32:raise ValueError('A credencial do agente precisa conter pelo menos 32 caracteres.')
    docker=docker or DockerServices(os.getenv('ESCRITURA_DOCKER_SOCKET','/var/run/docker.sock'),installation)
    path=directory/'operations.sqlite3'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE IF NOT EXISTS operations(key TEXT PRIMARY KEY,target TEXT NOT NULL,action TEXT NOT NULL,status TEXT NOT NULL,result TEXT NOT NULL,created REAL NOT NULL)')
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    app.state.token=token
    @app.middleware('http')
    async def auth(request,call_next):
        if not hmac.compare_digest(request.headers.get('Authorization',''),'Bearer '+token):
            return JSONResponse({'error':'Credencial do agente inválida.'},status_code=401)
        response=await call_next(request);response.headers['Cache-Control']='no-store';return response
    @app.exception_handler(IdentityError)
    async def error(request,error):return JSONResponse({'error':str(error)},status_code=error.status)
    @app.get('/v1/services')
    def services():return {'data':{'installation':installation,'services':docker.services()}}
    @app.get('/v1/services/{ident}/logs')
    def logs(ident:str):return {'data':docker.logs(ident)}
    @app.post('/v1/services/{ident}/{action}')
    def command(ident:str,action:str,request:Request):
        key=request.headers.get('Idempotency-Key','')
        if not re.fullmatch(r'[a-f0-9-]{36}',key):raise IdentityError('Identificador de operação obrigatório.')
        docker.require(ident)
        if action not in ('start','stop','restart'):raise IdentityError('Comando não permitido.')
        with sqlite3.connect(path,timeout=20) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT target,action,status,result FROM operations WHERE key=?',(key,)).fetchone()
            if row:
                if row[:2]!=(ident,action):raise IdentityError('Identificador já utilizado para outra operação.',409)
                if row[2]!='done':raise IdentityError('Resultado anterior inconclusivo. Confira o estado antes de uma nova operação.',409)
                return {'data':json.loads(row[3])}
            db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',(key,ident,action,'pending','',time.time()))
        result=docker.command(ident,action)
        with sqlite3.connect(path) as db:db.execute("UPDATE operations SET status='done',result=? WHERE key=?",(json.dumps(result),key))
        return {'data':result}
    return app


def main():
    import uvicorn
    app=create_agent(os.getenv('ESCRITURA_AGENT_DATA','/agent-data'),installation=os.getenv('ESCRITURA_INSTALLATION','escritura'),token_file=os.getenv('ESCRITURA_AGENT_TOKEN_FILE'))
    uvicorn.run(app,host='0.0.0.0',port=8766,loop='asyncio',http='h11',ws='none',proxy_headers=False,access_log=False)
if __name__=='__main__':main()
