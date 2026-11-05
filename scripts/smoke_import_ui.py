"""Synthetic archive intake without a period; per-member errors and original download."""
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'qa'),str(Path(__file__).resolve().parents[1]/'tests')]
from browser_support import scenario
from test_batch_import import zip_bytes
from test_persistence import fake_xml
from playwright.sync_api import expect

with scenario('local',chart=False) as s:
    page=s['page'];page.locator('.work-nav').get_by_role('button',name='Recepção',exact=True).click()
    packed=zip_bytes([('pasta/ficticio.xml',fake_xml()),('ruim.xml',b'<broken')])
    page.locator('#source-files').set_input_files({'name':'pacote.zip','mimeType':'application/zip','buffer':packed})
    page.get_by_role('button',name='Receber arquivos',exact=True).click()
    expect(page.locator('.workbench')).to_have_attribute('aria-busy','false')
    expect(page.locator('.alert.error')).to_have_count(0)
    expect(page.locator('#period')).to_have_value('')
    expect(page.get_by_role('cell',name='ruim.xml',exact=False)).to_be_visible()
    row=page.get_by_role('row').filter(has=page.get_by_role('cell',name='pacote.zip',exact=False))
    row.get_by_role('button',name='Decisões e versões',exact=True).click()
    expect(page.get_by_role('heading',name='Decisões · pacote.zip',exact=True)).to_be_visible()
    expect(page.get_by_text('Versão 2 · pacote',exact=False)).to_be_visible()
    with page.expect_download() as event:row.get_by_role('link',name='Original',exact=True).click()
    download=event.value
    assert Path(download.path()).read_bytes()==packed
    page.reload();expect(page.get_by_role('cell',name='ruim.xml',exact=False)).to_be_visible()
    expect(page.locator('.alert.error')).to_have_count(0)
    print('PASS: ZIP com XML válido e erro individual; recepção sem competência/plano; download byte a byte; reload persistente')
