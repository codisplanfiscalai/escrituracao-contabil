"""Independent fiscal closing/reopening in the integrated application's UI."""
from browser_support import scenario, expect


def main():
    with scenario() as s:
        page, frame = s['page'], s['frame']
        page.locator('.sidebar').get_by_role('link', name='Encerramento', exact=True).click()
        fiscal = frame.locator('[data-module="fiscal"]')
        accounting = frame.locator('[data-module="contabil"]')
        expect(fiscal.get_by_role('heading')).to_contain_text('aberta')
        expect(accounting.get_by_role('heading')).to_contain_text('aberta')
        frame.get_by_label('Motivo do controle por módulo').fill('Fechamento fiscal sintético')
        frame.get_by_label('Referência da conferência e apuração externa').fill('Apuração externa sintética conferida')
        for check in fiscal.locator('input[type=checkbox]').all():
            check.check()
        fiscal.get_by_role('button', name='Encerrar fiscal', exact=True).click()
        expect(fiscal.get_by_role('heading')).to_contain_text('encerrada')
        expect(accounting.get_by_role('heading')).to_contain_text('aberta')
        page.reload()
        expect(page.frame_locator('#workspace-frame').locator('[data-module="fiscal"]').get_by_role('heading')).to_contain_text('encerrada')
        frame.get_by_label('Motivo do controle por módulo').fill('Reabertura fiscal sintética')
        fiscal.get_by_role('button', name='Reabrir fiscal', exact=True).click()
        expect(fiscal.get_by_role('heading')).to_contain_text('aberta')
        expect(accounting.get_by_role('heading')).to_contain_text('aberta')
        print('PASS: independent fiscal close/reopen, accounting remains open, state survives reload; no JS errors')


if __name__ == '__main__':
    main()
