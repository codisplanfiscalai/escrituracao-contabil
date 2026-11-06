"""Reviewed assessment adjustments and explicit same-component balance reservations.

No statutory entitlement, cross-tax offset or accounting/financial posting is inferred.
"""
import json
import re
import uuid
from datetime import date
from decimal import Decimal, localcontext
from .accounting_store import digest, dump, identifier
from .tax_engine import TAXES, decimal_text

BALANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tax_assessment_adjustment_versions (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), adjustment_key TEXT NOT NULL,
 version INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('aprovada','cancelada')),
 snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,adjustment_key,version), UNIQUE(company_id,request_key));
CREATE INDEX IF NOT EXISTS tax_adjustment_cycle ON tax_assessment_adjustment_versions(company_id,cycle_id,id);
"""


def adjustment_spec(data):
    from .persistence import _text
    fields={'kind','date','component_key','revenue_code','effect','amount','description','reference'}
    if not isinstance(data,dict) or not isinstance(data.get('kind'),str) or data['kind'] not in {'manual','transporte'}:
        raise ValueError('Selecione ajuste manual ou transporte explícito')
    if data['kind']=='transporte':fields|={'source_assessment_id','source_assessment_hash'}
    if set(data)!=fields:raise ValueError('Informe somente os campos exigidos pelo ajuste')
    spec={key:_text(data[key],key,1000 if key in {'description','reference'} else 100,key!='revenue_code') for key in fields-{'source_assessment_id'}}
    component=spec['component_key']
    if component not in set(TAXES)|{'ICMS_ST','ICMS_DIFAL'} and not re.fullmatch(r'(?:FCP|RETENCAO):[A-Z][A-Z0-9_]{0,29}',component):
        raise ValueError('Componente do ajuste não suportado; CBS/IBS fora do cálculo')
    if {'CBS','IBS'} & set(re.split('[:_]',component)):
        raise ValueError('CBS/IBS permanecem fora do cálculo')
    if spec['effect'] not in {'debito','credito'}:raise ValueError('Declare débito ou crédito, sujeito à conferência do responsável')
    amount=decimal_text(spec['amount'])
    if amount<=0:raise ValueError('Valor do ajuste deve ser positivo')
    spec['amount']=format(amount,'.2f')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',spec['date']) or date.fromisoformat(spec['date']).isoformat()!=spec['date']:
        raise ValueError('Data do ajuste deve usar AAAA-MM-DD')
    if data['kind']=='transporte':
        spec['source_assessment_id']=identifier(data['source_assessment_id'])
        if not re.fullmatch('[0-9a-f]{64}',spec['source_assessment_hash']):raise ValueError('Hash da apuração de origem inválido')
    return spec


class TaxBalancesMixin:
    def tax_assessment_adjustments(self, company_id, cycle_id=None):
        self._company(identifier(company_id))
        if cycle_id is not None:self._work_cycle(company_id,cycle_id)
        query='SELECT * FROM tax_assessment_adjustment_versions WHERE company_id=?'
        args=[company_id]
        if cycle_id is not None:query+=' AND cycle_id=?';args.append(cycle_id)
        results=[];seen=set()
        for row in self.db.execute(query+' ORDER BY id DESC',args):
            value=dict(row);snapshot=json.loads(value['snapshot']);value['snapshot']=snapshot
            if digest(snapshot)!=value['snapshot_hash'] or any(snapshot[k]!=value[k] for k in ('company_id','cycle_id','adjustment_key','version','state')):
                raise ValueError('Histórico de ajustes da apuração alterado')
            value['current']=value['adjustment_key'] not in seen;seen.add(value['adjustment_key']);results.append(value)
        return results

    def _open_assessment_adjustment_period(self, company_id, cycle_id):
        cycle=self._work_cycle(company_id,cycle_id)
        if cycle['state']!='aberta':raise ValueError('Competência encerrada')
        self.assert_module_period_open(company_id,cycle['competence'],{'fiscal'})
        return cycle

    def _tax_balance_source(self, company_id, cycle_id, spec):
        cycle=self._work_cycle(company_id,cycle_id)
        row=self.db.execute('SELECT cycle_id FROM tax_assessment_versions WHERE company_id=? AND id=?',(company_id,spec['source_assessment_id'])).fetchone()
        if not row:raise ValueError('Apuração de origem não pertence à empresa')
        source_cycle=self._work_cycle(company_id,row['cycle_id'])
        if source_cycle['competence']>=cycle['competence']:raise ValueError('Origem deve anteceder a competência de destino')
        rows=self.tax_assessments(company_id,source_cycle['id']);assessment=rows[0]
        if assessment['id']!=spec['source_assessment_id'] or assessment['snapshot_hash']!=spec['source_assessment_hash'] or assessment['state']!='validada':
            raise ValueError('Selecione a última apuração validada da origem')
        closed=self.module_period_state(company_id,source_cycle['competence'],'fiscal')
        if closed['state']!='encerrada':raise ValueError('Fiscal da origem deve estar encerrado')
        if self.preview_tax_assessment(company_id,source_cycle['id'])['snapshot_hash']!=assessment['snapshot_hash']:
            raise ValueError('Apuração da origem não corresponde aos fatos atuais')
        group=next((g for g in assessment['snapshot']['totals'] if g.get('component_key',g['tax'])==spec['component_key'] and g['revenue_code']==spec['revenue_code']),None)
        if not group:raise ValueError('Componente e receita devem corresponder exatamente à origem, sem compensação entre tributos')
        balance=Decimal(group['saldo_aritmetico'])
        if not balance:raise ValueError('Origem sem saldo aritmético para transportar')
        effect='credito' if balance<0 else 'debito'
        if spec['effect']!=effect:raise ValueError('Efeito deve preservar a natureza do saldo da origem')
        active=[r for r in self.tax_assessment_adjustments(company_id) if r['current'] and r['state']=='aprovada' and r['snapshot']['data']['kind']=='transporte']
        allocations=[r for r in active if r['snapshot']['data']['source_assessment_id']==assessment['id'] and r['snapshot']['data']['component_key']==spec['component_key'] and r['snapshot']['data']['revenue_code']==spec['revenue_code']]
        with localcontext() as context:
            context.prec=50
            reserved=sum((Decimal(r['snapshot']['data']['amount']) for r in allocations),Decimal(0))
            available=abs(balance)-reserved
        proof={'assessment_id':assessment['id'],'assessment_hash':assessment['snapshot_hash'],'cycle_id':source_cycle['id'],
               'competence':source_cycle['competence'],'fiscal_closure_version':closed['version'],
               'component_key':spec['component_key'],'revenue_code':spec['revenue_code'],'balance':format(balance,'.2f'),'effect':effect}
        return proof,{'reserved':format(reserved,'.2f'),'available':format(available,'.2f'),
                      'allocations':[(r['id'],r['snapshot_hash']) for r in allocations]}

    def tax_balance_sources(self, company_id, cycle_id):
        cycle=self._work_cycle(company_id,cycle_id);sources=[]
        for source in self.work_cycles(company_id):
            if source['competence']>=cycle['competence'] or self.module_period_state(company_id,source['competence'],'fiscal')['state']!='encerrada':continue
            rows=self.tax_assessments(company_id,source['id'])
            if not rows or rows[0]['state']!='validada':continue
            assessment=rows[0]
            for group in assessment['snapshot']['totals']:
                balance=Decimal(group['saldo_aritmetico'])
                if not balance:continue
                spec={'source_assessment_id':assessment['id'],'source_assessment_hash':assessment['snapshot_hash'],
                      'component_key':group.get('component_key',group['tax']),'revenue_code':group['revenue_code'],'effect':'credito' if balance<0 else 'debito'}
                try:
                    proof,capacity=self._tax_balance_source(company_id,cycle_id,spec)
                    sources.append({**proof,**capacity})
                except ValueError as error:
                    sources.append({**spec,'assessment_id':assessment['id'],'assessment_hash':assessment['snapshot_hash'],
                                    'competence':source['competence'],'blocker':str(error)})
        return sources

    def preview_assessment_adjustment(self, company_id, cycle_id, data):
        cycle=self._open_assessment_adjustment_period(company_id,cycle_id)
        spec=adjustment_spec(data);source=None;capacity=None;catalog=None
        if spec['date'][:7]!=cycle['competence']:raise ValueError('Data do ajuste deve pertencer à competência de destino')
        if spec['revenue_code']:
            catalog=self.resolve_tax_code(company_id,'revenue',spec['revenue_code'],spec['date'])
        if spec['kind']=='transporte':
            source,capacity=self._tax_balance_source(company_id,cycle_id,spec)
            if Decimal(spec['amount'])>Decimal(capacity['available']):raise ValueError('Valor excede o saldo disponível; confira reservas em outras competências')
        current=self.preview_tax_assessment(company_id,cycle_id)
        snapshot={'profile':'previa-ajuste-apuracao-v1','company_id':identifier(company_id),'cycle_id':identifier(cycle_id),'spec':spec,
                  'source':source,'capacity':capacity,'catalog':catalog,'destination_hash':current['snapshot_hash']}
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def apply_assessment_adjustment(self, company_id, cycle_id, data, expected_hash, request_key, reason, review_reference, confirmed=False):
        from .persistence import _text
        reason=_text(reason,'Motivo do ajuste',2000);review_reference=_text(review_reference,'Referência da conferência',1000)
        request_key=_text(request_key,'Tentativa',80);spec=adjustment_spec(data)
        if confirmed is not True:raise ValueError('Confirme valor, origem, natureza e autorização do ajuste, sem presumir direito a crédito')
        request_hash=digest(['aplicar',identifier(cycle_id),spec,expected_hash,reason,review_reference])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous=self._assessment_adjustment_retry(company_id,request_key,request_hash)
            if previous:return previous
            preview=self.preview_assessment_adjustment(company_id,cycle_id,spec)
            if preview['snapshot_hash']!=expected_hash:raise ValueError('Prévia ou disponibilidade alterada; confira novamente')
            snapshot={'profile':'ajuste-apuracao-v1','company_id':identifier(company_id),'cycle_id':identifier(cycle_id),
                      'adjustment_key':uuid.uuid4().hex,'version':1,'state':'aprovada','data':spec,
                      'source':preview['snapshot']['source'],'catalog':preview['snapshot']['catalog'],
                      'capacity_at_review':preview['snapshot']['capacity'],'destination_hash_at_review':preview['snapshot']['destination_hash'],
                      'preview_hash':expected_hash,'review_reference':review_reference}
            result=self._insert_assessment_adjustment(snapshot,request_key,request_hash,reason)
        return result

    def _assessment_adjustment_retry(self, company_id, request_key, request_hash):
        row=self.db.execute('SELECT id,request_hash FROM tax_assessment_adjustment_versions WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
        if not row:return None
        if row['request_hash']!=request_hash:raise ValueError('Tentativa de ajuste usada com outro conteúdo')
        return next(r for r in self.tax_assessment_adjustments(company_id) if r['id']==row['id'])

    def _insert_assessment_adjustment(self, snapshot, request_key, request_hash, reason):
        company_id=snapshot['company_id']
        row_id=self.db.execute('INSERT INTO tax_assessment_adjustment_versions(company_id,cycle_id,adjustment_key,version,state,snapshot,snapshot_hash,request_key,request_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (company_id,snapshot['cycle_id'],snapshot['adjustment_key'],snapshot['version'],snapshot['state'],dump(snapshot),digest(snapshot),request_key,request_hash,self.actor,reason,self._now())).lastrowid
        self._audit(company_id,'ajuste_apuracao_'+snapshot['state'],{'adjustment_id':row_id,'snapshot_hash':digest(snapshot),'reason':reason})
        return next(r for r in self.tax_assessment_adjustments(company_id,snapshot['cycle_id']) if r['id']==row_id)

    def cancel_assessment_adjustment(self, company_id, cycle_id, adjustment_id, expected_hash, request_key, reason, review_reference, confirmed=False):
        from .persistence import _text
        reason=_text(reason,'Motivo do cancelamento',2000);review_reference=_text(review_reference,'Referência da conferência',1000)
        request_key=_text(request_key,'Tentativa',80);adjustment_id=identifier(adjustment_id)
        if confirmed is not True:raise ValueError('Confirme o cancelamento do ajuste')
        request_hash=digest(['cancelar',identifier(cycle_id),adjustment_id,expected_hash,reason,review_reference])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous=self._assessment_adjustment_retry(company_id,request_key,request_hash)
            if previous:return previous
            self._open_assessment_adjustment_period(company_id,cycle_id)
            row=next((r for r in self.tax_assessment_adjustments(company_id,cycle_id) if r['id']==adjustment_id),None)
            if not row or not row['current'] or row['state']!='aprovada' or row['snapshot_hash']!=expected_hash:
                raise ValueError('Ajuste alterado, cancelado ou fora do contexto; atualize a conferência')
            snapshot={**row['snapshot'],'version':row['version']+1,'state':'cancelada','cancels_id':row['id'],
                      'cancels_hash':row['snapshot_hash'],'review_reference':review_reference}
            result=self._insert_assessment_adjustment(snapshot,request_key,request_hash,reason)
        return result

    def assessment_adjustment_lines(self, company_id, cycle_id):
        rows=[r for r in self.tax_assessment_adjustments(company_id,cycle_id) if r['current']]
        lines=[];blockers=[]
        for row in rows:
            if row['state']!='aprovada':continue
            snapshot=row['snapshot'];spec=snapshot['data']
            if spec['revenue_code']:
                try:
                    if self.resolve_tax_code(company_id,'revenue',spec['revenue_code'],spec['date'])!=snapshot['catalog']:
                        raise ValueError('Cadastro de receita alterado; cancele e confira novo ajuste')
                except ValueError as error:
                    blockers.append('Ajuste #'+str(row['id'])+': '+str(error));continue
            if spec['kind']=='transporte':
                try:
                    proof,capacity=self._tax_balance_source(company_id,cycle_id,spec)
                    if proof!=snapshot['source'] or Decimal(capacity['available'])<0:raise ValueError('Origem ou reservas do transporte alteradas')
                except ValueError as error:
                    blockers.append('Ajuste #'+str(row['id'])+': '+str(error));continue
            lines.append({'tax':spec['component_key'].split(':')[0],'component_key':spec['component_key'],'revenue_code':spec['revenue_code'],
                          'amount':spec['amount'],'effect':spec['effect'],'base':None,'rate':None,'origin':'ajuste_apuracao_'+spec['kind'],
                          'adjustment_id':row['id'],'adjustment_hash':row['snapshot_hash'],'reference':spec['reference'],'source':snapshot['source']})
        return rows,lines,blockers

    def assert_no_outgoing_tax_balances(self, company_id, cycle_id):
        assessments={r['id'] for r in self.tax_assessments(company_id,cycle_id)}
        if any(r['current'] and r['state']=='aprovada' and r['snapshot']['data']['kind']=='transporte' and r['snapshot']['data']['source_assessment_id'] in assessments for r in self.tax_assessment_adjustments(company_id)):
            raise ValueError('Há transportes de saldo ativos desta origem; cancele-os nas competências de destino abertas antes de reabrir o fiscal')
