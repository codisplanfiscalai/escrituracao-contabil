"""Synthetic temporary browser scenarios shared by acceptance checks."""
from contextlib import contextmanager
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'tests')]
from src.server.runtime import PortalServer
from src.local_app import LocalServer
from src.persistence import AccountingStore
from test_persistence import fake_accounts, BUYER
from playwright.sync_api import sync_playwright,expect

@contextmanager
def scenario(mode='portal',chart=True):
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'synthetic.sqlite3'
        with AccountingStore(path) as s:
            company=s.create_company('Alfa sintética',cnpj=BUYER)['id']
            other=s.create_company('Beta sintética')['id']
            plan=s.import_plan(company,'Plano sintético',fake_accounts())['id'] if chart else None
            first=s.save_work_cycle(company,'2026-08','2026-09',plan,'Teste')['id'] if chart else None
            second=s.save_work_cycle(company,'2026-09','2026-10',plan,'Teste')['id'] if chart else None
            third=s.save_work_cycle(other,'2026-08','2026-09',None,'Teste')['id'] if chart else None
            accounts={a['code']:a['id'] for a in s.list_accounts(company,plan)} if chart else {}
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=PortalServer(path,port) if mode=='portal' else LocalServer(path,port)
        if mode=='portal':
            identity=server.app.state.identity
            identity.setup({'token':identity.setup_secret,'name':'Operador sintético','email':'qa@example.test','password':'synthetic-browser-password'},'local')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        if mode=='portal':
            deadline=time.monotonic()+15
            while not server.server.started:
                if time.monotonic()>deadline:raise RuntimeError('Servidor não iniciou')
                time.sleep(.05)
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=None if Path(p.chromium.executable_path).exists() else shutil.which('chromium'),headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1080},accept_downloads=True)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{port}')
                if mode=='portal':
                    page.get_by_label('E-mail',exact=True).fill('qa@example.test');page.get_by_label('Senha',exact=True).fill('synthetic-browser-password')
                    page.get_by_role('button',name='Entrar no ambiente').click()
                    page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click()
                    frame=page.frame_locator('#workspace-frame')
                else:frame=page
                expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
                yield {'page':page,'frame':frame,'company':company,'other':other,'first':first,'second':second,'third':third,'accounts':accounts,'plan':plan,'path':path,'server':server,'errors':errors,'temp':Path(temp)}
                assert not errors,errors
                browser.close()
        finally:server.shutdown();thread.join(10);server.server_close()
