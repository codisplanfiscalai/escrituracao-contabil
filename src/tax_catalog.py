"""Company-owned reference codes. A registered code never determines tax treatment."""
import json
import re
from datetime import date
from .accounting_store import digest, dump, identifier

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS tax_catalog_versions (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 kind TEXT NOT NULL, code TEXT NOT NULL, version INTEGER NOT NULL, state TEXT NOT NULL,
 data TEXT NOT NULL, snapshot_hash TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(company_id,kind,code,version));
"""
CODE_FIELDS = {'cfop':'cfop','ncm':'ncm','service_code':'service','revenue_code':'revenue'}


def validate_catalog_code(kind, code, data):
    from .persistence import _text
    if kind not in set(CODE_FIELDS.values()):
        raise ValueError('Tipo da tabela inválido')
    code = _text(code,'Código',30)
    if kind == 'cfop' and not re.fullmatch(r'[1-7][0-9]{3}',code):
        raise ValueError('CFOP exige quatro dígitos; código não homologado')
    if kind == 'ncm' and not re.fullmatch(r'[0-9]{8}',code):
        raise ValueError('NCM exige oito dígitos; classificação não validada')
    if kind in {'service','revenue'} and not re.fullmatch(r'[A-Za-z0-9./-]{1,30}',code):
        raise ValueError('Código de serviço/receita tem formato não suportado')
    if not isinstance(data,dict) or set(data) != {'description','valid_from','valid_to','source_reference'}:
        raise ValueError('Informe descrição, vigência e origem da tabela')
    data = {key:_text(value,key,1000 if key in {'source_reference','description'} else 10,key!='valid_to') for key,value in data.items()}
    for key in ('valid_from','valid_to'):
        if data[key] and (not re.fullmatch(r'\d{4}-\d{2}-\d{2}',data[key]) or date.fromisoformat(data[key]).isoformat()!=data[key]):
            raise ValueError('Vigência deve usar AAAA-MM-DD')
    if data['valid_to'] and data['valid_from']>data['valid_to']:
        raise ValueError('Vigência invertida')
    return code,data


class TaxCatalogMixin:
    def _tax_catalog_row(self, row):
        result = dict(row)
        result['data'] = json.loads(result['data'])
        proof = {k:result[k] for k in ('kind','code','version','state','data')}
        if digest(proof) != result['snapshot_hash']:
            raise ValueError('Tabela de códigos alterada')
        return result

    def tax_catalog(self, company_id):
        self._company(identifier(company_id))
        return [self._tax_catalog_row(r) for r in self.db.execute('SELECT * FROM tax_catalog_versions WHERE company_id=? ORDER BY id DESC',(company_id,))]

    def tax_code_page(self, company_id, *, kind='', query='', code=None, offset=0):
        from .persistence import _text
        self._company(identifier(company_id));query=_text(query,'Busca do código',100,False)
        if kind and kind not in set(CODE_FIELDS.values()):raise ValueError('Tipo da tabela inválido')
        if isinstance(offset,str) and re.fullmatch(r'[0-9]{1,6}',offset):offset=int(offset)
        if type(offset)!=int or offset<0:raise ValueError('Página inválida')
        where=['c.company_id=?'];args=[company_id]
        if kind:where.append('c.kind=?');args.append(kind)
        if code is not None:
            if not kind:raise ValueError('Histórico exige tipo da tabela')
            where.append('c.code=?');args.append(_text(code,'Código',30))
        else:
            where.append('c.version=(SELECT MAX(v.version) FROM tax_catalog_versions v WHERE v.company_id=c.company_id AND v.kind=c.kind AND v.code=c.code)')
            if query:where.append('instr(lower(c.code),lower(?))>0');args.append(query)
        clause=' AND '.join(where)
        total=self.db.execute('SELECT COUNT(*) FROM tax_catalog_versions c WHERE '+clause,args).fetchone()[0]
        rows=self.db.execute('SELECT c.* FROM tax_catalog_versions c WHERE '+clause+' ORDER BY c.id DESC LIMIT 100 OFFSET ?',[*args,offset])
        return {'items':[self._tax_catalog_row(r) for r in rows],'total':total,'offset':offset,'limit':100,'kind':kind,'query':query,'code':code}

    def save_tax_code(self, company_id, kind, code, data, state, expected_version, reason, *, _origin=None, _in_transaction=False):
        from .persistence import _text
        from .company_profiles import expected_version as version_check
        if kind not in set(CODE_FIELDS.values()) or state not in {'ativo','inativo'}:
            raise ValueError('Tipo ou estado da tabela inválido')
        code,data = validate_catalog_code(kind,code,data)
        if _origin is not None:
            data['import_origin'] = _origin
        version_check(expected_version)
        reason = _text(reason,'Motivo',2000)
        with self._import_transaction(_in_transaction):
            if not _in_transaction:
                self.db.execute('BEGIN IMMEDIATE')
            self._company(identifier(company_id))
            old = self.db.execute('SELECT version FROM tax_catalog_versions WHERE company_id=? AND kind=? AND code=? ORDER BY version DESC LIMIT 1',(company_id,kind,code)).fetchone()
            if expected_version != (old['version'] if old else 0):
                raise ValueError('Código alterado; recarregue a versão')
            self._assert_tax_validity_open(company_id,data['valid_from'],data['valid_to'])
            proof = {'kind':kind,'code':code,'version':expected_version+1,'state':state,'data':data}
            code_id = self.db.execute('INSERT INTO tax_catalog_versions(company_id,kind,code,version,state,data,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (company_id,kind,code,expected_version+1,state,dump(data),digest(proof),self.actor,reason,self._now())).lastrowid
            self._audit(company_id,'codigo_tributario_versionado',{'id':code_id,'kind':kind,'code':code,'version':expected_version+1,'reason':reason})
        return self._tax_catalog_row(self.db.execute('SELECT * FROM tax_catalog_versions WHERE id=?',(code_id,)).fetchone())

    def resolve_tax_code(self, company_id, kind, code, day):
        self._company(identifier(company_id))
        rows = (self._tax_catalog_row(r) for r in self.db.execute('SELECT * FROM tax_catalog_versions WHERE company_id=? AND kind=? AND code=? ORDER BY version DESC',(company_id,kind,code)))
        selected = next((r for r in rows if r['data']['valid_from']<=day),None)
        if not selected or selected['state']!='ativo' or (selected['data']['valid_to'] and selected['data']['valid_to']<day):
            raise ValueError(f'Código {kind} {code} sem versão ativa e vigente nesta empresa/data')
        return selected
