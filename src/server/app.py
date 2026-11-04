"""API corporativa autenticada; reutiliza os serviços contábeis existentes."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import json
import os
from pathlib import Path
import sqlite3
import threading
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.staticfiles import StaticFiles
from .identity import Identity, IdentityError, PERMISSIONS, digest
from ..local_app import dispatch, APIError, MAX_BODY, WEB_ROOT
from ..persistence import AccountingStore

ROOT = Path(__file__).resolve().parents[2]
PORTAL = ROOT / 'src' / 'portal'
COOKIE = 'escritura_session'
WRITE_ROUTES = {'periods','plans','mappings','files','file-analysis','file-removal','billing-association-preview','billing-associations','document-reviews','accounting-batches'}
REVIEW_ROUTES = {'accounting-review','accounting-close','accounting-evidence'}
CLIENT_GET = {'companies','periods','documents','files','accounting-evidence','accounting-evidence-file'}
CLIENT_POST = {'files'}


def create_app(directory, public_url='http://127.0.0.1:8765', database=None, setup_file=None, key_file=None, worker=True):
    parsed=urlsplit(public_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise ValueError('A URL pública deve conter somente protocolo, host e porta.')
    if parsed.scheme not in ('https','http') or not parsed.hostname:
        raise ValueError('URL pública inválida.')
    if parsed.scheme=='http' and parsed.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('O acesso de rede exige HTTPS.')
    public_url=public_url.rstrip('/')
    metadata=ROOT/'src'/'distribution.json'
    version=os.environ.get('ESCRITURA_VERSION')
    if not version:
        version=json.loads(metadata.read_text(encoding='utf-8'))['version'] if metadata.exists() else (ROOT/'VERSION').read_text(encoding='utf-8').strip()
    identity=Identity(directory,public_url,setup_file,key_file)
    accounting=Path(database).resolve() if database else identity.directory/'accounting.sqlite3'
    accounting.parent.mkdir(parents=True,exist_ok=True)
    with_store=AccountingStore(accounting,actor='sistema')
    with_store.close()
    stop=threading.Event()
    def deliver():
        while not stop.wait(2):
            try: identity.deliver_one()
            except Exception: pass  # A fila retém diagnóstico sem conteúdo de mensagens.
    @asynccontextmanager
    async def lifespan(app):
        thread=threading.Thread(target=deliver,daemon=True,name='EscrituraEmail') if worker else None
        if thread:thread.start()
        yield
        stop.set()
        if thread:thread.join(timeout=20)
    app=FastAPI(title='Escritura',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    app.state.identity=identity
    app.state.accounting=accounting
    app.state.public_url=public_url

    @app.middleware('http')
    async def boundaries(request,call_next):
        try:
            if request.headers.get('host')!=parsed.netloc:
                raise IdentityError('Host não permitido.',403)
            if request.method not in ('GET','POST','HEAD'):
                raise IdentityError('Método não permitido.',405)
            origin=request.headers.get('origin')
            if origin and origin!=public_url:raise IdentityError('Origem não permitida.',403)
            if request.headers.get('sec-fetch-site','') not in ('','same-origin','none'):
                raise IdentityError('Origem não permitida.',403)
            if request.method=='POST':
                if origin!=public_url:raise IdentityError('Origem obrigatória.',403)
                if request.headers.get('content-type','').split(';')[0]!='application/json':raise IdentityError('Envie JSON.',415)
                if 'transfer-encoding' in request.headers:raise IdentityError('Envio em blocos não permitido.',400)
                length=request.headers.get('content-length','')
                if not length.isdigit() or int(length)>MAX_BODY:raise IdentityError('Envio excede o limite permitido.',413)
                body=await asyncio.wait_for(request.body(), timeout=15)
                if len(body)>MAX_BODY:raise IdentityError('Envio excede o limite permitido.',413)
            response=await call_next(request)
        except IdentityError as error:
            response=JSONResponse({'error':str(error)},status_code=error.status)
        response.headers.update({
            'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'X-Frame-Options':'SAMEORIGIN','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'",
            'Permissions-Policy':'camera=(), microphone=(), geolocation=()'})
        if parsed.scheme=='https':response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.exception_handler(IdentityError)
    @app.exception_handler(APIError)
    async def invalid(request,error):return JSONResponse({'error':str(error)},status_code=error.status)
    @app.exception_handler(sqlite3.IntegrityError)
    async def conflict(request,error):return JSONResponse({'error':'Registro duplicado ou vínculo inválido.'},status_code=409)
    @app.exception_handler(ValueError)
    async def value_error(request,error):return JSONResponse({'error':str(error)},status_code=400)

    def actor(request,permission=None):
        raw=request.cookies.get(COOKIE,'')
        user=identity.authenticate(raw)
        if request.method=='POST':
            csrf=request.headers.get('X-CSRF-Token') or request.headers.get('X-Local-Token','')
            if not hmac.compare_digest(csrf,identity.csrf(raw)):raise IdentityError('Sessão de formulário inválida.',403)
        if permission:identity.require(user,permission)
        return user

    async def data(request):
        try:value=await request.json()
        except Exception:raise IdentityError('JSON inválido.') from None
        if not isinstance(value,dict):raise IdentityError('Envie um objeto JSON.')
        return value

    def peer(request):return request.client.host if request.client else 'local'
    def answer(value):return {'data':value}
    def login_response(result,raw):
        response=JSONResponse(answer(result))
        if raw:response.set_cookie(COOKIE,raw,max_age=28800,httponly=True,secure=parsed.scheme=='https',samesite='strict',path='/')
        return response
    def company_scope(user,company):
        if user['role']!='admin' and str(company) not in user['companies']:
            raise IdentityError('Empresa não autorizada para este usuário.',403)
    def companies(user):
        store=AccountingStore(accounting,actor=user['id'])
        try:rows=store.list_companies()
        finally:store.close()
        return rows if user['role']=='admin' else [c for c in rows if str(c['id']) in user['companies']]

    @app.get('/health/live')
    def live():return {'status':'ok'}
    @app.get('/health/ready')
    def ready():
        with identity.connect() as db:db.execute('SELECT 1 FROM users LIMIT 1').fetchone()
        return {'status':'ready'}
    @app.get('/api/v1/status')
    def status():
        return answer({'configured':identity.configured(),'product':'Escritura','version':version,
                       'display_name':identity.settings().get('general',{}).get('display_name') or 'Escritura'})
    @app.post('/api/v1/setup')
    async def setup(request:Request):return answer(identity.setup(await data(request),peer(request)))
    @app.post('/api/v1/auth/login')
    async def login(request:Request):return login_response(*identity.login(await data(request),peer(request)))
    @app.post('/api/v1/auth/mfa')
    async def mfa_login(request:Request):
        body=await data(request)
        return login_response(*identity.verify_login(body.get('challenge'),body.get('code'),peer(request)))
    @app.post('/api/v1/auth/forgot')
    async def forgot(request:Request):return answer(identity.request_reset((await data(request)).get('email'),peer(request)))
    @app.post('/api/v1/auth/reset')
    async def reset(request:Request):
        body=await data(request)
        return answer(identity.reset_password(body.get('token'),body.get('password'),body.get('code',''),peer(request)))
    @app.get('/api/v1/auth/me')
    def me(request:Request):
        user=actor(request)
        return answer({'user':user,'csrf':identity.csrf(request.cookies[COOKIE]),'menu':identity.settings().get('menu',[])})
    @app.post('/api/v1/auth/logout')
    def logout(request:Request):
        user=actor(request);identity.revoke(user,digest(request.cookies[COOKIE]))
        response=JSONResponse(answer({'ok':True}));response.delete_cookie(COOKIE,path='/');return response
    @app.get('/api/v1/sessions')
    def sessions(request:Request):
        user=actor(request)
        rows=identity.sessions(user)
        for row in rows:row['current']=row['id']==digest(request.cookies[COOKIE])
        return answer(rows)
    @app.post('/api/v1/sessions/revoke')
    async def revoke(request:Request):
        user=actor(request);identity.revoke(user,str((await data(request)).get('id','')));return answer({'ok':True})
    @app.post('/api/v1/mfa/begin')
    async def begin(request:Request):return answer(identity.begin_mfa(actor(request),(await data(request)).get('password')))
    @app.post('/api/v1/mfa/confirm')
    async def confirm(request:Request):
        user=actor(request);body=await data(request)
        return answer(identity.confirm_mfa(user,body.get('token'),body.get('code')))
    @app.post('/api/v1/mfa/disable')
    async def disable(request:Request):
        user=actor(request);body=await data(request);identity.disable_mfa(user,body.get('password'),body.get('code'));return answer({'ok':True})
    @app.get('/api/v1/users')
    def users(request:Request):actor(request,'users.manage');return answer(identity.users())
    @app.post('/api/v1/users')
    async def save_user(request:Request):
        user=actor(request,'users.manage');body=await data(request)
        # Somente administrador global pode conceder perfis ou empresas irrestritas.
        if user['role']!='admin':raise IdentityError('Administração global necessária.',403)
        return answer(identity.save_user(user,body,[c['id'] for c in companies(user)]))
    @app.get('/api/v1/roles')
    def roles(request:Request):
        user=actor(request)
        if not {'users.manage','roles.manage'} & set(user['permissions']):raise IdentityError('Seu perfil não permite esta operação.',403)
        return answer({'roles':identity.roles(),'permissions':PERMISSIONS})
    @app.post('/api/v1/roles')
    async def save_role(request:Request):
        user=actor(request,'roles.manage')
        if user['role']!='admin':raise IdentityError('Administração global necessária.',403)
        return answer(identity.save_role(user,await data(request)))
    @app.get('/api/v1/settings')
    def settings(request:Request):actor(request,'settings.manage');return answer(identity.settings())
    @app.post('/api/v1/settings')
    async def save_settings(request:Request):
        user=actor(request,'settings.manage');identity.save_settings(user,await data(request));return answer({'ok':True})
    @app.get('/api/v1/mail')
    def mail(request:Request):actor(request,'settings.manage');return answer(identity.outbox())
    @app.post('/api/v1/mail/test')
    def test_mail(request:Request):return answer(identity.queue_test(actor(request,'settings.manage')))
    @app.get('/api/v1/audit')
    def audit(request:Request,before:int=2**63-1):actor(request,'audit.read');return answer(identity.audit(before))
    @app.get('/api/v1/dashboard')
    def dashboard(request:Request):
        user=actor(request);rows=companies(user)
        metrics={'companies':len(rows),'documents':0,'files':0,'batches':0}
        store=AccountingStore(accounting,actor=user['id'])
        try:
            for company in rows:
                metrics['documents']+=len(store.list_documents(company['id']))
                metrics['files']+=len(store.list_files(company['id']))
                if 'workspace.read' in user['permissions']:metrics['batches']+=len(store.list_accounting_batches(company['id']))
        finally:store.close()
        return answer({'metrics':metrics,'companies':rows})

    @app.api_route('/api/v1/client/{route}',methods=['GET','POST'])
    async def client_api(route:str,request:Request):
        permission='client.read' if request.method=='GET' else 'client.upload'
        user=actor(request,permission)
        if route not in (CLIENT_GET if request.method=='GET' else CLIENT_POST):raise IdentityError('Recurso não disponível.',404)
        return await domain(route,request,user)

    async def domain(route,request,user):
        body=await data(request) if request.method=='POST' else dict(request.query_params)
        if route=='companies' and request.method=='GET':return answer(companies(user))
        if route!='companies':company_scope(user,body.get('company_id'))
        store=AccountingStore(accounting,actor=user['id'])
        try:result=dispatch(store,request.method,route,body)
        finally:store.close()
        if route=='accounting-evidence-file' and request.method=='GET':
            return Response(result['content'],media_type=result['media_type'],
                            headers={'Content-Disposition':f'attachment; filename="{result["name"]}"'})
        return answer(result)

    @app.api_route('/api/{route}',methods=['GET','POST'])
    async def workspace_api(route:str,request:Request):
        permission='workspace.read'
        if request.method=='POST':
            if route=='companies':permission='companies.manage'
            elif route in REVIEW_ROUTES:permission='workspace.review'
            elif route in WRITE_ROUTES:permission='workspace.write'
            else:raise IdentityError('Recurso não disponível.',404)
        user=actor(request,permission)
        if route=='companies' and request.method=='POST' and user['role']!='admin':raise IdentityError('Administração global necessária.',403)
        return await domain(route,request,user)

    @app.get('/workspace')
    def workspace(request:Request):
        actor(request,'workspace.read')
        html=(WEB_ROOT/'index.html').read_text(encoding='utf-8').replace('__LOCAL_TOKEN__',identity.csrf(request.cookies[COOKIE]))
        html=html.replace('<body>','<body class="embedded-workspace">')
        html=html.replace('</head>','<link rel="stylesheet" href="/portal/workspace.css"></head>')
        return Response(html,media_type='text/html')
    @app.get('/')
    def index():return Response((PORTAL/'index.html').read_bytes(),media_type='text/html')
    @app.get('/public')
    def public():return Response((PORTAL/'public.html').read_bytes(),media_type='text/html')
    # Lista explícita: arquivos fiscais e diretórios de dados nunca são servidos.
    def static_handler(name):
        def serve():return Response((WEB_ROOT/name).read_bytes(),media_type='text/css' if name.endswith('.css') else 'text/javascript')
        return serve
    for filename in ('app.js','posting_editor.js','posting_math.js','style.css'):
        app.add_api_route('/'+filename,static_handler(filename),methods=['GET'])
    app.mount('/assets',StaticFiles(directory=WEB_ROOT/'assets'),name='identity-assets')
    app.mount('/portal',StaticFiles(directory=PORTAL),name='portal-assets')
    return app
