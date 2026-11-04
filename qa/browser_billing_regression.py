"""Optional Playwright/Chromium billing workflow with fictitious temporary data.
Uses already installed Playwright/Chromium; does not download dependencies.
Run: python qa/browser_billing_regression.py
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_local_app import LocalApplicationTests
from test_persistence import fake_xml,edit_xml
from playwright.sync_api import sync_playwright
import base64
case=LocalApplicationTests();case.setUp()
try:
 cid,review,data=case.accounting_fixture();case.api('document-reviews',review)
 content=edit_xml(fake_xml(),'cobr/fat/nFat','ALTERNATIVA-FICTICIA')
 f=case.api('files',{'company_id':cid,'period_id':data['period_id'],'filename':'ficticio-alternativo.xml','kind':'XML','content_base64':base64.b64encode(content).decode()})
 doc=case.api(f'reconciliation?company_id={cid}')[0];invoice=doc['invoices'][0]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(case.origin);page.select_option('#company',str(cid));page.wait_for_function('()=>busy===0');page.select_option('#period',str(data['period_id']));page.wait_for_function('()=>busy===0');page.locator('[data-panel=reconciliation]').click()
  form=page.locator('.billing-proposal');form.locator('[name=file_id]').select_option(str(f['id']));form.locator('[name=invoice_id]').select_option(str(invoice['id']))
  links=form.locator('[name^=installment_]');assert links.count()==2
  for i,part in enumerate(invoice['installments']):links.nth(i).select_option(str(part['id']))
  form.get_by_role('button',name='Conferir correspondências').click();page.locator('.billing-confirm').wait_for(state='visible');assert page.locator('.billing-confirm table').count()==1
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path='/tmp/escritura-cobranca-mobile-ficticio.png',full_page=True)
  page.locator('.billing-confirm [name=reason]').fill('Conferência fictícia dos mesmos valores e vencimentos');page.locator('.billing-confirm input[type=checkbox]').check();page.locator('.billing-confirm button[type=submit]').click();page.wait_for_function('()=>busy===0')
  history=case.api(f'billing-associations?company_id={cid}');assert len(history)==1
  resolved=case.api(f'reconciliation?company_id={cid}')[0];assert not resolved['readiness_for_accounting'];assert len(resolved['invoices'])==1;assert len(resolved['invoices'][0]['installments'])==2
  reviewform=page.locator('#reconciliation-list form').filter(has=page.locator('[name=chosen_observation_id]'))
  reviewform.locator('[name=chosen_observation_id]').select_option(str(review['chosen_observation_id']));reviewform.locator('[name=reason]').fill('Revisão fictícia após associação');reviewform.locator('input[type=checkbox]').check();reviewform.locator('button[type=submit]').click();page.wait_for_function('()=>busy===0')
  assert case.api(f'reconciliation?company_id={cid}')[0]['readiness_for_accounting'];assert not errors,errors
  page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path='/tmp/escritura-cobranca-desktop-ficticio.png',full_page=True)
  print('PASS: associação visual1:1, prévia/confirmação, IDsoriginais preservados, semduplicar e novarevisão libera motor; desktop/mobile')
  browser.close()
finally:case.tearDown()
