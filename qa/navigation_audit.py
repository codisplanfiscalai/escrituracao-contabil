"""Navigation paths and resource guides beyond the main menu, using synthetic data."""
from browser_support import scenario
from playwright.sync_api import expect
import base64
from test_persistence import fake_xml


def portal_paths():
    with scenario() as s:
        page,frame=s['page'],s['frame']
        origin=page.url.split('#')[0].rstrip('/')
        identity=page.request.get(origin+'/api/v1/auth/me').json()['data']['user']['id']
        def nav(label):
            page.locator('.sidebar').get_by_role('link',name=label,exact=True).click()
            expect(page.locator('.page-heading h1')).to_have_text(label)
        nav('Usuários')
        page.get_by_role('button',name='+ Novo usuário',exact=True).click()
        first=page.locator('[data-editor="user-editor/new"]')
        expect(first).to_be_visible();expect(page.get_by_role('dialog')).to_have_count(0)
        first.get_by_label('Nome',exact=True).fill('Rascunho de usuário sintético')
        first.get_by_label('E-mail',exact=True).fill('draft@example.test')
        first.get_by_label('Senha inicial',exact=True).fill('not-persisted-synthetic-secret')
        nav('Perfis e permissões')
        page.get_by_role('button',name='+ Novo perfil',exact=True).click()
        role=page.locator('[data-editor="role-editor/new"]')
        expect(role).to_be_visible();expect(page.get_by_role('dialog')).to_have_count(0)
        role.get_by_label('Nome do perfil',exact=True).fill('Perfil sintético em trabalho')
        role.locator('input[type=checkbox]').first.check()
        nav('Usuários')
        page.get_by_role('row').filter(has_text='Operador sintético').get_by_role('button',name='Editar',exact=True).click()
        expect(page.locator('.editor-guide:visible')).to_have_attribute('data-editor','user-editor/'+identity)
        page.locator('.activity-tabs a[href="#/user-editor/new"]').click()
        expect(first.get_by_label('Nome',exact=True)).to_have_value('Rascunho de usuário sintético')
        expect(first.get_by_label('Senha inicial',exact=True)).to_have_value('not-persisted-synthetic-secret')
        page.reload()
        expect(first).to_be_visible()
        expect(first.get_by_label('Nome',exact=True)).to_have_value('Rascunho de usuário sintético')
        expect(first.get_by_label('Senha inicial',exact=True)).to_have_value('')
        assert page.evaluate("(id)=>!localStorage.getItem('escritura-portal:'+id).includes('not-persisted-synthetic-secret')",identity)
        page.locator('.activity-tabs a[href="#/role-editor/new"]').click()
        expect(role.get_by_label('Nome do perfil',exact=True)).to_have_value('Perfil sintético em trabalho')
        expect(role.locator('input[type=checkbox]').first).to_be_checked()
        page.locator('.activity-tabs a[href="#/user-editor/new"]').click()
        page.go_back();expect(role).to_be_visible()
        page.go_forward();expect(first).to_be_visible()
        previous=page.url
        skip=page.get_by_role('link',name='Ir para o conteúdo',exact=True)
        skip.focus();skip.press('Enter')
        assert page.url==previous
        expect(page.locator('#content')).to_be_focused()
        # Close/reopen the editor without replacing its unfinished form.
        page.get_by_role('button',name='Fechar atividade Novo usuário',exact=True).click()
        nav('Usuários');page.get_by_role('button',name='+ Novo usuário',exact=True).click()
        expect(first.get_by_label('Nome',exact=True)).to_have_value('Rascunho de usuário sintético')
        page.locator('.activity-tabs a[href="#/role-editor/new"]').click()
        role.get_by_role('button',name='Salvar perfil',exact=True).click()
        expect(page.locator('.page-heading h1')).to_have_text('Perfis e permissões')
        expect(page.locator('.role-grid article').filter(has_text='Perfil sintético em trabalho')).to_be_visible()
        page.locator('.activity-tabs a[href="#/user-editor/new"]').click()
        expect(first.get_by_label('Nome',exact=True)).to_have_value('Rascunho de usuário sintético')
        nav('Minha conta e 2FA')
        security=page.locator('#content > section:visible')
        security.get_by_label('Senha atual',exact=True).fill('synthetic-browser-password')
        security.get_by_role('button',name='Configurar autenticador',exact=True).click()
        modal=page.get_by_role('dialog',name='Configurar 2FA',exact=True)
        expect(modal).to_be_visible()
        assert page.locator('.workspace').evaluate('(node)=>node.inert')
        modal.get_by_role('button',name='Confirmar ativação',exact=True).focus()
        page.keyboard.press('Tab');expect(modal.get_by_role('button',name='Fechar',exact=True)).to_be_focused()
        page.keyboard.press('Shift+Tab');expect(modal.get_by_role('button',name='Confirmar ativação',exact=True)).to_be_focused()
        page.keyboard.press('Escape');expect(modal).to_have_count(0)
        assert not page.locator('.workspace').evaluate('(node)=>node.inert')
        expect(security.get_by_role('button',name='Configurar autenticador',exact=True)).to_be_focused()
        # Secondary links and company cards must enter the same guide router.
        nav('Visão geral')
        page.locator('.next-steps').get_by_role('link',name='Organize os documentos',exact=False).click()
        expect(page.locator('.page-heading h1')).to_have_text('Recepção')
        expect(page.locator('.activity-tabs a[href="#/imports"]')).to_have_count(1)
        nav('Visão geral')
        page.locator('.company-list').get_by_role('button').filter(has_text='Beta sintética').click()
        expect(page.locator('.page-heading h1')).to_have_text('Escrituração')
        expect(frame.locator('#company')).to_have_value(str(s['other']))
        page.locator('.brand[href="#/dashboard"]').click()
        expect(page.locator('.page-heading h1')).to_have_text('Visão geral')
        page.locator('.small-avatar').click()
        expect(page.locator('.activity-tabs a[href="#/security"]')).to_have_count(1)
        # Unknown addresses are normalized; closing the final guide leaves a usable home.
        page.evaluate("location.hash='#/nao-existe'")
        expect(page.locator('.page-heading h1')).to_have_text('Visão geral')
        expect(page).to_have_url(page.url.split('#')[0]+'#/dashboard')
        while page.locator('.activity-tabs > div').count()>1:
            before=page.locator('.activity-tabs > div').count()
            page.locator('.activity-tabs button').first.click()
            expect(page.locator('.activity-tabs > div')).to_have_count(before-1)
        page.locator('.activity-tabs button').click()
        expect(page.locator('.activity-tabs a[href="#/dashboard"]')).to_have_count(1)
        expect(page.locator('.page-heading h1')).to_have_text('Visão geral')
        # A previously loaded client guide must reload when a dashboard card changes company.
        session=page.request.get(origin+'/api/v1/auth/me').json()['data']
        headers={'Origin':origin,'X-CSRF-Token':session['csrf']}
        response=page.request.post(origin+'/api/v1/users',data={'name':'Cliente sintético de navegação','email':'navigation-client@example.test','password':'synthetic-client-navigation','role':'client','companies':[str(s['company']),str(s['other'])]},headers=headers)
        assert response.ok,response.text()
        for company,name in [(s['company'],'cliente-alfa.xml'),(s['other'],'cliente-beta.xml')]:
            response=page.request.post(origin+'/api/v1/client/source-receive',data={'company_id':company,'request_key':name,'inputs':[{'filename':name,'content_base64':base64.b64encode(fake_xml()).decode()}]},headers=headers)
            assert response.ok,response.text()
        page.get_by_role('button',name='Sair',exact=True).click()
        expect(page.get_by_role('heading',name='Acesse sua conta',exact=True)).to_be_visible()
        page.get_by_label('E-mail',exact=True).fill('navigation-client@example.test')
        page.get_by_label('Senha',exact=True).fill('synthetic-client-navigation')
        page.get_by_role('button',name='Entrar no ambiente',exact=False).click()
        nav('Portal do cliente')
        expect(page.get_by_role('cell',name='cliente-alfa.xml',exact=True)).to_be_visible()
        expect(page.get_by_role('cell',name='cliente-beta.xml',exact=True)).to_have_count(0)
        nav('Visão geral')
        page.locator('.company-list').get_by_role('button').filter(has_text='Beta sintética').click()
        expect(page.locator('.page-heading h1')).to_have_text('Portal do cliente')
        expect(page.get_by_label('Empresa',exact=True)).to_have_value(str(s['other']))
        expect(page.get_by_role('cell',name='cliente-beta.xml',exact=True)).to_be_visible()
        expect(page.get_by_role('cell',name='cliente-alfa.xml',exact=True)).to_have_count(0)
        expect(page.locator('.editor-guide')).to_have_count(0)
        print('PASS portal: editores de usuário/perfil em guias independentes; rascunhos e permissões após reload; senhas não persistidas; voltar/avançar; atalhos/cards e listas de cliente por empresa; skip link; última guia; modal 2FA com foco contido e restaurado')


def source_and_report_guides(mode):
    with scenario(mode) as s:
        page,frame=s['page'],s['frame']
        def nav(label):
            if mode=='portal':page.locator('.sidebar').get_by_role('link',name=label,exact=True).click()
            else:frame.locator('.work-nav').get_by_role('button',name=label,exact=True).click()
        def idle():
            expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
            expect(frame.locator('.alert.error')).to_have_count(0)
        frame.locator('#period').select_option(str(s['first']));idle()
        nav('Recepção')
        frame.locator('#source-files').set_input_files([
            {'name':'alfa.xml','mimeType':'application/xml','buffer':fake_xml()},
            {'name':'beta.xml','mimeType':'application/xml','buffer':fake_xml(number=2)}])
        frame.get_by_role('button',name='Receber arquivos',exact=True).click();idle()
        frame.get_by_label('Motivo da organização / retirada',exact=True).fill('Organização sintética')
        root=frame.locator('.workbench > section:visible')
        for name in ['alfa.xml','beta.xml']:
            row=root.locator('tbody tr').filter(has_text=name)
            row.get_by_role('button',name='Organizar em 2026-09',exact=True).click();idle()
            row.get_by_role('button',name='Decisões e versões',exact=True).click();idle()
            expect(frame.locator('.source-tabs button').filter(has_text='Decisões · '+name)).to_have_count(1)
            row.get_by_role('button',name='Dependências / retirada',exact=True).click();idle()
            panel=frame.locator('.source-guide:visible')
            panel.get_by_label('Motivo da retirada desta fonte',exact=True).fill('Motivo separado de '+name)
        frame.locator('.source-tabs button').filter(has_text='Dependências · alfa.xml').click()
        expect(frame.locator('.source-guide:visible').get_by_label('Motivo da retirada desta fonte',exact=True)).to_have_value('Motivo separado de alfa.xml')
        nav('Livros e relatórios')
        expect(frame.get_by_role('tablist',name='Guias dos livros')).to_be_visible()
        expect(frame.get_by_role('tab')).to_have_count(5)
        diary=frame.get_by_role('tab',name='Diário',exact=True)
        diary.click();expect(diary).to_have_attribute('aria-selected','true')
        frame.get_by_role('tabpanel',name='Diário',exact=True).evaluate('(node)=>node.dataset.navigationMarker="preservado"')
        frame.get_by_role('tab',name='Razão',exact=True).click()
        diary.click()
        assert frame.get_by_role('tabpanel',name='Diário',exact=True).get_attribute('data-navigation-marker')=='preservado'
        diary.press('ArrowRight');expect(frame.get_by_role('tab',name='Razão',exact=True)).to_be_focused()
        frame.get_by_role('tab',name='Razão',exact=True).press('Home')
        expect(frame.get_by_role('tab',name='Balancete',exact=True)).to_be_focused()
        nav('Recepção')
        expect(frame.locator('.source-guide:visible').get_by_label('Motivo da retirada desta fonte',exact=True)).to_have_value('Motivo separado de alfa.xml')
        frame.get_by_role('button',name='Fechar dependências de alfa.xml',exact=True).click()
        root.locator('tbody tr').filter(has_text='alfa.xml').get_by_role('button',name='Dependências / retirada',exact=True).click();idle()
        expect(frame.locator('.source-guide:visible').get_by_label('Motivo da retirada desta fonte',exact=True)).to_have_value('Motivo separado de alfa.xml')
        if mode=='local':
            expect(frame.locator('.resource-tabs button').filter(has_text='Recepção')).to_have_count(1)
            frame.get_by_role('button',name='Fechar recurso Recepção',exact=True).click()
            nav('Recepção')
            expect(frame.locator('.source-guide:visible').get_by_label('Motivo da retirada desta fonte',exact=True)).to_have_value('Motivo separado de alfa.xml')
            while frame.locator('.resource-tabs > div').count()>1:
                frame.locator('.resource-tabs > div > button:last-child').first.click()
            frame.locator('.resource-tabs > div > button:last-child').click()
            expect(frame.locator('.resource-tabs > div')).to_have_count(1)
        print(f'PASS {mode}: decisões/dependências de duas fontes em guias; motivos separados e preservados; cinco livros em guias com componentes mantidos e teclado; recursos locais com fechamento/reabertura')

if __name__=='__main__':
    portal_paths()
    for mode in ['local','portal']:source_and_report_guides(mode)
