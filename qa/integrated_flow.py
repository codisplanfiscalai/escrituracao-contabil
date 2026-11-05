"""Nova jornada real, com dados sintéticos, nos modos local e autenticado."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1]/'tests')]
from src.persistence import AccountingStore
from src.local_app import LocalServer
from src.server.runtime import PortalServer
from test_persistence import fake_accounts, fake_xml, BUYER
from playwright.sync_api import sync_playwright, expect


def run(mode):
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'synthetic.sqlite3'
        with AccountingStore(path) as s:
            company=s.create_company('Empresa inteiramente sintética',cnpj=BUYER)['id']
            plan=s.import_plan(company,'Plano sintético',fake_accounts())['id']
            accounts={r['code']:r['id'] for r in s.list_accounts(company,plan)}
            cycle=s.save_work_cycle(company,'2026-08','2026-09',plan,'Configuração sintética')
            for kind in ['entrada','pagamento']:
                s.save_work_policy(company,plan,kind,'2026-08','Política '+kind,accounts['1.1.1'],accounts['2.1'],'Aprovação sintética',True)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=PortalServer(path,port) if mode=='portal' else LocalServer(path,port)
        if mode=='portal':
            identity=server.app.state.identity
            identity.setup({'token':identity.setup_secret,'name':'Operador sintético','email':'journey@example.test','password':'synthetic-integrated-password'},'local')
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
                    page.get_by_label('E-mail',exact=True).fill('journey@example.test')
                    page.get_by_label('Senha',exact=True).fill('synthetic-integrated-password')
                    page.get_by_role('button',name='Entrar no ambiente').click()
                    page.get_by_role('link',name='Escrituração',exact=True).first.click()
                    frame=page.frame_locator('#workspace-frame')
                else:frame=page
                def idle():
                    expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
                    expect(frame.locator('.alert.error')).to_have_count(0)
                def nav(label):
                    idle()
                    if mode=='portal':page.locator('.sidebar').get_by_role('link',name=label,exact=True).click()
                    else:frame.locator('.work-nav').get_by_role('button',name=label,exact=True).click()
                    expected={'Recepção':'Recepção e caixa de entrada','Livros e relatórios':'Livros e relatórios','Encerramento':'Encerramento da competência','Histórico':'Histórico preservado e migração','Histórico contábil':'Histórico preservado e migração'}
                    expect(frame.get_by_role('heading',name=expected.get(label,label),exact=True)).to_be_visible()
                    idle()
                def post():
                    frame.locator('#operation-reason').fill('Conferência e escrituração sintéticas')
                    frame.get_by_role('button',name='Salvar versão',exact=True).click();idle()
                    frame.get_by_role('button',name='Conferir versão',exact=True).click();idle()
                    frame.get_by_role('button',name='Escriturar',exact=True).click();idle()
                    expect(frame.get_by_role('status')).to_contain_text('Operação escriturada')
                idle();nav('Recepção')
                frame.locator('#source-files').set_input_files({'name':'ficticio.xml','mimeType':'application/xml','buffer':fake_xml()})
                frame.get_by_role('button',name='Receber arquivos',exact=True).click();idle()
                frame.get_by_label('Motivo da organização / retirada',exact=True).fill('Conferido para setembro')
                frame.get_by_role('button',name='Organizar em 2026-09',exact=True).click();idle()
                nav('Escrituração');frame.get_by_role('button',name='Escriturar documento',exact=True).click();idle()
                frame.get_by_label('Política',exact=True).select_option(label='Política entrada · v1')
                frame.get_by_role('button',name='Aplicar contas da política',exact=True).click()
                frame.locator('#operation-reference').fill('Documento sintético conferido')
                post()
                # Opening is an explicit declaration, not an inferred zero.
                frame.get_by_role('button',name='Saldos iniciais',exact=True).click();idle()
                frame.locator('#operation-reference').fill('Abertura sintética zero')
                frame.get_by_label('Confirmo que os saldos iniciais são zero',exact=True).check();post()
                # Incomplete form survives tab switches and a complete browser reload.
                frame.get_by_role('button',name='+ Lançamento manual',exact=True).click();idle()
                frame.locator('#operation-reference').fill('Rascunho persistente sem valor')
                frame.get_by_role('button',name='Preservar rascunho da guia',exact=True).click();idle()
                nav('Financeiro');nav('Escrituração')
                expect(frame.locator('#operation-reference')).to_have_value('Rascunho persistente sem valor')
                page.reload()
                if mode=='portal':
                    page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click();frame=page.frame_locator('#workspace-frame')
                idle()
                frame.locator('.draft-tabs').get_by_role('button',name='Manual / ajuste',exact=False).click()
                expect(frame.locator('#operation-reference')).to_have_value('Rascunho persistente sem valor')
                # Close incomplete tab: draft preserved, no fake ledger movement.
                frame.locator('.draft-tabs').get_by_role('button',name='Manual / ajuste',exact=False).locator('span').click();idle()
                nav('Histórico contábil' if mode=='portal' else 'Histórico')
                frame.get_by_role('button',name='Reabrir guia',exact=True).click();idle()
                expect(frame.locator('#operation-reference')).to_have_value('Rascunho persistente sem valor')
                frame.locator('.draft-tabs').get_by_role('button',name='Manual / ajuste',exact=False).locator('span').click();idle()
                nav('Financeiro')
                frame.get_by_role('button',name='Preparar liquidação',exact=True).first.click()
                frame.get_by_label('Política',exact=True).select_option(label='Política pagamento')
                frame.get_by_label('Valor',exact=True).fill('10.10')
                frame.get_by_label('Data',exact=True).fill('2026-09-20')
                frame.get_by_role('textbox',name='Referência',exact=True).fill('Pagamento parcial sintético')
                frame.get_by_role('button',name='Abrir ficha da liquidação',exact=True).click();idle();post()
                nav('Financeiro');expect(frame.locator('b').filter(has_text='30.00').first).to_be_visible()
                nav('Livros e relatórios')
                frame.get_by_label('Motivo da exportação',exact=True).fill('Conferência sintética dos livros')
                frame.get_by_role('button',name='Conferir e preservar exportação operacional',exact=True).click();idle()
                with page.expect_download() as event:frame.get_by_role('link',name='escrituracao.json',exact=True).click()
                artifact=event.value;book=json.loads(Path(artifact.path()).read_text())
                assert book['totals']['debit']=='110.40',book['totals']
                assert book['totals']['debit']==book['totals']['credit']
                assert len(book['diary'])==4 and len(book['fiscal_book'])==1
                nav('Encerramento');frame.locator('section:visible').get_by_label('Motivo',exact=True).fill('Encerramento sintético')
                frame.get_by_role('button',name='Encerrar competência',exact=True).click();idle()
                expect(frame.get_by_role('button',name='Reabrir com motivo')).to_be_visible()
                if errors:raise AssertionError(errors)
                browser.close()
            with AccountingStore(path) as s:
                assert len(s.work_operations(company,cycle['id']))==3
                assert s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0]==4
                assert not s.list_accounting_batches(company)
                assert not s.list_fiscal_entries(company)
                assert not s.list_manual_journals(company)
                assert s.db.execute('PRAGMA foreign_key_check').fetchall()==[]
            print(f'PASS {mode}: recepção → organização → operação → conferência → escrituração → abertura → rascunhos/reload → liquidação → livros/download → encerramento; sem gravadores antigos')
        finally:server.shutdown();thread.join(10);server.server_close()

if __name__=='__main__':
    for mode in ['local','portal']:run(mode)
