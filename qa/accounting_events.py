"""Exercise both composed Vue panels in one local/portal session, synthetic only."""
from pathlib import Path
from browser_support import scenario, expect, AccountingStore
from test_nfe_events import document_xml, event_xml


def run(mode):
    with scenario(mode) as env:
        with AccountingStore(env['path']) as store:
            company, cycle = env['company'], env['first']
            policy = store.save_work_policy(company, env['plan'], 'entrada', '2026-08',
                'Política sintética', env['accounts']['1.1.1'], env['accounts']['2.1'], 'Teste', True)
            source = store.receive_sources(company, [{'filename':'documento.xml','content':document_xml()}], 'doc')['items'][0]
            doc = store.organize_source(company, source['input_id'], cycle, source['snapshot_hash'], 'Teste')['evidence']['document_ids'][0]
            op = store.save_work_operation(company, cycle,
                store.prepare_work_operation(company, cycle, doc, policy_id=policy['id']), 'Teste', 'draft')
            event = store.receive_sources(company, [{'filename':'evento.xml','content':event_xml(kind='110110')}], 'event')['items'][0]
        page, frame = env['page'], env['frame']
        page.reload()
        frame.get_by_label('Competência dos movimentos', exact=True).select_option(str(cycle))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy', 'false')

        def nav(label):
            if mode == 'portal':
                menu = page.get_by_role('button', name='Abrir menu', exact=True)
                if menu.is_visible() and not page.locator('.sidebar.visible').count():
                    menu.click()
                page.locator('.sidebar').get_by_role('link', name=label, exact=True).click()
            else:
                frame.locator('.work-nav').get_by_role('button', name=label, exact=True).click()

        def report(total):
            nav('Livros e relatórios')
            panel = frame.locator('.accounting-report')
            expect(panel).to_be_visible()
            panel.get_by_role('button', name='Consultar relatório', exact=True).click()
            expect(panel.locator('.accounting-report-result')).to_contain_text('Débitos '+total+' · créditos '+total)
            return panel

        report('0.00')
        nav('Recepção')
        events = frame.locator('.nfe-events-panel')
        if events.get_attribute('open') is None:
            events.locator('summary').first.click()
        events.get_by_role('button', name='Consultar eventos recebidos', exact=True).click()
        events.get_by_role('button', name='Conferir evento '+str(event['input_id']), exact=True).click()
        events.get_by_label('Decisão sobre o evento', exact=True).select_option('manter_fluxo')
        events.get_by_label('Motivo da decisão do evento', exact=True).fill('Conferência sintética integrada')
        events.get_by_label('Referência da conferência externa do evento', exact=True).fill('Fixture sem autorização real')
        events.get_by_label('Conferi origens, retorno, ambiente e consequências; esta anotação não aplica efeito fiscal', exact=True).check()
        events.get_by_role('button', name='Registrar decisão do evento', exact=True).click()
        expect(events.get_by_role('status').filter(has_text='Decisão #')).to_be_visible()
        report('0.00')
        with AccountingStore(env['path']) as store:
            store.review_work_operation(company, op['operation_id'], op['snapshot_hash'], 'Conferência explícita')
            store.post_work_operation(company, op['operation_id'], op['snapshot_hash'], 'Escrituração explícita')
            proof = store.nfe_event_posting_proof(company, op['operation_id'])
            assert proof and len(proof['snapshot']['reviews']) == 1
        frame.get_by_role('button', name='Atualizar', exact=True).click()
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy', 'false')
        panel = report('100.30')
        folder = Path('/tmp/contabil18-composition-qa'); folder.mkdir(exist_ok=True)
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(folder/f'{mode}-reports-desktop.png'), full_page=True, animations='disabled')
        nav('Recepção')
        events = frame.locator('.nfe-events-panel')
        if events.get_attribute('open') is None:
            events.locator('summary').first.click()
        events.get_by_role('button', name='Consultar eventos recebidos', exact=True).click()
        events.get_by_role('button', name='Conferir evento '+str(event['input_id']), exact=True).click()
        events.get_by_role('button', name='Consultar evidência de eventos na escrituração', exact=True).click()
        expect(events.get_by_text('Evidência histórica da escrituração', exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        events.get_by_role('heading', name='Conferência do evento 110110 / 1', exact=True).scroll_into_view_if_needed()
        assert frame.locator('body').evaluate('el=>el.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(folder/f'{mode}-events-mobile.png'), full_page=True, animations='disabled')
        frame.get_by_label('Empresa', exact=True).select_option(str(env['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy', 'false')
        expect(frame.locator('.event-review')).to_have_count(0)
        nav('Livros e relatórios')
        expect(frame.locator('.accounting-report-result')).to_have_count(0)
        assert not env['errors'], env['errors']
        print(f'PASS {mode}: event review and configurable reports in one Vue session, explicit posting/proof, navigation, mobile and tenant reset')


if __name__ == '__main__':
    for mode in ('local', 'portal'):
        run(mode)
