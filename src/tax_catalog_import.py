"""Reviewed, company-owned catalogue snapshots; no network fetch or legal inference."""
import csv
import hashlib
import io
import json
import re
from datetime import date
from urllib.parse import urlsplit
from .accounting_store import digest, dump, identifier
from .tax_catalog import validate_catalog_code

CATALOG_IMPORT_SCHEMA = """
CREATE TABLE IF NOT EXISTS tax_catalog_imports (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, filename TEXT NOT NULL,
 raw_bytes BLOB NOT NULL, raw_sha256 TEXT NOT NULL, snapshot TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS tax_catalog_import_applications (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 import_id INTEGER NOT NULL REFERENCES tax_catalog_imports(id), request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS tax_catalog_scopes (
 company_id INTEGER NOT NULL REFERENCES companies(id), kind TEXT NOT NULL, code TEXT NOT NULL,
 snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL, PRIMARY KEY(company_id,kind,code));
"""
MAX_CATALOG_BYTES = 8 * 1024 * 1024
FIELDS = {'code','description','valid_from','valid_to'}
SYSTEMS = {'ncm':{'NCM'}, 'cfop':{'CFOP'}, 'revenue':{'DARF','RECEITA_ESTADUAL','RECEITA_MUNICIPAL'},
           'service':{'LC116','NFSE_NACIONAL','SERVICO_MUNICIPAL'}}
STATES = set('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())


def iso_day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value) or date.fromisoformat(value).isoformat()!=value:
        raise ValueError('Data deve usar AAAA-MM-DD')
    return value


def metadata(value):
    from .persistence import _text
    fields={'kind','system','jurisdiction','publisher','source_url','edition','retrieved_on','coverage','transformation_reference'}
    if not isinstance(value,dict) or set(value)!=fields:
        raise ValueError('Informe tipo, sistema, jurisdição, órgão, URL, edição, consulta, recorte e conversão')
    result={key:_text(v,key,1000 if key in {'source_url','transformation_reference'} else 200) for key,v in value.items()}
    if result['kind'] not in SYSTEMS or result['system'] not in SYSTEMS[result['kind']]:
        raise ValueError('Sistema não corresponde ao tipo de cadastro')
    jurisdiction=result['jurisdiction'];system=result['system']
    if system=='RECEITA_ESTADUAL':
        valid=jurisdiction.startswith('UF:') and jurisdiction[3:] in STATES
    elif system in {'SERVICO_MUNICIPAL','RECEITA_MUNICIPAL'}:
        valid=bool(re.fullmatch(r'MUN:[0-9]{7}',jurisdiction))
    else:
        valid=jurisdiction=='BR'
    if not valid:
        raise ValueError('Jurisdição exige BR, UF:XX ou MUN:código IBGE de sete dígitos conforme o sistema')
    url=urlsplit(result['source_url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError('A URL de origem deve ser HTTPS, sem credenciais ou fragmento; não será acessada pelo servidor')
    if result['coverage'] not in {'parcial','snapshot_informado'}:
        raise ValueError('Declare o recorte; completude não é certificada')
    if iso_day(result['retrieved_on'])>date.today().isoformat():
        raise ValueError('Data de consulta não pode estar no futuro')
    return result


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Chave JSON repetida no arquivo')
        result[key]=value
    return result


def parse_catalog(content, filename, meta):
    if not isinstance(content,bytes) or not 0<len(content)<=MAX_CATALOG_BYTES:
        raise ValueError('Arquivo de cadastro deve ter de 1 byte a 8 MiB')
    try:
        text=content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('Converta explicitamente para UTF-8 e registre a transformação') from None
    if filename.lower().endswith('.json'):
        try:
            obj=json.loads(text,object_pairs_hook=unique_object)
        except (json.JSONDecodeError,RecursionError):
            raise ValueError('JSON de cadastro inválido') from None
        if not isinstance(obj,dict) or set(obj)!={'profile','records'} or obj['profile']!='cadastro-fiscal-v1':
            raise ValueError('Use o perfil cadastro-fiscal-v1; leiautes nativos oficiais não são presumidos')
        rows=obj['records']
        parser='cadastro-fiscal-json-v1'
    elif filename.lower().endswith('.csv'):
        try:
            reader=csv.DictReader(io.StringIO(text,newline=''),delimiter=';',strict=True)
            if reader.fieldnames!=['code','description','valid_from','valid_to']:
                raise ValueError('CSV exige cabeçalho code;description;valid_from;valid_to, nessa ordem')
            rows=[]
            for row in reader:
                if len(rows)>=15000:raise ValueError('Limite de 15000 registros excedido')
                rows.append(row)
        except csv.Error:
            raise ValueError('CSV de cadastro inválido') from None
        parser='cadastro-fiscal-csv-v1'
    else:
        raise ValueError('Importação disponível em CSV ou JSON do perfil documentado; PDF/HTML/XLSX exigem conversão conferida')
    if not isinstance(rows,list) or not 1<=len(rows)<=15000:
        raise ValueError('Importação exige de 1 a 15000 registros por snapshot')
    normalized=[];seen=set()
    for index,row in enumerate(rows,1):
        try:
            if not isinstance(row,dict) or set(row)!=FIELDS:
                raise ValueError('Registro exige somente code, description, valid_from e valid_to')
            code,data=validate_catalog_code(meta['kind'],row['code'],{**{key:row[key] for key in FIELDS-{'code'}},'source_reference':'Recibo de importação'})
            if code in seen:
                raise ValueError('Código repetido; use snapshots separados para outras vigências')
            seen.add(code)
            normalized.append({'code':code,**{key:data[key] for key in FIELDS-{'code'}}})
        except (ValueError,TypeError) as error:
            raise ValueError(f'Registro {index}: {error}') from None
    return {'profile':parser,'metadata':meta,'records':sorted(normalized,key=lambda r:r['code']),
            'limits':['Origem declarada pelo operador; URL e hash não autenticam conteúdo oficial',
                      'Ausências não inativam códigos existentes','Não define tributação, alíquota ou direito a crédito']}


def selected_codes(codes):
    if not isinstance(codes,list) or not 1<=len(codes)<=500 or any(not isinstance(c,str) for c in codes) or len(set(codes))!=len(codes):
        raise ValueError('Selecione de 1 a 500 códigos distintos')
    return sorted(codes)


class TaxCatalogImportMixin:
    def _catalog_import(self, company_id, import_id):
        self._company(identifier(company_id))
        row=self.db.execute('SELECT * FROM tax_catalog_imports WHERE company_id=? AND id=?',(company_id,identifier(import_id))).fetchone()
        if not row:
            raise ValueError('Importação não pertence à empresa')
        result=dict(row);result['snapshot']=json.loads(result['snapshot'])
        if digest(result['snapshot'])!=result['snapshot_hash'] or hashlib.sha256(bytes(result['raw_bytes'])).hexdigest()!=result['raw_sha256'] or digest([result['filename'],result['raw_sha256'],result['snapshot_hash'],result['reason']])!=result['request_hash']:
            raise ValueError('Arquivo ou snapshot de importação alterado')
        return result

    def catalog_imports(self, company_id):
        self._company(identifier(company_id))
        return [self.catalog_import_detail(company_id,r['id'],limit=0) for r in self.db.execute('SELECT id FROM tax_catalog_imports WHERE company_id=? ORDER BY id DESC',(company_id,))]

    def catalog_import_detail(self, company_id, import_id, *, query='', offset=0, limit=100):
        row=self._catalog_import(company_id,import_id)
        from .persistence import _text
        query=_text(query,'Busca',100,False).casefold()
        if isinstance(offset,str) and re.fullmatch(r'[0-9]{1,6}',offset):offset=int(offset)
        if isinstance(limit,str) and re.fullmatch(r'[0-9]{1,3}',limit):limit=int(limit)
        if type(offset)!=int or offset<0 or type(limit)!=int or not 0<=limit<=100:
            raise ValueError('Paginação inválida')
        records=row['snapshot']['records'];filtered=[r for r in records if query in (r['code']+' '+r['description']).casefold()]
        return {key:row[key] for key in ('id','filename','raw_sha256','snapshot_hash','actor','reason','created_at')} | {
            'metadata':row['snapshot']['metadata'],'parser':row['snapshot']['profile'],'limits':row['snapshot']['limits'],
            'total_records':len(records),'filtered_records':len(filtered),'offset':offset,'records':filtered[offset:offset+limit]}

    def receive_catalog_import(self, company_id, filename, content, meta, request_key, reason):
        from .persistence import _text
        filename=_text(filename,'Arquivo',200)
        request_key=_text(request_key,'Tentativa',80);reason=_text(reason,'Motivo',2000)
        normalized=parse_catalog(content,filename,metadata(meta))
        raw_hash=hashlib.sha256(content).hexdigest();snapshot_hash=digest(normalized)
        request_hash=digest([filename,raw_hash,snapshot_hash,reason])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self._company(identifier(company_id))
            old=self.db.execute('SELECT id,request_hash FROM tax_catalog_imports WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if old:
                if old['request_hash']!=request_hash:raise ValueError('Tentativa de recepção usada com outro conteúdo')
                return {'import':self.catalog_import_detail(company_id,old['id']),'duplicate':True}
            import_id=self.db.execute('INSERT INTO tax_catalog_imports(company_id,request_key,request_hash,filename,raw_bytes,raw_sha256,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (company_id,request_key,request_hash,filename,content,raw_hash,dump(normalized),snapshot_hash,self.actor,reason,self._now())).lastrowid
            self._audit(company_id,'cadastro_recebido_sem_ativacao',{'import_id':import_id,'raw_sha256':raw_hash,'snapshot_hash':snapshot_hash,'reason':reason})
        return {'import':self.catalog_import_detail(company_id,import_id),'duplicate':False}

    def catalog_import_original(self, company_id, import_id):
        row=self._catalog_import(company_id,import_id)
        extension='json' if row['snapshot']['profile']=='cadastro-fiscal-json-v1' else 'csv'
        return {'name':f'cadastro-{row["id"]}.{extension}','media_type':'application/octet-stream','content':bytes(row['raw_bytes'])}

    def _catalog_scope(self, company_id, kind, code):
        row=self.db.execute('SELECT * FROM tax_catalog_scopes WHERE company_id=? AND kind=? AND code=?',(company_id,kind,code)).fetchone()
        if not row:return None
        data=json.loads(row['snapshot'])
        if digest(data)!=row['snapshot_hash']:raise ValueError('Escopo do cadastro alterado')
        return data

    def preview_catalog_application(self, company_id, import_id, codes, application_from):
        receipt=self._catalog_import(company_id,import_id);meta=receipt['snapshot']['metadata']
        application_from=iso_day(application_from)
        codes=selected_codes(codes)
        source={r['code']:r for r in receipt['snapshot']['records']}
        if set(codes)-set(source):raise ValueError('Código selecionado não pertence ao arquivo')
        current={}
        for code in codes:
            row=self.db.execute('SELECT * FROM tax_catalog_versions WHERE company_id=? AND kind=? AND code=? ORDER BY version DESC LIMIT 1',(company_id,meta['kind'],code)).fetchone()
            if row:current[code]=self._tax_catalog_row(row)
        scopes={code:self._catalog_scope(company_id,meta['kind'],code) for code in codes};blockers=[];changes=[]
        for code in sorted(codes):
            scope=scopes[code]
            if scope and (scope['system'],scope['jurisdiction'])!=(meta['system'],meta['jurisdiction']):
                blockers.append(code+': Sistema/jurisdição difere do escopo já vinculado a este código na empresa; não há conversão ou colisão silenciosa')
            record=source[code];start=max(application_from,record['valid_from']);end=record['valid_to']
            if end and start>end:blockers.append(code+': código sem vigência na data de aplicação declarada')
            try:self._assert_tax_validity_open(company_id,start,end)
            except ValueError as error:blockers.append(code+': '+str(error))
            origin={'import_id':receipt['id'],'raw_sha256':receipt['raw_sha256'],'system':meta['system'],'jurisdiction':meta['jurisdiction'],
                    'source_url':meta['source_url'],'edition':meta['edition'],'source_valid_from':record['valid_from'],'source_valid_to':end,
                    'application_from':application_from,'authority_status':'origem_declarada_na_importacao'}
            data={'description':record['description'],'valid_from':start,'valid_to':end,
                  'source_reference':f'Importação #{receipt["id"]}; {meta["system"]}; edição {meta["edition"]}; SHA-256 {receipt["raw_sha256"]}'}
            previous=current.get(code)
            changes.append({'code':code,'state':'ativo','data':data,'origin':origin,'expected_version':previous['version'] if previous else 0,
                            'previous':previous})
        snapshot={'profile':'aplicacao-cadastro-v1','company_id':identifier(company_id),'import_id':receipt['id'],
                  'import_hash':receipt['snapshot_hash'],'raw_sha256':receipt['raw_sha256'],'filename':receipt['filename'],'parser':receipt['snapshot']['profile'],
                  'metadata':meta,'application_from':application_from,'scopes':scopes,
                  'legacy_count':sum(code in current and scopes[code] is None for code in codes),
                  'legacy_hash':digest([(current[c]['id'],current[c]['snapshot_hash']) for c in codes if c in current and scopes[c] is None]),
                  'changes':changes,'blockers':blockers}
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def catalog_applications(self, company_id, import_id, *, summary=False):
        self._catalog_import(company_id,import_id);results=[]
        for row in self.db.execute('SELECT * FROM tax_catalog_import_applications WHERE company_id=? AND import_id=? ORDER BY id DESC',(company_id,import_id)):
            data=dict(row);data['snapshot']=json.loads(data['snapshot'])
            if digest(data['snapshot'])!=data['snapshot_hash']:raise ValueError('Aplicação de cadastro alterada')
            if summary:
                results.append({key:data[key] for key in ('id','import_id','actor','reason','created_at')} | {
                    'manifest_hash':data['snapshot_hash'],'version_count':len(data['snapshot']['versions']),'review_reference':data['snapshot']['review_reference']})
            else:results.append(data)
        return results

    def catalog_application(self, company_id, application_id):
        self._company(identifier(company_id))
        row=self.db.execute('SELECT * FROM tax_catalog_import_applications WHERE company_id=? AND id=?',(company_id,identifier(application_id))).fetchone()
        if not row:raise ValueError('Aplicação não pertence à empresa')
        data=dict(row);data['snapshot']=json.loads(data['snapshot'])
        if digest(data['snapshot'])!=data['snapshot_hash']:raise ValueError('Aplicação de cadastro alterada')
        return data

    def apply_catalog_import(self, company_id, import_id, codes, application_from, expected_hash, request_key, reason, review_reference, confirmed=False, acknowledge_legacy=False):
        from .persistence import _text
        reason=_text(reason,'Motivo da aplicação',2000);review_reference=_text(review_reference,'Referência da revisão de conteúdo, vigências e jurisdição',1000)
        request_key=_text(request_key,'Tentativa',80)
        codes=selected_codes(codes)
        if confirmed is not True:raise ValueError('Confirme a revisão do conteúdo, origem, vigências, seleção e jurisdição')
        request_hash=digest([identifier(import_id),codes,application_from,expected_hash,reason,review_reference,acknowledge_legacy])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self._company(identifier(company_id))
            old=self.db.execute('SELECT id,request_hash FROM tax_catalog_import_applications WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if old:
                if old['request_hash']!=request_hash:raise ValueError('Tentativa de aplicação usada com outro conteúdo')
                return self.catalog_application(company_id,old['id'])
            preview=self.preview_catalog_application(company_id,import_id,codes,application_from)
            if preview['snapshot_hash']!=expected_hash:raise ValueError('Prévia, códigos ou escopo alterados; atualize a conferência')
            snapshot=preview['snapshot'];meta=snapshot['metadata']
            if snapshot['blockers']:raise ValueError('; '.join(snapshot['blockers']))
            if snapshot['legacy_count'] and acknowledge_legacy is not True:
                raise ValueError('Há códigos legados sem escopo vinculado; confira-os e reconheça essa situação antes de vincular o novo sistema')
            versions=[]
            for change in snapshot['changes']:
                origin={**change['origin'],'review_reference':review_reference}
                code=self.save_tax_code(company_id,meta['kind'],change['code'],change['data'],'ativo',change['expected_version'],reason,
                                        _origin=origin,_in_transaction=True)
                versions.append(code)
                if not snapshot['scopes'][change['code']]:
                    scope={'system':meta['system'],'jurisdiction':meta['jurisdiction'],'import_id':snapshot['import_id'],
                           'review_reference':review_reference,'legacy_version':change['expected_version'],'actor':self.actor,'created_at':self._now()}
                    self.db.execute('INSERT INTO tax_catalog_scopes(company_id,kind,code,snapshot,snapshot_hash) VALUES(?,?,?,?,?)',(company_id,meta['kind'],change['code'],dump(scope),digest(scope)))
            manifest={'profile':'cadastro-aplicado-v1','preview_hash':expected_hash,'import_id':snapshot['import_id'],
                      'import_hash':snapshot['import_hash'],'raw_sha256':snapshot['raw_sha256'],'filename':snapshot['filename'],'parser':snapshot['parser'],
                      'metadata':meta,'application_from':application_from,'versions':versions,
                      'review_reference':review_reference,'acknowledge_legacy':acknowledge_legacy,'legacy_hash':snapshot['legacy_hash']}
            applied_id=self.db.execute('INSERT INTO tax_catalog_import_applications(company_id,import_id,request_key,request_hash,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                (company_id,import_id,request_key,request_hash,dump(manifest),digest(manifest),self.actor,reason,self._now())).lastrowid
            self._audit(company_id,'cadastro_importado_versionado',{'application_id':applied_id,'import_id':snapshot['import_id'],'manifest_hash':digest(manifest),'count':len(versions),'reason':reason})
        return self.catalog_application(company_id,applied_id)
