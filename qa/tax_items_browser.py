"""Synthetic mixed item treatments and explicit component profiles through the UI."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from browser_support import scenario, expect
from src.persistence import AccountingStore
from test_persistence import fake_xml, NS


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    with scenario() as s:
        page,frame=s['page'],s['frame']
        with AccountingStore(s['path']) as store:
            for code in ('00000000','00000001'):
                store.save_tax_code(s['company'],'ncm',code,{'description':'NCM sintético','valid_from':'2026-01-01','valid_to':'','source_reference':'Fixture não normativa'},'ativo',0,'Teste')
            def rule(key,tax,rate,treatment,method='percentual',**extra):
                store.save_tax_rule(s['company'],key,'Regra sintética '+key,{'tax':tax,'rate':rate,'base_field':'total','effect':'informativo' if tax=='RETENCAO' else 'debito',
                    'operation':'entrada','valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Validação sintética',
                    'item_treatment':treatment,'calculation':{'scope':'item','method':method,'reduction_percent':'0','base_rounding':'centavos_antes_da_taxa',**extra}},'aprovada',0,'Teste')
            rule('icms-a','ICMS','2.5','A');rule('icms-b','ICMS','7','B')
            rule('difal','ICMS_DIFAL','12','B','difal',origin_rate='4',negative_policy='bloquear')
            rule('retention','RETENCAO','2','A','retencao',component_code='TESTE')
            policy=store.save_work_policy(s['company'],s['plan'],'entrada','2026-08','Política sintética',s['accounts']['1.1.1'],s['accounts']['2.1'],'Teste',True)
            root=ET.fromstring(fake_xml());info=root.find('.//n:infNFe',{'n':NS})
            for index,code in enumerate(('00000000','00000001'),1):
                det=ET.SubElement(info,'{'+NS+'}det',nItem=str(index));prod=ET.SubElement(det,'{'+NS+'}prod')
                ET.SubElement(prod,'{'+NS+'}NCM').text=code;ET.SubElement(prod,'{'+NS+'}xProd').text='Item sintético '+str(index)
            source=store.receive_sources(s['company'],[{'filename':'itens-sinteticos.xml','content':ET.tostring(root)}],'items-ui')['items'][0]
            doc=store.organize_source(s['company'],source['input_id'],s['first'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
            payload=store.prepare_work_operation(s['company'],s['first'],doc,policy_id=policy['id'])
            store.save_work_operation(s['company'],s['first'],payload,'Teste','items-ui-op')
        page.reload();page.locator('.sidebar').get_by_role('link',name='Tributação e apuração',exact=True).click()
        frame.get_by_role('heading',name='Tributação e apuração',exact=True).wait_for()
        frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.get_by_label('Identificador da regra',exact=True).fill('st-ui')
        frame.get_by_label('Nome da regra',exact=True).fill('ST declarada sintética')
        frame.get_by_label('Perfil de cálculo',exact=True).select_option('st')
        expect(frame.get_by_label('Tributo da regra',exact=True)).to_have_value('ICMS_ST')
        for label,value in [('Natureza da regra','entrada'),('Campo da base','total'),('Efeito na apuração','debito'),('Arredondamento da regra','meio_para_cima'),('Arredondamento da base do item','centavos_antes_da_taxa'),('Tratamento de resultado negativo','bloquear')]:
            frame.get_by_label(label,exact=True).select_option(value)
        for label,value in [('Tratamento de escopo do item','A'),('Redução percentual declarada','0'),('Margem percentual declarada','50'),('Alíquota percentual informada','10'),('Início da vigência da regra','2026-09-01'),('Referência da validação da regra','Fixture sem validade legal'),('Motivo da versão da regra','Teste')]:
            frame.get_by_label(label,exact=True).fill(value)
        frame.get_by_role('button',name='Aprovar versão da regra',exact=True).click()
        frame.get_by_role('status').filter(has_text='Regra tributária versionada').wait_for()
        page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click()
        frame.get_by_role('button',name='Abrir operação',exact=True).click()
        frame.get_by_text('Tributação por item e tratamentos mistos',exact=True).click()
        frame.get_by_role('button',name='Propor vínculos dos itens da fonte',exact=True).click()
        for index,(total,treatment,taxes) in enumerate([('60.00','A','ICMS, ICMS_ST, RETENCAO:TESTE'),('40.30','B','ICMS, ICMS_DIFAL')]):
            item=frame.locator(f'[data-tax-item="{index}"]')
            item.get_by_label('Total líquido atribuído ao item',exact=True).fill(total)
            item.get_by_label('Tratamento declarado do item',exact=True).fill(treatment)
            item.get_by_label('Componentes a calcular',exact=True).fill(taxes)
            item.get_by_label('Componentes a calcular',exact=True).blur()
        frame.locator('[data-tax-item="0"]').get_by_label('Dedução própria declarada para ST',exact=True).fill('3.00')
        frame.locator('#operation-reason').fill('Conferência de itens sintéticos')
        frame.get_by_role('button',name='Salvar versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Versão salva').wait_for()
        frame.get_by_role('button',name='Gerar prévia de tributação',exact=True).click()
        frame.get_by_role('button',name='Aplicar cálculo em nova versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Tributos calculados').wait_for()
        expect(frame.get_by_label('ICMS informado',exact=True)).to_have_value('4.32')
        if args.screenshots:
            frame.locator('[data-tax-item="0"]').get_by_label('Descrição do item',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/'itens-form-desktop.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_timeout(300)
            frame.locator('[data-tax-item="0"]').get_by_label('Descrição do item',exact=True).scroll_into_view_if_needed()
            assert frame.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/'itens-form-mobile.png'),full_page=True)
            page.set_viewport_size({'width':1440,'height':1080})
        frame.get_by_role('button',name='Conferir versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Versão conferida').wait_for()
        frame.get_by_role('button',name='Escriturar',exact=True).click()
        frame.get_by_role('status').filter(has_text='Operação escriturada').wait_for()
        page.locator('.sidebar').get_by_role('link',name='Tributação e apuração',exact=True).click()
        frame.get_by_role('button',name='Gerar prévia da apuração',exact=True).click()
        frame.get_by_label('Motivo da apuração ou validação',exact=True).fill('Conferência sintética')
        frame.get_by_role('button',name='Preservar versão da apuração',exact=True).click()
        frame.get_by_role('status').filter(has_text='Memória da apuração preservada').wait_for()
        with page.expect_download() as downloaded:frame.get_by_role('button',name='Baixar memória JSON',exact=True).click()
        memory=json.loads(Path(downloaded.value.path()).read_text())['snapshot']
        assert len(memory['lines'])==5
        totals={g.get('component_key',g['tax']):g['debito'] for g in memory['totals']}
        assert totals['ICMS']=='4.32' and totals['ICMS_ST']=='6.00' and totals['ICMS_DIFAL']=='3.22'
        assert next(g for g in memory['totals'] if g['tax']=='RETENCAO')['informativo']=='1.20'
        if args.screenshots:page.screenshot(path=str(args.screenshots/'itens-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert frame.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth+1')
        if args.screenshots:page.screenshot(path=str(args.screenshots/'itens-mobile.png'),full_page=True)
        print('PASS: source item links, mixed ICMS rates, explicit ST profile UI, DIFAL and retention components, posting and item assessment JSON; mobile/no JS errors')


if __name__=='__main__':main()
