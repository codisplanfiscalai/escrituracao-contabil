'use strict';
const {createApp,h}=Vue;
const menu=[
 {id:'dashboard',label:'Visão geral',icon:'◫',group:'PRINCIPAL'},
 {id:'companies',label:'Empresas',icon:'▥',group:'OPERAÇÃO',permission:'companies.manage'},
 {id:'setup',label:'Competências',icon:'▦',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'chart',label:'Planos e mapeamentos',icon:'≡',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'imports',label:'Documentos',icon:'▧',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'reconciliation',label:'Conciliação',icon:'⇄',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'fiscal',label:'Lançamento fiscal',icon:'▧',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'accounting',label:'Escrituração',icon:'▤',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'history',label:'Histórico contábil',icon:'◷',group:'OPERAÇÃO',permission:'workspace.read'},
 {id:'client',label:'Portal do cliente',icon:'◇',group:'RELACIONAMENTO',permission:'client.read'},
 {id:'users',label:'Usuários',icon:'♙',group:'ADMINISTRAÇÃO',permission:'users.manage'},
 {id:'roles',label:'Perfis e permissões',icon:'▣',group:'ADMINISTRAÇÃO',permission:'roles.manage'},
 {id:'settings',label:'Configurações',icon:'⚙',group:'ADMINISTRAÇÃO',permission:'settings.manage'},
 {id:'email',label:'E-mail',icon:'✉',group:'ADMINISTRAÇÃO',permission:'settings.manage'},
 {id:'audit',label:'Auditoria',icon:'◷',group:'ADMINISTRAÇÃO',permission:'audit.read'},
 {id:'security',label:'Minha conta e 2FA',icon:'⊙',group:'CONTA'},
];
const app=createApp({
 render:EscrituraRender,
 data:()=>({ready:false,busy:false,configured:true,user:null,csrf:'',version:'',page:'dashboard',menuOpen:false,menuSearch:'',error:'',notice:'',authMode:'login',auth:{name:'',email:'',password:'',token:'',code:''},challenge:'',resetToken:'',dashboard:{metrics:{},companies:[]},users:[],roles:[],permissions:{},sessions:[],audit:[],mail:[],dialog:'',userForm:{},roleForm:{},companyForm:{name:'',cnpj:'',prosoft_company_code:'',prosoft_plan_code:''},settings:{general:{},smtp:{mode:'starttls',port:587}},menuOrder:menu.map(m=>m.id),allMenu:menu,workspacePages:['fiscal','setup','chart','imports','reconciliation','accounting','history'],clientCompany:'',workspacePeriod:'',clientPeriod:'',clientData:{files:[],documents:[],periods:[]},uploadKind:'XML',uploadFile:null,mfa:{password:'',code:'',token:'',secret:''},recoveryCodes:[],pageGeneration:0,clientGeneration:0,routeGeneration:0,workspaceMounted:false,workspaceTabs:[]}),
 computed:{
  initials(){return this.user?.name.split(' ').filter(Boolean).slice(0,2).map(s=>s[0].toUpperCase()).join('')||'E';},
  pageTitle(){return menu.find(m=>m.id===this.page)?.label||'Visão geral';},
  pageSubtitle(){return ({dashboard:'Uma visão clara do seu trabalho e das próximas etapas.',users:'Pessoas, vínculos e acessos em um único lugar.',roles:'Permissões explícitas para cada responsabilidade.',client:'Envie documentos e acompanhe as informações da sua empresa.',security:'Gerencie a proteção da conta e seus dispositivos.',audit:'Acompanhe as alterações e identifique seus responsáveis.',email:'Configure e acompanhe a entrega transacional.',settings:'Personalize o ambiente e organize a navegação.',companies:'Cadastre e organize as empresas do seu ambiente.'})[this.page]||'Trabalhe com as origens preservadas e decisões rastreáveis.';},
  menuGroups(){const order=this.menuOrder;const items=menu.filter(m=>(!m.permission||this.can(m.permission))&&m.label.toLowerCase().includes(this.menuSearch.toLowerCase())).sort((a,b)=>order.indexOf(a.id)-order.indexOf(b.id));return [...new Set(items.map(m=>m.group))].map(label=>({label,items:items.filter(m=>m.group===label)}));},
  openWorkspaceTabs(){return this.workspaceTabs.map(id=>menu.find(m=>m.id===id)).filter(Boolean);},
  metrics(){return [{key:'companies',label:'Empresas',help:'No seu escopo de acesso',icon:'▥'},{key:'files',label:'Arquivos recebidos',help:'Origens preservadas',icon:'▧'},{key:'documents',label:'Documentos',help:'Disponíveis para conferência',icon:'≡'},{key:'batches',label:'Lotes contábeis',help:'Com histórico de decisões',icon:'▤'}];},
  nextSteps(){return this.can('workspace.read')?[{title:'Organize os documentos',text:'Receba XML e SPED na competência correta.',href:'#/imports'},{title:'Concilie as informações',text:'Confira origens e diferenças.',href:'#/reconciliation'},{title:'Prepare a escrituração',text:'Revise e preserve as evidências.',href:'#/accounting'}]:[{title:'Envie seus documentos',text:'Selecione a empresa e a competência.',href:'#/client'},{title:'Proteja seu acesso',text:'Ative a autenticação em duas etapas.',href:'#/security'}];},
  dialogTitle(){return ({user:this.userForm.id?'Editar usuário':'Novo usuário',role:'Perfil de acesso',mfa:'Configurar 2FA',recovery:'Códigos de recuperação'})[this.dialog]||'';}
 },
 methods:{
  structuredCopy(value){return JSON.parse(JSON.stringify(value));},
  can(permission){return this.user?.permissions.includes(permission)||false;},
  date(value){return value?new Date(Number(value)*1000).toLocaleString('pt-BR'):'—';},
  async api(path,data,method){const options={method:method||(data?'POST':'GET'),cache:'no-store',credentials:'same-origin',headers:{'X-CSRF-Token':this.csrf}};if(data){options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}const response=await fetch(path.startsWith('/api/')?path:'/api/v1/'+path,options);let body;try{body=await response.json();}catch{throw Error('O servidor não respondeu como esperado.');}if(!response.ok){if(response.status===401&&!path.startsWith('auth/')){this.user=null;this.csrf='';this.auth.password='';}throw Error(body.error||'Não foi possível concluir a operação.');}return body.data;},
  async run(action){if(this.busy)return;this.busy=true;this.error='';this.notice='';try{await action();}catch(e){this.error=e.message;}finally{this.busy=false;}},
  async init(){try{const s=await this.api('status');this.configured=s.configured;this.version=s.version;try{const session=await this.api('auth/me');this.acceptSession(session);}catch{}this.route();if(this.user)await this.loadPage();}catch(e){this.error=e.message;}finally{this.ready=true;}},
  acceptSession(session){this.user=session.user;this.csrf=session.csrf;if(session.menu?.length)this.menuOrder=[...session.menu.filter(id=>menu.some(m=>m.id===id)),...menu.map(m=>m.id).filter(id=>!session.menu.includes(id))];},
  async flushWorkspace(){const frame=document.querySelector('#workspace-frame');if(frame?.contentWindow?.EscrituraWorkspace)await frame.contentWindow.EscrituraWorkspace.flush();},
  async route(){
   const navigation=++this.routeGeneration;
   try{await this.flushWorkspace();}catch(e){if(navigation===this.routeGeneration){this.error='Rascunho pendente: '+e.message;history.replaceState(null,'','#/'+this.page);}return;}
   if(navigation!==this.routeGeneration)return;
   const hash=location.hash.slice(2);
   if(hash.startsWith('reset/')){this.user=null;this.csrf='';this.authMode='reset';this.resetToken=hash.slice(6);return;}
   const target=menu.find(m=>m.id===hash);
   this.page=target&&(!target.permission||this.can(target.permission))?target.id:'dashboard';
   if(this.workspacePages.includes(this.page)){this.workspaceMounted=true;if(!this.workspaceTabs.includes(this.page))this.workspaceTabs.push(this.page);}
   this.menuOpen=false;this.error='';this.notice='';this.dialog='';
   if(this.user){this.loadPage();await Vue.nextTick();this.activateWorkspace();document.querySelector('#content')?.focus({preventScroll:true});window.scrollTo(0,0);}
  },
  activateWorkspace(){if(this.workspacePages.includes(this.page))document.querySelector('#workspace-frame')?.contentWindow?.EscrituraWorkspace?.navigate(this.page==='history'?'audit':this.page);},
  async closeWorkspaceTab(id){try{await this.flushWorkspace();const index=this.workspaceTabs.indexOf(id);if(index<0)return;this.workspaceTabs.splice(index,1);if(this.page===id)location.hash='#/'+(this.workspaceTabs[Math.min(index,this.workspaceTabs.length-1)]||'dashboard');}catch(e){this.error='Rascunho pendente: '+e.message;}},
  async submitAuth(){await this.run(async()=>{if(!this.configured){await this.api('setup',this.auth);this.configured=true;this.auth.token='';this.notice='Ambiente configurado. Entre com sua conta.';return;}if(this.authMode==='forgot'){this.notice=(await this.api('auth/forgot',{email:this.auth.email})).message;return;}if(this.authMode==='reset'){this.notice=(await this.api('auth/reset',{token:this.resetToken,password:this.auth.password,code:this.auth.code})).message;this.auth.password='';this.auth.code='';this.authMode='login';history.replaceState(null,'','#/dashboard');return;}const session=await this.api(this.challenge?'auth/mfa':'auth/login',this.challenge?{challenge:this.challenge,code:this.auth.code}:{email:this.auth.email,password:this.auth.password});this.auth.password='';this.auth.code='';if(session.mfa_required){this.challenge=session.challenge;return;}this.challenge='';this.acceptSession(session);history.replaceState(null,'','#/dashboard');this.page='dashboard';await this.loadPage();});},
  async logout(){await this.run(async()=>{await this.flushWorkspace();await this.api('auth/logout',{});document.querySelector('#workspace-frame')?.contentWindow?.PostingEditor?.clearDrafts();this.workspaceMounted=false;this.workspaceTabs=[];this.user=null;this.csrf='';this.dashboard={metrics:{},companies:[]};this.clientData={files:[],documents:[],periods:[]};});},
  async loadPage(){const generation=++this.pageGeneration;const page=this.page;try{const dash=await this.api('dashboard');if(generation!==this.pageGeneration)return;this.dashboard=dash;
    if(page==='users'||page==='roles'){const [users,roles]=await Promise.all([page==='users'?this.api('users'):Promise.resolve([]),this.api('roles')]);if(generation!==this.pageGeneration)return;this.users=users;this.roles=roles.roles;this.permissions=roles.permissions;}
    if(page==='settings'||page==='email'){const [settings,mail]=await Promise.all([this.api('settings'),this.api('mail')]);if(generation!==this.pageGeneration)return;this.settings={general:{display_name:'Escritura',support_email:'',...settings.general},smtp:{host:'',port:587,mode:'starttls',sender:'',username:'',password:'',...settings.smtp}};this.mail=mail;}
    if(page==='security'){const sessions=await this.api('sessions');if(generation!==this.pageGeneration)return;this.sessions=sessions;}
    if(page==='audit'){const audit=await this.api('audit');if(generation!==this.pageGeneration)return;this.audit=audit;}
    if(page==='client'){if(!dash.companies.some(c=>String(c.id)===this.clientCompany)){this.clientCompany=String(dash.companies[0]?.id||'');}await this.loadClient();}
   }catch(e){if(generation===this.pageGeneration)this.error=e.message;}
  },
  async openCompany(company){try{await this.flushWorkspace();this.clientCompany=String(company.id);const control=document.querySelector('#workspace-frame')?.contentDocument?.querySelector('#company');if(control&&control.value!==this.clientCompany){control.value=this.clientCompany;control.dispatchEvent(new Event('change',{bubbles:true}));}location.hash=this.can('workspace.read')?'#/imports':'#/client';}catch(e){this.error='Rascunho pendente: '+e.message;}},
  selectWorkspace(event){
   const frame=event.target, doc=frame.contentDocument;
   if(!doc)return;
   this.activateWorkspace();
   const company=doc.querySelector('#company'),period=doc.querySelector('#period');
   const wantedCompany=this.clientCompany,wantedPeriod=this.workspacePeriod;
   let attempts=0,companyRestored=false;
   doc.addEventListener('escritura:context',()=>{this.clientCompany=company?.value||'';this.workspacePeriod=period?.value||'';});
   const restore=()=>{
    if(!frame.isConnected||++attempts>100)return;
    if(!wantedCompany||!company)return;
    if(!companyRestored){
     if(![...company.options].some(o=>o.value===wantedCompany)){setTimeout(restore,100);return;}
     company.value=wantedCompany;company.dispatchEvent(new Event('change',{bubbles:true}));companyRestored=true;
    }
    if(companyRestored&&company.value!==wantedCompany)return;
    if(wantedPeriod&&period){
     if(![...period.options].some(o=>o.value===wantedPeriod)){setTimeout(restore,100);return;}
     period.value=wantedPeriod;period.dispatchEvent(new Event('change',{bubbles:true}));
    }
   };restore();
  },
  async saveCompany(){await this.run(async()=>{await this.api('/api/companies',this.companyForm);this.companyForm={name:'',cnpj:'',prosoft_company_code:'',prosoft_plan_code:''};await this.loadPage();this.notice='Empresa cadastrada.';});},
  editUser(user){this.error='';this.userForm=user?{...this.structuredCopy(user),active:!!user.active,password:''}:{name:'',email:'',password:'',role:'client',companies:[],active:true};this.dialog='user';},
  closeDialog(){this.dialog='';this.error='';this.mfa={password:'',code:'',secret:'',token:''};this.recoveryCodes=[];},
  async saveUser(){await this.run(async()=>{const own=this.userForm.id===this.user.id;await this.api('users',this.userForm);this.dialog='';if(own){this.user=null;this.csrf='';this.notice='Conta atualizada. Entre novamente.';}else{await this.loadPage();this.notice='Usuário salvo. Sessões anteriores foram encerradas.';}});},
  async saveRole(){await this.run(async()=>{await this.api('roles',this.roleForm);this.dialog='';await this.loadPage();this.notice='Perfil salvo.';});},
  moveMenu(i,delta){const order=[...this.menuOrder];[order[i],order[i+delta]]=[order[i+delta],order[i]];this.menuOrder=order;},
  async saveSettings(section){await this.run(async()=>{await this.api('settings',{[section]:section==='menu'?this.menuOrder:this.settings[section]});if(section==='smtp')this.settings.smtp.password='';this.notice='Configuração salva.';});},
  async testEmail(){await this.run(async()=>{this.notice=(await this.api('mail/test',{})).message;this.mail=await this.api('mail');});},
  async loadClient(){const generation=++this.clientGeneration;const company=this.clientCompany;this.clientData={files:[],documents:[],periods:[]};this.clientPeriod='';this.uploadFile=null;if(!company)return;try{const [periods,files,documents]=await Promise.all(['periods','files','documents'].map(route=>this.api('client/'+route+'?company_id='+encodeURIComponent(company))));if(generation!==this.clientGeneration||company!==this.clientCompany)return;this.clientData={periods,files,documents};}catch(e){if(generation===this.clientGeneration)this.error=e.message;}},
  async uploadClient(){await this.run(async()=>{if(!this.uploadFile)throw Error('Selecione um arquivo.');if(this.uploadFile.size>10*1024*1024)throw Error('O arquivo excede 10 MiB.');const file=this.uploadFile,company=this.clientCompany,period=this.clientPeriod;const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));if(company!==this.clientCompany)throw Error('A empresa foi alterada. Selecione o documento novamente.');await this.api('client/files',{company_id:company,period_id:period,kind:this.uploadKind,filename:file.name,content_base64:btoa(binary)});await this.loadClient();this.notice='Documento recebido e origem preservada.';});},
  async beginMfa(){await this.run(async()=>{const enrollment=await this.api('mfa/begin',{password:this.mfa.password});this.mfa={...enrollment,password:'',code:''};this.dialog='mfa';});},
  async confirmMfa(){await this.run(async()=>{const result=await this.api('mfa/confirm',{token:this.mfa.token,code:this.mfa.code});this.recoveryCodes=result.recovery_codes;this.dialog='recovery';this.mfa={password:'',code:'',secret:'',token:''};this.user=null;this.csrf='';this.notice='2FA ativado. Guarde os códigos e entre novamente.';});},
  async disableMfa(){await this.run(async()=>{await this.api('mfa/disable',{password:this.mfa.password,code:this.mfa.code});this.user=null;this.csrf='';this.mfa={};this.notice='2FA desabilitado. Entre novamente.';});},
  async revokeSession(session){await this.run(async()=>{await this.api('sessions/revoke',{id:session.id});if(session.current){this.user=null;this.csrf='';}else this.sessions=await this.api('sessions');});},
  async olderAudit(){await this.run(async()=>{const rows=await this.api('audit?before='+this.audit[this.audit.length-1].id);this.audit.push(...rows);if(!rows.length)this.notice='Não há eventos anteriores.';});}
 },
 mounted(){this.init();window.addEventListener('hashchange',()=>this.route());window.addEventListener('keydown',event=>{if(event.key==='Escape'){this.closeDialog();this.menuOpen=false;}});}
});
app.component('data-table',{props:['rows','columns'],render(){if(!this.rows?.length)return h('div',{class:'empty'},[h('span','▧'),h('h3','Nenhum registro neste recorte'),h('p','Os registros aparecerão aqui conforme as operações forem realizadas.')]);return h('div',{class:'table-scroll'},h('table',[h('thead',h('tr',Object.values(this.columns).map(label=>h('th',label)))),h('tbody',this.rows.map(row=>h('tr',Object.keys(this.columns).map(key=>{let value=key.split('.').reduce((value,part)=>value?.[part],row);if(key==='created'&&typeof value==='number')value=new Date(value*1000).toLocaleString('pt-BR');return h('td',typeof value==='object'?JSON.stringify(value):String(value??'—'));}))))]));}});
app.mount('#app');
