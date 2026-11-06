"""Synthetic FCP/gross-up group authoring and accounting-safe application."""
import argparse
import json
from pathlib import Path
from browser_support import scenario, expect
from src.persistence import AccountingStore
from test_persistence import fake_xml


def run(mode,args):
    with scenario(mode) as s:
        page,frame=s['page'],s['frame']
        with AccountingStore(s['path']) as store:
            store.save_tax_rule(s['company'],'inside-own','Regra inteiramente sintética',{'tax':'ICMS','rate':'18','base_field':'net_base','effect':'debito','operation':'entrada','model':'55',
                'valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Fixture sem validade legal',
                'calculation':{'scope':'item','method':'por_dentro','reduction_percent':'0','base_rounding':'centavos_antes_da_taxa',
                    'input_basis':'liquido_sem_componentes_do_grupo','residual_policy':'bloquear','denominator_components':[{'component':'ICMS','rate':'18'},{'component':'FCP:TESTE','rate':'2'}]}},'aprovada',0,'Teste')
            policy=store.save_work_policy(s['company'],s['plan'],'entrada','2026-08','Política sintética',s['accounts']['1.1.1'],s['accounts']['2.1'],'Teste',True)
            source=store.receive_sources(s['company'],[{'filename':'FCP-Sintetico.xml','content':fake_xml(total='125.00',billing=False)}],'fcp-source')['items'][0]
            doc=store.organize_source(s['company'],source['input_id'],s['first'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
            payload=store.prepare_work_operation(s['company'],s['first'],doc,policy_id=policy['id'])
            original=store.save_work_operation(s['company'],s['first'],payload,'Teste','fcp-operation')
        def nav(label):
            if mode=='portal':page.locator('.sidebar').get_by_role('link',name=label,exact=True).click()
            else:frame.locator('.work-nav').get_by_role('button',name=label,exact=True).click()
        page.reload();nav('Tributação e apuração')
        frame.get_by_role('heading',name='Tributação e apuração',exact=True).wait_for()
        frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.get_by_label('Identificador da regra',exact=True).fill('fcp-ui')
        frame.get_by_label('Nome da regra',exact=True).fill('FCP inteiramente sintético')
        frame.get_by_label('Perfil de cálculo',exact=True).select_option('fcp')
        expect(frame.get_by_label('Tributo da regra',exact=True)).to_have_value('FCP')
        frame.get_by_label('Formação da base FCP',exact=True).select_option('declarada')
        expect(frame.get_by_label('Campo da base',exact=True)).to_be_enabled()
        frame.get_by_label('Formação da base FCP',exact=True).select_option('por_dentro')
        expect(frame.get_by_label('Campo da base',exact=True)).to_have_value('net_base')
        expect(frame.get_by_label('Campo da base',exact=True)).to_be_disabled()
        for label,value in [('Natureza da regra','entrada'),('Modelo da regra','55'),('Efeito na apuração','informativo'),('Arredondamento da regra','meio_para_cima'),
                            ('Arredondamento da base do item','centavos_antes_da_taxa'),('Significado da base líquida','liquido_sem_componentes_do_grupo'),('Diferença de arredondamento do grupo','bloquear')]:
            frame.get_by_label(label,exact=True).select_option(value)
        for label,value in [('Identificador da modalidade FCP','TESTE'),('Redução percentual declarada','0'),('Alíquota percentual informada','2'),('Início da vigência da regra','2026-09-01'),
                            ('Referência da validação da regra','Fixture sintética; nenhum enquadramento legal'),('Motivo da versão da regra','Teste de parâmetros declarados')]:
            frame.get_by_label(label,exact=True).fill(value)
        frame.get_by_role('button',name='Aprovar versão da regra',exact=True).click()
        expect(frame.locator('.alert.error')).to_contain_text('componentes e taxas no denominador')
        for index,(component,rate) in enumerate([('ICMS','18'),('FCP:TESTE','2')]):
            frame.get_by_role('button',name='Adicionar componente ao denominador',exact=True).click()
            row=frame.locator(f'[data-grossup-component="{index}"]')
            row.get_by_label('Componente incluído por dentro',exact=True).fill(component)
            row.get_by_label('Taxa incluída no denominador (%)',exact=True).fill(rate)
        frame.get_by_role('button',name='Aprovar versão da regra',exact=True).click()
        frame.get_by_role('status').filter(has_text='Regra tributária versionada').wait_for()
        nav('Escrituração');frame.get_by_role('button',name='Abrir operação',exact=True).click()
        frame.get_by_text('Tributação por item e tratamentos mistos',exact=True).click()
        frame.get_by_role('button',name='Adicionar item tributário',exact=True).click()
        item=frame.locator('[data-tax-item="0"]')
        for label,value in [('Descrição do item','Item sintético'),('Total líquido atribuído ao item','125.00'),('Origem e conferência dos valores do item','Fixture e base líquida declarada'),
                            ('Componentes a calcular','ICMS, FCP:TESTE'),('Base líquida sem componentes do grupo','100.00')]:
            item.get_by_label(label,exact=True).fill(value)
        item.get_by_label('Componentes a calcular',exact=True).blur()
        frame.locator('#operation-reason').fill('Teste sintético do grupo por dentro')
        frame.get_by_role('button',name='Salvar versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Versão salva').wait_for()
        frame.get_by_role('button',name='Gerar prévia de tributação',exact=True).click()
        frame.get_by_role('button',name='Aplicar cálculo em nova versão',exact=True).wait_for()
        if args.screenshots:
            frame.get_by_role('button',name='Aplicar cálculo em nova versão',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/f'fcp-{mode}-desktop.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
            assert frame.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/f'fcp-{mode}-mobile.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':1440,'height':1080})
        frame.get_by_role('button',name='Aplicar cálculo em nova versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Tributos calculados').wait_for()
        expect(frame.get_by_label('ICMS informado',exact=True)).to_have_value('22.50')
        with AccountingStore(s['path']) as store:
            current=store.get_work_operation(s['company'],original['operation_id'])
            assert current['payload']['entries']==original['payload']['entries']
            assert current['payload']['finance']==original['payload']['finance']
        frame.get_by_role('button',name='Conferir versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Versão conferida').wait_for()
        frame.get_by_role('button',name='Escriturar',exact=True).click()
        frame.get_by_role('status').filter(has_text='Operação escriturada').wait_for()
        nav('Tributação e apuração')
        frame.get_by_role('button',name='Gerar prévia da apuração',exact=True).click()
        frame.get_by_label('Motivo da apuração ou validação',exact=True).fill('Conferência sintética')
        frame.get_by_role('button',name='Preservar versão da apuração',exact=True).click()
        frame.get_by_role('status').filter(has_text='Memória da apuração preservada').wait_for()
        with page.expect_download() as downloaded:frame.get_by_role('button',name='Baixar memória JSON',exact=True).click()
        snapshot=json.loads(Path(downloaded.value.path()).read_text())['snapshot']
        assert snapshot['grossup_groups'][0]['grossed_base']=='125.00'
        assert snapshot['grossup_groups'][0]['rounded_tax_sum']=='25.00'
        assert snapshot['grossup_groups'][0]['allocation_performed'] is False
        assert next(g for g in snapshot['totals'] if g['tax']=='FCP')['informativo']=='2.50'
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_label('Alíquota percentual informada',exact=True)).to_have_value('')
        print('PASS '+mode+': missing denominator blocked, explicit FCP group/rates, liquid-base gross-up, trace/reconciliation, no financial or journal mutation, reviewed posting and assessment JSON, mobile and tenant reset')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    for mode in ('local','portal'):run(mode,args)


if __name__=='__main__':main()
