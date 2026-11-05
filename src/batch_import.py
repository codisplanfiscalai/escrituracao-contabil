"""Company-scoped batches, immutable received inputs and archive provenance."""
import hashlib
import json
import time
from pathlib import PurePosixPath

from .archive_reader import archive_members, safe_member, MAX_EXPANDED_BYTES, MAX_MEMBERS
from .accounting_store import dump, identifier
from .reconciliation import SPED_PROFILE

MAX_BATCH_SECONDS = 60

BATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS import_batches (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, actor TEXT NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, completed_at TEXT, UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS import_items (
 id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES import_batches(id),
 parent_id INTEGER REFERENCES import_items(id), position INTEGER NOT NULL,
 filename TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT, size INTEGER NOT NULL,
 original BLOB, file_id INTEGER REFERENCES files(id), status TEXT NOT NULL,
 details TEXT NOT NULL, UNIQUE(batch_id,parent_id,position));
CREATE INDEX IF NOT EXISTS import_items_file ON import_items(file_id);
"""


def inferred_kind(filename):
    suffix = PurePosixPath(filename.replace('\\', '/')).suffix.lower()
    return {'.xml': 'XML', '.txt': 'SPED', '.sped': 'SPED', '.zip': 'ZIP', '.7z': '7Z', '.rar': 'RAR'}.get(suffix)


class BatchImportMixin:
    def list_import_batches(self, company_id, period_id=None):
        self._company(company_id)
        if period_id is not None:
            period_id = self._owned('periods', company_id, identifier(period_id))['id']
        return [self.import_batch_result(company_id, row['id']) for row in self.db.execute(
            'SELECT id FROM import_batches WHERE company_id=? AND (? IS NULL OR period_id=?) ORDER BY id DESC',
            (company_id, period_id, period_id)).fetchall()]

    def import_batch_result(self, company_id, batch_id):
        self._company(company_id)
        row = self.db.execute('SELECT * FROM import_batches WHERE company_id=? AND id=?', (company_id, identifier(batch_id))).fetchone()
        if not row:
            raise ValueError('Lote de importação não pertence à empresa')
        result = dict(row)
        result['items'] = [{**dict(item), 'details': json.loads(item['details'])} for item in self.db.execute(
            'SELECT id,parent_id,position,filename,kind,sha256,size,file_id,status,details FROM import_items WHERE batch_id=? ORDER BY id', (row['id'],))]
        counts = {}
        for item in result['items']:
            counts[item['status']] = counts.get(item['status'], 0) + 1
        result['counts'] = counts
        return result

    def read_import_original(self, company_id, item_id):
        self._company(company_id)
        row = self.db.execute('SELECT i.* FROM import_items i JOIN import_batches b ON b.id=i.batch_id WHERE b.company_id=? AND i.id=?',
                              (company_id, identifier(item_id))).fetchone()
        if not row:
            raise ValueError('Origem não pertence à empresa')
        if row['original'] is not None:
            content = bytes(row['original'])
        elif row['file_id'] is not None:
            content = bytes(self._owned('files', company_id, row['file_id'])['original'])
        else:
            raise ValueError('Entrada não extraída; consulte o pacote original')
        return {'name': 'original-' + str(row['id']) + '.bin', 'content': content, 'media_type': 'application/octet-stream', 'sha256': row['sha256']}

    def import_batch(self, company_id, period_id, inputs, request_key, sped_profile=None):
        from .persistence import MAX_FILE_BYTES, _text
        self._company(company_id)
        period = self._owned('periods', company_id, period_id)
        request_key = _text(request_key, 'identificador do lote', 100)
        if sped_profile not in {None, SPED_PROFILE}:
            raise ValueError('Perfil SPED não suportado')
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_MEMBERS:
            raise ValueError('Envie de 1 a 500 arquivos por lote')
        deadline = time.monotonic() + MAX_BATCH_SECONDS
        manifest = []
        total = 0
        for item in inputs:
            if not isinstance(item, dict):
                raise ValueError('Cada entrada do lote deve ser um objeto')
            name = _text(item.get('filename'), 'nome do arquivo', 255)
            if '/' in name or '\\' in name or name in {'.', '..'}:
                raise ValueError('Envie nomes de arquivos sem caminho')
            content = item.get('content')
            if not isinstance(content, bytes) or len(content) > MAX_FILE_BYTES:
                raise ValueError('Cada arquivo ou pacote deve ter até 10 MiB')
            total += len(content)
            kind = item.get('kind') or inferred_kind(name) or 'DESCONHECIDO'
            if not isinstance(kind, str) or kind not in {'XML', 'SPED', 'ZIP', '7Z', 'RAR', 'DESCONHECIDO'}:
                raise ValueError('Tipo de entrada não reconhecido')
            manifest.append({'filename': name, 'kind': kind, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)})
        if total > MAX_EXPANDED_BYTES:
            raise ValueError('Lote excede 100 MiB de originais')
        fingerprint = hashlib.sha256(dump({'period': period['id'], 'inputs': manifest, 'profile': sped_profile}).encode()).hexdigest()
        # A single transaction serializes retry keys and all results. import_file uses
        # a savepoint while called here; a file failure cannot commit half a batch.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM import_batches WHERE company_id=? AND request_key=?', (company_id, request_key)).fetchone()
            if old:
                if old['request_hash'] != fingerprint:
                    raise ValueError('Identificador de lote já utilizado com outro conteúdo')
                result = self.import_batch_result(company_id, old['id'])
                result['duplicate'] = True
                return result
            batch_id = self.db.execute('INSERT INTO import_batches(company_id,period_id,request_key,request_hash,actor,status,created_at) VALUES(?,?,?,?,?,?,?)',
                                       (company_id, period['id'], request_key, fingerprint, self.actor, 'processando', self._now())).lastrowid
            expanded = sum(meta['size'] for meta in manifest if meta['kind'] not in {'ZIP', '7Z', 'RAR'})
            entries = len(inputs)
            def record(position, name, kind, content, parent=None, error=None):
                digest = hashlib.sha256(content).hexdigest() if content is not None else None
                ident = self.db.execute('INSERT INTO import_items(batch_id,parent_id,position,filename,kind,sha256,size,original,status,details) VALUES(?,?,?,?,?,?,?,?,?,?)',
                                        (batch_id, parent, position, name, kind, digest, len(content) if content is not None else 0, content,
                                         'rejeitado' if error else 'recebido', dump({'error': error} if error else {}))).lastrowid
                return ident
            def finish(ident, status, details, file_id=None):
                self.db.execute('UPDATE import_items SET status=?,details=?,file_id=? WHERE id=?', (status, dump(details), file_id, ident))
                # Top-level bytes remain immutable; member originals live in files.
                if file_id is not None:
                    self.db.execute('UPDATE import_items SET original=NULL WHERE id=? AND parent_id IS NOT NULL', (ident,))
            def leaf(ident, name, kind, content):
                if time.monotonic() >= deadline:
                    finish(ident, 'rejeitado', {'error': 'Tempo máximo do lote excedido; original preservado'})
                    return
                if kind not in {'XML', 'SPED'}:
                    finish(ident, 'rejeitado', {'error': 'Extensão não suportada ou pacote aninhado; original preservado'})
                    return
                try:
                    result = self.import_file(company_id, period['id'], PurePosixPath(name.replace('\\', '/')).name,
                                              content, kind, sped_profile=sped_profile if kind == 'SPED' else None, _in_batch=True)
                    finish(ident, result['status'], {**result['metadata'], 'duplicate': result['duplicate']}, result['id'])
                except ValueError as exc:
                    finish(ident, 'rejeitado', {'error': str(exc)})
            for position, (item, meta) in enumerate(zip(inputs, manifest), 1):
                name, kind, content = meta['filename'], meta['kind'], item['content']
                ident = record(position, name, kind, content)
                if kind not in {'ZIP', '7Z', 'RAR'}:
                    leaf(ident, name, kind, content)
                    continue
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ValueError('Tempo máximo do lote excedido; original preservado')
                    members = archive_members(content, kind, timeout=remaining)
                    if entries + len(members) > MAX_MEMBERS:
                        raise ValueError('Lote excede 500 entradas, incluindo pacotes')
                    entries += len(members)
                    if expanded + sum(len(m.get('content', b'')) for m in members) > MAX_EXPANDED_BYTES:
                        raise ValueError('Lote excede 100 MiB de expansão')
                    seen = set()
                    for index, member in enumerate(members, 1):
                        member_name = member['name']
                        error = member.get('error')
                        try:
                            safe_name = safe_member(member_name)
                            if safe_name in seen:
                                raise ValueError('Nome interno repetido; confira o pacote original')
                            seen.add(safe_name)
                        except ValueError as exc:
                            error = str(exc)
                        data = member.get('content')
                        child_kind = inferred_kind(member_name) or 'DESCONHECIDO'
                        child = record(index, member_name, child_kind, data, ident, error)
                        if error:
                            continue
                        expanded += len(data)
                        leaf(child, member_name, child_kind, data)
                    finish(ident, 'expandido', {'members': len(members), 'warning': 'Original preservado; consulte os resultados individuais'})
                except ValueError as exc:
                    finish(ident, 'rejeitado', {'error': str(exc)})
            self.db.execute("UPDATE import_batches SET status='concluido',completed_at=? WHERE id=?", (self._now(), batch_id))
            self._audit(company_id, 'lote_importado', {'batch_id': batch_id, 'inputs': len(inputs), 'expanded_bytes': expanded, 'request_hash': fingerprint})
            result = self.import_batch_result(company_id, batch_id)
            result['duplicate'] = False
            return result
