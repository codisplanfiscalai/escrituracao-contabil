"""Real Chromium acceptance for configurable reports, using synthetic data only."""
from pathlib import Path
from browser_support import scenario, expect, AccountingStore


def run(mode):
    with scenario(mode) as env:
        with AccountingStore(env['path'], actor='qa-sintetico') as store:
            for index, (day, amount) in enumerate([('02', '0.10'), ('15', '0.20'), ('25', '7.00')]):
                p = store.prepare_work_operation(env['company'], env['first'], operation='ajuste')
                p['reference'] = 'QA sintético de relatórios'
                p['fiscal'].update(total=amount, posting_date='2026-09-'+day)
                for entry, code in zip(p['entries'], ['1.1.1', '2.1']):
                    entry.update(account_id=env['accounts'][code], date='2026-09-'+day, amount=amount, memo='QA inteiramente sintético')
                op = store.save_work_operation(env['company'], env['first'], p, 'Teste', f'qa-report-{index}')
                store.review_work_operation(env['company'], op['operation_id'], op['snapshot_hash'], 'Conferido')
                store.post_work_operation(env['company'], op['operation_id'], op['snapshot_hash'], 'Escriturado')
        frame = env['frame']
        frame.get_by_label('Competência dos movimentos', exact=True).select_option(str(env['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy', 'false')
        frame.get_by_role('button', name='Atualizar', exact=True).click()
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy', 'false')
        if mode == 'portal':
            env['page'].locator('.sidebar').get_by_role('link', name='Livros e relatórios', exact=True).click()
        else:
            frame.locator('.work-nav').get_by_role('button', name='Livros e relatórios', exact=True).click()
        panel = frame.locator('.accounting-report')
        expect(panel).to_be_visible()
        panel.get_by_label('Relatório', exact=True).select_option('razao')
        panel.get_by_label('Conta ou grupo de contas', exact=True).fill('1')
        panel.get_by_label('Data inicial do relatório', exact=True).fill('2026-09-10')
        panel.get_by_label('Data final do relatório', exact=True).fill('2026-09-20')
        panel.get_by_role('button', name='Consultar relatório', exact=True).click()
        expect(panel.locator('.accounting-report-result')).to_contain_text('Débitos 0.20 · créditos 0.00 · saldo final 0.30')
        expect(panel.locator('tbody tr')).to_have_count(1)
        expect(panel.locator('tbody')).to_contain_text('2026-09-15')
        panel.get_by_label('Relatório', exact=True).select_option('balancete')
        expect(panel.locator('.accounting-report-result')).to_have_count(0)
        panel.get_by_label('Nível do balancete', exact=True).select_option('sintetico')
        panel.get_by_role('button', name='Consultar relatório', exact=True).click()
        expect(panel.locator('tbody tr')).to_have_count(2)
        expect(panel).to_contain_text('não somar linhas sintéticas sobrepostas')
        panel.scroll_into_view_if_needed()
        folder = Path('/tmp/accounting-reports-qa'); folder.mkdir(exist_ok=True)
        env['page'].screenshot(path=str(folder / f'{mode}-desktop.png'), full_page=True, animations='disabled')
        env['page'].set_viewport_size({'width':390,'height':844})
        panel.scroll_into_view_if_needed()
        env['page'].screenshot(path=str(folder / f'{mode}-mobile.png'), full_page=True, animations='disabled')
        if mode == 'portal':
            width = env['page'].locator('#workspace-frame').content_frame.locator('body').evaluate('(e)=>[e.scrollWidth,e.clientWidth]')
        else:
            width = env['page'].locator('body').evaluate('(e)=>[e.scrollWidth,e.clientWidth]')
        assert width[0] <= width[1], width
        root_width = env['page'].locator('body').evaluate('(e)=>[e.scrollWidth,e.clientWidth]')
        assert root_width[0] <= root_width[1], root_width
        # Switching tenant destroys the previous report rather than retaining it.
        frame.get_by_label('Empresa', exact=True).select_option(str(env['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy', 'false')
        expect(frame.locator('.accounting-report-result')).to_have_count(0)
        assert not env['errors'], env['errors']
        print(f'PASS {mode}: exact subperiod balances, hierarchy, filter invalidation, mobile width, company reset; no JS errors')


if __name__ == '__main__':
    for mode in ('local', 'portal'):
        run(mode)
