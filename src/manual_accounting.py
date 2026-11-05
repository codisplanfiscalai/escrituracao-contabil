"""Escrituração manual explícita, com revisões imutáveis e fechamento local."""
import json
from datetime import date
from decimal import Decimal, localcontext

from .accounting_store import amount, digest, dump, identifier

MANUAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS manual_journals (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), plan_id INTEGER NOT NULL REFERENCES plans(id),
 reversal_of INTEGER UNIQUE REFERENCES manual_journals(id));
CREATE TABLE IF NOT EXISTS manual_journal_revisions (
 id INTEGER PRIMARY KEY, journal_id INTEGER NOT NULL REFERENCES manual_journals(id),
 version INTEGER NOT NULL, status TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 review_actor TEXT, review_reason TEXT, reviewed_at TEXT, closed_at TEXT,
 UNIQUE(journal_id,version));
CREATE TABLE IF NOT EXISTS manual_journal_requests (
 company_id INTEGER NOT NULL REFERENCES companies(id), request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, revision_id INTEGER NOT NULL REFERENCES manual_journal_revisions(id),
 PRIMARY KEY(company_id,request_key));
"""


def journal_snapshot(company, period, plan, lines, reference, reversal_of=None):
    """Pure validation: accounts have already been resolved within the selected plan."""
    from .persistence import _text
    reference = _text(reference, 'referência manual', 300)
    if not isinstance(lines, list) or not 2 <= len(lines) <= 10000:
        raise ValueError('Informe de 2 a 10000 partidas manuais')
    entries, groups = [], {}
    with localcontext() as context:
        context.prec = 40
        for item in lines:
            if not isinstance(item, dict):
                raise ValueError('Cada partida deve ser objeto')
            posted = _text(item.get('date'), 'data', 10)
            try:
                parsed = date.fromisoformat(posted)
            except ValueError:
                raise ValueError('Data contábil inválida') from None
            if parsed.isoformat() != posted or posted[:7] != period['processing_competence']:
                raise ValueError('Data deve pertencer à competência dos movimentos')
            side = item.get('side')
            if side not in ('D', 'C'):
                raise ValueError('Partida deve indicar D ou C')
            account = item.get('account', {})
            if account.get('plan_id') != plan['id'] or account.get('kind') != 'analitica':
                raise ValueError('Partida exige conta analítica do plano selecionado')
            value = amount(item.get('amount'))
            group = _text(item.get('group'), 'grupo', 100)
            memo = _text(item.get('memo'), 'histórico', 1000)
            # A group is a journal event on one day, including split postings.
            groups.setdefault((posted, group), {'D': Decimal(0), 'C': Decimal(0)})[side] += Decimal(value)
            entries.append({'line': len(entries)+1, 'date': posted, 'group': group,
                            'side': side, 'amount': value, 'memo': memo, 'account': account})
        if any(total['D'] != total['C'] for total in groups.values()):
            raise ValueError('Débitos e créditos devem equilibrar por data e grupo')
        totals = {name: format(sum((row[side] for row in groups.values()), Decimal(0)), '.2f')
                  for name, side in (('debit', 'D'), ('credit', 'C'))}
    return {'engine': 'manual-journal-v1', 'company': company, 'period': period, 'plan': plan,
            'reference': reference, 'reversal_of': reversal_of, 'entries': entries, 'totals': totals,
            'externally_posted': False}


def validate_sealed_journal(revision):
    if revision['status'] != 'fechado' or not all(revision.get(k) for k in ('review_actor', 'review_reason', 'reviewed_at', 'closed_at')):
        raise ValueError('Lançamento manual exige revisão e fechamento explícitos')
    snapshot = revision['snapshot']
    if digest(snapshot) != revision['snapshot_hash']:
        raise ValueError('Hash do lançamento manual divergente')
    try:
        if snapshot['engine'] != 'manual-journal-v1':
            raise ValueError('Motor manual não suportado')
        for key in ('company', 'period', 'plan'):
            if snapshot[key]['id'] != revision[{'company':'company_id','period':'period_id','plan':'plan_id'}[key]]:
                raise ValueError('Contexto do lançamento manual divergente')
        if any(snapshot[key]['company_id'] != revision['company_id'] for key in ('period', 'plan')):
            raise ValueError('Empresa do plano/período divergente')
        expected = journal_snapshot(snapshot['company'], snapshot['period'], snapshot['plan'], snapshot['entries'], snapshot['reference'], revision['reversal_of'])
        if expected != snapshot:
            raise ValueError('Snapshot do lançamento manual inconsistente')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Estrutura do lançamento manual inválida') from exc
    return snapshot


class ManualAccountingMixin:
    def _manual_revision(self, company_id, journal_id, version=None):
        self._company(company_id)
        query = 'SELECT r.*,j.company_id,j.period_id,j.plan_id,j.reversal_of FROM manual_journal_revisions r JOIN manual_journals j ON j.id=r.journal_id WHERE j.company_id=? AND j.id=?'
        args = [company_id, identifier(journal_id)]
        if version is not None:
            query += ' AND r.version=?'; args.append(identifier(version))
        row = self.db.execute(query+' ORDER BY r.version DESC LIMIT 1', args).fetchone()
        if not row:
            raise ValueError('Lançamento manual não pertence à empresa ou não existe')
        result = dict(row); result['snapshot'] = json.loads(result['snapshot'])
        return result

    def list_manual_journals(self, company_id, period_id=None, journal_id=None):
        self._company(company_id)
        if period_id is not None:
            period_id = self._owned('periods', company_id, identifier(period_id))['id']
        if journal_id is not None:
            selected = self._manual_revision(company_id, journal_id)
            if period_id is not None and selected['period_id'] != period_id:
                raise ValueError('Lançamento manual não pertence ao período selecionado')
            versions = self.db.execute('SELECT version FROM manual_journal_revisions WHERE journal_id=? ORDER BY version DESC', (journal_id,)).fetchall()
            return [self._manual_revision(company_id, journal_id, row['version']) for row in versions]
        rows = self.db.execute('SELECT id,period_id FROM manual_journals WHERE company_id=? ORDER BY id DESC', (company_id,)).fetchall()
        return [self._manual_revision(company_id, row['id']) for row in rows if period_id is None or row['period_id'] == period_id]

    def save_manual_journal(self, company_id, period_id, plan_id, entries, reference, reason, request_key,
                            journal_id=None, expected_version=0):
        from .persistence import _text
        reason = _text(reason, 'motivo', 2000)
        request_key = _text(request_key, 'identificador da tentativa', 100)
        period_id, plan_id = identifier(period_id), identifier(plan_id)
        journal_id = identifier(journal_id) if journal_id is not None else None
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 0:
            raise ValueError('Versão esperada deve ser inteiro não negativo')
        request_hash = digest({'period':period_id, 'plan':plan_id, 'entries':entries, 'reference':reference,
                               'reason':reason, 'journal':journal_id, 'expected_version':expected_version})
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            self._company(company_id)
            existing = self.db.execute('SELECT * FROM manual_journal_requests WHERE company_id=? AND request_key=?', (company_id, request_key)).fetchone()
            if existing:
                if existing['request_hash'] != request_hash:
                    raise ValueError('Identificador da tentativa já utilizado com outro conteúdo')
                row = self.db.execute('SELECT journal_id,version FROM manual_journal_revisions WHERE id=?', (existing['revision_id'],)).fetchone()
                return self._manual_revision(company_id, row['journal_id'], row['version'])
            previous = self._manual_revision(company_id, journal_id) if journal_id else None
            if previous:
                if previous['status'] == 'fechado' or previous['reversal_of'] is not None:
                    raise ValueError('Lançamento fechado ou estorno não permite edição; crie estorno vinculado')
                if expected_version != previous['version']:
                    raise ValueError('Versão desatualizada; confira a revisão vigente')
                if (period_id, plan_id) != (previous['period_id'], previous['plan_id']):
                    raise ValueError('Edição deve preservar período e plano')
            elif expected_version != 0:
                raise ValueError('Novo lançamento exige versão esperada zero')
            company = self._company(company_id)
            period = self._owned('periods', company_id, period_id)
            plan = self._owned('plans', company_id, plan_id)
            accounts = {row['id']: row for row in self.list_accounts(company_id, plan_id)}
            if not isinstance(entries, list) or not all(isinstance(line, dict) for line in entries):
                raise ValueError('Partidas devem ser lista de objetos')
            resolved = []
            for line in entries:
                account = accounts.get(identifier(line.get('account_id')))
                if not account:
                    raise ValueError('Conta não pertence ao plano selecionado')
                resolved.append({**line, 'account': account})
            snapshot = journal_snapshot(company, period, plan, resolved, reference)
            if not previous:
                journal_id = self.db.execute('INSERT INTO manual_journals(company_id,period_id,plan_id) VALUES(?,?,?)', (company_id, period_id, plan_id)).lastrowid
            else:
                self.db.execute("UPDATE manual_journal_revisions SET status='substituido' WHERE id=?", (previous['id'],))
            revision = self._insert_manual_revision(company_id, journal_id, (previous['version']+1) if previous else 1, snapshot, reason)
            self.db.execute('INSERT INTO manual_journal_requests VALUES(?,?,?,?)', (company_id, request_key, request_hash, revision['id']))
        return revision

    def _insert_manual_revision(self, company_id, journal_id, version, snapshot, reason):
        self.db.execute('INSERT INTO manual_journal_revisions(journal_id,version,status,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?)',
                        (journal_id, version, 'previa', dump(snapshot), digest(snapshot), self.actor, reason, self._now()))
        self._audit(company_id, 'lancamento_manual_versionado', {'journal_id':journal_id,'version':version,'snapshot_hash':digest(snapshot),'reason':reason})
        return self._manual_revision(company_id, journal_id)

    def transition_manual_journal(self, company_id, journal_id, snapshot_hash, reason, target):
        from .persistence import _text
        reason = _text(reason, 'motivo', 2000)
        if target not in ('revisado', 'fechado'):
            raise ValueError('Transição manual inválida')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            revision = self._manual_revision(company_id, journal_id)
            snapshot = revision['snapshot']
            if snapshot_hash != revision['snapshot_hash'] or digest(snapshot) != snapshot_hash:
                raise ValueError('Hash divergente; confira a revisão vigente')
            if revision['status'] != ('previa' if target == 'revisado' else 'revisado'):
                raise ValueError('Fechamento manual exige revisão explícita da versão vigente')
            # Revalidate the sealed content, including contextual ownership, before transition.
            probe = {**revision, 'status':'fechado', 'review_actor':self.actor, 'review_reason':reason,
                     'reviewed_at':self._now(), 'closed_at':self._now()}
            validate_sealed_journal(probe)
            if target == 'revisado':
                self.db.execute("UPDATE manual_journal_revisions SET status=?,review_actor=?,review_reason=?,reviewed_at=? WHERE id=?", (target,self.actor,reason,self._now(),revision['id']))
            else:
                self.db.execute('UPDATE manual_journal_revisions SET status=?,closed_at=? WHERE id=?', (target,self._now(),revision['id']))
            self._audit(company_id, 'lancamento_manual_'+target, {'journal_id':revision['journal_id'],'version':revision['version'],'snapshot_hash':snapshot_hash,'reason':reason})
        return self._manual_revision(company_id, journal_id)

    def reverse_manual_journal(self, company_id, journal_id, period_id, posting_date, reason, expected_hash):
        from .persistence import _text
        reason = _text(reason, 'motivo do estorno', 2000)
        period_id = identifier(period_id)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            original = self._manual_revision(company_id, journal_id)
            if expected_hash != original['snapshot_hash']:
                raise ValueError('Hash do original divergente')
            source = validate_sealed_journal(original)
            if original['reversal_of'] is not None:
                raise ValueError('Estorno de estorno não implementado; registre ajuste explícito')
            existing = self.db.execute('SELECT id FROM manual_journals WHERE reversal_of=?', (original['journal_id'],)).fetchone()
            if existing:
                reversal = self._manual_revision(company_id,existing['id'])
                if reversal['period_id'] == period_id and reversal['reason'] == reason and all(line['date'] == posting_date for line in reversal['snapshot']['entries']):
                    return reversal
                raise ValueError('Lançamento já possui estorno vinculado com outros parâmetros')
            period = self._owned('periods', company_id, period_id)
            if not isinstance(posting_date, str) or posting_date < max(line['date'] for line in source['entries']):
                raise ValueError('Estorno não pode anteceder o lançamento original')
            lines = [{**line,'date':posting_date,'side':'C' if line['side']=='D' else 'D'} for line in source['entries']]
            snapshot = journal_snapshot(source['company'],period,source['plan'],lines,'Estorno do lançamento '+str(original['journal_id']),original['journal_id'])
            new_id = self.db.execute('INSERT INTO manual_journals(company_id,period_id,plan_id,reversal_of) VALUES(?,?,?,?)', (company_id,period['id'],original['plan_id'],original['journal_id'])).lastrowid
            revision = self._insert_manual_revision(company_id,new_id,1,snapshot,reason)
            self._audit(company_id,'estorno_manual_criado',{'journal_id':new_id,'original_journal_id':original['journal_id'],'original_hash':expected_hash,'reason':reason})
        return revision
