"""Append-only event observations and reviewed operational decisions, no posting."""
import json
import xml.etree.ElementTree as ET
from .accounting_store import digest,dump,identifier
from .nfe_events import parse_nfe_event,NS

EVENT_SCHEMA="""
CREATE TABLE IF NOT EXISTS nfe_event_observations (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 input_id INTEGER NOT NULL UNIQUE REFERENCES source_inputs(id), document_key TEXT NOT NULL,
 event_identity TEXT NOT NULL, original_hash TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS event_document ON nfe_event_observations(company_id,document_key,event_identity,id);
CREATE TABLE IF NOT EXISTS nfe_event_reviews (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 event_identity TEXT NOT NULL, version INTEGER NOT NULL, request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 UNIQUE(company_id,event_identity,version), UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS nfe_event_posting_proofs (
 revision_id INTEGER PRIMARY KEY REFERENCES work_revisions(id),
 company_id INTEGER NOT NULL REFERENCES companies(id), snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL);
"""
DECISIONS={'pendente','suspender','manter_fluxo'}


class NFeEventMixin:
    def _index_nfe_event(self,company_id,input_id,snapshot):
        identity=digest([snapshot[k] for k in ('key','environment','event_type','sequence')])
        self.db.execute('INSERT INTO nfe_event_observations(company_id,input_id,document_key,event_identity,original_hash,snapshot,snapshot_hash) VALUES(?,?,?,?,?,?,?)',
                        (company_id,input_id,snapshot['key'],identity,snapshot['file_sha256'],dump(snapshot),digest(snapshot)))

    def _event_observation(self,company_id,row):
        value=dict(row);snapshot=json.loads(value['snapshot'])
        if digest(snapshot)!=value['snapshot_hash'] or snapshot['key']!=value['document_key'] or digest([snapshot[k] for k in ('key','environment','event_type','sequence')])!=value['event_identity']:
            raise ValueError('Observação de evento alterada')
        source=self._source_revision(company_id,value['input_id']);issues=[]
        try:
            if source['evidence'].get('nfe_event')!=snapshot or source['sha256']!=value['original_hash'] or parse_nfe_event(self.source_original(company_id,value['input_id'])['content'])!=snapshot:
                raise ValueError('Origem do evento diverge da observação preservada')
        except ValueError as error:issues.append(str(error))
        return {**value,'snapshot':snapshot,'filename':source['filename'],'source_state':source['evidence']['state'],'integrity_issues':issues}

    def _event_review_row(self,row):
        if not row:return None
        result=dict(row);result['snapshot']=json.loads(result['snapshot'])
        if digest(result['snapshot'])!=result['snapshot_hash'] or any(result['snapshot'][k]!=result[k] for k in ('company_id','event_identity','version','request_hash')):
            raise ValueError('Decisão de evento alterada')
        return result

    def _event_context(self,company_id,identity):
        rows=self.db.execute('SELECT * FROM nfe_event_observations WHERE company_id=? AND event_identity=? ORDER BY id',(company_id,identity)).fetchall()
        if not rows:raise ValueError('Evento não pertence à empresa')
        observations=[self._event_observation(company_id,row) for row in rows]
        event=observations[0]['snapshot'];key=event['key'];blockers=[]
        proofs=sorted({(o['original_hash'],o['snapshot_hash']) for o in observations})
        for item in observations:blockers.extend(item['integrity_issues']);blockers.extend(item['snapshot']['issues'])
        if len(proofs)>1:blockers.append('Origens diferentes para a mesma identidade de evento; não escolher uma versão automaticamente')
        doc=self.db.execute('SELECT id,period_id FROM documents WHERE company_id=? AND business_key=?',(company_id,key)).fetchone()
        document=None
        if doc:
            source=self._work_source(company_id,doc['id']);environments=set()
            try:
                self._verify_work_originals(company_id,doc['id'])
                for file in source['files']:
                    original=self._owned('files',company_id,file['id'])
                    if original['kind']=='XML' and original['status']!='excluido':
                        root=ET.fromstring(bytes(original['original']))
                        tags=root.findall('.//n:infNFe/n:ide/n:tpAmb',NS)
                        if len(tags)!=1 or (tags[0].text or '').strip() not in {'1','2'}:
                            blockers.append('XML documental sem ambiente único suportado')
                        else:environments.add(tags[0].text.strip())
            except (ValueError,ET.ParseError) as error:blockers.append(str(error))
            if environments!={event['environment']}:blockers.append('Ambiente do documento não confirmado por XML compatível com o evento')
            period=self._owned('periods',company_id,doc['period_id'])
            operation=self.db.execute('SELECT id FROM work_operations WHERE company_id=? AND document_id=?',(company_id,doc['id'])).fetchone()
            revision=self._work_revision(company_id,operation['id']) if operation else None
            cycle=self.db.execute('SELECT id,state,version FROM work_cycles WHERE company_id=? AND competence=?',(company_id,period['processing_competence'])).fetchone()
            document={'id':doc['id'],'source_hash':source['source_hash'],'competence':period['processing_competence'],'environments':sorted(environments),
                      'operation':{k:revision[k] for k in ('operation_id','version','state','snapshot_hash')} if revision else None,
                      'cycle':dict(cycle) if cycle else None,
                      'module_states':{m:{k:v for k,v in self.module_period_state(company_id,period['processing_competence'],m).items() if k in {'version','state'}} for m in ('fiscal','contabil')}}
        else:blockers.append('Documento com essa chave ainda não está organizado nesta empresa')
        # Decisions follow source evidence, not changing operation versions or period state.
        evidence={'profile':'contexto-eventos-nfe-v1','company_id':identifier(company_id),'event_identity':identity,
                  'key':key,'proofs':proofs,'document_id':doc['id'] if doc else None,
                  'document_source_hash':document['source_hash'] if document else None,'blockers':sorted(set(blockers))}
        fingerprint=digest(evidence)
        review=self._event_review_row(self.db.execute('SELECT * FROM nfe_event_reviews WHERE company_id=? AND event_identity=? ORDER BY version DESC LIMIT 1',(company_id,identity)).fetchone())
        current=bool(review and review['snapshot']['context_hash']==fingerprint)
        decision=review['snapshot']['decision'] if current else 'pendente'
        origin_rows=[{k:o[k] for k in ('id','input_id','original_hash','snapshot_hash','filename','source_state','integrity_issues')} for o in observations]
        return {'event_identity':identity,'event':event,'observations':origin_rows,'document':document,'evidence':evidence,'context_hash':fingerprint,
                'blockers':evidence['blockers'],'review':review,'review_current':current,'decision':decision,
                'blocking':bool(blockers or decision!='manter_fluxo'),'duplicate_copies':len(observations)-len(proofs),
                'notice':'Decisão operacional conferida; não confirma autorização SEFAZ nem altera escrituração, impostos ou títulos'}

    def nfe_event_preview(self,company_id,input_id):
        self._company(company_id)
        row=self.db.execute('SELECT event_identity FROM nfe_event_observations WHERE company_id=? AND input_id=?',(company_id,identifier(input_id))).fetchone()
        if not row:raise ValueError('Fonte não contém evento processado suportado nesta empresa')
        context=self._event_context(company_id,row['event_identity'])
        if len(dump(context).encode())>8*1024*1024:raise ValueError('Contexto de eventos acima de 8 MiB; tratamento individual necessário')
        return {'snapshot':context,'snapshot_hash':digest(context)}

    def nfe_event_queue(self,company_id,query='',offset=0):
        from .persistence import _text
        self._company(company_id);query=_text(query,'Busca de evento',100,False).casefold()
        if type(offset) is not int or offset<0:raise ValueError('Deslocamento inválido')
        groups=self.db.execute('SELECT event_identity,MIN(input_id) input_id,document_key FROM nfe_event_observations WHERE company_id=? GROUP BY event_identity,document_key ORDER BY MIN(id) DESC',(company_id,)).fetchall()
        if query:groups=[g for g in groups if query in g['document_key'].casefold()]
        result=[]
        for group in groups[offset:offset+20]:
            context=self._event_context(company_id,group['event_identity']);event=context['event']
            result.append({'input_id':group['input_id'],'key':event['key'],'event_type':event['event_type'],'sequence':event['sequence'],'environment':event['environment'],
                           'return_code':event['return_code'],'decision':context['decision'],'blocking':context['blocking'],'copies':len(context['observations']),
                           'document_id':context['document']['id'] if context['document'] else None})
        return {'items':result,'offset':offset,'limit':20,'total':len(groups)}

    def nfe_document_events(self,company_id,document_id):
        document=self._owned('documents',company_id,identifier(document_id))
        contexts=[self._event_context(company_id,r['event_identity']) for r in self.db.execute('SELECT DISTINCT event_identity FROM nfe_event_observations WHERE company_id=? AND document_key=? ORDER BY event_identity',(company_id,document['business_key']))]
        rows=[{'event_identity':c['event_identity'],'context_hash':c['context_hash'],'decision':c['decision'],'blocking':c['blocking'],
               'review_hash':c['review']['snapshot_hash'] if c['review'] else None} for c in contexts]
        snapshot={'document_id':document['id'],'events':rows}
        return {**snapshot,'blocking':any(r['blocking'] for r in rows),'snapshot_hash':digest(snapshot)}

    def nfe_event_issues(self,company_id,document_id):
        if document_id is None:return []
        events=self.nfe_document_events(company_id,document_id)
        return [{'field':'nfe_events','message':'Há evento de NF-e/NFC-e pendente ou suspenso; confira em Recepção antes de escriturar','severity':'bloqueio'}] if events['blocking'] else []

    def nfe_event_history(self,company_id,input_id):
        context=self.nfe_event_preview(company_id,input_id)['snapshot']
        return [self._event_review_row(row) for row in self.db.execute('SELECT * FROM nfe_event_reviews WHERE company_id=? AND event_identity=? ORDER BY version DESC',(company_id,context['event_identity']))]

    def _record_nfe_event_posting(self,company_id,revision):
        if revision['document_id'] is None:return
        summary=self.nfe_document_events(company_id,revision['document_id'])
        if not summary['events']:return
        if summary['blocking']:raise ValueError('Eventos pendentes impedem a escrituração')
        reviews=[]
        for event in summary['events']:
            row=self._event_review_row(self.db.execute('SELECT * FROM nfe_event_reviews WHERE company_id=? AND event_identity=? ORDER BY version DESC LIMIT 1',(company_id,event['event_identity'])).fetchone())
            reviews.append(row)
        snapshot={'profile':'eventos-na-escrituracao-v1','company_id':identifier(company_id),'operation_id':revision['operation_id'],
                  'revision_id':revision['id'],'operation_hash':revision['snapshot_hash'],'document_id':revision['document_id'],
                  'events':summary,'reviews':reviews,'actor':self.actor,'created_at':self._now()}
        self.db.execute('INSERT INTO nfe_event_posting_proofs(revision_id,company_id,snapshot,snapshot_hash) VALUES(?,?,?,?)',
                        (revision['id'],company_id,dump(snapshot),digest(snapshot)))

    def nfe_event_posting_proof(self,company_id,operation_id):
        revision=self._work_revision(company_id,operation_id)
        row=self.db.execute('SELECT * FROM nfe_event_posting_proofs WHERE company_id=? AND revision_id=?',(company_id,revision['id'])).fetchone()
        if not row:return None
        result=dict(row);snapshot=json.loads(result['snapshot']);result['snapshot']=snapshot
        if digest(snapshot)!=result['snapshot_hash'] or snapshot['revision_id']!=revision['id'] or snapshot['company_id']!=identifier(company_id) or snapshot['operation_hash']!=revision['snapshot_hash']:
            raise ValueError('Evidência histórica dos eventos alterada')
        for review in snapshot['reviews']:
            preserved=self._event_review_row(self.db.execute('SELECT * FROM nfe_event_reviews WHERE company_id=? AND id=?',(company_id,review['id'])).fetchone())
            if preserved!=review:raise ValueError('Decisão vinculada à escrituração alterada')
        return result

    def review_nfe_event(self,company_id,input_id,expected_hash,decision,reason,review_reference,request_key,confirmed=False):
        from .persistence import _text
        company_id=identifier(company_id);input_id=identifier(input_id)
        if decision not in DECISIONS or confirmed is not True:raise ValueError('Escolha e confirme a decisão operacional do evento')
        reason=_text(reason,'Motivo da decisão',2000);reference=_text(review_reference,'Referência da conferência externa',1000);request_key=_text(request_key,'Tentativa',80)
        request_hash=digest([input_id,expected_hash,decision,reason,reference])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous=self.db.execute('SELECT * FROM nfe_event_reviews WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if previous:
                if previous['request_hash']!=request_hash:raise ValueError('Tentativa de evento usada com outro conteúdo')
                return {**self._event_review_row(previous),'duplicate':True}
            preview=self.nfe_event_preview(company_id,input_id);context=preview['snapshot']
            if preview['snapshot_hash']!=expected_hash:raise ValueError('Prévia do evento alterada; confira novamente')
            if decision=='manter_fluxo' and context['blockers']:raise ValueError('Resolva a correlação, integridade e cobertura antes de manter o fluxo')
            identity=context['event_identity']
            version=self.db.execute('SELECT COALESCE(MAX(version),0)+1 FROM nfe_event_reviews WHERE company_id=? AND event_identity=?',(company_id,identity)).fetchone()[0]
            preserved={**context,'review':{k:context['review'][k] for k in ('id','version','snapshot_hash')} if context['review'] else None}
            snapshot={'profile':'decisao-evento-nfe-v1','company_id':company_id,'event_identity':identity,'version':version,'request_hash':request_hash,
                      'context_hash':context['context_hash'],'context':preserved,'decision':decision,'actor':self.actor,'reason':reason,
                      'review_reference':reference,'created_at':self._now(),'effect':'Anotação e controle de pendência; nenhum movimento, título ou dado fiscal alterado'}
            ident=self.db.execute('INSERT INTO nfe_event_reviews(company_id,event_identity,version,request_key,request_hash,snapshot,snapshot_hash) VALUES(?,?,?,?,?,?,?)',
                                  (company_id,identity,version,request_key,request_hash,dump(snapshot),digest(snapshot))).lastrowid
            self._audit(company_id,'evento_nfe_conferido',{'review_id':ident,'snapshot_hash':digest(snapshot),'decision':decision,'reason':reason})
        return {**self._event_review_row(self.db.execute('SELECT * FROM nfe_event_reviews WHERE id=?',(ident,)).fetchone()),'duplicate':False}
