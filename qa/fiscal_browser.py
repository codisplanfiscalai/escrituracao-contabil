"""Synthetic persistent fiscal tabs, manual edit/review and service/mobile regression."""
from pathlib import Path
import argparse
import shutil
import socket
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.server.runtime import PortalServer
from src.persistence import AccountingStore
from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        path=Path(temporary)/'synthetic.sqlite3'
        server=PortalServer(path,port)
        identity=server.app.state.identity
        identity.setup({'token':identity.setup_secret,'name':'Operador fictício','email':'fiscal@example.test','password':'synthetic-fiscal-password'},'local')
        with AccountingStore(path) as store:
            company=store.create_company('Empresa fictícia','TEST','TEST')['id']
            period=store.create_period(company,'2026-08','2026-09')['id']
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        deadline=time.monotonic()+15
        while not server.server.started:
            if time.monotonic()>deadline:raise RuntimeError('Servidor não iniciou')
            time.sleep(.05)
        try:
            with sync_playwright() as p:
                executable=None if Path(p.chromium.executable_path).exists() else (shutil.which('chromium') or shutil.which('google-chrome'))
                browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1100})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{port}')
                page.get_by_label('E-mail',exact=True).fill('fiscal@example.test')
                page.get_by_label('Senha',exact=True).fill('synthetic-fiscal-password')
                page.get_by_role('button',name='Entrar no ambiente').click()
                page.get_by_role('link',name='Lançamento fiscal',exact=True).click()
                frame=page.frame_locator('iframe');frame.locator('#company').select_option(str(company))
                frame.locator('#period').select_option(str(period))
                expect(frame.locator('#fiscal-period-status')).to_contain_text('2026-09')
                frame.get_by_role('button',name='Nova guia manual',exact=True).click()
                form=frame.locator('#fiscal-form')
                for name,value in [('number','100'),('series','1'),('issued_date','2026-08-15'),('entry_date','2026-09-01'),('posting_date','2026-09-03'),('total','100,30')]:
                    form.locator('[name="'+name+'"]').fill(value)
                form.locator('#fiscal-reason').fill('Entrada fictícia emitida em agosto.')
                form.get_by_role('button',name='Salvar rascunho da guia',exact=True).click()
                expect(frame.locator('#fiscal-draft-state')).to_contain_text('Guia salva')
                page.get_by_role('link',name='Visão geral',exact=True).click()
                page.get_by_role('link',name='Lançamento fiscal',exact=True).click()
                frame=page.frame_locator('iframe');form=frame.locator('#fiscal-form')
                expect(form.locator('[name="number"]')).to_have_value('100')
                expect(form.locator('[name="issued_date"]')).to_have_value('2026-08-15')
                form.get_by_role('button',name='Salvar versão fiscal',exact=True).click()
                try:
                    expect(frame.get_by_role('heading',name='Ficha #1 · v1 · rascunho',exact=True)).to_be_visible(timeout=8000)
                except Exception:
                    print('Fiscal UI diagnostic:',frame.locator('#status').inner_text(),frame.locator('#fiscal-draft-state').inner_text(),errors,flush=True)
                    print('Invalid fields:',form.locator(':invalid').evaluate_all('(nodes)=>nodes.map(n=>({name:n.name,value:n.value,message:n.validationMessage}))'),flush=True)
                    raise
                review=frame.locator('#fiscal-entries form').first
                review.get_by_label('Motivo da revisão fiscal',exact=True).fill('Datas e fonte conferidas no teste.')
                review.get_by_role('checkbox').check()
                review.get_by_role('button',name='Revisar ficha #1',exact=True).click()
                frame.get_by_role('heading',name='Ficha #1 · v1 · revisado',exact=True).wait_for()
                frame.get_by_role('button',name='Editar ficha #1',exact=True).click()
                expect(frame.locator('#fiscal-tabs button[aria-selected="true"]')).to_have_text('Editar #1')
                form.locator('[name="total"]').fill('110,30');form.locator('#fiscal-reason').fill('Correção fictícia.')
                form.get_by_role('button',name='Salvar versão fiscal',exact=True).click()
                frame.get_by_role('heading',name='Ficha #1 · v2 · rascunho',exact=True).wait_for()
                frame.get_by_role('button',name='Nova guia manual',exact=True).click()
                expect(frame.locator('#fiscal-tabs button[aria-selected="true"]')).to_have_text('Novo lançamento 3')
                form.locator('[name="operation"]').select_option('servico_tomado')
                expect(form.locator('[name="model"]')).to_have_value('SERVICO')
                for name,value in [('number','SERV-1'),('issued_date','2026-09-15'),('entry_date','2026-09-15'),('posting_date','2026-09-15'),('total','90,00'),('service_code','INFORMADO'),('iss_base','90,00'),('iss_amount','4,50')]:
                    form.locator('[name="'+name+'"]').fill(value)
                form.locator('#fiscal-reason').fill('Serviço fictício, ISS informado sem cálculo.')
                form.get_by_role('button',name='Salvar versão fiscal',exact=True).click()
                try:
                    frame.get_by_role('heading',name='Ficha #2 · v1 · rascunho',exact=True).wait_for(timeout=8000)
                except Exception:
                    print('Service diagnostic:',frame.locator('#status').inner_text(),frame.locator('#fiscal-draft-state').inner_text(),flush=True)
                    print(form.locator(':invalid').evaluate_all('(nodes)=>nodes.map(n=>({name:n.name,value:n.value,message:n.validationMessage}))'),flush=True)
                    raise
                if args.screenshots:page.screenshot(path=str(args.screenshots/'fiscal-desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                expect(page.locator('.sidebar')).to_have_css('transform','matrix(1, 0, 0, 1, -246, 0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                inner=page.frames[1]
                assert inner.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                if args.screenshots:page.screenshot(path=str(args.screenshots/'fiscal-mobile.png'),full_page=True)
                assert not errors,errors
                with AccountingStore(path) as store:
                    entries=store.list_fiscal_entries(company)
                    assert len(entries)==2
                    one=next(e for e in entries if e['id']==1)
                    assert one['history'][1]['data']['total']=='100.30'
                    assert one['current']['data']['total']=='110.30'
                    assert entries[0]['current']['data']['iss_amount']=='4.50'
                browser.close()
        finally:
            server.shutdown();thread.join(15);server.server_close()
    print('PASS: fiscal persistent tabs, August/September dates, manual inclusion/edit/review, service fields, mobile and no browser errors')


if __name__=='__main__':main()
