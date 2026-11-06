"""Synthetic organized XML -> explicit draft preparation -> observed item evidence."""
import argparse
import json
from pathlib import Path
from browser_support import scenario,expect
from src.persistence import AccountingStore
from test_document_preparation import item_xml


def run(mode,args):
    with scenario(mode) as s:
        with AccountingStore(s['path']) as store:
            policy=store.save_work_policy(s['company'],s['plan'],'entrada','2026-08','Política sintética',s['accounts']['1.1.1'],s['accounts']['2.1'],'Teste',True)
            for n in (1,2):
                source=store.receive_sources(s['company'],[{'filename':f'synthetic-{n}.xml','content':item_xml(n)}],f'input-{n}')['items'][0]
                store.organize_source(s['company'],source['input_id'],s['first'],source['snapshot_hash'],'Teste')
            originals=[tuple(r) for r in store.db.execute('SELECT id,original,sha256 FROM files')]
        page,frame=s['page'],s['frame'];page.reload()
        def nav():
            if mode=='portal':page.locator('.sidebar').get_by_role('link',name='Escrituração',exact=True).click()
            else:frame.locator('.work-nav').get_by_role('button',name='Escrituração',exact=True).click()
        nav();frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.get_by_text('Preparar operações dos documentos organizados',exact=True).click()
        frame.get_by_role('button',name='Selecionar documentos visíveis para preparar',exact=True).click()
        frame.get_by_label('Natureza da preparação',exact=True).select_option('entrada')
        frame.get_by_label('Política da preparação',exact=True).select_option(str(policy['id']))
        frame.get_by_label('Data de escrituração dos documentos',exact=True).fill('2026-09-20')
        frame.get_by_label('Modo dos itens na preparação',exact=True).select_option('propor_itens_xml')
        frame.get_by_label('Total atribuído aos itens',exact=True).select_option('vProd')
        frame.get_by_label('icms_base',exact=True).check()
        frame.get_by_role('button',name='Gerar prévia da preparação',exact=True).click()
        expect(frame.get_by_text('Rascunhos podem ser preparados após conferência.',exact=True)).to_be_visible()
        expect(frame.get_by_role('button',name='Criar rascunhos da prévia',exact=True)).to_be_disabled()
        frame.get_by_role('button',name='Inspecionar caminhos do documento 1',exact=True).click()
        expect(frame.locator('pre').filter(has_text='imposto/ICMS/ICMS00/vBC')).to_have_count(1)
        with AccountingStore(s['path']) as store:
            assert store.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0]==0
        frame.get_by_label('Motivo da preparação dos documentos',exact=True).fill('Preparação sintética revisada')
        frame.get_by_label('Referência da conferência da preparação',exact=True).fill('Fixture sem validade fiscal')
        frame.get_by_label('Conferi documentos, origens, política, data e cópias; autorizo somente criar rascunhos',exact=True).check()
        if args.screenshots:
            frame.get_by_role('heading',name='Prévia da preparação dos documentos',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/f'preparation-{mode}-desktop.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
            frame.get_by_role('heading',name='Prévia da preparação dos documentos',exact=True).scroll_into_view_if_needed()
            assert frame.locator('body').evaluate('el=>el.scrollWidth<=innerWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/f'preparation-{mode}-mobile.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':1440,'height':1080})
        def lose(route):
            response=route.fetch()
            if not response.ok:route.fulfill(response=response);return
            route.abort('failed')
        page.route('**/api/document-preparation-apply',lose)
        frame.get_by_role('button',name='Criar rascunhos da prévia',exact=True).click()
        expect(frame.locator('.alert.error')).to_have_count(1)
        page.unroute('**/api/document-preparation-apply',lose)
        frame.get_by_role('button',name='Criar rascunhos da prévia',exact=True).click()
        frame.get_by_role('status').filter(has_text='Somente rascunhos foram criados').wait_for()
        with AccountingStore(s['path']) as store:
            operations=store.work_operations(s['company'],s['first'])
            assert len(operations)==2 and all(o['state']=='rascunho' for o in operations)
            assert len(store.document_preparations(s['company'],s['first']))==1
            for table in ('work_movements','finance_titles','tax_calculations'):assert store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
            assert [tuple(r) for r in store.db.execute('SELECT id,original,sha256 FROM files')]==originals
            assert all(not o['validation']['ready'] for o in operations)
        with page.expect_download() as download:frame.get_by_role('button',name='Baixar preparação e evidências XML',exact=True).click()
        manifest=json.loads(Path(download.value.path()).read_text())
        assert len(manifest['operations'])==2
        assert manifest['operations'][0]['payload']['tax_items'][0]['values']=={'total':'60.00','icms_base':'60.00'}
        frame.get_by_role('button',name='Abrir operação',exact=True).first.click()
        frame.get_by_text('Valores observados do XML da ficha',exact=True).click()
        expect(frame.get_by_label('CFOP do item',exact=True).first).to_have_value('')
        expect(frame.get_by_label('Componentes a calcular',exact=True).first).to_have_value('')
        expect(frame.get_by_label('ICMS informado',exact=True)).to_have_value('')
        page.reload();nav()
        frame.get_by_text('Preparar operações dos documentos organizados',exact=True).click()
        frame.get_by_role('button',name='Consultar últimas 50 preparações',exact=True).click()
        frame.get_by_role('button',name=f'Abrir preparação {manifest["id"]}',exact=True).click()
        frame.get_by_role('heading',name=f'Manifesto da preparação #{manifest["id"]}',exact=True).wait_for()
        frame.locator('#period').select_option(str(s['second']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_role('button',name='Baixar preparação e evidências XML',exact=True)).to_have_count(0)
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_role('button',name='Selecionar documentos visíveis para preparar',exact=True)).to_be_disabled()
        print('PASS '+mode+': organized documents, explicit policy/date/item copies, paths/raw values/absences, no writes in preview, lost-response retry, saved drafts only/no postings, original bytes retained, XML evidence in ficha, manifest reload/download, mobile and context reset')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    for mode in ('local','portal'):run(mode,args)


if __name__=='__main__':main()
