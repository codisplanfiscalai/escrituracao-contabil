"""Optional Chromium/Playwright smoke using synthetic inputs and temporary databases."""
from pathlib import Path
import sys
import shutil
import tempfile
import threading
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from playwright.sync_api import sync_playwright, expect
from src.local_app import LocalServer
from src.persistence import AccountingStore
from test_batch_import import zip_bytes
from test_product_catalog import product_xml
from test_persistence import fake_xml,ISSUER

with tempfile.TemporaryDirectory() as directory:
    database=Path(directory)/'synthetic.sqlite3'
    with AccountingStore(database) as store:
        company=store.create_company('Empresa inteiramente fictícia','1','1',ISSUER)['id']
        period=store.create_period(company,'2026-09','2026-09')['id']
    server=LocalServer(database,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
            page=browser.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.select_option('#company',str(company))
            page.select_option('#period',str(period))
            page.locator('[data-panel="imports"]').click()
            packed=zip_bytes([('pasta/produto.xml',product_xml()),('ruim.xml',b'<broken')])
            page.set_input_files('#upload-file',[{'name':'ficticio.zip','mimeType':'application/zip','buffer':packed},
                                                {'name':'segundo.xml','mimeType':'application/xml','buffer':product_xml(2,description='Nova descrição fictícia')}])
            page.locator('#file-form button').click()
            expect(page.locator('#status')).to_contain_text('Lote #')
            assert '1 entrada(s) rejeitada(s)' in page.locator('#status').inner_text()
            assert page.locator('#import-batches-list details').count()>0
            page.locator('#import-batches-list > details > summary').first.click()
            with page.expect_download() as info:
                page.locator('#import-batches-list button').first.click()
            download=info.value
            assert download.suggested_filename=='ficticio.zip'
            assert Path(download.path()).read_bytes()==packed
            form=page.locator('#products-list form').first
            form.locator('select').select_option(index=1)
            form.locator('input').fill('Conferência fictícia na tela')
            form.locator('button').click()
            expect(page.locator('#status')).to_contain_text('Revisão do produto registrada')
            page.reload()
            page.select_option('#company',str(company));page.select_option('#period',str(period))
            page.locator('[data-panel="imports"]').click()
            expect(page.locator('#import-batches-list')).to_contain_text('Lote #')
            assert not errors,errors
            print('PASS: lote misto, erro individual, produto divergente/revisão, download byte a byte e persistência após recarga; sem erros JS')
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()


from pathlib import Path
import socket
import sys
import tempfile
import threading
import time

from playwright.sync_api import sync_playwright,expect
import uvicorn
from src.server.app import create_app
from test_batch_import import zip_bytes
from test_persistence import fake_xml,ISSUER
with tempfile.TemporaryDirectory() as directory:
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    origin=f'http://127.0.0.1:{port}'
    app=create_app(directory,origin,worker=False)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,access_log=False,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);thread.start()
    startup_deadline=time.monotonic()+15
    while not server.started:
        if time.monotonic()>startup_deadline:raise RuntimeError('Servidor de teste não iniciou em 15 segundos')
        time.sleep(.05)
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
            context=browser.new_context()
            request=context.request;headers={'Origin':origin};password='synthetic-password-2026-ficticio'
            def post(path,data):
                response=request.post(origin+path,data=data,headers=headers)
                assert response.ok,response.text()
                return response.json()['data']
            post('/api/v1/setup',{'token':app.state.identity.setup_secret,'name':'Administrador fictício','email':'admin@example.test','password':password})
            session=post('/api/v1/auth/login',{'email':'admin@example.test','password':password});headers['X-CSRF-Token']=session['csrf']
            company=post('/api/companies',{'name':'Empresa fictícia','prosoft_company_code':'1','prosoft_plan_code':'1','cnpj':ISSUER})['id']
            period=post('/api/periods',{'company_id':company,'reference_competence':'2026-09','processing_competence':'2026-09'})['id']
            post('/api/v1/users',{'name':'Cliente fictício','email':'client@example.test','password':password,'role':'client','companies':[company]})
            post('/api/v1/auth/logout',{})
            session=post('/api/v1/auth/login',{'email':'client@example.test','password':password});headers['X-CSRF-Token']=session['csrf']
            page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(origin+'/#/client')
            page.get_by_label('Empresa',exact=True).select_option(str(company))
            page.get_by_label('Período',exact=True).select_option(str(period))
            page.locator('input[type=file]').set_input_files([{'name':'pacote.zip','mimeType':'application/zip','buffer':zip_bytes([('valido.xml',fake_xml()),('ruim.xml',b'bad')])}])
            page.get_by_role('button',name='Enviar lote').click()
            expect(page.locator('.alert.success')).to_contain_text('Lote #')
            expect(page.locator('body')).to_contain_text('ruim.xml')
            page.reload()
            page.get_by_label('Empresa',exact=True).select_option(str(company))
            expect(page.locator('body')).to_contain_text('ruim.xml')
            assert not errors,errors
            print('PASS: portal cliente autenticado, envio ZIP, erros individuais e histórico persistido após recarga; sem erros JS')
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10);listener.close()
