"""CSV plan → competence → manual service operation, in the common workbench."""
from pathlib import Path
import argparse
from browser_support import scenario
from playwright.sync_api import expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    with scenario('local',chart=False) as s:
        page=s['page']
        def nav(label):page.locator('.work-nav').get_by_role('button',name=label,exact=True).click()
        def idle():expect(page.locator('.workbench')).to_have_attribute('aria-busy','false');expect(page.locator('.alert.error')).to_have_count(0)
        nav('Plano e políticas')
        section=page.locator('section:visible')
        section.get_by_label('Nome da versão',exact=True).fill('Plano importado sintético')
        section.get_by_label('Arquivo CSV',exact=True).set_input_files({'name':'plano.csv','mimeType':'text/csv','buffer':b'codigo;descricao;tipo;natureza;superior;acesso\n1;Ativo;sintetica;devedora;;10\n1.1;Caixa;analitica;devedora;1;11\n2;Passivo;sintetica;credora;;20\n2.1;Obrigacao;analitica;credora;2;21\n'})
        section.locator('form').first.get_by_label('Motivo',exact=True).fill('Original sintético completo')
        section.get_by_role('button',name='Importar plano',exact=True).click();idle()
        nav('Competências');section=page.locator('section:visible')
        section.get_by_label('Movimentos',exact=True).fill('2026-09')
        section.get_by_label('Referência dos parâmetros',exact=True).fill('2026-08')
        section.get_by_label('Plano',exact=True).select_option(label='Plano importado sintético · v1')
        section.get_by_label('Motivo',exact=True).fill('Configuração manual')
        section.get_by_role('button',name='Salvar competência',exact=True).click();idle()
        nav('Escrituração');page.get_by_role('button',name='+ Lançamento manual',exact=True).click();idle()
        page.locator('#operation-reference').fill('Serviço sintético')
        page.get_by_label('Natureza',exact=True).select_option('servico_tomado')
        page.get_by_label('Modelo',exact=True).select_option('SERVICO')
        page.get_by_label('Número',exact=True).fill('SINTETICO-1')
        page.get_by_label('Emissão',exact=True).fill('2026-08-30')
        page.get_by_label('Data de escrituração',exact=True).fill('2026-09-01')
        page.get_by_label('Valor total',exact=True).fill('123,45')
        page.get_by_label('ISS informado',exact=True).fill('6,17')
        for i,account in enumerate(['1.1 · Caixa','2.1 · Obrigacao'],1):
            page.get_by_label(f'Conta {i}',exact=True).select_option(label=account)
            page.get_by_label(f'Histórico {i}',exact=True).fill('Serviço informado')
        page.locator('#operation-reason').fill('Escrituração sintética')
        page.get_by_role('button',name='Salvar versão',exact=True).click();idle()
        page.get_by_role('button',name='Conferir versão',exact=True).click();idle()
        page.get_by_role('button',name='Escriturar',exact=True).click();idle()
        nav('Livros e relatórios');page.get_by_role('button',name='Livro fiscal',exact=True).click()
        expect(page.locator('section:visible')).to_contain_text('SINTETICO-1')
        expect(page.locator('section:visible')).to_contain_text('6.17')
        if args.screenshots:page.screenshot(path=str(args.screenshots/'escrituracao-manual.png'),full_page=True)
        nav('Competências');section=page.locator('section:visible')
        section.get_by_label('Movimentos',exact=True).fill('2026-10')
        section.get_by_label('Referência dos parâmetros',exact=True).fill('2026-09')
        section.get_by_label('Motivo',exact=True).fill('Continuidade de outubro')
        section.get_by_role('button',name='Salvar competência',exact=True).click();idle()
        october=page.locator('#period').input_value()
        september=page.locator('#period option').filter(has_text='2026-09').get_attribute('value')
        page.locator('#period').select_option(september);idle()
        nav('Escrituração')
        page.get_by_label('Competência de destino do estorno',exact=True).select_option(october)
        page.get_by_label('Data do estorno',exact=True).fill('2026-10-01')
        page.get_by_role('button',name='Preparar estorno vinculado',exact=True).click();idle()
        expect(page.locator('#period')).to_have_value(october)
        page.locator('#operation-reason').fill('Estorno informado em outubro')
        page.get_by_role('button',name='Conferir versão',exact=True).click();idle()
        page.get_by_role('button',name='Escriturar',exact=True).click();idle()
        from src.persistence import AccountingStore
        with AccountingStore(s['path']) as store:
            book=store.work_books(s['company'],int(october))
            assert all(r['closing']=='0.00' for r in book['trial_balance']),book['trial_balance']
            assert len(book['fiscal_book'])==0
        # Earlier persistent fiscal guides remain consultable and can be resumed,
        # preserving original fields rather than silently discarding them.
        with AccountingStore(s['path'],actor='operador-local') as store:
            period=store._work_cycle(s['company'],int(october))['period_id']
            store.save_fiscal_workspace(s['company'],period,'Guia anterior sintética',{'data':{'operation':'servico_tomado','model':'SERVICO','number':'LEGADO-42','posting_date':'2026-10-01','issued_date':'2026-09-30','total':'12.30'}},'legacy-guide-ui')
        page.get_by_role('button',name='Atualizar',exact=True).click();idle()
        nav('Histórico')
        page.locator('section:visible').get_by_label('Motivo',exact=True).fill('Retomada explícita da guia antiga')
        page.get_by_role('button',name='Retomar como operação',exact=True).click();idle()
        expect(page.get_by_label('Número',exact=True)).to_have_value('LEGADO-42')
        print('PASS: plano CSV com atributos e original; referência e movimentos distintos; serviço manual com ISS informado; versão/conferência/escrituração; livro fiscal; estorno vinculado em outra competência; retomada de guia fiscal antiga')
if __name__=='__main__':main()
