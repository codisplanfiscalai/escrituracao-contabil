"""Reviewed preparation of saved drafts from organized documents and observed XML."""
import json
from datetime import date
from decimal import Decimal
from .accounting_store import digest,dump,identifier
from .nfe_item_values import extract_item_values,BASE_PATHS

PREPARATION_SCHEMA="""
CREATE TABLE IF NOT EXISTS document_preparation_batches (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,request_key));
CREATE INDEX IF NOT EXISTS preparation_cycle ON document_preparation_batches(company_id,cycle_id,id);
"""


def preparation_config(data):
    from .persistence import _text
    if not isinstance(data,dict) or set(data)!={'operation','policy_id','posting_date','item_mode','total_source','copy_bases'}:
        raise ValueError('Informe natureza, política, data, modo dos itens e escolhas de cópia')
    config={key:_text(data[key],key,40) for key in ('operation','posting_date','item_mode','total_source')}
    if config['operation'] not in {'entrada','saida'}:raise ValueError('Declare entrada ou saída para os documentos selecionados')
    config['policy_id']=identifier(data['policy_id'])
    if date.fromisoformat(config['posting_date']).isoformat()!=config['posting_date']:raise ValueError('Data de escrituração inválida')
    if config['item_mode'] not in {'cabecalho','observar_xml','propor_itens_xml'}:raise ValueError('Selecione o modo de preparação dos itens')
    if not isinstance(data['copy_bases'],list) or any(not isinstance(v,str) or v not in BASE_PATHS for v in data['copy_bases']) or len(set(data['copy_bases']))!=len(data['copy_bases']):
        raise ValueError('Selecione bases observadas suportadas, sem repetições')
    config['copy_bases']=sorted(data['copy_bases'])
    if config['total_source'] not in {'nao_copiar','vProd'}:raise ValueError('Declare se vProd será copiado para o total atribuído dos itens')
    if config['item_mode']!='propor_itens_xml' and (config['copy_bases'] or config['total_source']!='nao_copiar'):
        raise ValueError('Cópias de valores exigem proposta de itens explícita')
    return config


def document_choices(rows):
    if not isinstance(rows,list) or not 1<=len(rows)<=50:raise ValueError('Selecione de 1 a 50 documentos organizados')
    result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'document_id','observation_id'}:raise ValueError('Selecione documento e origem, quando houver múltiplas')
        result.append({'document_id':identifier(row['document_id']),'observation_id':identifier(row['observation_id']) if row['observation_id'] is not None else None})
    if len({r['document_id'] for r in result})!=len(result):raise ValueError('Documento repetido na preparação')
    return sorted(result,key=lambda r:r['document_id'])


class DocumentPreparationMixin:
    def document_item_values(self, company_id, document_id, observation_id):
        source=self._work_source(company_id,document_id)
        observation=next((o for o in source['observations'] if o['id']==identifier(observation_id)),None)
        if not observation:raise ValueError('Selecione uma observação ativa do documento')
        self._verify_work_originals(company_id,document_id)
        file=self._owned('files',company_id,observation['file_id'])
        if file['kind']!='XML':raise ValueError('Extração de itens disponível somente para XML NF-e/NFC-e 4.00')
        values=extract_item_values(bytes(file['original']))
        if values['key']!=source['business_key']:raise ValueError('Chave do XML não corresponde ao documento selecionado')
        snapshot={'profile':'evidencia-itens-xml-v1','company_id':identifier(company_id),'document_id':identifier(document_id),
                  'observation_id':observation['id'],'file_id':file['id'],'source_hash':source['source_hash'],'values':values}
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def assert_xml_item_evidence(self, company_id, payload, *, current=True):
        if 'xml_item_evidence' not in payload:return
        evidence=payload['xml_item_evidence']
        if not isinstance(evidence,dict) or set(evidence)!={'snapshot','snapshot_hash'} or not isinstance(evidence['snapshot'],dict) or digest(evidence['snapshot'])!=evidence['snapshot_hash']:
            raise ValueError('Evidência dos itens XML alterada')
        snapshot=evidence['snapshot']
        if snapshot.get('company_id')!=identifier(company_id) or any(snapshot.get(k)!=payload.get(k) for k in ('document_id','observation_id','source_hash')):
            raise ValueError('Evidência XML fora do contexto da ficha')
        if current and self.document_item_values(company_id,payload['document_id'],payload['observation_id'])!=evidence:
            raise ValueError('Origem dos valores XML alterada; reconcilie a evidência antes de conferir')

    def preview_document_preparation(self, company_id, cycle_id, documents, data):
        from .tax_engine import decimal_text
        choices=document_choices(documents);config=preparation_config(data)
        cycle=self._work_cycle(company_id,cycle_id);company=self._company(company_id)
        if cycle['state']!='aberta':raise ValueError('Competência encerrada')
        self.assert_module_period_open(company_id,cycle['competence'],{'fiscal','contabil'})
        if config['posting_date'][:7]!=cycle['competence']:raise ValueError('Data deve pertencer à competência dos movimentos')
        policy=self._work_policy(company_id,cycle,config['policy_id'],config['operation'])
        account_ids={policy['debit_account_id'],policy['credit_account_id']}
        accounts=[a for a in self.list_accounts(company_id,cycle['plan_id']) if a['id'] in account_ids]
        items=[];size=2048
        for choice in choices:
            item={**choice,'blockers':[],'warnings':[]}
            try:
                document_id=choice['document_id']
                if self.db.execute('SELECT 1 FROM work_operations WHERE company_id=? AND document_id=?',(company_id,document_id)).fetchone():raise ValueError('Documento já possui operação; abra a ficha existente')
                if self._work_legacy_document_reservation(company_id,document_id):raise ValueError('Documento reservado no histórico; não duplicar')
                self._verify_work_originals(company_id,document_id)
                observed_source=self._work_source(company_id,document_id)
                if observed_source['differences']:item['warnings'].append('Há divergências entre origens; a ficha exige conferência explícita')
                if observed_source['billing_issues']:item['warnings'].append('Há críticas da cobrança na origem; confira parcelas e valores na ficha')
                payload=self.prepare_work_operation(company_id,cycle_id,document_id,choice['observation_id'],config['policy_id'],config['operation'])
                if choice['observation_id'] is not None and payload['observation_id']!=choice['observation_id']:raise ValueError('Origem solicitada ausente; não substituir automaticamente')
                fiscal=payload['fiscal'];cnpj=company['cnpj']
                direction='saida' if cnpj and fiscal['issuer']==cnpj and fiscal['buyer']!=cnpj else 'entrada' if cnpj and fiscal['buyer']==cnpj and fiscal['issuer']!=cnpj else ''
                if direction!=config['operation']:raise ValueError('Partes do documento não confirmam a natureza e a empresa declaradas; exige tratamento individual')
                fiscal['posting_date']=config['posting_date']
                for line in payload['entries']:line['date']=config['posting_date']
                if config['item_mode']!='cabecalho':
                    evidence=self.document_item_values(company_id,document_id,payload['observation_id']);payload['xml_item_evidence']=evidence
                    rows=evidence['snapshot']['values']['items']
                    item['warnings'].extend('Item '+r['nItem']+': '+issue for r in rows for issue in r['issues'])
                    item['warnings'].extend('Item '+r['nItem']+': grupos não extraídos '+', '.join(r['unhandled_groups']) for r in rows if r['unhandled_groups'])
                    if config['item_mode']=='propor_itens_xml':
                        if not rows:raise ValueError('XML sem detalhes; não é possível propor itens')
                        proposed=[]
                        for row in rows:
                            fields=row['fields'];values={'total':''}
                            if config['total_source']=='vProd':
                                source=fields.get('prod/vProd')
                                if not source or source['issue']:raise ValueError('Item '+row['nItem']+': vProd ausente ou inválido para cópia')
                                values['total']=format(decimal_text(source['value']),'.2f')
                            for target in config['copy_bases']:
                                source=row['bases'].get(target)
                                if not source:raise ValueError('Item '+row['nItem']+': base solicitada '+target+' ausente ou não coberta; não presumir zero')
                                values[target]=format(decimal_text(source['value']),'.2f')
                            proposed.append({'id':row['nItem'],'description':fields.get('prod/xProd',{}).get('value',''),'cfop':'',
                                'ncm':fields.get('prod/NCM',{}).get('value',''),'service_code':'','treatment':'',
                                'source_reference':'XML '+evidence['snapshot']['values']['file_sha256']+'; '+row['source_locator']+'; valores atuais e enquadramento exigem conferência',
                                'source_locator':row['source_locator'],'taxes':[],'no_tax_reason':'','values':values})
                        payload['tax_items']=proposed
                        if config['total_source']=='vProd' and sum((Decimal(p['values']['total']) for p in proposed),Decimal(0))!=Decimal(fiscal['total']):
                            item['warnings'].append('Soma dos vProd copiados difere de vNF; confira alocação líquida antes de calcular ou escriturar')
                        item['warnings'].append('CFOP, tratamentos e componentes ficaram sem decisão tributária; complete e calcule antes de conferir')
                    if not rows:item['warnings'].append('Nenhum detalhe encontrado no XML; somente observação de cabeçalho')
                item.update(payload=payload,payload_hash=digest(payload),observation_id=payload['observation_id'])
            except ValueError as error:item['blockers'].append(str(error))
            size+=len(dump(item).encode())
            if size>8*1024*1024:raise ValueError('Prévia acima de 8 MiB; reduza a seleção')
            items.append(item)
        snapshot={'profile':'previa-preparacao-documentos-v1','company_id':identifier(company_id),'cycle_id':identifier(cycle_id),
                  'cycle_version':cycle['version'],'policy_snapshot':policy,'accounts_snapshot':accounts,
                  'module_versions':{m:self.module_period_state(company_id,cycle['competence'],m)['version'] for m in ('fiscal','contabil')},
                  'config':config,'items':items,'ready':not any(i['blockers'] for i in items)}
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def apply_document_preparation(self, company_id, cycle_id, documents, data, expected_hash, request_key, reason, review_reference, confirmed=False):
        from .persistence import _text
        choices=document_choices(documents);config=preparation_config(data)
        reason=_text(reason,'Motivo da preparação',2000);review_reference=_text(review_reference,'Referência da conferência',1000);request_key=_text(request_key,'Tentativa',80)
        if confirmed is not True:raise ValueError('Confirme documentos, origens, política, data e escolhas dos valores; somente rascunhos serão criados')
        request_hash=digest([identifier(cycle_id),choices,config,expected_hash,reason,review_reference])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous=self.db.execute('SELECT id,request_hash FROM document_preparation_batches WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if previous:
                if previous['request_hash']!=request_hash:raise ValueError('Tentativa de preparação usada com outro conteúdo')
                return {**self.document_preparation_detail(company_id,previous['id']),'duplicate':True}
            preview=self.preview_document_preparation(company_id,cycle_id,choices,config)
            if preview['snapshot_hash']!=expected_hash:raise ValueError('Prévia da preparação alterada; confira novamente')
            if not preview['snapshot']['ready']:raise ValueError('Há pendências; nenhum documento foi preparado')
            rows=[]
            for item in preview['snapshot']['items']:
                result=self.save_work_operation(company_id,cycle_id,item['payload'],reason,'prepare:'+digest([request_key,item['document_id']]),_in_transaction=True)
                rows.append({'document_id':item['document_id'],'observation_id':item['observation_id'],'proposal_hash':item['payload_hash'],'proposal':item['payload'],
                             'operation_id':result['operation_id'],'version':result['version'],'snapshot_hash':result['snapshot_hash'],'warnings':item['warnings']})
            now=self._now()
            snapshot={'profile':'preparacao-documentos-v1','company_id':identifier(company_id),'cycle_id':identifier(cycle_id),'config':config,'items':rows,
                      'preview_hash':expected_hash,'request_hash':request_hash,'actor':self.actor,'reason':reason,'review_reference':review_reference,'created_at':now}
            batch=self.db.execute('INSERT INTO document_preparation_batches(company_id,cycle_id,request_key,request_hash,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                                 (company_id,cycle_id,request_key,request_hash,dump(snapshot),digest(snapshot),self.actor,reason,now)).lastrowid
            self._audit(company_id,'documentos_preparados_em_rascunho',{'batch_id':batch,'snapshot_hash':digest(snapshot),'count':len(rows),'reason':reason})
        return {**self.document_preparation_detail(company_id,batch),'duplicate':False}

    def document_preparation_detail(self, company_id, batch_id):
        row=self.db.execute('SELECT * FROM document_preparation_batches WHERE company_id=? AND id=?',(identifier(company_id),identifier(batch_id))).fetchone()
        if not row:raise ValueError('Preparação não pertence à empresa')
        result=dict(row);result['snapshot']=json.loads(result['snapshot']);snapshot=result['snapshot']
        if digest(snapshot)!=result['snapshot_hash'] or any(snapshot[k]!=result[k] for k in ('company_id','cycle_id','request_hash','actor','reason','created_at')):raise ValueError('Manifesto de preparação alterado')
        result['operations']=[]
        for item in snapshot['items']:
            operation=self._work_revision(company_id,item['operation_id'],item['version'])
            if digest(item['proposal'])!=item['proposal_hash'] or operation['snapshot_hash']!=item['snapshot_hash'] or operation['document_id']!=item['document_id'] or operation['cycle_id']!=result['cycle_id']:raise ValueError('Vínculo da preparação com a operação alterado')
            result['operations'].append(operation)
        return result

    def document_preparations(self, company_id, cycle_id):
        self._work_cycle(company_id,cycle_id)
        return [dict(r) for r in self.db.execute('SELECT id,actor,reason,created_at,snapshot_hash FROM document_preparation_batches WHERE company_id=? AND cycle_id=? ORDER BY id DESC LIMIT 50',(company_id,cycle_id))]
