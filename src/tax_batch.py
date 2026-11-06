"""Explicit, bounded, atomic tax calculation batches; never review or post entries."""
import json
import re
from .accounting_store import digest, dump, identifier

TAX_BATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS tax_calculation_batches (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,request_key));
CREATE INDEX IF NOT EXISTS tax_batch_cycle ON tax_calculation_batches(company_id,cycle_id,id);
"""
MAX_BATCH=100
MAX_PREVIEW_BYTES=8*1024*1024


def batch_ids(values):
    if not isinstance(values,list) or not 1<=len(values)<=MAX_BATCH:
        raise ValueError('Selecione de 1 a 100 operações salvas')
    ids=[identifier(value) for value in values]
    if len(ids)!=len(set(ids)):raise ValueError('Não repita operações na seleção do lote')
    return sorted(ids)


class TaxBatchMixin:
    def preview_tax_batch(self, company_id, cycle_id, operation_ids):
        company_id=identifier(company_id);ids=batch_ids(operation_ids)
        cycle=self._work_cycle(company_id,cycle_id)
        if cycle['state']!='aberta':raise ValueError('Competência encerrada; lote não pode alterar movimentos')
        self.assert_module_period_open(company_id,cycle['competence'],{'fiscal'})
        state=self.module_period_state(company_id,cycle['competence'],'fiscal')
        items=[];size=1024
        for operation_id in ids:
            item={'operation_id':operation_id,'blockers':[]}
            try:
                operation=self._work_revision(company_id,operation_id)
                if operation['cycle_id']!=cycle['id']:raise ValueError('Operação fora da competência selecionada')
                item.update(input_version=operation['version'],input_hash=operation['snapshot_hash'],state=operation['state'],reference=operation['payload'].get('reference',''))
                self.assert_operation_modules_open(company_id,cycle,operation['payload'])
                self._verify_work_originals(company_id,operation['document_id'])
                if operation['document_id']:
                    source=self._work_source(company_id,operation['document_id'])
                    if source['source_hash']!=operation['payload'].get('source_hash') or not any(o['id']==operation['payload'].get('observation_id') for o in source['observations']):
                        raise ValueError('Fonte documental selecionada ausente ou alterada; reconcilie a ficha antes de calcular o lote')
                preview=self.preview_operation_tax(company_id,operation_id)
                memory=preview['snapshot']
                components=[{**group,'rate':'por item','effect':', '.join(sorted({line['effect'] for line in memory['lines'] if line['component_key']==group['component_key']}))} for group in memory['component_output']] if 'component_output' in memory else [{'component_key':line['tax'],**{key:line[key] for key in ('tax','base','rate','amount','effect')}} for line in memory['lines']]
                item.update(memory=memory,memory_hash=preview['snapshot_hash'],components=components)
            except ValueError as error:item['blockers'].append(str(error))
            size+=len(dump(item).encode('utf-8'))
            if size>MAX_PREVIEW_BYTES:raise ValueError('Prévia do lote acima de 8 MiB; reduza a seleção')
            items.append(item)
        snapshot={'profile':'previa-tributacao-lote-v1','company_id':company_id,'cycle_id':cycle['id'],'competence':cycle['competence'],
                  'cycle_version':cycle['version'],'fiscal_module_version':state['version'],'items':items,
                  'ready':not any(item['blockers'] for item in items),
                  'limits':['Somente regras aprovadas aplicáveis; não infere incidência ou alíquotas',
                            'Aplicação cria rascunhos; não confere, escritura ou altera títulos/partidas automaticamente','CBS/IBS fora do cálculo']}
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def _tax_batch_row(self, row):
        result=dict(row);result['snapshot']=json.loads(result['snapshot'])
        snapshot=result['snapshot']
        if digest(snapshot)!=result['snapshot_hash'] or any(snapshot[k]!=result[k] for k in ('company_id','cycle_id','actor','reason','request_hash','created_at')):
            raise ValueError('Manifesto do lote tributário alterado')
        return result

    def tax_batch_detail(self, company_id, batch_id):
        self._company(identifier(company_id))
        row=self.db.execute('SELECT * FROM tax_calculation_batches WHERE company_id=? AND id=?',(company_id,identifier(batch_id))).fetchone()
        if not row:raise ValueError('Lote tributário não pertence à empresa')
        result=self._tax_batch_row(row);calculations=[]
        for item in result['snapshot']['items']:
            calculation=self._tax_calculation(company_id,item['calculation_id'])
            output=self._work_revision(company_id,item['operation_id'],item['output_version'])
            memory=calculation['snapshot']
            if calculation['snapshot_hash']!=item['memory_hash'] or calculation['cycle_id']!=result['cycle_id'] or calculation['operation_id']!=item['operation_id'] or memory['input_hash']!=item['input_hash'] or memory['input_version']!=item['input_version'] or output['snapshot_hash']!=item['output_hash'] or output['cycle_id']!=result['cycle_id'] or output['payload'].get('tax_calculation',{}).get('id')!=calculation['id']:
                raise ValueError('Vínculo do lote com cálculo ou versão de operação alterado')
            calculations.append(calculation)
        return {**result,'calculations':calculations}

    def tax_batches(self, company_id, cycle_id, offset=0):
        self._work_cycle(company_id,cycle_id)
        if isinstance(offset,str) and re.fullmatch(r'[0-9]{1,6}',offset):offset=int(offset)
        if type(offset)!=int or offset<0:raise ValueError('Página inválida')
        rows=[self._tax_batch_row(r) for r in self.db.execute('SELECT * FROM tax_calculation_batches WHERE company_id=? AND cycle_id=? ORDER BY id DESC LIMIT 20 OFFSET ?',(company_id,cycle_id,offset))]
        return {'items':[{k:r[k] for k in ('id','company_id','cycle_id','actor','reason','created_at','snapshot_hash')}|{'count':len(r['snapshot']['items'])} for r in rows],
                'total':self.db.execute('SELECT COUNT(*) FROM tax_calculation_batches WHERE company_id=? AND cycle_id=?',(company_id,cycle_id)).fetchone()[0],
                'offset':offset,'limit':20}

    def apply_tax_batch(self, company_id, cycle_id, operation_ids, expected_hash, request_key, reason, confirmed=False):
        from .persistence import _text
        reason=_text(reason,'Motivo da tributação em lote',2000);request_key=_text(request_key,'Tentativa do lote',80)
        ids=batch_ids(operation_ids)
        if confirmed is not True:raise ValueError('Confirme a revisão de todas as operações, regras, bases, efeitos e valores da prévia do lote')
        request_hash=digest([identifier(cycle_id),ids,expected_hash,reason])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous=self.db.execute('SELECT id,request_hash FROM tax_calculation_batches WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if previous:
                if previous['request_hash']!=request_hash:raise ValueError('Tentativa de lote usada com outro conteúdo')
                return {**self.tax_batch_detail(company_id,previous['id']),'duplicate':True}
            preview=self.preview_tax_batch(company_id,cycle_id,ids)
            if preview['snapshot_hash']!=expected_hash:raise ValueError('Prévia do lote alterada; confira novamente todas as operações')
            if not preview['snapshot']['ready']:raise ValueError('Lote contém pendências; nenhuma operação foi alterada')
            items=[]
            for item in preview['snapshot']['items']:
                key='batchtax:'+digest([identifier(company_id),request_key,item['operation_id']])
                result=self.apply_operation_tax(company_id,item['operation_id'],item['memory_hash'],key,reason,_in_transaction=True)
                operation=result['operation'];calculation=result['calculation']
                items.append({'operation_id':item['operation_id'],'reference':item['reference'],'input_version':item['input_version'],
                              'input_hash':item['input_hash'],'calculation_id':calculation['id'],'memory_hash':calculation['snapshot_hash'],
                              'output_version':operation['version'],'output_hash':operation['snapshot_hash']})
            created_at=self._now()
            snapshot={'profile':'tributacao-lote-v1','company_id':identifier(company_id),'cycle_id':identifier(cycle_id),'request_hash':request_hash,'created_at':created_at,
                      'competence':preview['snapshot']['competence'],'preview_hash':expected_hash,'items':items,'actor':self.actor,'reason':reason,
                      'effect':'Novas versões de rascunho; conferência e escrituração permanecem individuais'}
            batch_id=self.db.execute('INSERT INTO tax_calculation_batches(company_id,cycle_id,request_key,request_hash,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                                    (company_id,cycle_id,request_key,request_hash,dump(snapshot),digest(snapshot),self.actor,reason,created_at)).lastrowid
            self._audit(company_id,'tributacao_lote_aplicada',{'batch_id':batch_id,'snapshot_hash':digest(snapshot),'count':len(items),'reason':reason})
        return {**self.tax_batch_detail(company_id,batch_id),'duplicate':False}
