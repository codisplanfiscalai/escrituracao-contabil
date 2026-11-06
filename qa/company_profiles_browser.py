"""Synthetic client/office registration and source search before competence."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_support import scenario, expect
from src.persistence import AccountingStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    with scenario(chart=False) as s:
        page, frame = s['page'], s['frame']
        page.locator('.sidebar').get_by_role('link', name='Empresas', exact=True).click()
        page.get_by_label('Cliente para cadastro', exact=True).select_option(str(s['company']))
        page.get_by_role('button', name='Salvar cadastro do cliente').wait_for()
        page.get_by_label('Nome fantasia', exact=True).fill('Fantasia Alfa sintética')
        page.get_by_label('Regime tributário declarado', exact=True).fill('Regime sintético')
        page.get_by_label('FAP informado', exact=True).fill('1,0000')
        page.get_by_label('CRC', exact=True).fill('CRC-SINTETICO')
        page.get_by_label('Contato responsável', exact=True).fill('Contato Alfa')
        page.get_by_label('Motivo da atualização do cliente').fill('Cadastro sintético completo')
        with page.expect_response(lambda r: '/api/company-profile' in r.url and r.request.method == 'POST') as saved:
            page.get_by_role('button', name='Salvar cadastro do cliente').click()
        assert saved.value.status == 200, saved.value.text()
        page.get_by_role('status').filter(has_text='Cadastro do cliente salvo com nova versão.').wait_for()
        page.get_by_label('Cliente para cadastro').select_option(str(s['other']))
        expect(page.get_by_label('Nome fantasia', exact=True)).to_have_value('')
        page.get_by_label('Cliente para cadastro').select_option(str(s['company']))
        expect(page.get_by_label('Nome fantasia', exact=True)).to_have_value('Fantasia Alfa sintética')
        if args.screenshots:
            page.screenshot(path=str(args.screenshots/'cliente.png'), full_page=True)
        page.locator('.sidebar').get_by_role('link', name='Configurações', exact=True).click()
        page.get_by_label('Nome da empresa usuária').fill('Escritório sintético')
        page.get_by_label('Motivo da atualização da empresa usuária').fill('Identidade própria')
        page.get_by_role('button', name='Salvar empresa usuária').click()
        page.get_by_role('status').filter(has_text='Empresa usuária salva separadamente dos clientes.').wait_for()
        page.reload()
        expect(page.get_by_label('Nome da empresa usuária')).to_have_value('Escritório sintético')
        if args.screenshots:
            page.screenshot(path=str(args.screenshots/'empresa-usuaria.png'), full_page=True)
        page.locator('.sidebar').get_by_role('link', name='Recepção', exact=True).click()
        expect(frame.locator('#period')).to_have_value('')
        frame.get_by_label('Buscar fontes', exact=True).fill('inexistente')
        frame.get_by_role('button', name='Buscar sem competência', exact=True).click()
        frame.get_by_role('status').filter(has_text='Busca: 0 de 0 fontes.').wait_for()
        expect(frame.locator('#period')).to_have_value('')
        page.set_viewport_size({'width':390, 'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        assert frame.locator('body').evaluate('(el)=>el.scrollWidth <= innerWidth+1')
        if args.screenshots:
            page.screenshot(path=str(args.screenshots/'recepcao-mobile.png'), full_page=True)
        with AccountingStore(s['path']) as store:
            assert len(store.list_companies()) == 2
            assert store.work_cycles(s['company']) == []
            assert store.client_profile(s['company'])['data']['labor']['fap'] == '1,0000'
        print('PASS: five registration sections, client isolation, office identity, reload and search with no competence; no JS errors')


if __name__ == '__main__':
    main()
