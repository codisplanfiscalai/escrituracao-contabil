"""Synthetic rates/codes, company models, operation tax and assessment in browser."""
import json
import argparse
from pathlib import Path
from browser_support import scenario, expect
from src.persistence import AccountingStore
from test_persistence import fake_xml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots',type=Path)
    args = parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    with scenario() as s:
        page, frame = s['page'], s['frame']
        with AccountingStore(s['path']) as store:
            policy = store.save_work_policy(s['company'],s['plan'],'entrada','2026-08','Política sintética',s['accounts']['1.1.1'],s['accounts']['2.1'],'Teste',True)
            source = store.receive_sources(s['company'],[{'filename':'Tributacao-Sintetica.xml','content':fake_xml()}],'tax-browser-source')['items'][0]
            organized = store.organize_source(s['company'],source['input_id'],s['first'],source['snapshot_hash'],'Teste')
            payload = store.prepare_work_operation(s['company'],s['first'],organized['evidence']['document_ids'][0],policy_id=policy['id'])
            payload['fiscal'].update(cfop='1102',ncm='00000000')
            operation = store.save_work_operation(s['company'],s['first'],payload,'Teste','tax-browser-operation')
        page.locator('.sidebar').get_by_role('link',name='Tributação e apuração',exact=True).click()
        frame.get_by_role('heading',name='Tributação e apuração',exact=True).wait_for()
        for kind,code in [('cfop','1102'),('ncm','00000000'),('service','SYN-1'),('revenue','0000')]:
            frame.get_by_label('Tabela do código',exact=True).select_option(kind)
            frame.get_by_label('Código cadastrado',exact=True).fill(code)
            frame.get_by_label('Descrição do código',exact=True).fill('Código inteiramente sintético')
            frame.get_by_label('Origem e versão da tabela',exact=True).fill('Fixture sem validade legal')
            frame.get_by_label('Vigência inicial do código',exact=True).fill('2026-01-01')
            frame.get_by_label('Motivo do cadastro do código',exact=True).fill('Teste sintético')
            frame.get_by_role('button',name='Salvar versão do código',exact=True).click()
            expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.get_by_label('Identificador da regra',exact=True).fill('tax-browser')
        frame.get_by_label('Nome da regra',exact=True).fill('Regra inteiramente sintética')
        for label,value in [('Tributo da regra','ICMS'),('Natureza da regra','entrada'),('Modelo da regra','55'),('Campo da base','total'),('Efeito na apuração','debito'),('Arredondamento da regra','meio_para_cima')]:
            frame.get_by_label(label,exact=True).select_option(value)
        frame.get_by_label('CFOP de escopo',exact=True).fill('1102')
        frame.get_by_label('NCM de escopo',exact=True).fill('00000000')
        frame.get_by_label('Código de receita da regra',exact=True).fill('0000')
        frame.get_by_label('Alíquota percentual informada',exact=True).fill('2.5')
        frame.get_by_label('Início da vigência da regra',exact=True).fill('2026-09-01')
        frame.get_by_label('Referência da validação da regra',exact=True).fill('Validação sintética')
        frame.get_by_label('Motivo da versão da regra',exact=True).fill('Teste de aprovação explícita')
        frame.get_by_role('button',name='Aprovar versão da regra',exact=True).click()
        frame.get_by_role('status').filter(has_text='Regra tributária versionada').wait_for()
        frame.get_by_text('Modelos reutilizáveis e cópia independente',exact=True).click()
        frame.get_by_label('Regra aprovada para modelo',exact=True).select_option(index=1)
        frame.get_by_label('Nome do modelo',exact=True).fill('Modelo sintético')
        frame.get_by_label('Motivo do modelo',exact=True).fill('Preservar versão')
        frame.get_by_role('button',name='Preservar modelo da regra',exact=True).click()
        frame.get_by_role('status').filter(has_text='Modelo preservado').wait_for()
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_label('Alíquota percentual informada',exact=True)).to_have_value('')
        frame.get_by_label('Empresa de origem do modelo',exact=True).select_option(str(s['company']))
        frame.get_by_label('Modelo a copiar',exact=True).select_option(index=1)
        frame.get_by_label('Identificador da regra copiada',exact=True).fill('copy-tax')
        frame.get_by_label('Nome da regra copiada',exact=True).fill('Cópia ajustável sintética')
        frame.get_by_label('Motivo da cópia',exact=True).fill('Teste de isolamento')
        frame.get_by_role('button',name='Copiar modelo como rascunho',exact=True).click()
        frame.get_by_role('status').filter(has_text='Modelo copiado como rascunho').wait_for()
        frame.get_by_role('button',name='Editar regra',exact=True).click()
        frame.get_by_label('Alíquota percentual informada',exact=True).fill('7')
        frame.get_by_label('Motivo da versão da regra',exact=True).fill('Alterar apenas o destino')
        frame.get_by_role('button',name='Salvar regra como rascunho',exact=True).click()
        frame.get_by_role('status').filter(has_text='Regra tributária versionada').wait_for()
        with AccountingStore(s['path']) as store:
            assert store.tax_rules(s['company'])[0]['spec']['rate']=='2.5'
            assert store.tax_rules(s['other'])[0]['spec']['rate']=='7'
            assert store.tax_rules(s['other'])[0]['state']=='rascunho'
        frame.locator('#company').select_option(str(s['company']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click()
        frame.get_by_role('button',name='Abrir operação',exact=True).click()
        frame.locator('#operation-reason').fill('Conferência tributária sintética')
        frame.get_by_role('button',name='Gerar prévia de tributação',exact=True).click()
        frame.get_by_role('button',name='Aplicar cálculo em nova versão',exact=True).wait_for()
        frame.get_by_role('button',name='Aplicar cálculo em nova versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Tributos calculados').wait_for()
        expect(frame.get_by_label('ICMS informado',exact=True)).to_have_value('2.51')
        frame.get_by_role('button',name='Conferir versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Versão conferida').wait_for()
        frame.get_by_role('button',name='Escriturar',exact=True).click()
        frame.get_by_role('status').filter(has_text='Operação escriturada').wait_for()
        page.locator('.sidebar').get_by_role('link',name='Tributação e apuração',exact=True).click()
        frame.get_by_role('button',name='Gerar prévia da apuração',exact=True).click()
        frame.get_by_role('button',name='Preservar versão da apuração',exact=True).wait_for()
        frame.get_by_label('Motivo da apuração ou validação',exact=True).fill('Revisão sintética')
        frame.get_by_role('button',name='Preservar versão da apuração',exact=True).click()
        frame.get_by_role('status').filter(has_text='Memória da apuração preservada').wait_for()
        frame.get_by_label('Conferi fatos, regras, vigência, tabelas, bases, efeitos e memória da apuração',exact=True).check()
        frame.get_by_role('button',name='Validar apuração conferida',exact=True).click()
        frame.get_by_role('status').filter(has_text='Apuração parametrizada validada').wait_for()
        with page.expect_download() as downloaded:
            frame.get_by_role('button',name='Baixar memória JSON',exact=True).click()
        memory = json.loads(Path(downloaded.value.path()).read_text())
        assert memory['snapshot']['totals'][0]['debito']=='2.51'
        assert memory['snapshot']['lines'][0]['rule']['catalog_references']['ncm']['code']=='00000000'
        if args.screenshots:page.screenshot(path=str(args.screenshots/'tributacao-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert frame.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth+1')
        if args.screenshots:page.screenshot(path=str(args.screenshots/'tributacao-mobile.png'),full_page=True)
        page.set_viewport_size({'width':1440,'height':1080})
        page.locator('.sidebar').get_by_role('link',name='Encerramento',exact=True).click()
        frame.get_by_label('Motivo do controle por módulo').fill('Fechamento após apuração parametrizada')
        frame.get_by_label('Referência da conferência da apuração').fill('Memória sintética validada')
        fiscal = frame.locator('[data-module="fiscal"]')
        for check in fiscal.locator('input[type=checkbox]').all():check.check()
        fiscal.get_by_role('button',name='Encerrar fiscal',exact=True).click()
        expect(fiscal.get_by_role('heading')).to_contain_text('encerrada')
        expect(frame.locator('[data-module="contabil"]').get_by_role('heading')).to_contain_text('aberta')
        print('PASS: four company code catalogs, approved percentage rule, independent draft model copy, calculation/review/post, assessed totals and JSON trace; mobile/no JS errors')


if __name__=='__main__':main()
