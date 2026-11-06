"""Processed XML events, reviewed annotations and historical posting proofs."""
import argparse
import json
from pathlib import Path
from browser_support import scenario,expect
from src.persistence import AccountingStore
from test_nfe_events import event_xml,document_xml


def run(mode,args):
    with scenario(mode) as s:
        with AccountingStore(s['path']) as store:
            policy=store.save_work_policy(s['company'],s['plan'],'entrada','2026-08','Política sintética',s['accounts']['1.1.1'],s['accounts']['2.1'],'Teste',True)
            source=store.receive_sources(s['company'],[{'filename':'documento.xml','content':document_xml()}],'document')['items'][0]
            doc=store.organize_source(s['company'],source['input_id'],s['first'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
            operation=store.save_work_operation(s['company'],s['first'],store.prepare_work_operation(s['company'],s['first'],doc,policy_id=policy['id']),'Teste','draft')
            original=[tuple(r) for r in store.db.execute('SELECT id,original,sha256 FROM files')]
        page,frame=s['page'],s['frame'];page.reload()
        def nav():
            if mode=='portal':page.locator('.sidebar').get_by_role('link',name='Recepção',exact=True).click()
            else:frame.locator('.work-nav').get_by_role('button',name='Recepção',exact=True).click()
        nav();frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        path=s['temp']/'evento-sintetico.xml';path.write_bytes(event_xml(kind='110110'))
        frame.locator('#source-files').set_input_files(path)
        frame.get_by_role('button',name='Receber arquivos',exact=True).click()
        frame.get_by_role('status').filter(has_text='Origens recebidas').wait_for()
        panel=frame.locator('.nfe-events-panel');panel.locator('summary').first.click()
        panel.get_by_role('button',name='Consultar eventos recebidos',exact=True).click()
        panel.get_by_role('button',name='Conferir evento 2',exact=True).click()
        expect(panel.get_by_text('Autorização não verificada.',exact=False)).to_be_visible()
        panel.get_by_text('Campos e caminhos observados do evento',exact=True).click()
        expect(panel.locator('tbody').filter(has_text='xCorrecao')).to_have_count(1)
        with AccountingStore(s['path']) as store:
            assert not store.get_work_operation(s['company'],operation['operation_id'])['validation']['ready']
            assert store.db.execute('SELECT COUNT(*) FROM nfe_event_reviews').fetchone()[0]==0
        expect(panel.get_by_role('button',name='Registrar decisão do evento',exact=True)).to_be_disabled()
        panel.get_by_label('Decisão sobre o evento',exact=True).select_option('manter_fluxo')
        panel.get_by_label('Motivo da decisão do evento',exact=True).fill('Conferência sintética sem efeito legal presumido')
        panel.get_by_label('Referência da conferência externa do evento',exact=True).fill('Fixture controlada, sem autorização real')
        panel.get_by_label('Conferi origens, retorno, ambiente e consequências; esta anotação não aplica efeito fiscal',exact=True).check()
        if args.screenshots:
            panel.get_by_role('heading',name='Conferência do evento 110110 / 1',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/f'events-{mode}-desktop.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':390,'height':844})
            panel.get_by_role('heading',name='Conferência do evento 110110 / 1',exact=True).scroll_into_view_if_needed()
            assert frame.locator('body').evaluate('el=>el.scrollWidth<=innerWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/f'events-{mode}-mobile.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':1440,'height':1080})
        def lose(route):
            response=route.fetch()
            if not response.ok:route.fulfill(response=response);return
            route.abort('failed')
        page.route('**/api/nfe-event-review',lose)
        panel.get_by_role('button',name='Registrar decisão do evento',exact=True).click()
        expect(frame.locator('.alert.error')).to_have_count(1)
        page.unroute('**/api/nfe-event-review',lose)
        panel.get_by_role('button',name='Registrar decisão do evento',exact=True).click()
        panel.get_by_role('status').filter(has_text='Decisão #').wait_for()
        with AccountingStore(s['path']) as store:
            op=store.get_work_operation(s['company'],operation['operation_id'])
            assert op['validation']['ready'] and op['payload']==operation['payload']
            assert store.db.execute('SELECT COUNT(*) FROM nfe_event_reviews').fetchone()[0]==1
            for table in ('work_movements','finance_titles'):assert store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
            assert [tuple(r) for r in store.db.execute('SELECT id,original,sha256 FROM files')]==original
            store.review_work_operation(s['company'],op['operation_id'],op['snapshot_hash'],'Conferência explícita')
            store.post_work_operation(s['company'],op['operation_id'],op['snapshot_hash'],'Escrituração explícita')
            proof=store.nfe_event_posting_proof(s['company'],op['operation_id'])
        page.reload();nav();panel=frame.locator('.nfe-events-panel');panel.locator('summary').first.click()
        panel.get_by_role('button',name='Consultar eventos recebidos',exact=True).click()
        panel.get_by_role('button',name='Conferir evento 2',exact=True).click()
        panel.get_by_role('button',name='Consultar evidência de eventos na escrituração',exact=True).click()
        expect(panel.get_by_text('Evidência histórica da escrituração',exact=True)).to_be_visible()
        with page.expect_download() as downloaded:panel.get_by_role('button',name='Baixar conferência e histórico do evento',exact=True).click()
        manifest=json.loads(Path(downloaded.value.path()).read_text())
        assert manifest['posting_proof']==proof and len(manifest['history'])==1
        with page.expect_download() as downloaded:panel.get_by_role('button',name='Baixar original do evento 2',exact=True).click()
        assert Path(downloaded.value.path()).read_bytes()==event_xml(kind='110110')
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(panel.locator('.event-review')).to_have_count(0)
        expect(panel).to_contain_text('0 identidades')
        print('PASS '+mode+': event intake, observed paths/text, pending posting block, explicit external review, lost-response retry without duplicates, no automatic changes/postings/titles, historical posting proof, exact original download, reload, mobile and tenant reset')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    for mode in ('local','portal'):run(mode,args)
