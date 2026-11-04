"""Synthetic regression: persistent activity tabs, scoped drafts and interrupted saves."""
from pathlib import Path
import argparse
import shutil
import socket
import sys
import tempfile
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.server.runtime import PortalServer
from src.persistence import AccountingStore
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--screenshots', type=Path); args = parser.parse_args()
    if args.screenshots: args.screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        path = Path(temporary) / 'synthetic.sqlite3'
        server = PortalServer(path, port)
        identity = server.app.state.identity
        identity.setup({'token': identity.setup_secret, 'name': 'Operador fictício', 'email': 'ui@example.test', 'password': 'synthetic-ui-password'}, 'local')
        with AccountingStore(path) as store:
            company = store.create_company('Empresa Alfa sintética', 'ALFA', 'TEST')['id']
            other = store.create_company('Empresa Beta sintética', 'BETA', 'TEST')['id']
            first = store.create_period(company, '2026-08', '2026-09')['id']
            second = store.create_period(company, '2026-09', '2026-10')['id']
            third = store.create_period(other, '2026-08', '2026-09')['id']
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        deadline = time.monotonic() + 15
        while not server.server.started:
            if time.monotonic() > deadline: raise RuntimeError('Servidor não iniciou')
            time.sleep(.05)
        try:
            with sync_playwright() as p:
                executable = None if Path(p.chromium.executable_path).exists() else shutil.which('chromium')
                browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
                page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce', locale='pt-BR')
                errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{port}')
                page.get_by_label('E-mail', exact=True).fill('ui@example.test')
                page.get_by_label('Senha', exact=True).fill('synthetic-ui-password')
                page.get_by_role('button', name='Entrar no ambiente').click()
                page.get_by_role('link', name='Escrituração', exact=True).click()
                frame = page.frame_locator('#workspace-frame')
                def idle():
                    expect(frame.locator('main')).to_have_attribute('aria-busy', 'false')
                def scope(cid, pid):
                    frame.locator('#company').select_option(str(cid)); idle()
                    frame.locator('#period').select_option(str(pid)); idle()
                scope(company, first)
                page.evaluate("document.querySelector('#workspace-frame').contentWindow.qaInstance='original'")
                reason = frame.locator('#accounting-form [name=reason]')
                memo = frame.locator('[data-field=memo]').first
                reason.fill('Rascunho Alfa setembro'); memo.fill('Histórico preservado')
                frame.locator('[data-field=amount]').first.fill('100,30')
                key = frame.locator('[name=request_key]').input_value()
                frame.get_by_role('button', name='Adicionar partida', exact=True).click()
                expect(frame.locator('.posting-line')).to_have_count(3)
                for activity in ['Documentos', 'Conciliação', 'Lançamento fiscal', 'Configurações', 'Escrituração']:
                    page.get_by_role('link', name=activity, exact=True).first.click()
                    page.get_by_role('heading', name=activity, exact=True).wait_for()
                page.go_back(); expect(page.get_by_role('heading', name='Configurações', exact=True)).to_be_visible()
                page.go_forward(); expect(page.get_by_role('heading', name='Escrituração', exact=True)).to_be_visible()
                page.get_by_role('link', name='Atividade Documentos', exact=True).click()
                expect(page.get_by_role('heading', name='Documentos', exact=True)).to_be_visible()
                page.get_by_role('link', name='Atividade Escrituração', exact=True).click()
                expect(reason).to_have_value('Rascunho Alfa setembro'); expect(memo).to_have_value('Histórico preservado')
                assert page.evaluate("document.querySelector('#workspace-frame').contentWindow.qaInstance") == 'original'
                expect(page.locator('.activity-tabs>div')).to_have_count(4)
                frame.locator('#period').select_option(str(second)); idle()
                expect(reason).to_have_value(''); reason.fill('Rascunho Alfa outubro')
                frame.locator('#posting-mode').select_option('json')
                frame.locator('#posting-json-input').fill('[{"rascunho":"ainda incompleto"}]')
                scope(other, third); expect(reason).to_have_value(''); reason.fill('Rascunho Beta')
                scope(company, first)
                expect(reason).to_have_value('Rascunho Alfa setembro'); expect(memo).to_have_value('Histórico preservado')
                expect(frame.locator('.posting-line')).to_have_count(3)
                expect(frame.locator('[name=request_key]')).to_have_value(key)
                frame.locator('#refresh').click(); idle(); expect(reason).to_have_value('Rascunho Alfa setembro')
                frame.locator('#period').select_option(str(second)); idle()
                expect(frame.locator('#posting-mode')).to_have_value('json')
                expect(frame.locator('#posting-json-input')).to_have_value('[{"rascunho":"ainda incompleto"}]')
                frame.locator('#period').select_option(''); idle(); reason.fill('Rascunho aguardando competência')
                frame.locator('#period').select_option(str(first)); idle()
                expect(reason).to_have_value('Rascunho Alfa setembro')
                frame.locator('#period').select_option(''); idle()
                expect(reason).to_have_value('Rascunho aguardando competência')
                page.reload(); page.get_by_role('link', name='Escrituração', exact=True).click()
                scope(company, first); expect(reason).to_have_value('Rascunho Alfa setembro')
                expect(memo).to_have_value('Histórico preservado'); expect(frame.locator('[name=request_key]')).to_have_value(key)
                page.get_by_role('link', name='Lançamento fiscal', exact=True).first.click()
                frame.locator('#fiscal-new').click()
                fiscal = frame.locator('#fiscal-form')
                fiscal.locator('[name=number]').fill('FICTICIO-100')
                for operation, participant in [('saida', 'Cliente'), ('servico_tomado', 'Prestador do serviço'), ('servico_prestado', 'Tomador do serviço'), ('entrada', 'Fornecedor')]:
                    fiscal.locator('[name=operation]').select_option(operation)
                    expect(frame.locator('#fiscal-participant-label')).to_have_text(participant)
                    expect(fiscal.locator('[name=service_code]')).to_be_visible() if operation.startswith('servico') else expect(fiscal.locator('[name=service_code]')).to_be_hidden()
                fiscal.locator('[name=notes]').fill('Preservar durante interrupção')
                expect(frame.locator('#fiscal-draft-state')).to_contain_text('Guia salva')
                page.route('**/api/fiscal-workspaces', lambda route: route.abort('failed') if route.request.method == 'POST' else route.continue_())
                page.get_by_role('link', name='Documentos', exact=True).first.click()
                expect(page.get_by_role('alert')).to_contain_text('Rascunho pendente')
                expect(page.get_by_role('heading', name='Lançamento fiscal', exact=True)).to_be_visible()
                expect(fiscal.locator('[name=notes]')).to_have_value('Preservar durante interrupção')
                frame.locator('#period').select_option(str(second))
                expect(frame.locator('#period')).to_have_value(str(first))
                expect(frame.locator('#status')).to_contain_text('contexto mantido')
                expect(fiscal.locator('[name=notes]')).to_have_value('Preservar durante interrupção')
                page.unroute('**/api/fiscal-workspaces')
                page.get_by_role('link', name='Documentos', exact=True).first.click()
                expect(page.get_by_role('heading', name='Documentos', exact=True)).to_be_visible()
                page.get_by_role('link', name='Lançamento fiscal', exact=True).first.click()
                expect(fiscal.locator('[name=number]')).to_have_value('FICTICIO-100')
                if args.screenshots: page.screenshot(path=str(args.screenshots/'workspace-desktop.png'), full_page=True)
                for width in [1440, 1024, 768, 390, 320]:
                    page.set_viewport_size({'width': width, 'height': 900})
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), f'Portal overflow: {width}'
                    assert frame.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth+1'), f'Workspace overflow: {width}'
                    if args.screenshots and width == 390: page.screenshot(path=str(args.screenshots/'workspace-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1000})
                page.get_by_role('button', name='Fechar atividade Lançamento fiscal', exact=True).click()
                expect(page.get_by_role('heading', name='Documentos', exact=True)).to_be_visible()
                page.get_by_role('link', name='Lançamento fiscal', exact=True).first.click()
                expect(fiscal.locator('[name=number]')).to_have_value('FICTICIO-100')
                page.get_by_role('button', name='Sair', exact=True).click()
                page.get_by_role('heading', name='Acesse sua conta').wait_for()
                assert page.evaluate("Object.keys(sessionStorage).filter(k=>k.startsWith('escritura:posting-drafts:')).length") == 0
                assert not errors, errors
                browser.close()
                print('PASS: persistent iframe/activity tabs; accounting drafts separated by company/period, visual/JSON, refresh/reload; adaptive fiscal form; failed save blocks navigation and recovers; 1440/1024/768/390/320 responsive; close/reopen; logout clears recovery; no JS errors')
        finally:
            server.shutdown(); thread.join(timeout=10); server.server_close()


if __name__ == '__main__': main()
