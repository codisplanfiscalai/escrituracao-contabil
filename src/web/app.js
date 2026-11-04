'use strict';
const $ = (selector) => document.querySelector(selector);
const token = $('meta[name="local-token"]').content;
let companies = [], current = emptyContext();
function emptyContext(){return {periods:[],plans:[],mappings:[],files:[],documents:[],audit:[],reconciliation:[],observations:[]};}
let generation = 0;
let busy = 0;
let removalPreview = null;
const labels = {id:'ID',company_id:'Empresa',period_id:'Período',name:'Nome',prosoft_company_code:'Código Prosoft',prosoft_plan_code:'Plano Prosoft',cnpj:'CNPJ',reference_competence:'Referência',processing_competence:'Processamento',label:'Versão',created_at:'Criado em',updated_at:'Atualizado em',code:'Código',description:'Descrição',parent_code:'Conta superior',kind:'Tipo',nature:'Natureza',source_account:'Origem',target_code:'Destino',valid_from:'Início',valid_to:'Fim',state:'Estado',reason:'Motivo',filename:'Arquivo',sha256:'SHA-256',status:'Situação',actor:'Responsável',action:'Operação',details:'Detalhes',plan_id:'Plano',attributes:'Atributos'};
function notice(message, error=false) { const node=$('#status'); node.textContent=message; node.classList.toggle('error',error); node.hidden=false; }
function companyId() { return $('#company').value; }
function periodId() { return $('#period').value; }
function setBusy(delta) { busy+=delta; document.querySelectorAll('form button[type="submit"]').forEach(b=>{b.disabled=busy>0 || (!!b.closest('[data-needs-company]') && !companyId());}); $('#refresh').disabled=busy>0;document.querySelectorAll('#company,#period,.tab').forEach(control=>control.disabled=busy>0);$('main').setAttribute('aria-busy',busy>0?'true':'false'); }
async function api(route, data={}, method='GET') {
  let url='/api/'+route; const options={method,cache:'no-store',headers:{'X-Local-Token':token}};
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
  fillSelect($('#analysis-file'),current.files.filter(f=>!['excluido','rejeitado'].includes(f.status)),'Selecione um arquivo salvo',f=>`#${f.id} · ${f.filename} · ${f.kind}`);
  selectAnalysisProfile();
  ['periods','mappings','files','documents','audit'].forEach(key=>table('#'+key+'-list',current[key]));
  ['periods','plans','files','documents'].forEach(key=>$('#metric-'+key).textContent=current[key].length);
  const company=companies.find(c=>String(c.id)===companyId());
  $('#scope-info').textContent=company?`${company.name} · Empresa Prosoft ${company.prosoft_company_code} · Plano Prosoft ${company.prosoft_plan_code}`:'Cadastre ou selecione uma empresa para começar.';
  renderReconciliation();
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
  const version=++generation,company=companyId();
  if(!company){current=emptyContext();fillSelect($('#period'),[],'Todos os períodos',()=> '');fillSelect($('#mapping-plan'),[],'Selecione um plano',()=> '');render();await loadAccounts();return;}
  const responses=await Promise.all(['periods','plans','mappings','files','audit'].map(key=>api(key,{company_id:company})));
  if(version!==generation || company!==companyId())return;
  ['periods','plans','mappings','files','audit'].forEach((key,i)=>current[key]=responses[i]);
  fillSelect($('#period'),current.periods,'Todos os períodos',p=>`Base ${p.reference_competence} · Movimentos ${p.processing_competence}`);
  fillSelect($('#mapping-plan'),current.plans,'Selecione um plano',p=>`${p.label} · v${p.version} · #${p.id}`);
  if(!$('#mapping-plan').value && current.plans.length)$('#mapping-plan').value=String(current.plans[0].id);
  const results=await Promise.all(['documents','reconciliation','observations'].map(route=>api(route,{company_id:company,period_id:periodId()})));
  if(version!==generation)return;
  ['documents','reconciliation','observations'].forEach((key,index)=>current[key]=results[index]);render();await loadAccounts();
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
    table(sourceArea,doc.sources.filter(source=>source.entity_kind==='documento').map(source=>({'Arquivo':`#${source.file_id} · ${source.filename}`,'Formato':source.source_kind,'Localização':source.locator,'Período da fonte':source.period_id,'Situação da fonte':source.file_status,'Campos conferidos':Object.fromEntries(Object.entries(source.normalized).filter(([key])=>!['key','content_fingerprint'].includes(key)).map(([key,value])=>[fieldLabels[key]||key,value])),'Pendências':source.issues})));
    if(doc.differences.length){card.append(element('h4','Diferenças que exigem conferência'));const diffArea=element('div');diffArea.className='table-area';card.append(diffArea);table(diffArea,doc.differences.flatMap(diff=>diff.values.map(value=>({'Entidade':diff.entity||'documento','Campo':fieldLabels[diff.field]||diff.field,'Arquivo':'#'+value.file_id,'Localização':value.locator,'Valor na origem':value.value}))));}
    if(doc.issues.length){const issue=element('p',doc.issues.map(row=>`${row.file_id?'Arquivo #'+row.file_id+' · ':''}${row.locator||''}: ${row.messages.join('; ')}`).join('\n'));issue.className='error-text';card.append(issue);}
    card.append(element('h4',`Faturas identificadas: ${doc.invoices.length}`));
    doc.invoices.forEach(invoice=>{
      card.append(element('p',`Fatura #${invoice.id} · ${invoice.reference} · ${invoice.status}`));
      const details=element('details'),summary=element('summary','Valores e fontes da fatura'),pre=element('pre',JSON.stringify({valores:invoice.payload,origens:invoice.sources.map(s=>({arquivo:s.file_id,local:s.locator,valores:s.normalized,situacao:s.file_status}))},null,2));details.append(summary,pre);card.append(details);
      const parts=element('div');parts.className='table-area';card.append(parts);table(parts,invoice.installments.map(part=>({'Parcela':`#${part.id} · ${part.reference}`,'Vencimento':part.payload.dVenc,'Valor recebido':part.payload.vDup,'Situação':part.status,'Origens':part.sources.map(s=>({arquivo:s.file_id,local:s.locator,valores:s.normalized,situacao:s.file_status}))})));
    });
    card.append(element('p','Conferência parcial de fontes. Nenhum lançamento contábil ou arquivo Prosoft foi gerado.'));
    area.append(card);
  });
  const pending=current.observations.filter(row=>row.issues.length && (row.entity_kind==='registro'||!row.document_id||(row.entity_kind==='fatura'&&!row.invoice_id)||(row.entity_kind==='parcela'&&!row.installment_id)));
  table('#observation-list',pending.map(row=>({'Arquivo':`#${row.file_id} · ${row.filename}`,'Localização':row.locator,'Situação da fonte':row.file_status,'Pendências':row.issues,'Conteúdo de origem':row.raw})));
}
function selectAnalysisProfile(){const file=current.files.find(row=>String(row.id)===$('#analysis-file').value);$('#analysis-profile').value=file?(file.kind==='XML'?'nfe-4.00-header-billing-v3':'efd-icms-ipi-020-c100-v1'):'';}
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
  $('#removal-details').textContent=`Arquivo #${preview.file_id}: ${preview.filename}. Documentos afetados: ${preview.document_ids.length?preview.document_ids.join(', '):'nenhum'}. Faturas: ${preview.invoice_ids.join(', ')||'nenhuma'}. Parcelas: ${preview.installment_ids.join(', ')||'nenhuma'}. ${preview.consequence}`;
  $('#removal-confirm-form').reset();$('#removal-confirm-form').hidden=false;
  return {message:'Confira as dependências, informe o motivo e confirme a remoção lógica.'};
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
loadCompanies().catch(error=>notice(error.message,true));
