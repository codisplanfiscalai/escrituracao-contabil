"""Synthetic CSV receipts, reviewed versions, byte downloads and tenant reset."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from browser_support import scenario, expect
from src.persistence import AccountingStore


def run(mode,args):
    with scenario(mode,chart=False) as s:
        page,frame=s['page'],s['frame']
        if mode=='portal':page.locator('.sidebar').get_by_role('link',name='Tributação e apuração',exact=True).click()
        else:frame.locator('.work-nav').get_by_role('button',name='Tributação e apuração',exact=True).click()
        frame.get_by_role('heading',name='Tributação e apuração',exact=True).wait_for()
        frame.get_by_text('Importar cadastros com origem, versão e jurisdição',exact=True).click()
        panel=frame.locator('.catalog-import')
        raw=b'\xef\xbb\xbfcode;description;valid_from;valid_to\r\n1102;Codigo inteiramente sintetico A;2026-01-01;\r\n2102;Codigo inteiramente sintetico B;2026-01-01;\r\n'
        panel.locator('#catalog-import-file').set_input_files({'name':'sintetico.csv','mimeType':'text/csv','buffer':raw})
        for label,value in [('Órgão ou publicador declarado','Publicador sintético'),('URL da fonte declarada','https://example.invalid/tabela'),('Edição ou versão da fonte','SYN-1'),('Data de consulta da fonte',date.today().isoformat()),('Conversão e conferência do arquivo','Fixture criada no padrão, sem validade oficial'),('Motivo da recepção do cadastro','Teste sintético')]:
            panel.get_by_label(label,exact=True).fill(value)
        panel.get_by_role('button',name='Preservar arquivo sem ativar',exact=True).click()
        frame.get_by_role('status').filter(has_text='Arquivo preservado').wait_for()
        with AccountingStore(s['path']) as store:
            assert store.tax_catalog(s['company'])==[] and store.work_cycles(s['company'])==[]
        with page.expect_download() as downloaded:panel.get_by_role('button',name='Baixar arquivo recebido',exact=True).click()
        assert Path(downloaded.value.path()).read_bytes()==raw
        panel.get_by_role('button',name='Selecionar esta página',exact=True).click()
        panel.get_by_label('Aplicar a partir de',exact=True).fill('2026-09-01')
        panel.get_by_role('button',name='Conferir prévia dos códigos selecionados',exact=True).click()
        panel.get_by_label('Referência da revisão do cadastro',exact=True).fill('Conferência sintética de conteúdo, escopo e datas')
        panel.get_by_label('Motivo da aplicação do cadastro',exact=True).fill('Teste sintético')
        panel.get_by_label('Conferi conteúdo, origem declarada, vigências, códigos selecionados e jurisdição',exact=True).check()
        if args.screenshots:
            panel.get_by_label('Aplicar a partir de',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.screenshots/f'catalogo-{mode}-desktop.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
            panel.get_by_label('Aplicar a partir de',exact=True).scroll_into_view_if_needed()
            assert frame.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth+1')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(args.screenshots/f'catalogo-{mode}-mobile.png'),full_page=True,animations='disabled')
            page.set_viewport_size({'width':1440,'height':1080})
        panel.get_by_role('button',name='Ativar códigos conferidos nesta empresa',exact=True).click()
        frame.get_by_role('status').filter(has_text='Códigos selecionados ativados').wait_for()
        with page.expect_download() as downloaded:panel.get_by_role('button',name='Baixar manifesto da aplicação',exact=True).click()
        manifest=json.loads(Path(downloaded.value.path()).read_text())['snapshot']
        assert manifest['metadata']['edition']=='SYN-1' and len(manifest['versions'])==2
        with AccountingStore(s['path']) as store:
            current=store.resolve_tax_code(s['company'],'cfop','1102','2026-09-01')
            assert current['data']['import_origin']['raw_sha256']==hashlib.sha256(raw).hexdigest()
        second=b'code;description;valid_from;valid_to\n1102;Segunda edicao sintetica;2026-01-01;\n'
        panel.locator('#catalog-import-file').set_input_files({'name':'sintetico-v2.csv','mimeType':'text/csv','buffer':second})
        panel.get_by_label('Edição ou versão da fonte',exact=True).fill('SYN-2')
        panel.get_by_role('button',name='Preservar arquivo sem ativar',exact=True).click()
        frame.get_by_role('status').filter(has_text='Arquivo preservado').wait_for()
        panel.get_by_label('Selecionar código 1102',exact=True).check()
        panel.get_by_label('Aplicar a partir de',exact=True).fill('2026-10-01')
        panel.get_by_role('button',name='Conferir prévia dos códigos selecionados',exact=True).click()
        panel.get_by_label('Conferi conteúdo, origem declarada, vigências, códigos selecionados e jurisdição',exact=True).check()
        panel.get_by_role('button',name='Ativar códigos conferidos nesta empresa',exact=True).click()
        frame.get_by_role('status').filter(has_text='Códigos selecionados ativados').wait_for()
        with AccountingStore(s['path']) as store:
            assert store.resolve_tax_code(s['company'],'cfop','1102','2026-09-01')['version']==1
            assert store.resolve_tax_code(s['company'],'cfop','1102','2026-10-01')['version']==2
            assert store.resolve_tax_code(s['company'],'cfop','2102','2026-10-01')['state']=='ativo'
            assert store.work_cycles(s['company'])==[]
        frame.locator('#company').select_option(str(s['other']))
        expect(frame.locator('.workbench')).to_have_attribute('aria-busy','false')
        expect(panel.get_by_role('heading',name='Arquivo preservado',exact=False)).to_have_count(0)
        expect(panel.get_by_label('Órgão ou publicador declarado',exact=True)).to_have_value('')
        expect(panel.locator('#catalog-import-file')).to_have_value('')
        print('PASS '+mode+': receipt without period/activation, exact CSV bytes, reviewed selective code versions, provenance manifest, previous vigency, no removal of missing codes, mobile and tenant reset')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    for mode in ('local','portal'):run(mode,args)


if __name__=='__main__':main()
