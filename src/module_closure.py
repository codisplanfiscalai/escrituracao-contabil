"""Independent fiscal/accounting period locks, shared by application services."""
import json
from .accounting_store import digest, identifier

MODULE_SCHEMA = """
CREATE TABLE IF NOT EXISTS module_period_versions (
 company_id INTEGER NOT NULL REFERENCES companies(id), competence TEXT NOT NULL,
 module TEXT NOT NULL CHECK(module IN ('fiscal','contabil')), version INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('aberta','encerrada')), snapshot TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL, checks TEXT NOT NULL, evidence_reference TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(company_id,competence,module,version));
"""
CHECKS = {'fiscal': ['lancamentos', 'livros', 'correcoes', 'apuracao'],
          'contabil': ['lancamentos', 'livros', 'correcoes', 'saldos']}


def operation_modules(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('fiscal', {}), dict):
        return {'fiscal', 'contabil'}
    fiscal = payload.get('fiscal') or {}
    operation = fiscal.get('operation')
    has_fiscal = operation in {'entrada', 'saida', 'servico_tomado', 'servico_prestado'} or any(
        fiscal.get(key) not in (None, '') for key in ('model', 'number', 'cfop', 'icms_base', 'icms_amount', 'iss_base', 'iss_amount', 'pis_base', 'pis_amount', 'cofins_base', 'cofins_amount'))
    modules = {'fiscal'} if has_fiscal else set()
    if payload.get('entries') or not has_fiscal or payload.get('settlement') or payload.get('reversal'):
        modules.add('contabil')
    return modules


class ModuleClosureMixin:
    def module_period_state(self, company_id, competence, module):
        from .persistence import _month
        self._company(identifier(company_id))
        competence = _month(competence)
        if module not in CHECKS:
            raise ValueError('Módulo deve ser fiscal ou contabil')
        row = self.db.execute('SELECT * FROM module_period_versions WHERE company_id=? AND competence=? AND module=? ORDER BY version DESC LIMIT 1', (company_id, competence, module)).fetchone()
        if not row:
            return {'company_id': identifier(company_id), 'competence': competence, 'module': module, 'version': 0, 'state': 'aberta'}
        result = dict(row)
        result['snapshot'] = json.loads(result['snapshot'])
        result['checks'] = json.loads(result['checks'])
        if digest(result['snapshot']) != result['snapshot_hash']:
            raise ValueError('Snapshot do encerramento alterado')
        return result

    def assert_module_period_open(self, company_id, competence, modules):
        for module in sorted(set(modules)):
            if self.module_period_state(company_id, competence, module)['state'] != 'aberta':
                raise ValueError(f'Módulo {module} encerrado em {competence}; reabra com motivo antes de alterar ou escriturar')

    def assert_operation_modules_open(self, company_id, cycle, payload):
        modules = operation_modules(payload)
        reversal = payload.get('reversal')
        if isinstance(reversal, dict) and reversal.get('operation_id'):
            original = self._work_revision(company_id, reversal['operation_id'])
            modules |= operation_modules(original['payload'])
        self.assert_module_period_open(company_id, cycle['competence'], modules)

    def module_period_overview(self, company_id, cycle_id, module):
        cycle = self._work_cycle(company_id, cycle_id)
        state = self.module_period_state(company_id, cycle['competence'], module)
        overview = self.work_overview(company_id, cycle_id)
        operations = [o for o in overview['operations'] if module in operation_modules(o['payload'])]
        forms = []
        for row in self.db.execute('SELECT id,version,data FROM work_tabs WHERE company_id=? AND cycle_id=? AND operation_id IS NULL AND closed=0', (company_id, cycle_id)):
            if module in operation_modules(json.loads(row['data']).get('payload') or {}):
                forms.append((row['id'], row['version']))
        blockers = []
        if any(o['state'] not in {'escriturado', 'dispensado'} for o in operations):
            blockers.append('Resolva ou dispense as operações pendentes deste módulo')
        if forms:
            blockers.append('Resolva as guias incompletas deste módulo')
        documents = overview['documents'] if module == 'fiscal' else []
        if any(d['state'] == 'a_escriturar' for d in documents):
            blockers.append('Resolva os documentos fiscais organizados ainda não escriturados')
        if module == 'contabil' and not self.db.execute('SELECT 1 FROM work_balance_starts WHERE company_id=? AND competence<=?', (company_id, cycle['competence'])).fetchone():
            blockers.append('Declare os saldos iniciais ou confirme abertura zero')
        assessment = self.tax_assessment_readiness(company_id,cycle_id) if module=='fiscal' else None
        if assessment and assessment['required'] and not assessment['ready']:
            blockers.append(assessment['message'])
        snapshot = {'company_id': identifier(company_id), 'competence': cycle['competence'], 'module': module,
                    'version': state['version'], 'cycle_version': cycle['version'], 'global_state': cycle['state'],
                    'operations': [(o['operation_id'], o['version'], o['state'], o['snapshot_hash']) for o in operations],
                    'documents': [(d['id'], d['state'], d['source']['source_hash']) for d in documents], 'forms': forms,
                    'tax_assessment':assessment}
        return {'state': state, 'snapshot_hash': digest(snapshot), 'snapshot': snapshot, 'blockers': blockers,
                'required_checks': CHECKS[module], 'global_state': cycle['state']}

    def transition_module_period(self, company_id, cycle_id, module, target, expected_hash, reason, checks=None, evidence_reference=''):
        from .persistence import _json, _text
        reason = _text(reason, 'Motivo do encerramento/reabertura', 2000)
        evidence_reference = _text(evidence_reference, 'Referência da conferência', 1000, False)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            current = self.module_period_overview(company_id, cycle_id, module)
            if current['snapshot_hash'] != expected_hash:
                raise ValueError('Prévia do módulo alterada; recarregue a conferência')
            if target not in {'aberta', 'encerrada'} or current['state']['state'] == target:
                raise ValueError('Transição de módulo inválida')
            if current['global_state'] != 'aberta':
                raise ValueError('Fechamento global anterior preservado; reabra a competência antes desta ação')
            if target == 'encerrada':
                if current['blockers']:
                    raise ValueError('; '.join(current['blockers']))
                if not isinstance(checks, dict) or set(checks) != set(CHECKS[module]) or any(value is not True for value in checks.values()):
                    raise ValueError('Confirme lançamentos, livros, correções e apuração/saldos do módulo')
                if not evidence_reference:
                    raise ValueError('Informe referência da conferência da apuração ou dos saldos')
            else:
                checks = {}
            state = current['state']
            self.db.execute('INSERT INTO module_period_versions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                            (company_id, state['competence'], module, state['version'] + 1, target,
                             _json(current['snapshot']), expected_hash, _json(checks), evidence_reference, self.actor, reason, self._now()))
            self._audit(company_id, 'modulo_' + target, {'module': module, 'competence': state['competence'], 'version': state['version'] + 1, 'reason': reason, 'evidence_reference': evidence_reference})
        return self.module_period_overview(company_id, cycle_id, module)
