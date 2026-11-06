"""Explicit selection, all-or-none preview, lost-response retry and durable manifest."""
import argparse
import json
from pathlib import Path
from browser_support import scenario, expect
from src.persistence import AccountingStore
from test_persistence import fake_xml


def run(mode,args):
    with scenario(mode) as s:
        ids=[]
        with AccountingStore(s['path']) as store:
            policy=store.save_work_policy(s['company'],s['plan'],'entrada','2026-08','Política sintética',s['accounts']['1.1.1'],s['accounts']['2.1'],'Teste',True)
            store.save_tax_rule(s['company'],'batch','Regra sintética',{'tax':'ICMS','rate':'2.5','base_field':'total','effect':'debito','operation':'entrada','model':'55',
                'valid_from':'2026-09-01','rounding':'meio_para_cima','validation_reference':'Fixture sem validade legal'},'aprovada',0,'Teste')
            for n,total in ((1,'100.00'),(2,'200.00')):
                source=store.receive_sources(s['company'],[{'filename':f'Batch-{n}.xml','content':fake_xml(number=n,total=total,billing=False)}],f'source-{n}')['items'][0]
                doc=store.organize_source(s['company'],source['input_id'],s['first'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
                payload=store.prepare_work_operation(s['company'],s['first'],doc,policy_id=policy['id'])
                row=store.save_work_operation(s['company'],s['first'],payload,'Teste','operation-'+str(n));ids.append(row['operation_id'])
        page,frame=s['page'],s['frame'];page.reload()
        def nav(label):
            if mode=='portal':page.locator('.sidebar').get_by_role('link',name=label,exact=True).click()
            else:frame.locator('.work-nav').get_by_role('button',name=label,exact=True).click()
        frame.locator('#period').select_option(str(s['first']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        frame.get_by_role('button',name='Abrir operação',exact=True).last.click()
        frame.get_by_label('Observações',exact=True).fill('Alteração sintética ainda não salva')
        nav('Tributação e apuração')
        frame.get_by_text('Tributação em lote com prévia e conferência',exact=True).click()
        frame.get_by_role('button',name='Selecionar visíveis sem memória',exact=True).click()
        for operation_id in ids:expect(frame.get_by_label(f'Selecionar operação {operation_id} para tributação',exact=True)).to_be_checked()
        frame.get_by_role('button',name='Gerar prévia tributária do lote',exact=True).click()
        expect(frame.locator('.alert.error')).to_contain_text('Salve as alterações')
        nav('Escrituração');frame.locator('#operation-reason').fill('Salvar alteração sintética')
        frame.get_by_role('button',name='Salvar versão',exact=True).click()
        frame.get_by_role('status').filter(has_text='Versão salva').wait_for()
        with AccountingStore(s['path']) as store:
            row=store.get_work_operation(s['company'],ids[1]);payload=row['payload'];payload['fiscal']['total']=''
            store.save_work_operation(s['company'],s['first'],payload,'Teste','incomplete',ids[1],row['version'])
        nav('Tributação e apuração')
        frame.get_by_role('button',name='Gerar prévia tributária do lote',exact=True).click()
        expect(frame.get_by_text('Existem pendências; nenhuma operação pode ser aplicada neste lote.',exact=True)).to_be_visible()
        expect(frame.get_by_role('button',name='Aplicar lote em novas versões de rascunho',exact=True)).to_be_disabled()
        with AccountingStore(s['path']) as store:
            assert store.tax_batches(s['company'],s['first'])['total']==0
            row=store.get_work_operation(s['company'],ids[1]);payload=row['payload'];payload['fiscal']['total']='200.00'
            store.save_work_operation(s['company'],s['first'],payload,'Teste','corrected',ids[1],row['version'])
            originals={i:store.get_work_operation(s['company'],i) for i in ids}
        frame.get_by_role('button',name='Gerar prévia tributária do lote',exact=True).click()
        expect(frame.get_by_text('Todas as operações calculáveis; confira a memória de cada ficha.',exact=True)).to_be_visible()
        frame.get_by_role('button',name=f'Inspecionar memória da operação {ids[0]}',exact=True).click()
        frame.get_by_label('Motivo da tributação em lote',exact=True).fill('Conferência sintética do lote')
        confirmation=frame.get_by_label('Conferi todas as operações selecionadas, regras, bases, taxas, efeitos e valores da prévia do lote',exact=True)
        confirmation.check()
        if args.screenshots:
            frame.get_by_role('heading',name='Prévia da tributação em lote',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/f'batch-{mode}-desktop.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
            frame.get_by_role('heading',name='Prévia da tributação em lote',exact=True).scroll_into_view_if_needed()
            assert frame.locator('body').evaluate('el=>el.scrollWidth<=innerWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/f'batch-{mode}-mobile.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':1440,'height':1080})
        responses=[];intercepted=[]
        def lose_response(route):
            intercepted.append('request')
            response=route.fetch()
            intercepted.append(response.status)
            if not response.ok:
                responses.append(response.text()[:1000]);route.fulfill(response=response);return
            route.abort('failed')
        page.route('**/api/tax-batch-apply',lose_response)
        frame.get_by_role('button',name='Aplicar lote em novas versões de rascunho',exact=True).click()
        try:expect(frame.locator('.alert.error')).to_have_count(1)
        except AssertionError:
            current=next(f for f in page.frames if mode=='local' or f.url.endswith('/workspace')) if mode=='local' else page.frames[-1]
            print('BATCH_FAILURE',intercepted,responses,current.evaluate('()=>({busy:work.busy,error:work.error,notice:work.notice,confirmed:work.taxBatchConfirmed,attempt:work.taxBatchAttempt,receipt:work.taxBatchReceipt?.id})'),flush=True)
            raise
        assert not responses,responses
        page.unroute('**/api/tax-batch-apply',lose_response)
        frame.get_by_role('button',name='Aplicar lote em novas versões de rascunho',exact=True).click()
        frame.get_by_role('status').filter(has_text='aplicado em rascunhos').wait_for()
        with AccountingStore(s['path']) as store:
            history=store.tax_batches(s['company'],s['first']);assert history['total']==1
            assert store.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0]==2
            for operation_id in ids:
                current=store.get_work_operation(s['company'],operation_id)
                assert current['version']==originals[operation_id]['version']+1 and current['state']=='rascunho'
                for key in ('entries','finance'):assert current['payload'][key]==originals[operation_id]['payload'][key]
            for table in ('work_movements','finance_titles'):assert store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
        expect(frame.locator('input[aria-label^="Selecionar operação"]')).to_have_count(0)
        frame.get_by_label('Exibir somente operações sem memória',exact=True).uncheck()
        expect(frame.locator('input[aria-label^="Selecionar operação"]')).to_have_count(2)
        nav('Escrituração')
        expect(frame.get_by_label('ICMS informado',exact=True)).to_have_value('2.50')
        expect(frame.get_by_role('button',name='Conferir versão',exact=True)).to_be_enabled()
        nav('Tributação e apuração')
        with page.expect_download() as download:frame.get_by_role('button',name='Baixar manifesto e memórias do lote',exact=True).click()
        manifest=json.loads(Path(download.value.path()).read_text())
        assert len(manifest['snapshot']['items'])==len(manifest['calculations'])==2
        page.reload();nav('Tributação e apuração')
        frame.get_by_text('Tributação em lote com prévia e conferência',exact=True).click()
        frame.get_by_role('button',name='Consultar histórico de lotes tributários',exact=True).click()
        frame.get_by_role('button',name=f'Abrir manifesto do lote {manifest["id"]}',exact=True).click()
        frame.get_by_role('heading',name=f'Manifesto do lote #{manifest["id"]}',exact=True).wait_for()
        frame.locator('#period').select_option(str(s['second']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_role('button',name='Baixar manifesto e memórias do lote',exact=True)).to_have_count(0)
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(frame.get_by_role('button',name='Gerar prévia tributária do lote',exact=True)).to_be_disabled()
        print('PASS '+mode+': unsaved tabs blocked, per-document blockers/all-or-none preview, explicit review, known lost-response retry without duplicate, draft tab synchronized, no postings/finance effects, durable manifest/download/reload, mobile and context reset')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    for mode in ('local','portal'):run(mode,args)


if __name__=='__main__':main()
