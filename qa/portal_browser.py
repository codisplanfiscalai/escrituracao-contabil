"""Regressão visual e funcional com dados sintéticos descartáveis."""
import argparse
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.server.runtime import PortalServer
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',default='/tmp/escritura-portal-qa');args=parser.parse_args()
    screenshots=Path(args.screenshots);screenshots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=PortalServer(Path(temporary)/'accounting.sqlite3',port)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        deadline=time.monotonic()+15
        while not server.server.started:
            if time.monotonic()>deadline:raise RuntimeError('Servidor não iniciou')
            time.sleep(.05)
        try:
            with sync_playwright() as p:
                executable=None if Path(p.chromium.executable_path).exists() else (shutil.which('chromium') or shutil.which('google-chrome'))
                browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1,locale='pt-BR',reduced_motion='reduce')
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{port}')
                page.get_by_role('heading',name='Configure seu ambiente').wait_for()
                page.screenshot(path=str(screenshots/'primeiro-acesso.png'),full_page=True,animations="disabled")
                page.get_by_label('Chave de instalação').fill(server.app.state.identity.setup_secret)
                page.get_by_label('Nome do administrador').fill('Administrador de teste')
                page.get_by_label('E-mail',exact=True).fill('admin@example.test')
                page.get_by_label('Senha',exact=True).fill('synthetic-portal-password')
                page.get_by_role('button',name='Concluir configuração').click()
                page.get_by_role('heading',name='Acesse sua conta').wait_for()
                page.screenshot(path=str(screenshots/'login.png'),full_page=True,animations="disabled")
                page.get_by_role('button',name='Entrar no ambiente').click()
                page.get_by_role('heading',name='Visão geral',exact=True).wait_for()
                page.get_by_role('link',name='Empresas',exact=True).click()
                page.get_by_label('Nome',exact=True).fill('Empresa de demonstração')
                page.get_by_label('Código da empresa no Prosoft').fill('TEST')
                page.get_by_label('Código do plano no Prosoft').fill('DEMO')
                page.get_by_role('button',name='Cadastrar empresa',exact=True).click()
                page.get_by_text('Empresa cadastrada.').wait_for()
                page.get_by_role('link',name='Visão geral',exact=True).click()
                page.get_by_role('heading',name='Visão geral',exact=True).wait_for()
                page.get_by_text('Empresa de demonstração',exact=True).wait_for()
                page.screenshot(path=str(screenshots/'painel.png'),full_page=True,animations="disabled")
                page.get_by_role('link',name='Usuários',exact=True).click()
                page.get_by_role('button',name='Novo usuário',exact=False).click()
                modal=page.get_by_role('dialog')
                modal.get_by_label('Nome',exact=True).fill('Cliente de demonstração')
                modal.get_by_label('E-mail',exact=True).fill('client@example.test')
                modal.get_by_label('Senha inicial').fill('synthetic-client-password')
                modal.get_by_label('Empresa de demonstração',exact=True).check()
                modal.get_by_role('button',name='Salvar usuário').click()
                page.get_by_text('Cliente de demonstração',exact=True).wait_for()
                page.screenshot(path=str(screenshots/'usuarios.png'),full_page=True,animations="disabled")
                page.get_by_role('link',name='Competências',exact=True).click()
                frame=page.frame_locator('iframe')
                frame.get_by_label('Empresa de trabalho',exact=True).select_option(label='Empresa de demonstração')
                frame.get_by_label('Competência de referência',exact=True).fill('2026-08')
                frame.get_by_label('Competência de processamento',exact=True).fill('2026-09')
                frame.get_by_role('button',name='Cadastrar período',exact=True).click()
                frame.locator('#period option').nth(1).wait_for(state='attached')
                period=frame.locator('#period option').nth(1).get_attribute('value')
                frame.get_by_label('Período de trabalho',exact=True).select_option(period)
                page.get_by_role('link',name='Documentos',exact=True).click()
                frame=page.frame_locator('iframe')
                from playwright.sync_api import expect
                expect(frame.get_by_label('Empresa de trabalho',exact=True)).to_have_value('1')
                expect(frame.get_by_label('Período de trabalho',exact=True)).to_have_value(period)
                expect(frame.get_by_label('Empresa de trabalho',exact=True)).to_be_in_viewport()
                frame.get_by_role('heading',name='Receber arquivo XML ou SPED').wait_for()
                page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(screenshots/'documentos.png'),full_page=True,animations="disabled")
                expect(frame.get_by_label('Empresa de trabalho',exact=True)).to_have_value('1')
                expect(frame.get_by_label('Período de trabalho',exact=True)).to_have_value(period)
                page.get_by_role('link',name='Histórico contábil',exact=True).click()
                frame=page.frame_locator('iframe')
                frame.get_by_role('heading',name='Histórico de operações',exact=True).wait_for()
                expect(frame.get_by_label('Empresa de trabalho',exact=True)).to_have_value('1')
                page.get_by_role('link',name='Configurações',exact=True).click()
                page.get_by_label('Nome de exibição').fill('Escritura · Escritório')
                page.get_by_role('button',name='Salvar configurações',exact=True).click()
                page.get_by_text('Configuração salva.').wait_for()
                page.get_by_role('link',name='Visão geral',exact=True).click()
                page.set_viewport_size({'width':390,'height':844})
                page.get_by_role('button',name='Abrir menu',exact=True).click()
                page.get_by_role('link',name='Portal do cliente',exact=True).click()
                page.get_by_role('heading',name='Portal do cliente',exact=True).wait_for()
                page.screenshot(path=str(screenshots/'mobile.png'),full_page=True,animations="disabled")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'),'Overflow horizontal no mobile'
                page.set_viewport_size({'width':1440,'height':1000})
                page.get_by_role('button',name='Sair',exact=True).click()
                page.get_by_role('heading',name='Acesse sua conta').wait_for()
                page.get_by_label('E-mail',exact=True).fill('client@example.test')
                page.get_by_label('Senha',exact=True).fill('synthetic-client-password')
                page.get_by_role('button',name='Entrar no ambiente').click()
                page.get_by_role('heading',name='Visão geral',exact=True).wait_for()
                assert page.get_by_role('link',name='Usuários',exact=True).count()==0
                assert page.get_by_role('link',name='Escrituração',exact=True).count()==0
                page.get_by_role('link',name='Portal do cliente',exact=True).click()
                page.get_by_role('heading',name='Portal do cliente',exact=True).wait_for()
                page.get_by_label('Período',exact=True).select_option(period)
                page.get_by_label('Tipo',exact=True).select_option('SPED')
                page.get_by_label('Documento',exact=True).set_input_files({'name':'amostra-sintetica.txt','mimeType':'text/plain','buffer':b'|0000|DADOS SINTETICOS PARA PRESERVACAO|\r\n'})
                with page.expect_response(lambda response:response.url.endswith('/api/v1/client/files') and response.request.method=='POST') as uploaded:
                    page.get_by_role('button',name='Enviar documento',exact=True).click()
                assert uploaded.value.status==200,uploaded.value.text()
                page.get_by_role('status').filter(has_text='Documento recebido e origem preservada.').wait_for()
                page.get_by_role('cell',name='amostra-sintetica.txt',exact=True).wait_for()
                page.screenshot(path=str(screenshots/'cliente.png'),full_page=True,animations="disabled")
                assert not errors,errors
                browser.close()
                print('PASS: setup, login, dashboard, company, users, accounting iframe/context, settings, mobile, client scope/upload; no browser errors')
        except Exception:
            try:
                page.screenshot(path=str(screenshots/'falha.png'),full_page=True)
                print('Browser errors:',errors)
            except Exception:pass
            raise
        finally:
            server.shutdown();thread.join(timeout=10);server.server_close()

if __name__=='__main__':main()
