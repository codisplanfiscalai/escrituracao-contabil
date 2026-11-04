'use strict';
const $ = (selector) => document.querySelector(selector);
const token = $('meta[name="local-token"]').content;
let companies = [], current = emptyContext();
function emptyContext(){return {periods:[],plans:[],mappings:[],files:[],documents:[],audit:[],reconciliation:[],observations:[],batches:[],reviews:[],exports:[]};}
let generation = 0;
let busy = 0;
let removalPreview = null;
const labels = {id:'ID',company_id:'Empresa',period_id:'Período',name:'Nome',prosoft_company_code:'Código Prosoft',prosoft_plan_code:'Plano Prosoft',cnpj:'CNPJ',reference_competence:'Referência',processing_competence:'Processamento',label:'Versão',created_at:'Criado em',updated_at:'Atualizado em',code:'Código',description:'Descrição',parent_code:'Conta superior',kind:'Tipo',nature:'Natureza',source_account:'Origem',target_code:'Destino',valid_from:'Início',valid_to:'Fim',state:'Estado',reason:'Motivo',filename:'Arquivo',sha256:'SHA-256',status:'Situação',actor:'Responsável',action:'Operação',details:'Detalhes',plan_id:'Plano',attributes:'Atributos'};
function notice(message, error=false) { const node=$('#status'); node.textContent=message; node.classList.toggle('error',error); node.hidden=false; }
function companyId() { return $('#company').value; }
function periodId() { return $('#period').value; }
function setBusy(delta) { busy+=delta; document.querySelectorAll('form button[type="submit"]').forEach(b=>{b.disabled=busy>0 || (!!b.closest('[data-needs-company]') && !companyId());}); $('#refresh').disabled=busy>0;document.querySelectorAll('#company,#period,.tab').forEach(control=>control.disabled=busy>0);$('main').setAttribute('aria-busy',busy>0?'true':'false'); }
async function api(route, data={}, method='GET') {
  let url='/api/'+route; const options={method,keepalive:route==='fiscal-workspaces',cache:'no-store',headers:{'X-Local-Token':token}};
  if(method==='GET') { const query=new URLSearchParams(); Object.entries(data).forEach(([k,v])=>{if(v!==null && v!==undefined && v!=='')query.set(k,v);}); if(query.size)url+='?'+query; }
  else {options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}
  const response=await fetch(url,options); let body;
  try {body=await response.json();} catch {throw new Error('Resposta inválida do servidor local. Recarregue a página.');}
  if(!response.ok)throw new Error(body.error||'Operação não concluída.');
  return body.data;
}
function option(select,value,text){const element=document.createElement('option');element.value=String(value);element.textContent=text;select.append(element);}
function fillSelect(select,rows,empty,describe,oldValue=select.value){select.replaceChildren();option(select,'',empty);rows.forEach(row=>option(select,row.id,describe(row)));if(rows.some(row=>String(row.id)===oldValue))select.value=oldValue;}
function display(value){if(value===null || value===undefined || value==='')return '—';return typeof value==='object'?JSON.stringify(value,null,2):String(value);}
function table(selector,rows) {
  const area=typeof selector==='string'?$(selector):selector;area.replaceChildren();
  if(!Array.isArray(rows) || !rows.length){const p=document.createElement('p');p.className='empty';p.textContent=companyId()?'Nenhum registro neste recorte.':'Selecione uma empresa para consultar.';area.append(p);return;}
  const keys=[...new Set(rows.flatMap(row=>Object.keys(row)))];
  const table=document.createElement('table'),head=document.createElement('thead'),headRow=document.createElement('tr'),body=document.createElement('tbody');
  keys.forEach(key=>{const th=document.createElement('th');th.textContent=labels[key]||key;headRow.append(th);});head.append(headRow);
  rows.forEach(row=>{const tr=document.createElement('tr');keys.forEach(key=>{const td=document.createElement('td'),value=row[key],text=display(value);if(typeof value==='object'&&value!==null || text.length>180){const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Ver detalhes';pre.textContent=text;details.append(summary,pre);td.append(details);}else td.textContent=text;tr.append(td);});body.append(tr);});
  table.append(head,body);area.append(table);
}
function render(){
  removalPreview=null;
  $('#removal-confirm-form').hidden=true;
  fillSelect($('#removal-file'),current.files.filter(f=>f.status!=='excluido'),'Selecione um arquivo',f=>`#${f.id} · ${f.filename} · ${f.status}`);
  fillSelect($('#analysis-file'),current.files.filter(f=>f.status!=='excluido'),'Selecione um arquivo salvo',f=>`#${f.id} · ${f.filename} · ${f.kind}`);
  selectAnalysisProfile();
  ['periods','mappings','files','documents','audit'].forEach(key=>table('#'+key+'-list',current[key]));
  ['periods','plans','files','documents'].forEach(key=>$('#metric-'+key).textContent=current[key].length);
  const company=companies.find(c=>String(c.id)===companyId());
  $('#scope-info').textContent=company?`${company.name} · Empresa Prosoft ${company.prosoft_company_code} · Plano Prosoft ${company.prosoft_plan_code}`:'Cadastre ou selecione uma empresa para começar.';
  renderReconciliation();
  renderAccounting();
  fillSelect($('#accounting-plan'),current.plans,'Selecione um plano',p=>`${p.label} · v${p.version} · #${p.id}`);
  fillSelect($('#accounting-previous'),current.batches.filter(b=>b.status!=='substituido'),'Novo lote',b=>`#${b.id} · v${b.version} · ${b.status}`);
  table('#review-history',current.reviews);
  PostingEditor.refresh();
  setBusy(0);
}
async function loadCompanies(selected){companies=await api('companies');fillSelect($('#company'),companies,'Selecione uma empresa',c=>c.name,selected===undefined?companyId():String(selected));await loadContext();}
async function loadAccounts(){
  const plan=$('#mapping-plan').value,company=companyId();
  if(!company || !plan){table('#accounts-list',[]);$('#account-codes').replaceChildren();return;}
  const rows=await api('accounts',{company_id:company,plan_id:plan});
  if(company!==companyId() || plan!==$('#mapping-plan').value)return;
  table('#accounts-list',rows);const list=$('#account-codes');list.replaceChildren();rows.forEach(a=>{const item=document.createElement('option');item.value=a.code;item.textContent=a.description;list.append(item);});
}
async function loadContext(){
  setBusy(1);const requestedGeneration=generation+1;
  try{return await loadContextData();}
  catch(error){if(generation===requestedGeneration){current=emptyContext();render();table('#accounts-list',[]);$('#account-codes').replaceChildren();fillSelect($('#mapping-plan'),[],'Recarregue os dados',()=>'');}throw error;}
  finally{setBusy(-1);}
}
async function loadContextData(){
  const version=++generation,company=companyId();
  if(!company){FiscalEditor.clear();current=emptyContext();fillSelect($('#period'),[],'Todos os períodos',()=> '');fillSelect($('#mapping-plan'),[],'Selecione um plano',()=> '');render();await loadAccounts();return;}
  const responses=await Promise.all(['periods','plans','mappings','files','audit','accounting-batches','document-reviews','accounting-evidence'].map(key=>api(key,{company_id:company})));
  if(version!==generation || company!==companyId())return;
  ['periods','plans','mappings','files','audit','batches','reviews','exports'].forEach((key,i)=>current[key]=responses[i]);
  fillSelect($('#period'),current.periods,'Todos os períodos',p=>`Base ${p.reference_competence} · Movimentos ${p.processing_competence}`);
  fillSelect($('#mapping-plan'),current.plans,'Selecione um plano',p=>`${p.label} · v${p.version} · #${p.id}`);
  if(!$('#mapping-plan').value && current.plans.length)$('#mapping-plan').value=String(current.plans[0].id);
  const results=await Promise.all(['documents','reconciliation','observations'].map(route=>api(route,{company_id:company,period_id:periodId()})));
  if(version!==generation)return;
  ['documents','reconciliation','observations'].forEach((key,index)=>current[key]=results[index]);render();await loadAccounts();await FiscalEditor.load();
}
function element(tag,text){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;}
function renderReconciliation(){
  const area=$('#reconciliation-list');area.replaceChildren();
  const fieldLabels={total:'Valor do documento',issued_date:'Data de emissão',number:'Número',series:'Série',issuer:'Emitente',buyer:'Destinatário',key:'Chave NF-e',content_fingerprint:'Conteúdo XML',vLiq:'Líquido da fatura',vOrig:'Original da fatura',vDesc:'Desconto',vDup:'Valor da parcela',dVenc:'Vencimento',nFat:'Identificador da fatura',nDup:'Identificador da parcela'};
  const states={divergente:'Divergente',pendencia_de_origem:'Pendências na origem',coincidente_no_recorte:'Coincidente no recorte conferido',somente_xml:'Somente XML',somente_sped:'Somente SPED',aguardando_analise:'Aguardando análise das fontes salvas'};
  if(!current.reconciliation.length)area.append(element('p','Nenhum documento identificado neste recorte. Confira os arquivos e as observações pendentes.'));
  current.reconciliation.forEach(doc=>{
    const card=element('article');card.className='card';
    card.append(element('h3',`Documento #${doc.document_id} · ${states[doc.state]||doc.state}`),element('p',`Chave NF-e: ${doc.business_key}`));
    if(doc.unindexed_file_ids.length)card.append(element('p',`Arquivos ainda sem análise: ${doc.unindexed_file_ids.join(', ')}. Use a análise dos arquivos salvos em Documentos.`));
    const sourceArea=element('div');sourceArea.className='table-area';card.append(sourceArea);
    table(sourceArea,doc.sources.filter(source=>source.entity_kind==='documento').map(source=>({'Observação':source.id,'Arquivo':`#${source.file_id} · ${source.filename}`,'Formato':source.source_kind,'Localização':source.locator,'Período da fonte':source.period_id,'Situação da fonte':source.file_status,'Campos conferidos':Object.fromEntries(Object.entries(source.normalized).filter(([key])=>!['key','content_fingerprint'].includes(key)).map(([key,value])=>[fieldLabels[key]||key,value])),'Pendências':source.issues})));
    if(doc.differences.length){card.append(element('h4','Diferenças que exigem conferência'));const diffArea=element('div');diffArea.className='table-area';card.append(diffArea);table(diffArea,doc.differences.flatMap(diff=>diff.values.map(value=>({'Entidade':diff.entity||'documento','Campo':fieldLabels[diff.field]||diff.field,'Arquivo':'#'+value.file_id,'Localização':value.locator,'Valor na origem':value.value}))));}
    if(doc.issues.length){doc.issues.forEach(row=>{const remaining=row.unresolved_messages||row.messages;const issue=element('p',`${row.file_id?'Arquivo #'+row.file_id+' · ':''}${row.locator||''}: ${remaining.length?remaining.join('; '):'Identidade associada por decisão explícita.'}${row.resolved_messages?.length?' Histórico preservado: '+row.resolved_messages.join('; '):''}`);issue.className=remaining.length?'error-text':'muted';card.append(issue);});}
    card.append(element('h4',`Faturas identificadas: ${doc.invoices.length}`));
    doc.invoices.forEach(invoice=>{
      card.append(element('p',`Fatura #${invoice.id} · ${invoice.reference} · ${invoice.status}`));
      const details=element('details'),summary=element('summary','Valores e fontes da fatura'),pre=element('pre',JSON.stringify({valores:invoice.payload,origens:invoice.sources.map(s=>({arquivo:s.file_id,local:s.locator,valores:s.normalized,situacao:s.file_status}))},null,2));details.append(summary,pre);card.append(details);
      const parts=element('div');parts.className='table-area';card.append(parts);table(parts,invoice.installments.map(part=>({'Parcela':`#${part.id} · ${part.reference}`,'Vencimento':part.payload.dVenc,'Valor recebido':part.payload.vDup,'Situação':part.status,'Origens':part.sources.map(s=>({arquivo:s.file_id,local:s.locator,valores:s.normalized,situacao:s.file_status}))})));
    });
    renderBillingAssociation(card,doc);
    renderDocumentReview(card,doc);
    area.append(card);
  });
  const pending=current.observations.filter(row=>row.issues.length && (row.entity_kind==='registro'||!row.document_id||(row.entity_kind==='fatura'&&!row.invoice_id)||(row.entity_kind==='parcela'&&!row.installment_id)));
  table('#observation-list',pending.map(row=>({'Arquivo':`#${row.file_id} · ${row.filename}`,'Localização':row.locator,'Situação da fonte':row.file_status,'Pendências originais':row.issues,'Decisão de identidade':current.reconciliation.flatMap(d=>d.sources).find(s=>s.id===row.id)?.billing_resolution||'Sem associação válida','Conteúdo de origem':row.raw})));
}
function renderBillingAssociation(card,doc){
  const sources=doc.sources.filter(s=>s.source_kind==='XML'&&s.file_status!=='excluido');
  const candidates=[...new Set(sources.filter(s=>(s.entity_kind==='fatura'&&!s.invoice_id)||(s.entity_kind==='parcela'&&!s.installment_id)).map(s=>s.file_id))];
  const history=doc.billing_associations||[];
  if(history.length){const details=element('details'),summary=element('summary','Histórico de associações de cobrança'),area=element('div');area.className='table-area';table(area,history.map(h=>({'Decisão':h.id,'Arquivo':h.file_id,'Versão':h.version,'Vigente':h.current&&h.valid,'Motivo':h.reason,'Ator':h.actor,'Bloqueios':h.blockers,'Correspondências':h.snapshot.proposal})));details.append(summary,area);card.append(details);}
  if(!candidates.length||!doc.invoices.length)return;
  const section=element('section');section.className='billing-association';section.append(element('h4','Conferir referências de cobrança'),element('p','Associe referências diferentes somente quando valores e vencimentos coincidirem. Os registros originais permanecem preservados. Dados ausentes, valores divergentes e parcelas repetidas continuam bloqueados.'));
  const form=element('form');form.dataset.needsCompany='';form.className='billing-proposal';
  const file=labeledControl(form,'Arquivo com referência pendente','select','file_id');option(file,'','Selecione o arquivo');candidates.forEach(id=>{const source=sources.find(s=>s.file_id===id);option(file,id,`#${id} · ${source.filename}`);});
  const invoice=labeledControl(form,'Fatura canônica do documento','select','invoice_id');option(invoice,'','Selecione explicitamente a fatura');doc.invoices.forEach(i=>option(invoice,i.id,`#${i.id} · ${i.reference} · líquido ${i.payload.vLiq||'ausente'}`));
  const linksArea=element('div');form.append(linksArea);const previewButton=element('button','Conferir correspondências');previewButton.type='submit';form.append(previewButton);section.append(form);
  const confirm=element('form');confirm.dataset.needsCompany='';confirm.className='billing-confirm';confirm.hidden=true;const comparison=element('div');comparison.className='table-area';confirm.append(comparison);
  const reason=labeledControl(confirm,'Justificativa da associação','textarea','reason');reason.maxLength=2000;reason.rows=2;const checked=confirmedControl(confirm,'Conferi a relação 1:1 e confirmo a associação sem alterar os valores originais.');
  const save=element('button','Registrar associação de cobrança');save.type='submit';confirm.append(save);section.append(confirm);card.append(section);
  let proposal=null,preview=null,links=[];
  function invalidate(){preview=null;proposal=null;confirm.hidden=true;checked.checked=false;}
  function choose(){
    invalidate();links=[];linksArea.replaceChildren();const target=doc.invoices.find(i=>String(i.id)===invoice.value);
    const sourceInvoice=sources.find(s=>String(s.file_id)===file.value&&s.entity_kind==='fatura');
    if(sourceInvoice)linksArea.append(element('p',`Origem: fatura ${sourceInvoice.normalized.nFat||'sem identificador'} · original ${sourceInvoice.normalized.vOrig||'ausente'} · desconto ${sourceInvoice.normalized.vDesc||'ausente'} · líquido ${sourceInvoice.normalized.vLiq||'ausente'}`));
    if(!target||!file.value)return;
    sources.filter(s=>String(s.file_id)===file.value&&s.entity_kind==='parcela').forEach(source=>{
      const control=labeledControl(linksArea,`Origem ${source.normalized.nDup||'sem identificador'} · ${source.normalized.dVenc||'sem vencimento'} · ${source.normalized.vDup||'sem valor'} → parcela canônica`,'select','installment_'+source.id);option(control,'','Selecione explicitamente');
      target.installments.forEach(part=>option(control,part.id,`#${part.id} · ${part.reference} · ${part.payload.dVenc||'ausente'} · ${part.payload.vDup||'ausente'}`));control.addEventListener('change',invalidate);links.push({source,control});
    });
  }
  file.addEventListener('change',choose);invoice.addEventListener('change',choose);
  form.addEventListener('submit',async event=>{event.preventDefault();if(busy)return;invalidate();setBusy(1);try{
    proposal={company_id:companyId(),document_id:doc.document_id,period_id:doc.period_id,file_id:file.value,invoice_id:invoice.value,installment_links:links.map(({source,control})=>({observation_id:source.id,installment_id:control.value}))};
    preview=await api('billing-association-preview',proposal,'POST');
    table(comparison,[{'Entidade':'Fatura','Origem':preview.invoice.source.normalized,'Destino':preview.invoice.target.payload},...preview.installments.map(p=>({'Entidade':'Parcela','Origem':p.source.normalized,'Destino':p.target.payload}))]);confirm.hidden=false;notice('Correspondência conferida. Revise a prévia, informe o motivo e confirme.');
  }catch(error){invalidate();notice(error.message,true);}finally{setBusy(-1);}});
  localAction(confirm,async()=>{if(!preview||!proposal||proposal.company_id!==companyId()||!checked.checked)throw new Error('Gere e confira novamente a prévia de associação.');await api('billing-associations',{...proposal,expected_fingerprint:preview.expected_fingerprint,reason:reason.value,confirmed:true},'POST');});
}
function selectAnalysisProfile(){const file=current.files.find(row=>String(row.id)===$('#analysis-file').value);$('#analysis-profile').value=file?(file.kind==='XML'?'nfe-nfce-4.00-header-billing-v4':'efd-icms-ipi-020-c100-v2'):'';}
function formObject(form){return Object.fromEntries(new FormData(form));}
function bindForm(selector,handler){$(selector).addEventListener('submit',async event=>{event.preventDefault();const form=event.currentTarget;if(busy)return;setBusy(1);try{const result=await handler(form);notice(result?.message || 'Operação concluída. Os dados foram salvos localmente.',!!result?.error);}catch(error){notice(error.message,true);}finally{setBusy(-1);}});}
bindForm('#company-form',async form=>{const result=await api('companies',formObject(form),'POST');form.reset();await loadCompanies(result.id);});
bindForm('#period-form',async form=>{if(!companyId())throw new Error('Selecione uma empresa.');const result=await api('periods',{...formObject(form),company_id:companyId()},'POST');await loadContext();$('#period').value=String(result.id);await loadContext();});
bindForm('#plan-form',async form=>{if(!companyId())throw new Error('Selecione uma empresa.');const data=formObject(form);try{data.accounts=JSON.parse(data.accounts);}catch{throw new Error('O JSON das contas está inválido. Confira aspas, vírgulas e colchetes.');}if(!Array.isArray(data.accounts))throw new Error('Informe uma lista JSON de contas.');const result=await api('plans',{...data,company_id:companyId()},'POST');await loadContext();$('#mapping-plan').value=String(result.id);await loadAccounts();});
bindForm('#mapping-form',async form=>{if(!companyId())throw new Error('Selecione uma empresa.');const data=formObject(form);if(!data.valid_to)data.valid_to=null;await api('mappings',{...data,company_id:companyId()},'POST');await loadContext();});
bindForm('#file-form',async form=>{
  const company=companyId(),period=periodId();if(!company || !period)throw new Error('Selecione a empresa e um período de trabalho antes de importar.');
  const data=formObject(form);
  const file=$('#upload-file').files[0];if(!file)throw new Error('Selecione um arquivo.');if(file.size>10*1024*1024)throw new Error('Arquivo acima de 10 MiB. O envio base64 precisa caber no limite de 15 MiB.');
  const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
  const result=await api('files',{company_id:company,period_id:period,filename:file.name,kind:data.kind,sped_profile:data.kind==='SPED'?(data.sped_profile||null):null,content_base64:btoa(binary)},'POST');$('#upload-file').value='';await loadContext();
  const details=result.metadata?.error || result.metadata?.warning || '';
  return {message:result.duplicate?'Arquivo já recebido anteriormente. Nenhuma cópia foi criada.':`Arquivo recebido. Situação: ${result.status}. ${details}`,error:result.status==='rejeitado'||!!result.metadata?.error};
});
$('#file-form [name="kind"]').addEventListener('change',event=>{$('#sped-profile').disabled=event.target.value!=='SPED';});
$('#analysis-file').addEventListener('change',selectAnalysisProfile);
bindForm('#analysis-form',async form=>{if(!companyId())throw new Error('Selecione uma empresa.');const data=formObject(form);const result=await api('file-analysis',{...data,company_id:companyId()},'POST');await loadContext();return {message:result.duplicate?'Análise já registrada. Consulte Conciliação e as observações pendentes.':'Análise parcial registrada. Confira Conciliação e as observações pendentes.'};});
bindForm('#removal-preview-form',async()=>{
  const company=companyId(),file=$('#removal-file').value;
  if(!company || !file)throw new Error('Selecione a empresa e o arquivo.');
  const preview=await api('file-preview',{company_id:company,file_id:file});
  removalPreview={...preview,company_id:company};
  $('#removal-details').textContent=`Arquivo #${preview.file_id}: ${preview.filename}. Documentos afetados: ${preview.document_ids.length?preview.document_ids.join(', '):'nenhum'}. Faturas: ${preview.invoice_ids.join(', ')||'nenhuma'}. Parcelas: ${preview.installment_ids.join(', ')||'nenhuma'}. ${preview.consequence} ${preview.removal_blocked?'REMOÇÃO BLOQUEADA: lotes contábeis '+preview.closed_batch_ids.join(', ')+'; fichas fiscais protegidas '+(preview.protected_fiscal_entry_ids||[]).join(', '):''}`;
  $('#removal-confirm-form').reset();$('#removal-confirm-form').hidden=preview.removal_blocked;
  return {message:preview.removal_blocked?'Remoção bloqueada por período fiscal protegido ou lote fechado. As fontes serão preservadas.':'Confira as dependências, informe o motivo e confirme a remoção lógica.',error:preview.removal_blocked};
});
$('#removal-file').addEventListener('change',()=>{removalPreview=null;$('#removal-confirm-form').hidden=true;});
bindForm('#removal-confirm-form',async form=>{
  const preview=removalPreview;
  if(!preview || preview.company_id!==companyId() || String(preview.file_id)!==$('#removal-file').value)throw new Error('Confira novamente a prévia do arquivo.');
  if(!form.elements.confirmed.checked)throw new Error('Confirme que leu as consequências.');
  await api('file-removal',{company_id:preview.company_id,file_id:preview.file_id,preview_token:preview.preview_token,reason:form.elements.reason.value,confirmed:true},'POST');
  form.reset();await loadContext();return {message:'Arquivo removido logicamente. Original e histórico preservados; documentos vinculados ficam pendentes.'};
});
document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-current',b===button?'page':'false');});document.querySelectorAll('.panel').forEach(panel=>panel.hidden=panel.id!==button.dataset.panel);}));
$('#company').addEventListener('change',()=>{generation++;current=emptyContext();render();table('#accounts-list',[]);fillSelect($('#period'),[],'Todos os períodos',()=> '');fillSelect($('#mapping-plan'),[],'Selecione um plano',()=> '');loadContext().catch(e=>notice(e.message,true));});
$('#period').addEventListener('change',()=>loadContext().catch(e=>notice(e.message,true)));
$('#mapping-plan').addEventListener('change',()=>loadAccounts().catch(e=>notice(e.message,true)));
$('#refresh').addEventListener('click',()=>loadCompanies().then(()=>notice('Dados locais atualizados.')).catch(e=>notice(e.message,true)));
function labeledControl(form,labelText,tag,name){const label=element('label',labelText),control=element(tag);control.name=name;control.required=true;label.append(control);form.append(label);return control;}
function confirmedControl(form,text){const label=element('label'),check=element('input');check.type='checkbox';check.required=true;label.append(check,document.createTextNode(' '+text));form.append(label);return check;}
function localAction(form,handler){form.addEventListener('submit',async event=>{event.preventDefault();if(busy)return;setBusy(1);try{await handler();await loadContext();notice('Decisão registrada localmente. Confira o estado e os bloqueios.');}catch(error){notice(error.message,true);}finally{setBusy(-1);}});}
function renderDocumentReview(card,doc){
  card.append(element('h4','Decisão documental'));
  card.append(element('p',doc.review?`Revisão v${doc.review.version} · ${doc.review.valid?'fontes conferidas ainda vigentes':'CADUCA: fontes alteradas'} · fonte escolhida #${doc.review.chosen_observation_id} · ator local ${doc.review.actor}`:'Nenhuma revisão documental registrada.'));
  card.append(element('p',doc.readiness_for_accounting?'Documento disponível para prévia contábil explícita. Exportação Prosoft permanece indisponível.':`Bloqueios contábeis: ${doc.accounting_blockers.join('; ')}`));
  const active=doc.sources.filter(row=>row.entity_kind==='documento'&&row.file_status!=='excluido'&&row.period_id===doc.period_id);
  if(!active.length)return;
  const form=element('form');form.dataset.needsCompany='';
  const select=labeledControl(form,'Fonte escolhida após conferir diferenças','select','chosen_observation_id');option(select,'','Selecione explicitamente uma fonte');
  active.forEach(row=>option(select,row.id,`Observação #${row.id} · arquivo #${row.file_id} · ${row.filename} · total ${row.normalized.total}`));
  const reason=labeledControl(form,'Motivo da decisão','textarea','reason');reason.maxLength=2000;reason.rows=2;
  const checked=confirmedControl(form,'Conferi as fontes e diferenças acima. Esta seleção não associa títulos de identidade desconhecida.');
  const button=element('button','Registrar nova decisão');button.type='submit';form.append(button);card.append(form);
  localAction(form,async()=>{if(!checked.checked)throw new Error('Confirme a conferência das fontes.');await api('document-reviews',{company_id:companyId(),document_id:doc.document_id,period_id:doc.period_id,chosen_observation_id:select.value,expected_fingerprint:doc.source_fingerprint,reason:reason.value},'POST');});
}
function renderAccounting(){
  const area=$('#accounting-list');area.replaceChildren();
  const batches=current.batches.filter(batch=>!periodId()||String(batch.period_id)===periodId());
  if(!batches.length)area.append(element('p','Nenhuma prévia neste período.'));
  batches.forEach(batch=>{
    const card=element('article');card.className='card';card.append(element('h3',`Lote #${batch.id} · v${batch.version} · ${batch.status}`));
    card.append(element('p',`Débitos ${batch.snapshot.totals.debit} · Créditos ${batch.snapshot.totals.credit} · Anterior ${batch.previous_batch_id||'—'}`));
    if(batch.current_blockers.length){const warning=element('p',`Conferência atual: ${batch.current_blockers.join('; ')}`);warning.className='error-text';card.append(warning);}
    if(batch.status==='fechado')card.append(element('p','Snapshot histórico preservado. A conferência atual acima não altera o fechamento registrado.'));
    const details=element('details'),summary=element('summary','Examinar partidas, contas, versões e fontes do snapshot'),pre=element('pre',JSON.stringify(batch.snapshot,null,2));details.append(summary,pre);card.append(details);
    card.append(element('p',`Hash do snapshot: ${batch.snapshot_hash}`));
    if(['previa','revisado'].includes(batch.status)){
      const form=element('form');form.dataset.needsCompany='';
      const reason=labeledControl(form,'Motivo da revisão / fechamento local','textarea','reason');reason.rows=2;reason.maxLength=2000;
      const checked=confirmedControl(form,'Examinei o snapshot e confirmo esta etapa local.');
      const button=element('button',batch.status==='previa'?'Marcar prévia como revisada':'Fechar lote localmente');button.type='submit';form.append(button);card.append(form);
      localAction(form,async()=>{if(!checked.checked)throw new Error('Confira o snapshot.');await api(batch.status==='previa'?'accounting-review':'accounting-close',{company_id:companyId(),batch_id:batch.id,snapshot_hash:batch.snapshot_hash,reason:reason.value},'POST');});
    }
    if(batch.status==='fechado')renderEvidence(card,batch);
    area.append(card);
  });
}
function renderEvidence(card,batch){
  card.append(element('h4','Evidências para conferência'));
  card.append(element('p','Pacote próprio JSON/CSV do fechamento histórico. Não é arquivo de importação Prosoft nem escrituração fiscal oficial.'));
  const form=element('form');form.dataset.needsCompany='';
  const reason=labeledControl(form,'Motivo da geração de evidências','textarea','reason');reason.rows=2;reason.maxLength=2000;
  const submit=element('button','Preparar evidências do fechamento');submit.type='submit';form.append(submit);card.append(form);
  localAction(form,()=>api('accounting-evidence',{company_id:companyId(),batch_id:batch.id,snapshot_hash:batch.snapshot_hash,reason:reason.value},'POST'));
  current.exports.filter(item=>item.batch_id===batch.id).forEach(item=>{
    card.append(element('p',`Evidência #${item.id} · ${item.profile} · SHA-256 do manifesto: ${item.manifest_sha256}`));
    const actions=element('div');actions.className='download-actions';
    item.artifacts.forEach(artifact=>{const button=element('button',`Baixar ${artifact.name}`);button.type='button';button.className='secondary';
      button.addEventListener('click',async()=>{if(busy)return;const company=companyId();setBusy(1);button.disabled=true;try{
        const query=new URLSearchParams({company_id:company,export_id:item.id,name:artifact.name});
        const response=await fetch('/api/accounting-evidence-file?'+query,{cache:'no-store',headers:{'X-Local-Token':token}});
        if(!response.ok){const error=await response.json();throw new Error(error.error||'Falha ao baixar evidência.');}
        const bytes=await response.arrayBuffer();const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
        if(hash!==artifact.sha256||bytes.byteLength!==artifact.size)throw new Error('Evidência recebida não confere com o hash e tamanho registrados.');
        const url=URL.createObjectURL(new Blob([bytes],{type:artifact.media_type})),link=element('a');link.href=url;link.download=`escritura-lote-${batch.id}-${artifact.name}`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
        await loadContext();notice('Evidência conferida por SHA-256 e enviada ao download. A leitura ficou registrada no histórico.');
      }catch(error){notice(error.message,true);}finally{button.disabled=false;setBusy(-1);}});actions.append(button);
    });card.append(actions);
  });
}
bindForm('#accounting-form',async form=>{
  if(!companyId()||!periodId())throw new Error('Selecione empresa e período de trabalho.');
  const data=formObject(form);data.entries=PostingEditor.read();
  data.previous_batch_id=data.previous_batch_id||null;
  const batch=await api('accounting-batches',{...data,company_id:companyId(),period_id:periodId()},'POST');
  await loadContext();return {message:`Prévia #${batch.id} registrada. Examine o snapshot para revisar e fechar localmente.`};
});
const FiscalEditor=(()=>{
  let tabs=[],active=null,entries=[],parties=[],period=null,scope='',chain=Promise.resolve(),pending=0,saveError=null,creating=false;
  const form=()=>$('#fiscal-form'), uuid=()=>crypto.randomUUID();
  const scopeNow=()=>companyId()+':'+periodId();
  function blank(){return {data:{model:'55',operation:'entrada'},reason:'',expected_version:0,request_key:uuid(),period_id:periodId()};}
  function capture(){const value=structuredClone(active.data);value.data=formObject(form());value.reason=$('#fiscal-reason').value;value.as_proposal=$('#fiscal-proposal').checked;value.period_id=$('#fiscal-target-period').value;return value;}
  function persist(){
    if(!active)return Promise.resolve();
    const tab=active,payload=capture();tab.data=payload;pending++;$('#fiscal-draft-state').textContent='Salvando rascunho…';
    const operation=chain.then(async()=>{const result=await api('fiscal-workspaces',{company_id:tab.company_id,period_id:tab.period_id,title:tab.title,data:payload,request_key:tab.request_key,workspace_id:tab.id,version:tab.version},'POST');tab.version=result.version;saveError=null;});
    chain=operation.catch(e=>{saveError=e;notice('Rascunho não salvo: '+e.message,true);}).finally(()=>{pending--;if(!pending&&!saveError&&active===tab)$('#fiscal-draft-state').textContent='Guia salva · versão '+tab.version;});
    return operation;
  }
  async function flush(){await chain;if(saveError)throw saveError;}
  function adapt(){const service=form().elements.operation.value.startsWith('servico_');if(service)form().elements.model.value='SERVICO';else if(form().elements.model.value==='SERVICO')form().elements.model.value='55';form().querySelectorAll('[data-service]').forEach(n=>n.hidden=!service&&!n.querySelector('input')?.value);form().elements.key.disabled=service;form().elements.series.required=!service;}
  function displayActive(){
    form().hidden=!active;
    const nav=$('#fiscal-tabs');nav.replaceChildren();
    tabs.forEach(tab=>{const b=element('button',tab.title);b.type='button';b.setAttribute('aria-selected',String(tab===active));b.addEventListener('click',async()=>{try{if(active)await persist();await flush();active=tab;displayActive();}catch(e){notice(e.message,true);}});nav.append(b);});
    if(!active)return;
    form().reset();for(const [k,v] of Object.entries(active.data.data||{})){if(form().elements[k])form().elements[k].value=v??'';}
    fillSelect($('#fiscal-target-period'),current.periods,'Selecione competência',p=>p.processing_competence+' · base '+p.reference_competence,String(active.data.period_id||periodId()));
    fillSelect($('#fiscal-participant'),parties,'Não vinculado',p=>p.name+' · '+p.identifier_value+(p.pending?' · conferir':''),String(active.data.data?.participant_id||''));
    $('#fiscal-reason').value=active.data.reason||'';$('#fiscal-proposal').checked=!!active.data.as_proposal;adapt();$('#fiscal-draft-state').textContent='Guia persistida · versão '+active.version;
  }
  async function createTab(payload,title){
    if(creating)return;creating=true;form().inert=true;
    try{if(active)await persist();await flush();if(!companyId()||!periodId())throw Error('Selecione empresa e competência.');
    const tab=await api('fiscal-workspaces',{company_id:companyId(),period_id:periodId(),title,data:payload,request_key:uuid()},'POST');tabs.push(tab);active=tab;displayActive();}
    finally{creating=false;form().inert=false;}
  }
  function clear(){tabs=[];active=null;entries=[];parties=[];period=null;scope='';form().hidden=true;['#fiscal-tabs','#fiscal-entries','#fiscal-parties','#fiscal-period-history'].forEach(s=>$(s).replaceChildren());$('#fiscal-period-status').textContent='Selecione uma competência.';}
  function renderEntries(){
    const area=$('#fiscal-entries');area.replaceChildren();
    entries.forEach(entry=>{
      const card=element('article');card.className='card';const r=entry.current;
      card.append(element('h3',`Ficha #${entry.id} · ${r?'v'+r.version+' · '+r.state:'Somente proposta de retificação'}`));
      if(r){card.append(element('p',`${r.data.operation} · ${r.data.model} · ${r.data.number} · emissão ${r.data.issued_date} · escrituração ${r.data.posting_date} · ${r.data.total}`));r.warnings.forEach(w=>card.append(element('p',w)));if(!entry.source_current)card.append(element('p','Fontes alteradas: prepare nova versão para revisão.'));
        const edit=element('button','Editar ficha #'+entry.id);edit.type='button';edit.addEventListener('click',()=>createTab({data:r.data,reason:'',entry_id:entry.id,document_id:entry.document_id,expected_version:r.version,expected_source_hash:entry.source_hash,period_id:r.period_id,request_key:uuid()},'Editar #'+entry.id).catch(e=>notice(e.message,true)));card.append(edit);
        if(r.state==='rascunho'){const review=element('form');review.dataset.needsCompany='';const reason=labeledControl(review,'Motivo da revisão fiscal','input','reason');reason.required=true;const ack=confirmedControl(review,'Conferi os avisos, as datas e os valores desta versão.');const b=element('button','Revisar ficha #'+entry.id);b.type='submit';review.append(b);review.addEventListener('submit',async e=>{e.preventDefault();setBusy(1);try{await flush();await api('fiscal-review',{company_id:companyId(),entry_id:entry.id,snapshot_hash:r.snapshot_hash,reason:reason.value,acknowledged:ack.checked},'POST');await loadContext();notice('Revisão fiscal registrada.');}catch(error){notice(error.message,true);}finally{setBusy(-1);}});card.append(review);}
      }
      const history=element('details');history.append(element('summary','Histórico e propostas ('+entry.history.length+')'));entry.history.forEach(v=>history.append(element('pre',JSON.stringify({version:v.version,state:v.state,actor:v.actor,created_at:v.created_at,reason:v.reason,review_actor:v.review_actor,review_reason:v.review_reason,data:v.data,source_hash:v.source_hash},null,2))));card.append(history);area.append(card);
    });
  }
  function renderParties(){
    const area=$('#fiscal-parties');area.replaceChildren();
    parties.forEach(p=>{const card=element('article');card.className='card';card.append(element('h3',p.name||'Nome pendente'),element('p',p.identifier_kind+' '+p.identifier_value+' · '+p.roles.join(', ')));if(p.pending){const f=element('form');const select=labeledControl(f,'Nome de origem a adotar','select','observation_id');option(select,'','Selecione após conferir');p.observations.filter(o=>o.name).forEach(o=>option(select,o.id,o.name+' · '+o.source));const reason=labeledControl(f,'Motivo da decisão cadastral','input','reason');reason.required=true;const b=element('button','Revisar terceiro #'+p.id);b.type='submit';f.append(b);f.addEventListener('submit',async e=>{e.preventDefault();setBusy(1);try{await api('participant-review',{company_id:companyId(),participant_id:p.id,version:p.version,observation_id:select.value,reason:reason.value},'POST');await loadContext();}catch(error){notice(error.message,true);}finally{setBusy(-1);}});card.append(f);}const d=element('details');d.append(element('summary','Origens e divergências'),element('pre',JSON.stringify(p.observations,null,2)));card.append(d);area.append(card);});
  }
  async function load(){
    await flush();const requested=scopeNow(),g=generation;
    if(!companyId()||!periodId()){clear();return;}
    const base={company_id:companyId(),period_id:periodId()};const values=await Promise.all(['fiscal-workspaces','fiscal-entries','participants','fiscal-period'].map(r=>api(r,base)));
    if(g!==generation||requested!==scopeNow())return;
    const selected=scope===requested?active?.id:null;scope=requested;[tabs,entries,parties,period]=values;active=tabs.find(t=>t.id===selected)||tabs[0]||null;
    fillSelect($('#fiscal-source'),current.documents,'Selecione origem',d=>`#${d.id} · ${d.payload.model} · ${d.payload.number}`);displayActive();renderEntries();renderParties();
    $('#fiscal-period-status').textContent=`Competência ${period.competence} · ${period.state} · ${period.entries.length} fichas vigentes. Fechamentos contábeis permanecem protegidos.`;table('#fiscal-period-history',period.history);setBusy(0);
  }
  function init(){
    window.EscrituraFiscalFlush=async()=>{if(active)await persist();await flush();};
    $('#fiscal-new').addEventListener('click',()=>createTab(blank(),'Novo lançamento '+(tabs.length+1)).catch(e=>notice(e.message,true)));
    $('#fiscal-prepare').addEventListener('click',async()=>{try{await flush();const seed=await api('fiscal-seed',{company_id:companyId(),period_id:periodId(),document_id:$('#fiscal-source').value});const existing=entries.find(e=>e.document_id===seed.document_id||e.current?.data.key&&e.current.data.key===seed.data.key);await createTab({...blank(),data:existing?.current?.data||seed.data,entry_id:existing?.id,expected_version:existing?.current?.version||0,document_id:seed.document_id,expected_source_hash:seed.source_hash},'Documento #'+seed.document_id);}catch(e){notice(e.message,true);}});
    form().addEventListener('input',()=>{if(active){adapt();persist().catch(()=>{});}});
    $('#fiscal-flush').addEventListener('click',()=>persist().catch(e=>notice(e.message,true)));
    $('#fiscal-close-tab').addEventListener('click',async()=>{try{await persist();await flush();const t=active;await api('fiscal-workspaces',{company_id:t.company_id,period_id:t.period_id,workspace_id:t.id,version:t.version,title:t.title,data:t.data,request_key:t.request_key,closed:true},'POST');active=null;await load();}catch(e){notice(e.message,true);}});
    $('#fiscal-participant').addEventListener('change',()=>{const p=parties.find(p=>String(p.id)===$('#fiscal-participant').value);if(p){const side=form().elements.operation.value==='entrada'||form().elements.operation.value==='servico_tomado'?'issuer':'buyer';form().elements[side].value=p.identifier_value;persist().catch(()=>{});}});
    bindForm('#fiscal-form',async()=>{await persist();await flush();const tab=active,payload=structuredClone(tab.data);for(const k of ['total','iss_base','iss_amount'])if(payload.data[k])payload.data[k]=payload.data[k].replace(',','.');const row=await api('fiscal-entries',{...payload,company_id:tab.company_id},'POST');tab.data={...tab.data,entry_id:row.entry_id,expected_version:row.state==='retificacao_pendente'?tab.data.expected_version:row.version,request_key:uuid()};form().hidden=false;const updated=await api('fiscal-workspaces',{company_id:tab.company_id,period_id:tab.period_id,workspace_id:tab.id,version:tab.version,title:tab.title,data:tab.data,request_key:tab.request_key},'POST');Object.assign(tab,updated);await loadContext();return {message:row.state==='retificacao_pendente'?'Proposta registrada. O vigente não mudou.':'Versão fiscal salva para revisão.'};});
    bindForm('#fiscal-party-form',async f=>{await api('participants',{company_id:companyId(),...formObject(f)},'POST');await loadContext();return {message:'Terceiro localizado/cadastrado. Divergências preservadas para revisão.'};});
    bindForm('#fiscal-period-form',async f=>{if(!period)throw Error('Selecione competência.');const d=formObject(f);await api('fiscal-period',{...d,company_id:companyId(),period_id:periodId(),token:period.token,confirmed:f.elements.confirmed.checked},'POST');await loadContext();return {message:'Operação do período registrada com histórico.'};});
    window.addEventListener('beforeunload',e=>{if(pending||saveError){e.preventDefault();e.returnValue='';}});
  }
  return {init,load,clear};
})();
FiscalEditor.init();

PostingEditor.init({context:()=>({company:companyId(),period:periodId(),plan:$('#accounting-plan').value,periods:current.periods,mappings:current.mappings,documents:current.reconciliation}),onError:notice});
loadCompanies().catch(error=>notice(error.message,true));
