'use strict';
/* UI draft only. The server remains authoritative for reviews, mappings and balance. */
globalThis.PostingEditor=(function(){
  let options,scope=null,rows=[],drafts={},restoring=false,storageKey;
  const q=s=>document.querySelector(s),form=()=>q('#accounting-form');
  function node(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
  function addOption(select,value,text,disabled=false){const e=node('option',text);e.value=String(value);e.disabled=disabled;select.append(e);}
  function choices(select,list,describe,selected){
    select.replaceChildren();addOption(select,'','Selecione');
    list.forEach(item=>addOption(select,item.id,describe(item),!!item.disabled));
    if(selected&&!list.some(item=>String(item.id)===String(selected)))addOption(select,selected,`Indisponível #${selected}`,true);
    select.value=selected||'';
  }
  function context(){return options.context();}
  function snapshot(){return {rows:rows.map(raw),mode:q('#posting-mode').value,json:q('#posting-json-input').value,plan:q('#accounting-plan').value,reason:form().elements.reason.value,previous:form().elements.previous_batch_id.value,key:form().elements.request_key.value};}
  function save(){
    if(restoring||!scope||!context().company)return;
    drafts[scope]=snapshot();
    try{sessionStorage.setItem(storageKey,JSON.stringify(drafts));q('#posting-draft-state').textContent='Rascunho guardado nesta sessão · empresa e competência separadas.';}
    catch{q('#posting-draft-state').textContent='Rascunho em memória. O navegador não permitiu guardar a recuperação; mantenha esta janela aberta.';}
  }
  function restoreSelect(select,value){if(value&&![...select.options].some(o=>o.value===value))addOption(select,value,'Indisponível #'+value,true);select.value=value||'';}
  function restore(draft){
    restoring=true;
    try{reset();if(draft){restoreSelect(q('#accounting-plan'),draft.plan);restoreSelect(form().elements.previous_batch_id,draft.previous);form().elements.reason.value=draft.reason;form().elements.request_key.value=draft.key;q('#posting-json-input').value=draft.json;q('#posting-mode').value=draft.mode;rows=[];q('#posting-lines').replaceChildren();draft.rows.forEach(add);}mode();totals();}
    finally{restoring=false;}
  }
  function clearDrafts(){drafts={};try{sessionStorage.removeItem(storageKey);}catch{}}
  function newKey(){form().elements.request_key.value='local-'+crypto.randomUUID();}
  function mode(){const visual=q('#posting-mode').value==='visual';q('#posting-visual').hidden=!visual;q('#posting-json').hidden=visual;q('#posting-json-input').disabled=visual;q('#posting-json-input').required=!visual;rows.forEach(row=>Object.values(row.fields).forEach(control=>control.disabled=!visual));}
  function raw(row){const result=Object.fromEntries(Object.entries(row.fields).map(([key,control])=>[key,control.value]));result.observation_id=row.observation;return result;}
  function eligibleMappings(){
    const c=context(),period=c.periods.find(p=>String(p.id)===c.period),latest=new Map();
    if(!period)return [];
    c.mappings.filter(m=>String(m.plan_id)===c.plan&&m.valid_from<=period.processing_competence&&(!m.valid_to||m.valid_to>=period.processing_competence)).forEach(m=>{if(!latest.has(m.source_account)||latest.get(m.source_account).version<m.version)latest.set(m.source_account,m);});
    return [...latest.values()].filter(m=>m.state==='aprovado');
  }
  function refreshRow(row){
    const c=context(),selected=raw(row),docs=c.documents.filter(d=>String(d.period_id)===c.period).map(d=>({...d,id:d.document_id,disabled:!d.readiness_for_accounting}));
    choices(row.fields.document_id,docs,d=>`Documento #${d.id} · ${d.business_key.slice(-12)}${d.disabled?' · pendente':''}`,selected.document_id);
    choices(row.fields.mapping_id,eligibleMappings(),m=>`${m.source_account} → ${m.target_code} · v${m.version} · #${m.id}`,selected.mapping_id);
    const doc=c.documents.find(d=>String(d.document_id)===selected.document_id),chosen=doc?.sources.find(s=>String(s.id)===row.observation);
    const fresh=doc?.readiness_for_accounting&&String(doc.review?.chosen_observation_id)===row.observation;
    row.source.textContent=chosen?`Fonte #${chosen.id} · ${chosen.filename} · ${chosen.locator} · total ${chosen.normalized.total||'ausente'}${fresh?'':' · escolha/revisão desatualizada; selecione o documento novamente'}`:'Selecione um documento revisado para consultar a origem e o total.';
    row.source.classList.toggle('error-text',!!selected.document_id&&!fresh);
    const period=c.periods.find(p=>String(p.id)===c.period);
    if(period){const [y,m]=period.processing_competence.split('-').map(Number);row.fields.date.min=period.processing_competence+'-01';row.fields.date.max=period.processing_competence+'-'+String(new Date(Date.UTC(y,m,0)).getUTCDate()).padStart(2,'0');}
  }
  function totals(){
    const result=PostingMath.summarize(rows.map(raw)),area=q('#posting-totals');area.replaceChildren();
    area.append(node('p',`Débitos ${result.debit} · Créditos ${result.credit} · Diferença ${result.difference}`));
    const message=node('p',result.invalid?`${result.invalid} linha(s) incompleta(s): os totais acima são parciais.`:result.balanced?'Grupos equilibrados no rascunho. O servidor ainda verificará fontes, contas e reservas.':'Revise o equilíbrio de cada grupo e documento.');message.className=result.balanced?'muted':'error-text';area.append(message);
    const list=node('ul');result.groups.forEach(g=>list.append(node('li',`Documento #${g.document_id} · ${g.group}: D ${g.debit} / C ${g.credit} / diferença ${g.difference}`)));area.append(list);
  }
  function add(values={}){
    if(rows.length>=200)throw new Error('O editor visual aceita até 200 linhas. Use JSON avançado para lotes maiores.');
    const box=node('fieldset'),legend=node('legend',`Partida ${rows.length+1}`),grid=node('div');grid.className='posting-grid';box.append(legend,grid);box.className='posting-line';
    const row={box,legend,fields:{},observation:String(values.observation_id||'')};
    for(const [key,label,tag] of [['document_id','Documento revisado','select'],['group','Grupo','input'],['date','Data contábil','input'],['side','Lado','select'],['amount','Valor','input'],['mapping_id','Mapeamento aprovado','select'],['memo','Histórico da partida','input']]){
      const labelNode=node('label',label),control=node(tag);control.dataset.field=key;control.required=true;
      if(key==='side'){addOption(control,'','Selecione');addOption(control,'D','Débito');addOption(control,'C','Crédito');}
      if(key==='date')control.type='date';
      if(key==='amount'){control.inputMode='decimal';control.placeholder='100,30';control.maxLength=19;}
      if(key==='group')control.maxLength=100;
      if(key==='memo')control.maxLength=1000;
      control.value=values[key]===undefined?'':String(values[key]);labelNode.append(control);grid.append(labelNode);row.fields[key]=control;
    }
    row.source=node('p');row.source.className='help';box.append(row.source);
    const remove=node('button','Remover partida');remove.type='button';remove.className='secondary';box.append(remove);
    remove.addEventListener('click',()=>{rows=rows.filter(r=>r!==row);box.remove();rows.forEach((r,i)=>r.legend.textContent=`Partida ${i+1}`);totals();});
    row.fields.document_id.addEventListener('change',()=>{const doc=context().documents.find(d=>String(d.document_id)===row.fields.document_id.value);row.observation=doc?.review?String(doc.review.chosen_observation_id):'';row.fields.amount.value='';row.fields.date.value='';refreshRow(row);totals();});
    box.addEventListener('input',totals);rows.push(row);q('#posting-lines').append(box);
    // Options must be installed before restoring imported selections.
    const selectedDoc=String(values.document_id||''),selectedMap=String(values.mapping_id||'');
    choices(row.fields.document_id,[{id:selectedDoc}],()=>selectedDoc,selectedDoc);choices(row.fields.mapping_id,[{id:selectedMap}],()=>selectedMap,selectedMap);
    refreshRow(row);mode();totals();return row;
  }
  function reset(){rows=[];q('#posting-lines').replaceChildren();q('#posting-mode').value='visual';q('#posting-json-input').value='';form().elements.reason.value='';form().elements.previous_batch_id.value='';newKey();add();add();mode();}
  function refresh(){
    if(!options)return;const c=context(),next=JSON.stringify([c.company,c.period]);
    if(scope!==next){scope=next;restore(drafts[scope]);}else{const draft=drafts[scope];if(draft){restoreSelect(q('#accounting-plan'),draft.plan);restoreSelect(form().elements.previous_batch_id,draft.previous);}rows.forEach(refreshRow);totals();mode();}
  }
  function read(){
    if(q('#posting-mode').value==='json'){let result;try{result=JSON.parse(q('#posting-json-input').value);}catch{throw new Error('Partidas: JSON inválido.');}if(!Array.isArray(result))throw new Error('Partidas devem ser uma lista.');return result;}
    return rows.map((row,index)=>{
      const data=raw(row),doc=context().documents.find(d=>String(d.document_id)===data.document_id);
      if(!doc?.readiness_for_accounting||String(doc.review?.chosen_observation_id)!==data.observation_id)throw new Error(`Partida ${index+1}: confira novamente o documento e sua fonte revisada.`);
      if(!eligibleMappings().some(m=>String(m.id)===data.mapping_id))throw new Error(`Partida ${index+1}: selecione mapeamento aprovado vigente.`);
      return {...data,amount:PostingMath.normalize(data.amount)};
    });
  }
  function init(config){
    options=config;storageKey='escritura:posting-drafts:v1:'+(window.frameElement?.dataset.owner||'local');try{drafts=JSON.parse(sessionStorage.getItem(storageKey)||'{}');}catch{drafts={};}
    form().addEventListener('input',save);form().addEventListener('change',save);form().addEventListener('click',()=>queueMicrotask(save));
    const safe=fn=>()=>{try{fn();save();}catch(error){options.onError(error.message,true);}};
    q('#posting-add').addEventListener('click',safe(()=>add()));q('#posting-mode').addEventListener('change',mode);q('#posting-new-key').addEventListener('click',newKey);
    q('#accounting-plan').addEventListener('change',()=>{rows.forEach(refreshRow);totals();});
    q('#posting-to-json').addEventListener('click',safe(()=>{q('#posting-json-input').value=JSON.stringify(read(),null,2);q('#posting-mode').value='json';mode();}));
    q('#posting-from-json').addEventListener('click',safe(()=>{
      const data=read();if(data.length<2||data.length>200)throw new Error('Carregue de 2 a 200 partidas no editor visual; lotes maiores podem permanecer em JSON avançado.');
      const allowed=['document_id','observation_id','group','date','side','amount','mapping_id','memo'];
      for(const row of data){if(!row||typeof row!=='object'||Array.isArray(row)||Object.keys(row).some(k=>!allowed.includes(k)))throw new Error('JSON possui campos desconhecidos ou uma partida inválida; rascunho preservado.');for(const key of allowed)if(!['string','number'].includes(typeof row[key]))throw new Error('Partida incompleta; rascunho preservado.');PostingMath.cents(row.amount);}
      rows=[];q('#posting-lines').replaceChildren();q('#posting-mode').value='visual';data.forEach(add);mode();
    }));refresh();
  }
  return {init,refresh,read,save,clearDrafts};
})();
