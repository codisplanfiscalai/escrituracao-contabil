"""Identidade persistente, sessões, permissões, TOTP e entrega transacional."""
from __future__ import annotations
import base64
from contextlib import contextmanager
from email.message import EmailMessage
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import smtplib
import sqlite3
import ssl
import struct
import time
from urllib.parse import quote
from cryptography.fernet import Fernet

PERMISSIONS = {
    'workspace.read': 'Consultar escrituração', 'workspace.write': 'Preparar documentos e partidas',
    'workspace.review': 'Revisar e fechar lotes', 'companies.manage': 'Cadastrar empresas',
    'users.manage': 'Administrar usuários', 'roles.manage': 'Administrar perfis',
    'settings.manage': 'Configurar o sistema', 'audit.read': 'Consultar auditoria',
    'client.read': 'Consultar documentos do cliente', 'client.upload': 'Enviar documentos do cliente',
}
ROLES = {
    'admin': ('Administrador', list(PERMISSIONS)),
    'accountant': ('Operador contábil', ['workspace.read', 'workspace.write', 'client.read', 'client.upload']),
    'reviewer': ('Revisor', ['workspace.read', 'workspace.review', 'client.read']),
    'client': ('Cliente', ['client.read', 'client.upload']),
    'reader': ('Consulta', ['workspace.read', 'client.read']),
}

class IdentityError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        raise IdentityError('A senha deve conter de 12 a 128 caracteres.')
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 600_000).hex()
    return f'pbkdf2_sha256$600000${salt}${key}'


def verify_password(value, encoded):
    if not isinstance(value, str) or len(value) > 128:
        return False
    try:
        kind, rounds, salt, expected = encoded.split('$')
        if kind != 'pbkdf2_sha256' or int(rounds) != 600_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def otp(secret, counter):
    raw = hmac.new(base64.b32decode(secret), struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = raw[-1] & 15
    return str((struct.unpack('>I', raw[offset:offset+4])[0] & 0x7fffffff) % 1_000_000).zfill(6)


def private_file(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
            handle.write(value)
    except FileExistsError:
        pass
    return path.read_bytes().strip()


class Identity:
    def __init__(self, directory, public_url, setup_file=None, key_file=None):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'identity.sqlite3'
        self.public_url = public_url.rstrip('/')
        self.setup_file = Path(setup_file) if setup_file else self.directory / 'setup.token'
        self.setup_secret = private_file(self.setup_file, secrets.token_urlsafe(40).encode()).decode()
        if len(self.setup_secret) < 32:
            raise ValueError('A chave de instalação precisa conter pelo menos 32 caracteres.')
        self.key = private_file(Path(key_file) if key_file else self.directory / 'master.key', Fernet.generate_key())
        self.cipher = Fernet(self.key)
        self.dummy_password = password_hash(secrets.token_urlsafe(32))
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS roles(id TEXT PRIMARY KEY,name TEXT NOT NULL,permissions TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL REFERENCES roles(id),companies TEXT NOT NULL DEFAULT '[]',active INTEGER NOT NULL DEFAULT 1,mfa TEXT NOT NULL DEFAULT '',last_otp INTEGER NOT NULL DEFAULT -1,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),created REAL NOT NULL,seen REAL NOT NULL,expires REAL NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,label TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS challenges(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,purpose TEXT NOT NULL,secret TEXT NOT NULL DEFAULT '',expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS recovery(user_id TEXT NOT NULL,code TEXT NOT NULL,PRIMARY KEY(user_id,code));
            CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,count INTEGER NOT NULL,started REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,created REAL NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,target TEXT NOT NULL,details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT,recipient TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,available REAL NOT NULL,error TEXT NOT NULL DEFAULT '');
            ''')
            for key, (name, permissions) in ROLES.items():
                db.execute('INSERT OR IGNORE INTO roles VALUES(?,?,?)', (key, name, json.dumps(permissions)))
        try: os.chmod(self.path, 0o600)
        except OSError: pass

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally: db.close()

    def log(self, db, actor, action, target='', details=None):
        db.execute('INSERT INTO audit(created,actor,action,target,details) VALUES(?,?,?,?,?)',
                   (time.time(), actor, action, str(target), json.dumps(details or {}, ensure_ascii=False)))

    def configured(self):
        with self.connect() as db: return bool(db.execute('SELECT 1 FROM users LIMIT 1').fetchone())

    def throttle(self, key, limit=10, seconds=300):
        now = time.time()
        with self.connect() as db:
            db.execute('DELETE FROM attempts WHERE started<?', (now - 3600,))
            row = db.execute('SELECT * FROM attempts WHERE key=?', (digest(key),)).fetchone()
            if row and row['started'] + seconds > now:
                if row['count'] >= limit: raise IdentityError('Muitas tentativas. Aguarde alguns minutos.', 429)
                db.execute('UPDATE attempts SET count=count+1 WHERE key=?', (digest(key),))
            else: db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)', (digest(key), 1, now))

    def email(self, value):
        value = str(value).strip().lower()
        if len(value) > 254 or not re.fullmatch(r'[^\s@\r\n]+@[^\s@\r\n]+\.[^\s@\r\n]+', value):
            raise IdentityError('Informe um e-mail válido.')
        return value

    def setup(self, data, peer):
        self.throttle('setup:' + peer, 5)
        if not hmac.compare_digest(str(data.get('token', '')), self.setup_secret):
            raise IdentityError('Chave de instalação inválida.', 403)
        encoded = password_hash(data.get('password'))
        email = self.email(data.get('email', ''))
        name = str(data.get('name', '')).strip()[:160]
        if not name: raise IdentityError('Informe o nome do administrador.')
        with self.connect() as db:
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone(): raise IdentityError('Instalação já configurada.', 409)
            ident = secrets.token_hex(16)
            db.execute('INSERT INTO users(id,name,email,password,role,created) VALUES(?,?,?,?,?,?)', (ident,name,email,encoded,'admin',time.time()))
            self.log(db, ident, 'installation.configured')
        return {'configured': True}

    def _public_user(self, db, user):
        role = db.execute('SELECT * FROM roles WHERE id=?', (user['role'],)).fetchone()
        return {**{k: user[k] for k in ('id','name','email','role','active')}, 'active': bool(user['active']), 'companies': json.loads(user['companies']),
                'permissions': json.loads(role['permissions']), 'role_name': role['name'], 'mfa_enabled': bool(user['mfa'])}

    def _session(self, db, user, label):
        raw = secrets.token_urlsafe(48)
        now = time.time()
        db.execute('DELETE FROM sessions WHERE expires<?', (now - 86400,))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,0,?)', (digest(raw),user['id'],now,now,now+28800,label[:100]))
        self.log(db,user['id'],'session.created')
        return raw

    def csrf(self, token):
        return hmac.new(self.key, ('csrf:' + token).encode(), hashlib.sha256).hexdigest()

    def login(self, data, peer):
        email = str(data.get('email','')).lower().strip()
        self.throttle('login:ip:'+peer, 60)
        self.throttle('login:email:'+email, 10)
        with self.connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
            valid = verify_password(data.get('password'), user['password'] if user else self.dummy_password)
            if not valid or not user or not user['active']: raise IdentityError('Credenciais inválidas.', 401)
            if user['mfa']:
                challenge = secrets.token_urlsafe(40)
                db.execute('DELETE FROM challenges WHERE expires<?', (time.time(),))
                db.execute('INSERT INTO challenges VALUES(?,?,?,?,?)', (digest(challenge),user['id'],'login','',time.time()+300))
                return {'challenge':challenge, 'mfa_required':True}, None
            raw = self._session(db,user,peer)
            return {'user':self._public_user(db,user), 'csrf':self.csrf(raw)}, raw

    def authenticate(self, token):
        with self.connect() as db:
            now = time.time()
            session = db.execute('SELECT * FROM sessions WHERE token=?', (digest(token),)).fetchone()
            if not session or session['revoked'] or session['expires'] <= now or session['seen'] < now-1800:
                raise IdentityError('Sessão expirada. Entre novamente.',401)
            user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
            if not user or not user['active']: raise IdentityError('Conta indisponível.',401)
            db.execute('UPDATE sessions SET seen=? WHERE token=?', (now,digest(token)))
            return self._public_user(db,user)

    def require(self, user, permission):
        if permission not in user['permissions']: raise IdentityError('Seu perfil não permite esta operação.',403)

    def _proof(self, db, user, code, allow_recovery=True):
        if not user['mfa']: raise IdentityError('2FA não está habilitado.')
        secret = self.cipher.decrypt(user['mfa'].encode()).decode()
        counter = int(time.time()) // 30
        for candidate in (counter,counter-1,counter+1):
            if candidate > user['last_otp'] and hmac.compare_digest(otp(secret,candidate),str(code)):
                db.execute('UPDATE users SET last_otp=? WHERE id=?', (candidate,user['id']))
                return
        if allow_recovery:
            result=db.execute('DELETE FROM recovery WHERE user_id=? AND code=?',(user['id'],digest(str(code))))
            if result.rowcount: return
        raise IdentityError('Código inválido ou já utilizado.',401)

    def verify_login(self, challenge, code, peer):
        self.throttle('mfa:ip:'+peer,30)
        self.throttle('mfa:'+digest(str(challenge)),5)
        with self.connect() as db:
            row=db.execute("SELECT * FROM challenges WHERE token=? AND purpose='login' AND expires>?",(digest(str(challenge)),time.time())).fetchone()
            if not row: raise IdentityError('Desafio expirado. Entre novamente.',401)
            user=db.execute('SELECT * FROM users WHERE id=?',(row['user_id'],)).fetchone()
            if not user or not user['active']:raise IdentityError('Conta indisponível.',401)
            self._proof(db,user,code)
            db.execute('DELETE FROM challenges WHERE token=?',(row['token'],))
            raw=self._session(db,user,peer)
            return {'user':self._public_user(db,user),'csrf':self.csrf(raw)},raw

    def begin_mfa(self,user,password):
        self.throttle('mfa:enroll:'+user['id'],5)
        with self.connect() as db:
            row=db.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
            if not verify_password(password,row['password']):raise IdentityError('Senha atual inválida.',401)
            if row['mfa']:raise IdentityError('2FA já está habilitado.',409)
            secret=base64.b32encode(secrets.token_bytes(20)).decode()
            token=secrets.token_urlsafe(40)
            db.execute("DELETE FROM challenges WHERE user_id=? AND purpose='enroll'",(user['id'],))
            db.execute('INSERT INTO challenges VALUES(?,?,?,?,?)',(digest(token),user['id'],'enroll',self.cipher.encrypt(secret.encode()).decode(),time.time()+300))
            return {'token':token,'secret':secret,'uri':f'otpauth://totp/Escritura:{quote(user["email"],safe="")}?secret={secret}&issuer=Escritura&algorithm=SHA1&digits=6&period=30'}

    def confirm_mfa(self,user,token,code):
        self.throttle('mfa:confirm:'+user['id'],5)
        with self.connect() as db:
            row=db.execute("SELECT * FROM challenges WHERE token=? AND user_id=? AND purpose='enroll' AND expires>?",(digest(str(token)),user['id'],time.time())).fetchone()
            if not row:raise IdentityError('Configuração expirada.',401)
            secret=self.cipher.decrypt(row['secret'].encode()).decode()
            counter=int(time.time())//30
            matches=[c for c in (counter,counter-1,counter+1) if hmac.compare_digest(otp(secret,c),str(code))]
            if not matches:raise IdentityError('Código inválido.',401)
            db.execute('UPDATE users SET mfa=?,last_otp=? WHERE id=?',(row['secret'],matches[0],user['id']))
            db.execute('DELETE FROM challenges WHERE user_id=?',(user['id'],))
            db.execute('DELETE FROM recovery WHERE user_id=?',(user['id'],))
            codes=[secrets.token_hex(8) for _ in range(8)]
            db.executemany('INSERT INTO recovery VALUES(?,?)',[(user['id'],digest(c)) for c in codes])
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(user['id'],))
            self.log(db,user['id'],'mfa.enabled')
            return {'recovery_codes':codes}

    def disable_mfa(self,user,password,code):
        self.throttle('mfa:disable:'+user['id'],5)
        with self.connect() as db:
            row=db.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
            if not verify_password(password,row['password']):raise IdentityError('Senha atual inválida.',401)
            self._proof(db,row,code)
            db.execute("UPDATE users SET mfa='',last_otp=-1 WHERE id=?",(user['id'],))
            db.execute('DELETE FROM recovery WHERE user_id=?',(user['id'],))
            db.execute('DELETE FROM challenges WHERE user_id=?',(user['id'],))
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(user['id'],))
            self.log(db,user['id'],'mfa.disabled')

    def users(self):
        with self.connect() as db:return [self._public_user(db,r) for r in db.execute('SELECT * FROM users ORDER BY name')]

    def save_user(self,actor,data,valid_companies):
        email=self.email(data.get('email',''))
        name=str(data.get('name','')).strip()[:160]
        if not name:raise IdentityError('Informe o nome.')
        if not isinstance(data.get('companies',[]),list) or not isinstance(data.get('active',True),bool):
            raise IdentityError('Vínculos e situação do usuário inválidos.')
        companies=sorted({str(c) for c in data.get('companies',[])})
        if not set(companies)<=set(map(str,valid_companies)):raise IdentityError('Empresa não encontrada.')
        encoded=password_hash(data['password']) if data.get('password') else None
        with self.connect() as db:
            role=str(data.get('role','client'))
            if not db.execute('SELECT 1 FROM roles WHERE id=?',(role,)).fetchone():raise IdentityError('Perfil não encontrado.')
            ident=str(data.get('id') or secrets.token_hex(16))
            previous=db.execute('SELECT * FROM users WHERE id=?',(ident,)).fetchone()
            if data.get('id') and not previous:raise IdentityError('Usuário não encontrado.',404)
            active=bool(data.get('active',True))
            if previous and previous['role']=='admin' and (role!='admin' or not active):
                if db.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1 AND id!=?",(ident,)).fetchone()[0]==0:
                    raise IdentityError('Mantenha pelo menos um administrador ativo.',409)
            if previous:
                db.execute('UPDATE users SET name=?,email=?,role=?,companies=?,active=?,password=? WHERE id=?',(name,email,role,json.dumps(companies),int(active),encoded or previous['password'],ident))
                db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(ident,))
                db.execute('DELETE FROM challenges WHERE user_id=?',(ident,))
            else:
                if not encoded:raise IdentityError('Informe a senha inicial.')
                db.execute('INSERT INTO users(id,name,email,password,role,companies,active,created) VALUES(?,?,?,?,?,?,?,?)',(ident,name,email,encoded,role,json.dumps(companies),int(active),time.time()))
            self.log(db,actor['id'],'user.updated' if previous else 'user.created',ident)
            return self._public_user(db,db.execute('SELECT * FROM users WHERE id=?',(ident,)).fetchone())

    def roles(self):
        with self.connect() as db:return [{'id':r['id'],'name':r['name'],'permissions':json.loads(r['permissions'])} for r in db.execute('SELECT * FROM roles ORDER BY name')]

    def save_role(self,actor,data):
        ident=str(data.get('id') or secrets.token_hex(8))
        if ident in ROLES:raise IdentityError('Perfis padrão são preservados. Crie um perfil próprio.')
        permissions=sorted(set(data.get('permissions',[])))
        if not set(permissions)<=set(PERMISSIONS):raise IdentityError('Permissão desconhecida.')
        name=str(data.get('name','')).strip()[:100]
        if not name:raise IdentityError('Informe o nome do perfil.')
        with self.connect() as db:
            db.execute('INSERT INTO roles VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,permissions=excluded.permissions',(ident,name,json.dumps(permissions)))
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id IN(SELECT id FROM users WHERE role=?)',(ident,))
            self.log(db,actor['id'],'role.updated',ident,{'permissions':permissions})
        return {'id':ident}

    def sessions(self,user):
        with self.connect() as db:return [dict(r) for r in db.execute('SELECT token AS id,created,seen,expires,revoked,label FROM sessions WHERE user_id=? ORDER BY created DESC LIMIT 50',(user['id'],))]

    def revoke(self,user,ident):
        with self.connect() as db:
            db.execute('UPDATE sessions SET revoked=1 WHERE token=? AND user_id=?',(ident,user['id']))
            self.log(db,user['id'],'session.revoked',ident[:12])

    def settings(self,include_secret=False):
        with self.connect() as db:
            values={r['key']:json.loads(r['value']) for r in db.execute('SELECT * FROM settings')}
        if not include_secret:
            smtp=values.get('smtp',{}).copy()
            smtp['has_password']=bool(smtp.pop('password',''))
            values['smtp']=smtp
        return values

    def save_settings(self,user,data):
        allowed={'general','smtp','menu'}
        if not set(data)<=allowed:raise IdentityError('Configuração desconhecida.')
        with self.connect() as db:
            for key,value in data.items():
                if key=='smtp':
                    if not isinstance(value,dict):raise IdentityError('SMTP inválido.')
                    if value.get('mode') not in ('starttls','ssl'):raise IdentityError('SMTP exige TLS.')
                    if not 1<=int(value.get('port',0))<=65535:raise IdentityError('Porta SMTP inválida.')
                    self.email(value.get('sender',''))
                    if not re.fullmatch(r'[A-Za-z0-9.-]{1,253}',str(value.get('host',''))):raise IdentityError('Servidor SMTP inválido.')
                    old=db.execute("SELECT value FROM settings WHERE key='smtp'").fetchone()
                    value={k:value.get(k,'') for k in ('host','port','mode','sender','username','password')}
                    value['password']=self.cipher.encrypt(value['password'].encode()).decode() if value['password'] else (json.loads(old[0]).get('password','') if old else '')
                elif key=='general':
                    value={k:str(value.get(k,''))[:200] for k in ('display_name','support_email')}
                elif key=='menu':
                    if not isinstance(value,list) or len(value)>20:raise IdentityError('Menu inválido.')
                    value=[str(v) for v in value]
                db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)))
            self.log(db,user['id'],'settings.updated',details={'sections':list(data)})

    def _enqueue(self,db,email,subject,text):
        payload=self.cipher.encrypt(json.dumps({'subject':subject,'text':text}).encode()).decode()
        db.execute('INSERT INTO outbox(recipient,payload,available) VALUES(?,?,?)',(email,payload,time.time()))

    def request_reset(self,email,peer):
        self.throttle('reset:ip:'+peer,10)
        email=str(email).lower().strip()
        self.throttle('reset:email:'+email,3)
        if not self.settings().get('smtp',{}).get('host'):
            raise IdentityError('Recuperação por e-mail ainda não configurada. Contate o administrador.',503)
        with self.connect() as db:
            user=db.execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
            if user:
                raw=secrets.token_urlsafe(40)
                db.execute("DELETE FROM challenges WHERE user_id=? AND purpose='reset'",(user['id'],))
                db.execute('INSERT INTO challenges VALUES(?,?,?,?,?)',(digest(raw),user['id'],'reset','',time.time()+1800))
                self._enqueue(db,email,'Escritura · redefinição de senha',f'Abra o link em até 30 minutos:\n{self.public_url}/#/reset/{raw}\nSe não solicitou, ignore esta mensagem.')
                self.log(db,user['id'],'password.reset_requested')
        return {'message':'Se o endereço estiver cadastrado, enviaremos as instruções.'}

    def reset_password(self,token,password,code,peer):
        self.throttle('reset:consume:'+peer,10)
        encoded=password_hash(password)
        with self.connect() as db:
            row=db.execute("SELECT * FROM challenges WHERE token=? AND purpose='reset' AND expires>?",(digest(str(token)),time.time())).fetchone()
            if not row:raise IdentityError('Link inválido ou expirado.',400)
            user=db.execute('SELECT * FROM users WHERE id=?',(row['user_id'],)).fetchone()
            if not user or not user['active']:raise IdentityError('Link inválido ou expirado.',400)
            if user['mfa']:self._proof(db,user,code)
            db.execute('UPDATE users SET password=? WHERE id=?',(encoded,user['id']))
            db.execute('DELETE FROM challenges WHERE user_id=?',(user['id'],))
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(user['id'],))
            self.log(db,user['id'],'password.reset')
        return {'message':'Senha redefinida. Entre novamente.'}

    def queue_test(self,user):
        with self.connect() as db:
            self._enqueue(db,user['email'],'Escritura · teste de e-mail','A entrega transacional está funcionando.')
            self.log(db,user['id'],'email.test_requested')
        return {'message':'Teste incluído na fila de envio.'}

    def deliver_one(self,sender=None):
        settings=self.settings(include_secret=True).get('smtp',{})
        if not settings.get('host'):return False
        now=time.time()
        with self.connect() as db:
            row=db.execute("SELECT * FROM outbox WHERE (status='pending' OR (status='sending' AND available<?)) AND available<=? AND attempts<5 ORDER BY id LIMIT 1",(now-300,now)).fetchone()
            if not row:return False
            db.execute("UPDATE outbox SET status='sending',attempts=attempts+1,available=? WHERE id=?",(now,row['id']))
        try:
            payload=json.loads(self.cipher.decrypt(row['payload'].encode()))
            message=EmailMessage();message['Subject']=payload['subject'];message['From']=settings['sender'];message['To']=row['recipient']
            message['Message-ID']=f'<escritura-{row["id"]}@{settings["sender"].split("@")[1]}>'
            message.set_content(payload['text'])
            if sender:sender(settings,message)
            else:
                cls=smtplib.SMTP_SSL if settings['mode']=='ssl' else smtplib.SMTP
                kwargs={'timeout':15}
                if settings['mode']=='ssl':kwargs['context']=ssl.create_default_context()
                with cls(settings['host'],int(settings['port']),**kwargs) as smtp:
                    if settings['mode']=='starttls':smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
                    if settings.get('username'):smtp.login(settings['username'],self.cipher.decrypt(settings['password'].encode()).decode())
                    smtp.send_message(message)
            with self.connect() as db:db.execute("UPDATE outbox SET status='sent',payload='',error='' WHERE id=?",(row['id'],))
        except Exception:
            with self.connect() as db:db.execute("UPDATE outbox SET status=CASE WHEN attempts>=5 THEN 'failed' ELSE 'pending' END,available=?,error='Falha de conexão, autenticação ou entrega SMTP' WHERE id=?",(now+60,row['id']))
        return True

    def outbox(self):
        with self.connect() as db:return [dict(r) for r in db.execute('SELECT id,recipient,status,attempts,available,error FROM outbox ORDER BY id DESC LIMIT 100')]

    def audit(self,before=2**63-1):
        with self.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM audit WHERE id<? ORDER BY id DESC LIMIT 100',(int(before),))]
