"""Versioned fiscal working records. Originals and sealed accounting stay separate."""
from datetime import date
import json
import re

from .accounting_store import digest, dump, identifier

FISCAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS fiscal_entries (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 document_id INTEGER REFERENCES documents(id), entry_key TEXT NOT NULL,
 active_version INTEGER NOT NULL DEFAULT 0, UNIQUE(company_id,entry_key));
CREATE TABLE IF NOT EXISTS fiscal_revisions (
 id INTEGER PRIMARY KEY, entry_id INTEGER NOT NULL REFERENCES fiscal_entries(id),
 company_id INTEGER NOT NULL REFERENCES companies(id), version INTEGER NOT NULL,
 period_id INTEGER NOT NULL REFERENCES periods(id), state TEXT NOT NULL,
 data TEXT NOT NULL, source_snapshot TEXT NOT NULL, source_hash TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL, warnings TEXT NOT NULL, reason TEXT NOT NULL,
 actor TEXT NOT NULL, created_at TEXT NOT NULL, review_actor TEXT, review_reason TEXT,
 reviewed_at TEXT, request_key TEXT NOT NULL, request_hash TEXT NOT NULL,
 UNIQUE(entry_id,version), UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS fiscal_period_states (
 company_id INTEGER NOT NULL REFERENCES companies(id), competence TEXT NOT NULL,
 state TEXT NOT NULL, version INTEGER NOT NULL, reference TEXT NOT NULL,
 PRIMARY KEY(company_id,competence));
CREATE TABLE IF NOT EXISTS fiscal_period_history (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 competence TEXT NOT NULL, version INTEGER NOT NULL, state TEXT NOT NULL,
 reference TEXT NOT NULL, reason TEXT NOT NULL, actor TEXT NOT NULL,
 created_at TEXT NOT NULL, snapshot TEXT NOT NULL);
"""


def normalized(data, competence):
    from .persistence import _text, _money
    fields = {'model', 'number', 'series', 'key', 'issued_date', 'entry_date',
              'posting_date', 'operation', 'issuer', 'buyer', 'total', 'notes',
              'participant_id', 'service_code', 'municipality', 'iss_base', 'iss_amount'}
    if not isinstance(data, dict) or set(data) - fields:
        raise ValueError('Ficha fiscal contém campos não reconhecidos')
    value = {key: _text(data.get(key, ''), key, 2000 if key == 'notes' else 100, False) for key in fields}
    if value['model'] not in {'55', '65', 'SERVICO'}:
        raise ValueError('Este perfil suporta 55, 65 e ficha manual de serviço')
    if value['operation'] not in {'entrada', 'saida', 'servico_tomado', 'servico_prestado'}:
        raise ValueError('Informe entrada ou saída na perspectiva da empresa')
    service = value['model'] == 'SERVICO'
    if service != value['operation'].startswith('servico_'):
        raise ValueError('Operação de serviço exige ficha de serviço; entrada/saída exige 55/65')
    for key, size in ([] if service else [('number', 9), ('series', 3)]):
        if not re.fullmatch(r'[0-9]{1,' + str(size) + '}', value[key]):
            raise ValueError('Número/série devem conter dígitos no tamanho do documento')
    if not value['number'] or (not service and int(value['number']) == 0):
        raise ValueError('Número do documento deve ser positivo')
    for key in ('issued_date', 'entry_date', 'posting_date'):
        if key == 'entry_date' and not value[key]:
            continue
        try:
            if date.fromisoformat(value[key]).isoformat() != value[key]:
                raise ValueError()
        except ValueError:
            raise ValueError(f'Data inválida: {key}') from None
    if value['posting_date'][:7] != competence:
        raise ValueError('Data de escrituração deve pertencer à competência selecionada')
    for key in ('issuer', 'buyer'):
        if value[key] and not re.fullmatch(r'[0-9]{11}|[0-9]{14}', value[key]):
            raise ValueError('CPF/CNPJ informado deve conter 11 ou 14 dígitos')
    value['total'] = _money(value['total'], 'Valor do documento')
    for field in ('iss_base', 'iss_amount'):
        if value[field]:
            if not service:
                raise ValueError('Campos ISS são exclusivos da ficha manual de serviço')
            value[field] = _money(value[field], field)
    if value['municipality'] and not re.fullmatch(r'[0-9]{7}', value['municipality']):
        raise ValueError('Código de município deve conter sete dígitos')
    key = value['key']
    if service and key:
        raise ValueError('Chave 44 dígitos é de 55/65; use número e observações na ficha manual de serviço')
    if key:
        if not re.fullmatch(r'[0-9]{44}', key):
            raise ValueError('Chave deve conter 44 dígitos')
        dv = 11 - sum(int(d) * (2 + i % 8) for i, d in enumerate(reversed(key[:43]))) % 11
        dv = 0 if dv >= 10 else dv
        if int(key[-1]) != dv or key[20:22] != value['model'] or key[22:25] != value['series'].zfill(3) or key[25:34] != value['number'].zfill(9) or key[2:6] != value['issued_date'][2:4] + value['issued_date'][5:7] or (value['issuer'] and key[6:20] != value['issuer']):
            raise ValueError('Chave inconsistente com identificação, emissão ou dígito verificador')
    warnings = ['Serviço manual: ISS somente informado, sem cálculo, validação municipal ou importação NFS-e.'] if service else []
    if value['issued_date'][:7] != competence:
        warnings.append('Emissão fora da competência: conferir entrada/saída e enquadramento; não inferir situação fiscal automaticamente.')
    if not value['entry_date']:
        warnings.append('Data de entrada/saída não informada; nenhum valor presumido.')
    elif value['entry_date'][:7] != competence:
        warnings.append('Entrada/saída fora da competência; conferir escrituração extemporânea.')
    if value['entry_date'] and value['entry_date'] < value['issued_date']:
        warnings.append('Entrada/saída anterior à emissão; conferir as datas.')
    if not key:
        warnings.append('Sem chave de acesso: identidade e possível duplicidade exigem conferência.')
    if not value['issuer'] or not value['buyer']:
        warnings.append('Participante não identificado integralmente; conferir condições do modelo e operação.')
    return value, warnings


class FiscalLedgerMixin:
    def fiscal_document_state(self, company_id, document_id):
        row = self.db.execute('SELECT r.* FROM fiscal_entries e JOIN fiscal_revisions r ON r.entry_id=e.id AND r.version=e.active_version WHERE e.company_id=? AND e.document_id=?', (company_id, document_id)).fetchone()
        return self._fiscal_revision(row) if row else None

    def _fiscal_source(self, company_id, document_id):
        if document_id is None:
            return {}, digest({})
        return self._base_source_snapshot(company_id, document_id)

    def fiscal_seed(self, company_id, period_id, document_id):
        company = self._company(company_id)
        period = self._owned('periods', company_id, period_id)
        doc = self._owned('documents', company_id, document_id)
        payload = json.loads(doc['payload'])
        source, fingerprint = self._fiscal_source(company_id, doc['id'])
        return {'document_id': doc['id'], 'source_hash': fingerprint, 'source_snapshot': source,
                'data': {'model': payload['model'], 'number': payload['number'], 'series': payload['series'],
                         'key': payload.get('key', ''), 'issued_date': (payload.get('issued_at') or payload.get('issued_date', ''))[:10],
                         'entry_date': payload.get('entry_date', ''), 'posting_date': '',
                         'operation': payload.get('operation') or ('saida' if company['cnpj'] and company['cnpj'] == payload.get('issuer') else 'entrada' if company['cnpj'] and company['cnpj'] == payload.get('buyer') else ''),
                         'issuer': payload.get('issuer', ''), 'buyer': payload.get('buyer', ''),
                         'total': payload['total'], 'notes': ''}, 'competence': period['processing_competence']}

    def _fiscal_entry(self, company_id, entry_id):
        self._company(company_id)
        row = self.db.execute('SELECT * FROM fiscal_entries WHERE company_id=? AND id=?', (company_id, identifier(entry_id))).fetchone()
        if not row:
            raise ValueError('Ficha fiscal não pertence à empresa')
        return dict(row)

    def _fiscal_revision(self, row):
        result = dict(row)
        for key in ('data', 'source_snapshot', 'warnings'):
            result[key] = json.loads(result[key])
        return result

    def list_fiscal_entries(self, company_id, period_id=None):
        self._company(company_id)
        period = self._owned('periods', company_id, period_id) if period_id else None
        result = []
        for row in self.db.execute('SELECT * FROM fiscal_entries WHERE company_id=? ORDER BY id DESC', (company_id,)).fetchall():
            entry = dict(row)
            history = [self._fiscal_revision(r) for r in self.db.execute('SELECT * FROM fiscal_revisions WHERE entry_id=? ORDER BY version DESC', (row['id'],))]
            if period and not any(r['period_id'] == period['id'] for r in history):
                continue
            entry['history'] = history
            entry['current'] = next((r for r in history if r['version'] == row['active_version']), None)
            entry['proposals'] = [r for r in history if r['state'] == 'retificacao_pendente']
            _, fingerprint = self._fiscal_source(company_id, row['document_id'])
            entry['source_hash'] = fingerprint
            entry['source_current'] = bool(entry['current'] and entry['current']['source_hash'] == fingerprint)
            result.append(entry)
        return result

    def _fiscal_guard(self, company_id, period_id, document_id=None):
        period = self._owned('periods', company_id, period_id)
        state = self.db.execute('SELECT state FROM fiscal_period_states WHERE company_id=? AND competence=?', (company_id, period['processing_competence'])).fetchone()
        reasons = []
        if state and state[0] != 'aberto':
            reasons.append('Período fiscal ' + state[0])
        rows = self.db.execute("SELECT b.id FROM accounting_batches b JOIN periods p ON p.id=b.period_id WHERE b.company_id=? AND b.status='fechado' AND (p.processing_competence=? OR b.id IN (SELECT batch_id FROM accounting_batch_documents WHERE document_id=?))", (company_id, period['processing_competence'], document_id)).fetchall()
        if rows:
            reasons.append('Lotes contábeis fechados preservados: ' + ', '.join(str(r[0]) for r in rows))
        return reasons

    def save_fiscal_entry(self, company_id, period_id, data, reason, request_key, expected_version=0,
                          entry_id=None, document_id=None, expected_source_hash=None, as_proposal=False):
        from .persistence import _text
        self._company(company_id)
        reason = _text(reason, 'motivo da escrituração', 2000)
        request_key = _text(request_key, 'identificador da tentativa', 100)
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 0:
            raise ValueError('Versão esperada inválida')
        if not isinstance(as_proposal, bool):
            raise ValueError('Confirmação de proposta inválida')
        period = self._owned('periods', company_id, period_id)
        value, warnings = normalized(data, period['processing_competence'])
        request_hash = digest({'period': period['id'], 'data': value, 'reason': reason, 'version': expected_version,
                               'entry': str(entry_id or ''), 'document': str(document_id or ''), 'source': expected_source_hash, 'proposal': as_proposal})
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM fiscal_revisions WHERE company_id=? AND request_key=?', (company_id, request_key)).fetchone()
            if old:
                if old['request_hash'] != request_hash:
                    raise ValueError('Tentativa já utilizada com conteúdo diferente')
                self._audit(company_id, 'ficha_fiscal_tentativa_repetida', {'revision_id': old['id']})
                return self._fiscal_revision(old)
            entry = self._fiscal_entry(company_id, entry_id) if entry_id else None
            attaching = False
            if entry:
                if expected_version != entry['active_version']:
                    raise ValueError('Ficha alterada por outra operação; recarregue a versão vigente')
                if document_id is not None and identifier(document_id) != entry['document_id']:
                    old_data = self.db.execute('SELECT data FROM fiscal_revisions WHERE entry_id=? AND version=?', (entry['id'], entry['active_version'])).fetchone()
                    source_document = self._owned('documents', company_id, document_id)
                    if entry['document_id'] is not None or not old_data or not value['key'] or json.loads(old_data[0])['key'] != value['key'] or source_document['business_key'] != value['key']:
                        raise ValueError('Associação exige ficha manual e documento com a mesma chave; outras origens exigem conferência')
                    attaching = True
                else:
                    document_id = entry['document_id']
            elif expected_version:
                raise ValueError('Nova ficha deve usar versão esperada zero')
            if document_id is not None:
                document_id = self._owned('documents', company_id, document_id)['id']
                collision = self.db.execute('SELECT id FROM fiscal_entries WHERE company_id=? AND document_id=?', (company_id, document_id)).fetchone()
                if collision and (not entry or collision['id'] != entry['id']):
                    raise ValueError('Documento já possui ficha fiscal; edite a ficha existente')
            if value['key']:
                canonical = self.db.execute('SELECT id FROM documents WHERE company_id=? AND business_key=?', (company_id, value['key'])).fetchone()
                if canonical and canonical['id'] != document_id:
                    raise ValueError('Chave já importada: prepare a ficha pelo documento existente')
                for candidate in self.list_fiscal_entries(company_id):
                    latest = candidate['current'] or (candidate['history'][0] if candidate['history'] else None)
                    if latest and candidate['id'] != (entry or {}).get('id') and latest['data']['key'] == value['key']:
                        raise ValueError('Chave já registrada em outra ficha; confira antes de duplicar')
            source, fingerprint = self._fiscal_source(company_id, document_id)
            if value['participant_id']:
                party = next((p for p in self.list_participants(company_id) if str(p['id']) == value['participant_id']), None)
                if not party:
                    raise ValueError('Terceiro não pertence à empresa')
                source = {**source, 'participant': party}
                if party['pending']:
                    warnings.append('Terceiro possui divergências cadastrais para conferência.')
            if not value['key']:
                for candidate in self.list_fiscal_entries(company_id):
                    item = candidate['current']
                    if item and candidate['id'] != (entry or {}).get('id') and all(item['data'][k] == value[k] for k in ('model','number','series','issuer','issued_date')):
                        warnings.append(f'Possível coincidência com ficha #{candidate["id"]}; confira antes de revisar.')
            if document_id is not None and expected_source_hash != fingerprint:
                raise ValueError('Fontes alteradas; recarregue a ficha antes de salvar')
            guards = self._fiscal_guard(company_id, period['id'], document_id)
            if entry and entry['active_version']:
                old_period = self.db.execute('SELECT period_id FROM fiscal_revisions WHERE entry_id=? AND version=?', (entry['id'], entry['active_version'])).fetchone()[0]
                guards += self._fiscal_guard(company_id, old_period, document_id)
            if guards and not as_proposal:
                raise ValueError('; '.join(guards) + '. Registre proposta de retificação explícita; vigente não será alterado.')
            if guards and attaching:
                raise ValueError('Associação de origem em período protegido exige fluxo de retificação; vínculo vigente preservado')
            if as_proposal and not guards:
                raise ValueError('Período aberto: salve nova versão normal para revisão')
            if document_id is not None:
                warnings.append('Ficha derivada de documento importado; original preservado e alterações precisam de revisão.')
            if not entry:
                key = f'document:{document_id}' if document_id is not None else 'manual:' + request_key
                cur = self.db.execute('INSERT INTO fiscal_entries(company_id,document_id,entry_key) VALUES(?,?,?)', (company_id, document_id, key))
                entry = {'id': cur.lastrowid}
            version = self.db.execute('SELECT COALESCE(MAX(version),0)+1 FROM fiscal_revisions WHERE entry_id=?', (entry['id'],)).fetchone()[0]
            snapshot_hash = digest({'data': value, 'period': period, 'source': source, 'version': version, 'entry': entry['id']})
            cur = self.db.execute('INSERT INTO fiscal_revisions(entry_id,company_id,version,period_id,state,data,source_snapshot,source_hash,snapshot_hash,warnings,reason,actor,created_at,request_key,request_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                  (entry['id'], company_id, version, period['id'], 'retificacao_pendente' if guards else 'rascunho', dump(value), dump(source), fingerprint, snapshot_hash, dump(warnings), reason, self.actor, self._now(), request_key, request_hash))
            if not guards:
                self.db.execute('UPDATE fiscal_entries SET active_version=? WHERE id=?', (version, entry['id']))
                if attaching:
                    self.db.execute('UPDATE fiscal_entries SET document_id=? WHERE id=?', (document_id, entry['id']))
                    self._audit(company_id, 'ficha_manual_associada_origem', {'entry_id': entry['id'], 'document_id': document_id, 'version': version, 'reason': reason})
            self._audit(company_id, 'ficha_fiscal_proposta' if guards else 'ficha_fiscal_salva', {'entry_id': entry['id'], 'version': version, 'reason': reason, 'guards': guards, 'snapshot_hash': snapshot_hash})
            result = self.db.execute('SELECT * FROM fiscal_revisions WHERE id=?', (cur.lastrowid,)).fetchone()
        return self._fiscal_revision(result)

    def review_fiscal_entry(self, company_id, entry_id, snapshot_hash, reason, acknowledged=False):
        from .persistence import _text
        reason = _text(reason, 'motivo da revisão', 2000)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            entry = self._fiscal_entry(company_id, entry_id)
            row = self.db.execute('SELECT * FROM fiscal_revisions WHERE entry_id=? AND version=?', (entry['id'], entry['active_version'])).fetchone()
            if not row or row['snapshot_hash'] != snapshot_hash or row['state'] != 'rascunho':
                raise ValueError('Revisão exige rascunho vigente e hash exato; proposta não altera fechado')
            if self._fiscal_guard(company_id, row['period_id'], entry['document_id']):
                raise ValueError('Período protegido; revisão não pode alterar o vigente')
            _, current = self._fiscal_source(company_id, entry['document_id'])
            if row['source_hash'] != current:
                raise ValueError('Fontes alteradas: salve nova versão antes da revisão')
            if json.loads(row['warnings']) and acknowledged is not True:
                raise ValueError('Confirme a conferência dos avisos da ficha')
            self.db.execute("UPDATE fiscal_revisions SET state='revisado',review_actor=?,review_reason=?,reviewed_at=? WHERE id=?", (self.actor, reason, self._now(), row['id']))
            self._audit(company_id, 'ficha_fiscal_revisada', {'entry_id': entry['id'], 'version': row['version'], 'reason': reason, 'snapshot_hash': snapshot_hash})
            return self._fiscal_revision(self.db.execute('SELECT * FROM fiscal_revisions WHERE id=?', (row['id'],)).fetchone())

    def fiscal_period_status(self, company_id, period_id):
        period = self._owned('periods', company_id, period_id)
        row = self.db.execute('SELECT * FROM fiscal_period_states WHERE company_id=? AND competence=?', (company_id, period['processing_competence'])).fetchone()
        state = dict(row) if row else {'state': 'aberto', 'version': 0, 'reference': ''}
        entries = []
        for entry in self.list_fiscal_entries(company_id):
            current = entry['current']
            if current and self._owned('periods', company_id, current['period_id'])['processing_competence'] == period['processing_competence']:
                entries.append({'id': entry['id'], 'hash': current['snapshot_hash'], 'state': current['state'], 'source_current': entry['source_current'], 'source_hash': entry['source_hash']})
        state.update(competence=period['processing_competence'], entries=entries)
        state['token'] = digest(state)
        state['history'] = [dict(r) for r in self.db.execute('SELECT * FROM fiscal_period_history WHERE company_id=? AND competence=? ORDER BY version DESC', (company_id, period['processing_competence']))]
        return state

    def change_fiscal_period(self, company_id, period_id, target, token, reason, confirmed=False, reference=''):
        from .persistence import _text
        reason = _text(reason, 'motivo do período', 2000)
        reference = _text(reference, 'referência externa', 300, False)
        if confirmed is not True or target not in {'aberto', 'fechado', 'exportado'}:
            raise ValueError('Confirme explicitamente a operação do período')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            state = self.fiscal_period_status(company_id, period_id)
            if token != state['token']:
                raise ValueError('Período alterado; confira novamente o escopo')
            allowed = {'aberto': {'fechado'}, 'fechado': {'aberto', 'exportado'}, 'exportado': set()}
            if target not in allowed[state['state']]:
                raise ValueError('Transição não permitida; exportado exige proposta de retificação')
            if target in {'fechado', 'exportado'} and any(e['state'] != 'revisado' or not e['source_current'] for e in state['entries']):
                raise ValueError('Revise as fichas vigentes e as fontes atuais antes de proteger o período')
            if target == 'exportado' and not reference:
                raise ValueError('Informe referência da exportação externa; esta ação não gera arquivo')
            version = state['version'] + 1
            self.db.execute('INSERT INTO fiscal_period_states VALUES(?,?,?,?,?) ON CONFLICT(company_id,competence) DO UPDATE SET state=excluded.state,version=excluded.version,reference=excluded.reference', (company_id, state['competence'], target, version, reference))
            self.db.execute('INSERT INTO fiscal_period_history(company_id,competence,version,state,reference,reason,actor,created_at,snapshot) VALUES(?,?,?,?,?,?,?,?,?)', (company_id, state['competence'], version, target, reference, reason, self.actor, self._now(), dump(state)))
            self._audit(company_id, 'periodo_fiscal_' + target, {'competence': state['competence'], 'version': version, 'reason': reason, 'reference': reference})
        return self.fiscal_period_status(company_id, period_id)
