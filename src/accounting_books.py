"""Livros locais de movimentos e exportação preservada; sem homologação externa."""
import csv
import hashlib
import io
import json
from decimal import Decimal, localcontext

from .accounting_store import digest, dump, identifier
from .evidence_export import validate_historical_batch
from .manual_accounting import validate_sealed_journal

BOOKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounting_book_exports (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), plan_id INTEGER NOT NULL REFERENCES plans(id),
 book_hash TEXT NOT NULL, manifest_sha256 TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,period_id,plan_id,book_hash));
CREATE TABLE IF NOT EXISTS accounting_book_artifacts (
 export_id INTEGER NOT NULL REFERENCES accounting_book_exports(id), name TEXT NOT NULL,
 sha256 TEXT NOT NULL, content BLOB NOT NULL, PRIMARY KEY(export_id,name));
"""
PROFILE = 'accounting-movement-books-v1'
MEDIA_TYPES = {'books.json':'application/json; charset=utf-8', 'manifest.json':'application/json; charset=utf-8',
               'diario.csv':'text/csv; charset=utf-8', 'razao.csv':'text/csv; charset=utf-8',
               'balancete-movimentos.csv':'text/csv; charset=utf-8'}


def _csv(rows, columns, text_columns):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator='\r\n', extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        # Preserve leading zeros and prevent formulas, including leading whitespace.
        writer.writerow({key: "'"+str(value) if key in text_columns else value for key,value in row.items() if key in columns})
    return output.getvalue().encode('utf-8-sig')


class AccountingBooksMixin:
    def accounting_books(self, company_id, period_id, plan_id):
        # One SQLite read transaction avoids mixing revisions closed concurrently.
        with self.db:
            self.db.execute('BEGIN')
            return self._accounting_books(company_id, period_id, plan_id)

    def _accounting_books(self, company_id, period_id, plan_id):
        company = self._company(company_id)
        period = self._owned('periods', company_id, identifier(period_id))
        plan = self._owned('plans', company_id, identifier(plan_id))
        entries, sources = [], []
        for row in self.db.execute("SELECT id FROM accounting_batches WHERE company_id=? AND period_id=? AND plan_id=? AND status='fechado' ORDER BY id", (company_id,period['id'],plan['id'])).fetchall():
            batch = self._batch(company_id,row['id'])
            snapshot = validate_historical_batch(batch)
            sources.append({'kind':'documental','id':batch['id'],'version':batch['version'],'snapshot_hash':batch['snapshot_hash']})
            for line in snapshot['entries']:
                review = next(review for review in snapshot['documents'] if review['document_id']==line['document_id'])
                entries.append(self._book_line('documental',batch['id'],batch['version'],batch['snapshot_hash'],line,
                                               review['snapshot']['business_key'],line['document_id'],line['observation_id']))
        for revision in self.list_manual_journals(company_id,period['id']):
            if revision['plan_id'] != plan['id'] or revision['status'] != 'fechado':
                continue
            snapshot = validate_sealed_journal(revision)
            sources.append({'kind':'manual','id':revision['journal_id'],'version':revision['version'],'snapshot_hash':revision['snapshot_hash'],
                            'reversal_of':revision['reversal_of']})
            for line in snapshot['entries']:
                entries.append(self._book_line('manual',revision['journal_id'],revision['version'],revision['snapshot_hash'],line,snapshot['reference']))
        entries.sort(key=lambda line:(line['date'],line['source_kind'],line['source_id'],line['line']))
        ledger, accounts = [], {}
        with localcontext() as context:
            context.prec = 40
            for number,line in enumerate(entries,1):
                line['sequence'] = number
                account = accounts.setdefault(line['account_id'], {'account_id':line['account_id'],'account_code':line['account_code'],
                    'account_description':line['account_description'],'debit':Decimal(0),'credit':Decimal(0)})
                side = 'debit' if line['side']=='D' else 'credit'
                account[side] += Decimal(line['amount'])
                ledger.append({**line,'movement_balance':format(account['debit']-account['credit'],'.2f')})
            trial = [{**row,'debit':format(row['debit'],'.2f'),'credit':format(row['credit'],'.2f'),
                      'movement_balance':format(row['debit']-row['credit'],'.2f')} for row in sorted(accounts.values(),key=lambda row:(row['account_code'],row['account_id']))]
            totals = {key:format(sum((row[key] for row in accounts.values()),Decimal(0)),'.2f') for key in ('debit','credit')}
        if totals['debit'] != totals['credit']:
            raise ValueError('Livros com movimentos desequilibrados')
        result = {'profile':PROFILE,'company':company,'period':period,'plan':plan,'sources':sources,
                  'diary':entries,'ledger':ledger,'trial_balance_movements':trial,'totals':totals,
                  'opening_balances_included':False,'balance_convention':'debit_minus_credit_movements_only',
                  'closed_entries_only':True,'prosoft_validated':False,'pva_validated':False,'externally_posted':False}
        return {**result,'book_hash':digest(result)}

    @staticmethod
    def _book_line(kind, source_id, version, snapshot_hash, line, reference, document_id=None, observation_id=None):
        return {'source_kind':kind,'source_id':source_id,'source_version':version,'snapshot_hash':snapshot_hash,
                'line':line['line'],'date':line['date'],'group':line['group'],'side':line['side'],'amount':line['amount'],
                'memo':line['memo'],'account_id':line['account']['id'],'account_code':line['account']['code'],
                'account_description':line['account']['description'],'reference':reference,
                'document_id':document_id,'observation_id':observation_id}

    def create_book_export(self, company_id, period_id, plan_id, expected_hash, reason):
        from .persistence import _text
        reason = _text(reason,'motivo da exportação dos livros',2000)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            books = self._accounting_books(company_id,period_id,plan_id)
            if books['book_hash'] != expected_hash:
                raise ValueError('Livros alterados; confira nova prévia antes de exportar')
            if not books['sources']:
                raise ValueError('Nenhum lançamento fechado para exportar')
            existing = self.db.execute('SELECT id FROM accounting_book_exports WHERE company_id=? AND period_id=? AND plan_id=? AND book_hash=?',
                                       (company_id,books['period']['id'],books['plan']['id'],expected_hash)).fetchone()
            if existing:
                result = self._book_export(company_id,existing['id'])
                self._audit(company_id,'livros_contabeis_reexportados',{'export_id':existing['id'],'book_hash':expected_hash,'reason':reason})
                return {**result,'duplicate':True}
            columns = tuple(books['diary'][0])
            text_columns = ('source_kind','snapshot_hash','group','memo','account_code','account_description','reference')
            artifacts = {'books.json':(dump(books)+'\n').encode(),
                         'diario.csv':_csv(books['diary'],columns,text_columns),
                         'razao.csv':_csv(sorted(books['ledger'],key=lambda row:(row['account_code'],row['account_id'],row['sequence'])),columns+('movement_balance',),text_columns),
                         'balancete-movimentos.csv':_csv(books['trial_balance_movements'],('account_id','account_code','account_description','debit','credit','movement_balance'),('account_code','account_description'))}
            manifest = {'profile':PROFILE,'book_hash':expected_hash,'company_id':books['company']['id'],'period_id':books['period']['id'],
                        'plan_id':books['plan']['id'],'prosoft_validated':False,'pva_validated':False,'opening_balances_included':False,
                        'csv':{'encoding':'utf-8-sig','delimiter':',','line_ending':'CRLF','apostrophe_prefixed_columns':text_columns,
                               'text_recovery':'Remover exatamente o primeiro apóstrofo das colunas textuais; books.json preserva os originais.'},
                        'artifacts':[{'name':name,'sha256':hashlib.sha256(content).hexdigest(),'size':len(content)} for name,content in artifacts.items()]}
            artifacts['manifest.json'] = (dump(manifest)+'\n').encode()
            cur = self.db.execute('INSERT INTO accounting_book_exports(company_id,period_id,plan_id,book_hash,manifest_sha256,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?)',
                                  (company_id,books['period']['id'],books['plan']['id'],expected_hash,hashlib.sha256(artifacts['manifest.json']).hexdigest(),self.actor,reason,self._now()))
            export_id = cur.lastrowid
            for name,content in artifacts.items():
                self.db.execute('INSERT INTO accounting_book_artifacts VALUES(?,?,?,?)',(export_id,name,hashlib.sha256(content).hexdigest(),content))
            self._audit(company_id,'livros_contabeis_exportados',{'export_id':export_id,'book_hash':expected_hash,'reason':reason})
            return {**self._book_export(company_id,export_id),'duplicate':False}

    def _book_export(self, company_id, export_id):
        self._company(company_id)
        row = self.db.execute('SELECT * FROM accounting_book_exports WHERE id=? AND company_id=?',(identifier(export_id),company_id)).fetchone()
        if not row:
            raise ValueError('Exportação não pertence à empresa ou não existe')
        files = {item['name']:dict(item) for item in self.db.execute('SELECT * FROM accounting_book_artifacts WHERE export_id=? ORDER BY name',(export_id,))}
        if set(files) != set(MEDIA_TYPES):
            raise ValueError('Conjunto de arquivos contábeis incompleto')
        for item in files.values():
            if hashlib.sha256(bytes(item['content'])).hexdigest() != item['sha256']:
                raise ValueError('Hash do arquivo contábil preservado divergente')
        if files['manifest.json']['sha256'] != row['manifest_sha256']:
            raise ValueError('Hash do manifesto contábil divergente')
        try:
            manifest = json.loads(files['manifest.json']['content'])
            books = json.loads(files['books.json']['content'])
            if manifest['profile'] != PROFILE or any(manifest[key] != row[key] for key in ('book_hash','company_id','period_id','plan_id')):
                raise ValueError('Contexto do manifesto contábil divergente')
            expected = {name:{'name':name,'sha256':item['sha256'],'size':len(item['content'])} for name,item in files.items() if name != 'manifest.json'}
            if sorted(manifest['artifacts'],key=lambda item:item['name']) != sorted(expected.values(),key=lambda item:item['name']):
                raise ValueError('Manifesto não corresponde aos arquivos contábeis')
            if books['book_hash'] != row['book_hash'] or digest({key:value for key,value in books.items() if key != 'book_hash'}) != row['book_hash']:
                raise ValueError('Hash dos livros contábeis divergente')
        except (KeyError,TypeError,json.JSONDecodeError,UnicodeDecodeError) as exc:
            raise ValueError('Arquivos contábeis preservados inconsistentes') from exc
        artifacts = [{'name':name,'sha256':item['sha256'],'size':len(item['content'])} for name,item in files.items()]
        return {**dict(row),'artifacts':artifacts}

    def list_book_exports(self, company_id):
        self._company(company_id)
        return [self._book_export(company_id,row['id']) for row in self.db.execute('SELECT id FROM accounting_book_exports WHERE company_id=? ORDER BY id DESC',(company_id,)).fetchall()]

    def read_book_artifact(self, company_id, export_id, name):
        self._book_export(company_id,export_id)
        if not isinstance(name,str) or name not in MEDIA_TYPES:
            raise ValueError('Arquivo contábil não disponível')
        row = self.db.execute('SELECT * FROM accounting_book_artifacts WHERE export_id=? AND name=?',(export_id,name)).fetchone()
        content = bytes(row['content'])
        if hashlib.sha256(content).hexdigest() != row['sha256']:
            raise ValueError('Hash do arquivo contábil preservado divergente')
        return {'name':name,'media_type':MEDIA_TYPES[name],'content':content}
