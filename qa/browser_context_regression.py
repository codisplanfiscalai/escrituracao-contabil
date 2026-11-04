"""Optional Chromium regression for delayed/failed context changes.
Run with an environment that already has Playwright and Chromium installed:
    python qa/browser_context_regression.py
Synthetic data only; isolated temporary database. No download/installation here.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import json
from playwright.sync_api import sync_playwright
from test_local_app import LocalApplicationTests
case=LocalApplicationTests();case.setUp()
try:
 cid,review,data=case.accounting_fixture();case.api('document-reviews',review);batch=case.api('accounting-batches',data)
 case.api('accounting-review',{'company_id':cid,'batch_id':batch['id'],'snapshot_hash':batch['snapshot_hash'],'reason':'Conferência sintética da regressão'})
 old_period=data['period_id'];new_period=case.api('periods',{'company_id':cid,'reference_competence':'2026-09','processing_competence':'2026-10'})['id']
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page()
  errors=[];posts=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:posts.append(r.url) if r.method=='POST' else None)
  page.goto(case.origin);page.wait_for_function('() => companies.length===1 && busy===0');page.select_option('#company',str(cid));page.wait_for_function('() => current.batches.length===1 && busy===0');page.select_option('#period',str(old_period));page.wait_for_function('() => busy===0');page.locator('[data-panel=accounting]').click()
  page.locator('#accounting-list textarea[name=reason]').fill('Conferência sintética com atraso controlado');page.locator('#accounting-list input[type=checkbox]').check()
  held=[];pattern='**/api/accounting-batches?*';page.route(pattern,lambda route:held.append(route))
  page.select_option('#period',str(new_period));page.wait_for_function('() => busy>0');page.wait_for_timeout(200);assert len(held)==1
  assert page.locator('#accounting-list button[type=submit]').is_disabled()
  assert page.evaluate("[...document.querySelectorAll('#company,#period,.tab,form button[type=submit]')].every(x=>x.disabled)")
  page.locator('#accounting-list form').evaluate("form=>form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
  page.locator('#period-form').evaluate("form=>form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
  page.wait_for_timeout(100);assert not posts,posts
  held[0].continue_();page.unroute(pattern);page.wait_for_function('() => busy===0');assert page.locator('#accounting-list button[type=submit]').count()==0
  assert case.api(f'accounting-batches?company_id={cid}')[0]['status']=='revisado';print('PASS latency: pending period change disables actions/context; programmatic submits suppressed; success replaces old cards; original batch remains reviewed')
  page.select_option('#period',str(old_period));page.wait_for_function('() => busy===0');page.locator('#accounting-list textarea[name=reason]').fill('Conferência sintética com falha controlada');page.locator('#accounting-list input[type=checkbox]').check()
  held=[];page.route(pattern,lambda route:held.append(route));page.select_option('#period',str(new_period));page.wait_for_timeout(200);assert len(held)==1
  held[0].abort('failed');page.unroute(pattern);page.wait_for_function('() => busy===0');old_action=page.locator('#accounting-list button[type=submit]')
  result={'selected_period':page.locator('#period').input_value(),'original_batch_period':str(old_period),'stale_action_count':old_action.count(),'stale_action_enabled':old_action.is_enabled() if old_action.count() else False,'status':page.locator('#status').inner_text(),'js_errors':errors}
  if result['stale_action_enabled']:
   old_action.click();page.wait_for_function('() => busy===0');result['batch_after_stale_action']=case.api(f'accounting-batches?company_id={cid}')[0]['status'];result['post_requests']=posts
  result['batch_after_failed_load']=case.api(f'accounting-batches?company_id={cid}')[0]['status'];assert result['stale_action_count']==0,result;assert result['batch_after_failed_load']=='revisado',result;assert not errors,errors;print('PASS NETWORK FAILURE:',json.dumps(result,ensure_ascii=False));browser.close()
finally:case.tearDown()
