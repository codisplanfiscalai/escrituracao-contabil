"""Reviewed synthetic manual adjustment, closed-origin reservation and cancellation."""
import argparse
import json
from pathlib import Path
from browser_support import scenario, expect
from src.persistence import AccountingStore
from src.module_closure import CHECKS


def run(mode,args):
    with scenario(mode) as s:
        with AccountingStore(s['path']) as store:
            spec={'kind':'manual','date':'2026-09-15','component_key':'ICMS','revenue_code':'','effect':'credito','amount':'100.00',
                  'description':'Saldo inteiramente sintético','reference':'Fixture sem validade legal'}
            preview=store.preview_assessment_adjustment(s['company'],s['first'],spec)
            store.apply_assessment_adjustment(s['company'],s['first'],spec,preview['snapshot_hash'],'source','Teste','Conferência sintética',True)
            preview=store.preview_tax_assessment(s['company'],s['first'])
            row=store.create_tax_assessment(s['company'],s['first'],preview['snapshot_hash'],'source-assessment','Teste')
            store.validate_tax_assessment(s['company'],s['first'],row['id'],row['snapshot_hash'],'Teste',True)
            state=store.module_period_overview(s['company'],s['first'],'fiscal')
            store.transition_module_period(s['company'],s['first'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Teste')
            origin=store.tax_assessments(s['company'],s['first'])
        page,frame=s['page'],s['frame'];page.reload()
        if mode=='portal':page.locator('.sidebar').get_by_role('link',name='Tributação e apuração',exact=True).click()
        else:frame.locator('.work-nav').get_by_role('button',name='Tributação e apuração',exact=True).click()
        frame.locator('#period').select_option(str(s['second']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.get_by_text('Ajustes de apuração e saldos entre competências',exact=True).click()
        frame.get_by_role('button',name='Novo ajuste manual de apuração',exact=True).click()
        for label,value in [('Data do ajuste de apuração','2026-10-15'),('Componente do ajuste de apuração','ICMS'),('Valor do ajuste de apuração','20.00'),
                            ('Descrição do ajuste de apuração','Débito sintético'),('Referência que autoriza o ajuste ou transporte','Fixture sem validade legal')]:
            frame.get_by_label(label,exact=True).fill(value)
        frame.get_by_label('Efeito do ajuste de apuração',exact=True).select_option('debito')
        def confirmation():
            frame.get_by_label('Motivo do ajuste ou cancelamento',exact=True).fill('Teste sintético')
            frame.get_by_label('Referência da conferência do ajuste',exact=True).fill('Conferência sem validade legal')
            frame.get_by_label('Conferi origem, valor, natureza, autorização e efeitos do ajuste ou cancelamento, sem presumir direito a crédito',exact=True).check()
        frame.get_by_role('button',name='Conferir prévia do ajuste',exact=True).click()
        expect(frame.get_by_role('button',name='Aprovar ajuste de apuração',exact=True)).to_be_disabled()
        confirmation();frame.get_by_role('button',name='Aprovar ajuste de apuração',exact=True).click()
        frame.get_by_role('status').filter(has_text='Ajuste aprovado').wait_for()
        frame.get_by_role('button',name='Consultar saldos de origem e histórico',exact=True).click()
        frame.get_by_role('button',name='Preparar transporte deste saldo',exact=True).click()
        expect(frame.get_by_label('Componente do ajuste de apuração',exact=True)).to_have_attribute('readonly','')
        for label,value in [('Data do ajuste de apuração','2026-10-16'),('Valor do ajuste de apuração','101.00'),('Descrição do ajuste de apuração','Transporte sintético'),
                            ('Referência que autoriza o ajuste ou transporte','Conferência explícita sem direito legal presumido')]:
            frame.get_by_label(label,exact=True).fill(value)
        frame.get_by_role('button',name='Conferir prévia do ajuste',exact=True).click()
        expect(frame.locator('.alert.error')).to_contain_text('saldo disponível')
        frame.get_by_label('Valor do ajuste de apuração',exact=True).fill('60.00')
        frame.get_by_role('button',name='Conferir prévia do ajuste',exact=True).click()
        frame.get_by_role('heading',name='Prévia do ajuste de apuração',exact=True).wait_for()
        confirmation()
        if args.screenshots:
            frame.get_by_role('heading',name='Prévia do ajuste de apuração',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/f'balances-{mode}-desktop.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
            frame.get_by_role('heading',name='Prévia do ajuste de apuração',exact=True).scroll_into_view_if_needed()
            assert frame.locator('body').evaluate('el=>el.scrollWidth<=innerWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/f'balances-{mode}-mobile.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':1440,'height':1080})
        frame.get_by_role('button',name='Aprovar ajuste de apuração',exact=True).click()
        frame.get_by_role('status').filter(has_text='Ajuste aprovado').wait_for()
        frame.get_by_role('button',name='Gerar prévia da apuração',exact=True).click()
        frame.get_by_label('Motivo da apuração ou validação',exact=True).fill('Teste sintético')
        frame.get_by_role('button',name='Preservar versão da apuração',exact=True).click()
        frame.get_by_role('status').filter(has_text='Memória da apuração preservada').wait_for()
        frame.get_by_label('Conferi fatos, regras, vigência, tabelas, bases, efeitos e memória da apuração',exact=True).check()
        frame.get_by_role('button',name='Validar apuração conferida',exact=True).click()
        frame.get_by_role('status').filter(has_text='Apuração parametrizada validada').wait_for()
        with page.expect_download() as download:frame.get_by_role('button',name='Baixar memória JSON',exact=True).click()
        memory=json.loads(Path(download.value.path()).read_text())['snapshot']
        assert memory['profile']=='apuracao-parametrizada-v2'
        assert memory['totals'][0]['saldo_aritmetico']=='-40.00'
        assert memory['totals'][0]['ajustes_debito']=='20.00'
        assert len(memory['adjustments'])==2
        with AccountingStore(s['path']) as store:
            assert store.tax_assessments(s['company'],s['first'])==origin
            assert store.tax_balance_sources(s['company'],s['second'])[0]['available']=='40.00'
            carry=next(r for r in store.tax_assessment_adjustments(s['company'],s['second']) if r['snapshot']['data']['kind']=='transporte')
            assert store.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0]==0
        confirmation()
        frame.locator(f'[data-assessment-adjustment="{carry["id"]}"]').get_by_role('button',name='Cancelar ajuste em nova versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Cancelamento preservado').wait_for()
        with AccountingStore(s['path']) as store:
            assert not store.tax_assessment_readiness(s['company'],s['second'])['ready']
            assert store.tax_balance_sources(s['company'],s['second'])[0]['available']=='100.00'
        frame.get_by_label('Valor do ajuste de apuração',exact=True).fill('999')
        frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_label('Valor do ajuste de apuração',exact=True)).to_have_value('')
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.locator('[data-assessment-adjustment]')).to_have_count(0)
        print('PASS '+mode+': manual adjustment, closed-origin reference, overuse blocked, reviewed carry reservation, separated assessment JSON, no postings/origin mutation, append-only cancellation, stale validation, period/company reset and mobile')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    for mode in ('local','portal'):run(mode,args)


if __name__=='__main__':main()
