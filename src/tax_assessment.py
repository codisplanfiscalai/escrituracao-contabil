"""Versioned arithmetic assessment of posted facts under declared company rules."""
import json
from decimal import Decimal, localcontext
from .accounting_store import digest, dump, identifier
from .module_closure import operation_modules
from .tax_engine import TAXES, decimal_text


class TaxAssessmentMixin:
    def preview_tax_assessment(self, company_id, cycle_id):
        cycle = self._work_cycle(company_id,cycle_id)
        overview = self.work_overview(company_id,cycle_id)
        lines, blockers, fiscal_operations = [], [], []
        adjustments = [o for o in overview['operations'] if o['state']=='escriturado' and o['payload'].get('tax_adjustment_of') and not self.tax_operation_issues(company_id,o)]
        for operation in overview['operations']:
            payload = operation['payload']
            if payload.get('reversal'):
                original = self._work_revision(company_id,payload['reversal']['operation_id'])
                if original['payload'].get('tax_calculation') or any(original['payload'].get('fiscal',{}).get(prefix+'_amount') not in (None,'') for prefix in TAXES.values()):
                    if not any(str(a['payload']['tax_adjustment_of'])==str(original['operation_id']) and any(a['payload'].get('fiscal',{}).get(prefix+'_amount') not in (None,'') for prefix in TAXES.values()) for a in adjustments):
                        blockers.append(f"Estorno #{operation['operation_id']} de origem tributada exige ajuste fiscal explícito vinculado; tributos não foram revertidos por suposição")
                    fiscal_operations.append(operation)
            if 'fiscal' not in operation_modules(payload):
                continue
            if operation not in fiscal_operations:
                fiscal_operations.append(operation)
            if operation['state']=='dispensado':
                continue
            if operation['state']!='escriturado':
                blockers.append(f"Operação #{operation['operation_id']} ainda não escriturada")
                continue
            issues = self.tax_operation_issues(company_id,operation)
            if issues:
                blockers.extend(i['message'] for i in issues)
                continue
            covered = set()
            proof = payload.get('tax_calculation')
            if proof:
                for item in proof['memory']['lines']:
                    lines.append({'operation_id':operation['operation_id'],'operation_hash':operation['snapshot_hash'],
                                  'tax':item['tax'],'amount':item['amount'],'base':item['base'],'rate':item['rate'],
                                  'effect':item['effect'],'revenue_code':item['revenue_code'],'origin':'calculado_por_regra',
                                  'calculation_id':proof['id'],'rule':item['rule'],'tax_adjustment_of':payload.get('tax_adjustment_of')})
                    covered.add(item['tax'])
            manual = [(tax,prefix) for tax,prefix in TAXES.items() if tax not in covered and payload.get('fiscal',{}).get(prefix+'_amount') not in (None,'')]
            if manual:
                try:
                    matching = {r['spec']['tax']:r for r in self._matching_tax_rules(company_id,payload['fiscal'])}
                    for tax,prefix in manual:
                        rule = matching.get(tax)
                        if not rule:
                            raise ValueError(f"Operação #{operation['operation_id']}: {tax} informado sem regra de efeito aprovada")
                        amount = decimal_text(payload['fiscal'][prefix+'_amount'])
                        lines.append({'operation_id':operation['operation_id'],'operation_hash':operation['snapshot_hash'],
                                      'tax':tax,'amount':format(amount,'.2f'),'base':payload['fiscal'].get(prefix+'_base',''),
                                      'rate':None,'effect':rule['spec']['effect'],'revenue_code':rule['spec']['revenue_code'],
                                      'origin':'valor_informado_preservado_sem_recalculo','calculation_id':None,'rule':rule,'tax_adjustment_of':payload.get('tax_adjustment_of')})
                except ValueError as error:
                    blockers.append(str(error))
        for document in overview['documents']:
            if document['state']=='a_escriturar':
                blockers.append(f"Documento #{document['id']} organizado e ainda não escriturado")
        forms = []
        for row in self.db.execute('SELECT id,version,data FROM work_tabs WHERE company_id=? AND cycle_id=? AND operation_id IS NULL AND closed=0',(company_id,cycle_id)):
            if 'fiscal' in operation_modules(json.loads(row['data']).get('payload') or {}):
                forms.append((row['id'],row['version']))
        if forms:
            blockers.append('Há guias fiscais incompletas ainda abertas')
        totals = {}
        with localcontext() as context:
            context.prec = 40
            for line in lines:
                key = (line['tax'],line['revenue_code'])
                group = totals.setdefault(key,{'tax':key[0],'revenue_code':key[1],'debito':Decimal(0),'credito':Decimal(0),'informativo':Decimal(0)})
                group[line['effect']] += Decimal(line['amount'])
            groups = [{**g,'saldo_aritmetico':format(g['debito']-g['credito'],'.2f'),
                       **{k:format(g[k],'.2f') for k in ('debito','credito','informativo')}} for _,g in sorted(totals.items())]
        source = {'company_id':identifier(company_id),'competence':cycle['competence'],'cycle_version':cycle['version'],
                  'operations':[(o['operation_id'],o['version'],o['state'],o['snapshot_hash']) for o in fiscal_operations],
                  'documents':[(d['id'],d['state'],d['source']['source_hash']) for d in overview['documents']], 'forms':forms}
        snapshot = {'profile':'apuracao-parametrizada-v1','source':source,'lines':lines,'totals':groups,'blockers':blockers,
                    'formula':'saldo_aritmetico = soma(debito) - soma(credito)',
                    'limits':['Não é obrigação acessória ou guia de pagamento','Não infere créditos, regimes, vencimentos ou compensações','Saldo negativo não é transferido automaticamente','CBS/IBS fora do cálculo']}
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def tax_assessments(self, company_id, cycle_id):
        self._work_cycle(company_id,cycle_id)
        results = []
        for row in self.db.execute('SELECT * FROM tax_assessment_versions WHERE company_id=? AND cycle_id=? ORDER BY version DESC',(company_id,cycle_id)):
            result = dict(row)
            result['snapshot'] = json.loads(result['snapshot'])
            if digest(result['snapshot']) != result['snapshot_hash']:
                raise ValueError('Apuração armazenada alterada')
            results.append(result)
        return results

    def create_tax_assessment(self, company_id, cycle_id, expected_hash, request_key, reason):
        from .persistence import _text
        reason, request_key = _text(reason,'Motivo da apuração',2000), _text(request_key,'Tentativa',80)
        request_hash = digest([identifier(cycle_id),expected_hash,reason])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            cycle = self._work_cycle(company_id,cycle_id)
            self.assert_module_period_open(company_id,cycle['competence'],{'fiscal'})
            if cycle['state']!='aberta':
                raise ValueError('Competência encerrada')
            previous = self.db.execute('SELECT id,request_hash FROM tax_assessment_versions WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if previous:
                if previous['request_hash']!=request_hash:
                    raise ValueError('Tentativa de apuração usada com outro conteúdo')
                return next(r for r in self.tax_assessments(company_id,cycle_id) if r['id']==previous['id'])
            preview = self.preview_tax_assessment(company_id,cycle_id)
            if preview['snapshot_hash']!=expected_hash:
                raise ValueError('Prévia de apuração alterada; atualize a conferência')
            version = self.db.execute('SELECT COALESCE(MAX(version),0)+1 FROM tax_assessment_versions WHERE cycle_id=?',(cycle_id,)).fetchone()[0]
            assessment_id = self.db.execute('INSERT INTO tax_assessment_versions(company_id,cycle_id,version,request_key,request_hash,state,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (company_id,cycle_id,version,request_key,request_hash,'previa',dump(preview['snapshot']),expected_hash,self.actor,reason,self._now())).lastrowid
            self._audit(company_id,'apuracao_gerada',{'assessment_id':assessment_id,'version':version,'reason':reason})
        return next(r for r in self.tax_assessments(company_id,cycle_id) if r['id']==assessment_id)

    def validate_tax_assessment(self, company_id, cycle_id, assessment_id, expected_hash, reason, confirmed=False):
        from .persistence import _text
        reason = _text(reason,'Motivo da validação',2000)
        if confirmed is not True:
            raise ValueError('Confirme a revisão dos fatos, regras, bases, efeitos e memória de cálculo')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            cycle = self._work_cycle(company_id,cycle_id)
            self.assert_module_period_open(company_id,cycle['competence'],{'fiscal'})
            if cycle['state']!='aberta':
                raise ValueError('Competência encerrada')
            rows = self.tax_assessments(company_id,cycle_id)
            if not rows or rows[0]['id']!=identifier(assessment_id):
                raise ValueError('Valide a última versão da apuração')
            current = self.preview_tax_assessment(company_id,cycle_id)
            row = rows[0]
            if row['snapshot_hash']!=expected_hash or expected_hash!=current['snapshot_hash']:
                raise ValueError('Fatos ou parâmetros alterados; gere outra apuração')
            if row['snapshot']['blockers']:
                raise ValueError('; '.join(row['snapshot']['blockers']))
            if row['state']!='validada':
                self.db.execute("UPDATE tax_assessment_versions SET state='validada',review_actor=?,review_reason=?,reviewed_at=? WHERE id=?",(self.actor,reason,self._now(),row['id']))
                self._audit(company_id,'apuracao_validada',{'assessment_id':row['id'],'reason':reason})
        return self.tax_assessments(company_id,cycle_id)[0]

    def tax_assessment_readiness(self, company_id, cycle_id):
        cycle = self._work_cycle(company_id,cycle_id)
        required = any(r['state']=='aprovada' and r['spec']['valid_from'][:7]<=cycle['competence'] and (not r['spec']['valid_to'] or r['spec']['valid_to'][:7]>=cycle['competence']) for r in self.tax_rules(company_id))
        rows = self.tax_assessments(company_id,cycle_id)
        required = required or bool(rows)
        if not required:
            return {'required':False,'ready':True,'fingerprint':None}
        current = self.preview_tax_assessment(company_id,cycle_id)
        ready = bool(rows and rows[0]['state']=='validada' and rows[0]['snapshot_hash']==current['snapshot_hash'] and not current['snapshot']['blockers'])
        return {'required':True,'ready':ready,'fingerprint':current['snapshot_hash'],
                'assessment_id':rows[0]['id'] if rows else None,'message':'' if ready else 'Gere e valide a apuração parametrizada atual antes de encerrar o fiscal'}
