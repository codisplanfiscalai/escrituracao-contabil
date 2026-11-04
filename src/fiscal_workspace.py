"""Company-scoped participants and operator-owned persistent working tabs."""
import json
import re
from .accounting_store import dump, identifier

WORKSPACE_SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 identifier_kind TEXT NOT NULL, identifier_value TEXT NOT NULL, name TEXT NOT NULL,
 roles TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
 UNIQUE(company_id,identifier_kind,identifier_value));
CREATE TABLE IF NOT EXISTS participant_observations (
 id INTEGER PRIMARY KEY, participant_id INTEGER NOT NULL REFERENCES participants(id),
 name TEXT NOT NULL, role TEXT NOT NULL, source TEXT NOT NULL, state TEXT NOT NULL,
 actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(participant_id,name,role,source));
CREATE TABLE IF NOT EXISTS fiscal_workspaces (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), actor TEXT NOT NULL,
 request_key TEXT NOT NULL, title TEXT NOT NULL, data TEXT NOT NULL,
 version INTEGER NOT NULL, closed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
 UNIQUE(company_id,actor,request_key));
"""


class FiscalWorkspaceMixin:
    def _record_participant(self, company_id, identity, name, role, source):
        from .persistence import _text
        identity = re.sub(r'[.\-/\s]', '', _text(identity, 'identificador', 100))
        if not re.fullmatch(r'[0-9]{11}|[0-9]{14}', identity):
            raise ValueError('Participante exige CPF/CNPJ; não gerar identificador fictício')
        kind = 'CPF' if len(identity) == 11 else 'CNPJ'
        name = _text(name, 'nome', 500, False)
        if role not in {'cliente', 'fornecedor', 'prestador', 'tomador', 'emitente', 'destinatario', 'participante'}:
            raise ValueError('Papel do participante não reconhecido')
        row = self.db.execute('SELECT * FROM participants WHERE company_id=? AND identifier_kind=? AND identifier_value=?', (company_id, kind, identity)).fetchone()
        if row is None:
            cur = self.db.execute('INSERT INTO participants(company_id,identifier_kind,identifier_value,name,roles) VALUES(?,?,?,?,?)', (company_id, kind, identity, name, dump([role])))
            ident = cur.lastrowid
            state = 'coincidente' if name else 'pendente'
            self._audit(company_id, 'terceiro_cadastrado', {'participant_id': ident, 'source': source})
        else:
            ident = row['id']
            roles = set(json.loads(row['roles']))
            if role not in roles:
                roles.add(role)
                self.db.execute('UPDATE participants SET roles=?,version=version+1 WHERE id=?', (dump(sorted(roles)), ident))
            state = 'coincidente' if name and name == row['name'] else 'pendente'
        observed = self.db.execute('INSERT OR IGNORE INTO participant_observations(participant_id,name,role,source,state,actor,created_at) VALUES(?,?,?,?,?,?,?)', (ident, name, role, source, state, self.actor, self._now()))
        if row is not None and observed.rowcount:
            self.db.execute('UPDATE participants SET version=version+1 WHERE id=?', (ident,))
        return ident

    def observe_document_participants(self, company, file_id, payload):
        for field in ('issuer', 'buyer'):
            identity = payload.get(field)
            if not identity or identity == company['cnpj']:
                continue
            role = 'fornecedor' if field == 'issuer' and payload.get('buyer') == company['cnpj'] else 'cliente' if field == 'buyer' and payload.get('issuer') == company['cnpj'] else 'emitente' if field == 'issuer' else 'destinatario'
            self._record_participant(company['id'], identity, payload.get(field + '_name', ''), role, f'arquivo:{file_id}/{field}')

    def list_participants(self, company_id):
        self._company(company_id)
        rows = []
        for row in self.db.execute('SELECT * FROM participants WHERE company_id=? ORDER BY name,id', (company_id,)).fetchall():
            value = dict(row)
            value['roles'] = json.loads(value['roles'])
            value['observations'] = [dict(r) for r in self.db.execute('SELECT * FROM participant_observations WHERE participant_id=? ORDER BY id DESC', (row['id'],))]
            value['pending'] = any(o['state'] == 'pendente' for o in value['observations'])
            rows.append(value)
        return rows

    def save_participant(self, company_id, identity, name, role, reason):
        from .persistence import _text
        self._company(company_id)
        reason = _text(reason, 'motivo', 2000)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            ident = self._record_participant(company_id, identity, name, role, 'manual')
            self._audit(company_id, 'terceiro_informado', {'participant_id': ident, 'reason': reason})
        return next(p for p in self.list_participants(company_id) if p['id'] == ident)

    def review_participant(self, company_id, participant_id, version, observation_id, reason):
        from .persistence import _text
        reason = _text(reason, 'motivo da revisão do terceiro', 2000)
        self._company(company_id)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM participants WHERE company_id=? AND id=?', (company_id, identifier(participant_id))).fetchone()
            observation = self.db.execute('SELECT * FROM participant_observations WHERE participant_id=? AND id=?', (identifier(participant_id), identifier(observation_id))).fetchone()
            if not row or row['version'] != version or not observation or not observation['name']:
                raise ValueError('Terceiro alterado, origem sem nome ou fora da empresa; confira novamente')
            self.db.execute('UPDATE participants SET name=?,version=version+1 WHERE id=?', (observation['name'], row['id']))
            self.db.execute("UPDATE participant_observations SET state='conferido' WHERE participant_id=?", (row['id'],))
            self._audit(company_id, 'terceiro_revisado', {'participant_id': row['id'], 'before': dict(row), 'observation_id': observation['id'], 'reason': reason})
        return next(p for p in self.list_participants(company_id) if p['id'] == row['id'])

    def list_fiscal_workspaces(self, company_id, period_id):
        period = self._owned('periods', company_id, period_id)
        return [{**dict(r), 'data': json.loads(r['data'])} for r in self.db.execute('SELECT * FROM fiscal_workspaces WHERE company_id=? AND period_id=? AND actor=? AND closed=0 ORDER BY id', (company_id, period['id'], self.actor))]

    def save_fiscal_workspace(self, company_id, period_id, title, data, request_key, workspace_id=None, version=0, closed=False):
        from .persistence import _text
        period = self._owned('periods', company_id, period_id)
        title = _text(title, 'título da guia', 100)
        request_key = _text(request_key, 'tentativa da guia', 100)
        if not isinstance(data, dict) or len(dump(data).encode()) > 100000:
            raise ValueError('Rascunho deve ser objeto de até 100 KB')
        if type(version) is not int or version < 0 or type(closed) is not bool:
            raise ValueError('Versão/estado da guia inválidos')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if workspace_id:
                row = self.db.execute('SELECT * FROM fiscal_workspaces WHERE id=? AND company_id=? AND period_id=? AND actor=? AND closed=0', (identifier(workspace_id), company_id, period['id'], self.actor)).fetchone()
                if not row or row['version'] != version:
                    raise ValueError('Guia alterada, encerrada ou de outro operador; recarregue')
                self.db.execute('UPDATE fiscal_workspaces SET title=?,data=?,version=version+1,closed=?,updated_at=? WHERE id=?', (title, dump(data), int(closed), self._now(), row['id']))
                ident = row['id']
            else:
                row = self.db.execute('SELECT * FROM fiscal_workspaces WHERE company_id=? AND actor=? AND request_key=?', (company_id, self.actor, request_key)).fetchone()
                if row:
                    if row['period_id'] != period['id'] or row['data'] != dump(data) or row['title'] != title:
                        raise ValueError('Tentativa da guia já utilizada')
                    return {**dict(row), 'data': json.loads(row['data'])}
                cur = self.db.execute('INSERT INTO fiscal_workspaces(company_id,period_id,actor,request_key,title,data,version,closed,updated_at) VALUES(?,?,?,?,?,?,1,0,?)', (company_id, period['id'], self.actor, request_key, title, dump(data), self._now()))
                ident = cur.lastrowid
            self._audit(company_id, 'guia_fiscal_encerrada' if closed else 'guia_fiscal_salva', {'workspace_id': ident})
            result = dict(self.db.execute('SELECT * FROM fiscal_workspaces WHERE id=?', (ident,)).fetchone())
            result['data'] = json.loads(result['data'])
            return result
