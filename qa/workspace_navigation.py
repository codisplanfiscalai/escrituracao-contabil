"""All menu resources open in tabs; company/cycle drafts survive navigation and failures."""
from pathlib import Path
import argparse
from browser_support import scenario
from playwright.sync_api import expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    with scenario() as s:
        page,frame=s['page'],s['frame']
        def nav(label):
            page.locator('.sidebar').get_by_role('link',name=label,exact=True).click()
            expect(page.locator('.page-heading h1')).to_have_text(label)
        def idle():expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.locator('#period').select_option(str(s['first']));idle()
        frame.get_by_role('button',name='+ Lançamento manual',exact=True).click();idle()
        reference=frame.locator('#operation-reference');reference.fill('Alfa setembro durável')
        frame.get_by_role('button',name='Preservar rascunho da guia',exact=True).click();idle()
        page.evaluate("document.querySelector('#workspace-frame').contentWindow.qaInstance='original'")
        # Every resource, including administration and account, gets its own guide.
        resources=page.locator('.sidebar nav a').evaluate_all('(items)=>items.map(a=>({href:a.getAttribute("href"),label:a.textContent.replace(/•/g,"").trim().slice(1).trim()}))')
        for resource in resources:
            link=page.locator('.sidebar nav a[href="'+resource['href']+'"]')
            link.click()
            expect(page.locator('.activity-tabs a[href="'+resource['href']+'"]')).to_have_count(1)
            expect(page.locator('.alert.error')).to_have_count(0)
        nav('Escrituração');expect(reference).to_have_value('Alfa setembro durável')
        assert page.evaluate("document.querySelector('#workspace-frame').contentWindow.qaInstance")=='original'
        # General form and users survive switching; roles must not clear users.
        nav('Empresas');companyform=page.get_by_label('Nome',exact=True)
        companyform.fill('Cadastro em andamento')
        nav('Usuários');expect(page.locator('#content > section:visible tbody')).to_contain_text('Operador sintético')
        nav('Perfis e permissões');nav('Usuários');expect(page.locator('section:visible tbody')).to_contain_text('Operador sintético')
        nav('Empresas');expect(companyform).to_have_value('Cadastro em andamento')
        # Portal client company selection is independent from bookkeeping.
        nav('Portal do cliente');page.get_by_label('Empresa',exact=True).select_option(str(s['other']))
        nav('Escrituração');expect(frame.locator('#company')).to_have_value(str(s['company']))
        # Distinct work months and companies retain separate durable incomplete forms.
        frame.locator('#period').select_option(str(s['second']));idle()
        expect(reference).to_have_count(0)
        frame.get_by_role('button',name='+ Lançamento manual',exact=True).click();idle();reference.fill('Alfa outubro')
        frame.get_by_role('button',name='Preservar rascunho da guia',exact=True).click();idle()
        frame.locator('#company').select_option(str(s['other']));idle()
        expect(reference).to_have_count(0)
        frame.locator('#company').select_option(str(s['company']));idle()
        frame.locator('#period').select_option(str(s['first']));idle();expect(reference).to_have_value('Alfa setembro durável')
        # Failed persistence blocks navigation, keeping the current form intact.
        page.route('**/api/work-tabs',lambda r:r.abort('failed') if r.request.method=='POST' else r.continue_())
        reference.fill('Alteração ainda não salva')
        page.locator('.sidebar').get_by_role('link',name='Recepção',exact=True).click()
        expect(page.locator('.alert.error')).to_contain_text('Rascunho pendente')
        expect(reference).to_have_value('Alteração ainda não salva')
        page.unroute('**/api/work-tabs')
        nav('Recepção');nav('Escrituração');expect(reference).to_have_value('Alteração ainda não salva')
        page.reload();page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click();idle()
        expect(reference).to_have_value('Alteração ainda não salva')
        # The server may commit before a response is lost. Recover the saved attempt,
        # including after reload, instead of generating another manual operation.
        frame.locator('#operation-reason').fill('Tentativa com resposta perdida')
        def lost_response(route):
            if route.request.method=='POST':
                response=route.fetch();assert response.ok,response.text();route.abort('failed')
            else:route.continue_()
        page.route('**/api/work-operations',lost_response)
        frame.get_by_role('button',name='Salvar versão',exact=True).click()
        expect(frame.locator('.alert.error')).to_be_visible()
        page.unroute('**/api/work-operations')
        page.reload();page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click();idle()
        frame.get_by_role('button',name='Salvar versão',exact=True).click();idle()
        expect(frame.get_by_role('status')).to_contain_text('Resposta recuperada')
        from src.persistence import AccountingStore
        with AccountingStore(s['path']) as store:
            assert len(store.work_operations(s['company'],s['first']))==1
        nav('Empresas');expect(companyform).to_have_value('Cadastro em andamento')
        nav('Escrituração')
        for width in [1440,1024,768,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
            assert frame.locator('html').evaluate('(e)=>e.scrollWidth<=innerWidth+1'),width
            if args.screenshots:page.screenshot(path=str(args.screenshots/f'guides-{width}.png'),full_page=True)
        print(f'PASS: {len(resources)} recursos em guias; usuários/perfis; formulários; contexto cliente separado; rascunhos por empresa/mês; reload; interrupção e resposta perdida recuperadas sem duplicar; 1440/1024/768/390/320')
if __name__=='__main__':main()
