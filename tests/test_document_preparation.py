"""Synthetic XML observations and reviewed draft preparation; no XSD/legal approval."""
import copy
import hashlib
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import unittest
import xml.etree.ElementTree as ET
import test_work_application as fixtures
import test_tax_engine as taxes
from test_persistence import fake_xml,NS
from src.nfe_item_values import extract_item_values
from src.persistence import AccountingStore


def item_xml(number=1, *, wrapper=True, total='100.00', extra=False):
    root=ET.fromstring(fake_xml(number=number,total=total,billing=False,wrapper=wrapper))
    info=root.find('.//{'+NS+'}infNFe')
    for ordinal,value in ((1,'60.00'),(2,'40.00')):
        det=ET.Element('{'+NS+'}det',{'nItem':str(ordinal*10)})
        prod=ET.SubElement(det,'{'+NS+'}prod')
        for key,text in {'cProd':str(ordinal),'xProd':'Produto sintético '+str(ordinal),'NCM':'00000000','CFOP':'5102','uCom':'UN','qCom':'2.0000','vUnCom':'30.0000000000' if ordinal==1 else '20.0000000000','vProd':value,'indTot':'1'}.items():ET.SubElement(prod,'{'+NS+'}'+key).text=text
        if extra:ET.SubElement(prod,'{'+NS+'}vFrete').text=' 5.00 '
        tax=ET.SubElement(det,'{'+NS+'}imposto')
        for parent,branch,values in [('ICMS','ICMS00',{'CST':'00','orig':'0','vBC':value,'pICMS':'18.0000','vICMS':'10.80' if ordinal==1 else '7.20'}),
                                     ('PIS','PISAliq',{'CST':'01','vBC':value,'pPIS':'1.00','vPIS':'0.60' if ordinal==1 else '0.40'})]:
            group=ET.SubElement(ET.SubElement(tax,'{'+NS+'}'+parent),'{'+NS+'}'+branch)
            for key,text in values.items():ET.SubElement(group,'{'+NS+'}'+key).text=text
        info.insert(list(info).index(info.find('{'+NS+'}total')),det)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


class XMLItemValuesTests(unittest.TestCase):
    def test_exact_scoped_paths_decoded_text_and_absences(self):
        content=item_xml(extra=True);values=extract_item_values(content);row=values['items'][0]
        self.assertEqual(values['file_sha256'],hashlib.sha256(content).hexdigest())
        self.assertEqual(row['nItem'],'10');self.assertEqual(row['source_locator'],'infNFe/det[1]/prod')
        self.assertEqual(row['fields']['prod/vFrete']['raw'],' 5.00 ')
        self.assertEqual(row['fields']['prod/vFrete']['path'],'nfeProc/NFe/infNFe/det[1]/prod/vFrete')
        self.assertNotIn('prod/vDesc',row['fields']);self.assertNotIn('st_base',row['bases'])
        self.assertEqual(row['bases']['icms_base']['path'],'nfeProc/NFe/infNFe/det[1]/imposto/ICMS/ICMS00/vBC')
        self.assertEqual(values['sum_observed_vProd'],'100.00')

    def test_unwrapped_xml_and_unknown_tax_groups_do_not_mix_bases(self):
        root=ET.fromstring(item_xml(wrapper=False));tax=root.find('.//{'+NS+'}imposto')
        group=ET.SubElement(tax,'{'+NS+'}IBSCBS');ET.SubElement(group,'{'+NS+'}vBC').text='999.00'
        values=extract_item_values(ET.tostring(root));row=values['items'][0]
        self.assertTrue(row['fields']['prod/vProd']['path'].startswith('NFe/infNFe/'))
        self.assertEqual(row['bases']['icms_base']['value'],'60.00')
        self.assertIn('imposto/IBSCBS',row['unhandled_groups'])
        self.assertFalse(any('IBSCBS' in key for key in row['fields']))

    def test_invalid_decimals_remain_observed_but_never_become_copy_candidates(self):
        root=ET.fromstring(item_xml());root.find('.//{'+NS+'}vProd').text='1e3'
        root.find('.//{'+NS+'}vBC').text='-1.00'
        row=extract_item_values(ET.tostring(root))['items'][0]
        self.assertEqual(row['fields']['prod/vProd']['raw'],'1e3');self.assertTrue(row['fields']['prod/vProd']['issue'])
        self.assertNotIn('icms_base',row['bases'])

    def test_duplicates_entities_and_item_limit_are_rejected(self):
        for mode in ('nItem','field','group'):
            root=ET.fromstring(item_xml());details=root.findall('.//{'+NS+'}det')
            if mode=='nItem':details[1].set('nItem','10')
            if mode=='field':details[0].find('{'+NS+'}prod').append(copy.deepcopy(details[0].find('.//{'+NS+'}vProd')))
            if mode=='group':details[0].find('.//{'+NS+'}ICMS').append(copy.deepcopy(details[0].find('.//{'+NS+'}ICMS00')))
            with self.assertRaises(ValueError):extract_item_values(ET.tostring(root))
        with self.assertRaises(ValueError):extract_item_values(b'<!DOCTYPE n [<!ENTITY x SYSTEM "file:///etc/passwd">]><NFe/>')
        root=ET.fromstring(item_xml());info=root.find('.//{'+NS+'}infNFe');detail=info.find('{'+NS+'}det')
        for index in range(201):
            copy_detail=copy.deepcopy(detail);copy_detail.set('nItem',str(index+100));info.append(copy_detail)
        with self.assertRaisesRegex(ValueError,'200'):extract_item_values(ET.tostring(root))

    def test_nfce_65_is_read_without_inventing_a_recipient(self):
        from test_fiscal_ledger import nfce
        root=ET.fromstring(nfce());info=root.find('.//{'+NS+'}infNFe')
        detail=ET.fromstring(item_xml()).find('.//{'+NS+'}det');info.append(detail)
        values=extract_item_values(ET.tostring(root))
        self.assertEqual(values['model'],'65');self.assertEqual(len(values['items']),1)

    def test_st_fcp_cofins_paths_are_separate_and_unsupported_branches_are_reported(self):
        root=ET.fromstring(item_xml());group=root.find('.//{'+NS+'}ICMS00');group.tag='{'+NS+'}ICMS10'
        for name,value in [('vBCST','90.00'),('vBCFCP','55.00')]:ET.SubElement(group,'{'+NS+'}'+name).text=value
        tax=root.find('.//{'+NS+'}imposto');cofins=ET.SubElement(ET.SubElement(tax,'{'+NS+'}COFINS'),'{'+NS+'}COFINSAliq')
        for name,value in [('CST','01'),('vBC','50.00'),('pCOFINS','7.00'),('vCOFINS','3.50')]:ET.SubElement(cofins,'{'+NS+'}'+name).text=value
        row=extract_item_values(ET.tostring(root))['items'][0]
        self.assertEqual({k:v['value'] for k,v in row['bases'].items()},{'icms_base':'60.00','st_base':'90.00','fcp_base':'55.00','pis_base':'60.00','cofins_base':'50.00'})
        group.tag='{'+NS+'}ICMS60';row=extract_item_values(ET.tostring(root))['items'][0]
        self.assertIn('imposto/ICMS/ICMS60',row['unhandled_groups']);self.assertNotIn('icms_base',row['bases'])


class DocumentPreparationTests(unittest.TestCase):
    setUp=fixtures.WorkApplicationTests.setUp
    rule=taxes.TaxEngineTests.rule
    save=fixtures.WorkApplicationTests.save
    post=fixtures.WorkApplicationTests.post

    def config(self, **extra):
        return {'operation':'entrada','policy_id':self.policy['id'],'posting_date':'2026-09-20','item_mode':'observar_xml','total_source':'nao_copiar','copy_bases':[],**extra}

    def document(self, number=1, **kwargs):
        received=self.s.receive_sources(self.c,[{'filename':str(number)+'.xml','content':item_xml(number,**kwargs)}],'receipt-'+str(number))['items'][0]
        organized=self.s.organize_source(self.c,received['input_id'],self.cycle['id'],received['snapshot_hash'],'Teste')
        return {'document_id':organized['evidence']['document_ids'][0],'observation_id':None}

    def apply(self, documents, config=None, key='prepare'):
        config=config or self.config();preview=self.s.preview_document_preparation(self.c,self.cycle['id'],documents,config)
        return self.s.apply_document_preparation(self.c,self.cycle['id'],documents,config,preview['snapshot_hash'],key,'Teste','Conferência sintética',True)

    def test_preview_and_apply_only_create_drafts_and_preserve_originals(self):
        docs=[self.document(1),self.document(2)]
        before=[tuple(r) for r in self.s.db.execute('SELECT id,original,sha256 FROM files')]
        preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,self.config())
        self.assertTrue(preview['snapshot']['ready']);self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0],0)
        result=self.apply(docs)
        self.assertEqual(len(result['operations']),2)
        for row in result['operations']:
            self.assertEqual(row['state'],'rascunho');self.assertEqual(row['payload']['fiscal']['posting_date'],'2026-09-20')
            self.assertEqual([r['date'] for r in row['payload']['entries']],['2026-09-20']*2)
            self.assertIn('xml_item_evidence',row['payload']);self.assertNotIn('tax_items',row['payload'])
        for table in ('work_movements','finance_titles','tax_calculations'):self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)
        self.assertEqual([tuple(r) for r in self.s.db.execute('SELECT id,original,sha256 FROM files')],before)

    def test_explicit_copy_proposes_facts_without_cfop_or_tax_decision(self):
        docs=[self.document()];config=self.config(item_mode='propor_itens_xml',total_source='vProd',copy_bases=['icms_base','pis_base'])
        result=self.apply(docs,config);payload=result['operations'][0]['payload']
        first=payload['tax_items'][0]
        self.assertEqual(first['id'],'10');self.assertEqual(first['values'],{'total':'60.00','icms_base':'60.00','pis_base':'60.00'})
        self.assertEqual(first['cfop'],'');self.assertEqual(first['taxes'],[]);self.assertEqual(first['no_tax_reason'],'')
        self.assertFalse(self.s.get_work_operation(self.c,result['operations'][0]['operation_id'])['validation']['ready'])
        blank=self.s.preview_document_preparation(self.c,self.cycle['id'],[self.document(2)],self.config(item_mode='propor_itens_xml'))
        self.assertEqual(blank['snapshot']['items'][0]['payload']['tax_items'][0]['values'],{'total':''})

    def test_gross_copy_mismatch_is_warning_not_a_silent_net_formula(self):
        docs=[self.document(total='110.00',extra=True)]
        config=self.config(item_mode='propor_itens_xml',total_source='vProd')
        preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)
        self.assertTrue(preview['snapshot']['ready'])
        self.assertTrue(any('vNF' in w for w in preview['snapshot']['items'][0]['warnings']))
        result=self.apply(docs,config);payload=result['operations'][0]['payload']
        self.assertEqual(payload['fiscal']['total'],'110.00');self.assertEqual(payload['tax_items'][0]['values']['total'],'60.00')
        row=self.s.get_work_operation(self.c,result['operations'][0]['operation_id']);payload=copy.deepcopy(row['payload'])
        for item in payload['tax_items']:item['taxes']=['ICMS']
        row=self.save(payload,row['operation_id'],row['version'])
        self.rule(calculation={'scope':'item','method':'percentual','reduction_percent':'0','base_rounding':'centavos_antes_da_taxa'})
        with self.assertRaisesRegex(ValueError,'Soma|soma'):self.s.preview_operation_tax(self.c,row['operation_id'])

    def test_missing_requested_base_blocks_all_documents_without_assuming_zero(self):
        docs=[self.document()];config=self.config(item_mode='propor_itens_xml',copy_bases=['st_base'])
        preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)
        self.assertFalse(preview['snapshot']['ready'])
        with self.assertRaisesRegex(ValueError,'nenhum documento'):self.apply(docs,config)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0],0)

    def test_retry_and_canonical_document_uniqueness_survive_post_commit(self):
        docs=[self.document()];config=self.config();preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)
        first=self.apply(docs);again=self.s.apply_document_preparation(self.c,self.cycle['id'],docs,config,preview['snapshot_hash'],'prepare','Teste','Conferência sintética',True)
        self.assertTrue(again['duplicate']);self.assertEqual(first['snapshot'],again['snapshot'])
        with self.assertRaises(ValueError):self.apply(docs,key='other')
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_operations').fetchone()[0],1)

    def test_failure_after_first_save_rolls_back_entire_preparation(self):
        docs=[self.document(1),self.document(2)];original=self.s.save_work_operation;calls=0
        def fail(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==2:raise ValueError('Falha sintética')
            return original(*args,**kwargs)
        counts={t:self.s.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('work_operations','work_revisions','work_requests','audit','document_preparation_batches')}
        with patch.object(self.s,'save_work_operation',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'Falha sintética'):self.apply(docs)
        for table,count in counts.items():self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],count)

    def test_concurrent_retries_create_one_manifest_and_one_operation_per_document(self):
        docs=[self.document()];config=self.config();preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)
        def apply(_):
            with AccountingStore(self.path) as store:return store.apply_document_preparation(self.c,self.cycle['id'],docs,config,preview['snapshot_hash'],'race','Teste','Teste',True)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,range(2)))
        self.assertEqual(sorted(r['duplicate'] for r in results),[False,True]);self.assertEqual(results[0]['id'],results[1]['id'])

    def test_source_changes_invalid_observation_and_wrong_direction_block(self):
        docs=[self.document()];config=self.config();preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)
        wrong=[{**docs[0],'observation_id':999999}]
        self.assertFalse(self.s.preview_document_preparation(self.c,self.cycle['id'],wrong,config)['snapshot']['ready'])
        row=self.s.source_inbox(self.c)[0];evidence=copy.deepcopy(row['evidence']);evidence['issues'].append('Nota de conferência')
        with self.s.db:self.s._append_source_revision(self.c,row['input_id'],evidence,'Teste')
        with self.assertRaisesRegex(ValueError,'alterada'):self.s.apply_document_preparation(self.c,self.cycle['id'],docs,config,preview['snapshot_hash'],'stale','Teste','Teste',True)
        # Wrong declared direction is blocked before any source or fiscal effect.
        self.s.db.execute('UPDATE companies SET cnpj=? WHERE id=?',('9'*14,self.c));self.s.db.commit()
        self.assertFalse(self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)['snapshot']['ready'])

    def test_xml_evidence_is_in_tax_memory_and_tampering_requires_reconciliation(self):
        docs=[self.document()];result=self.apply(docs,self.config(item_mode='propor_itens_xml',total_source='vProd',copy_bases=['icms_base']))
        row=self.s.get_work_operation(self.c,result['operations'][0]['operation_id']);payload=copy.deepcopy(row['payload'])
        for item in payload['tax_items']:item['taxes']=['ICMS']
        row=self.save(payload,row['operation_id'],row['version'])
        self.rule(calculation={'scope':'item','method':'percentual','reduction_percent':'0','base_rounding':'centavos_antes_da_taxa'})
        preview=self.s.preview_operation_tax(self.c,row['operation_id']);self.assertEqual(preview['snapshot']['profile'],'tributacao-itens-v4')
        self.assertEqual(preview['snapshot']['xml_item_evidence'],payload['xml_item_evidence'])
        applied=self.s.apply_operation_tax(self.c,row['operation_id'],preview['snapshot_hash'],'calc','Teste')['operation']
        self.assertTrue(applied['validation']['ready'])
        payload=copy.deepcopy(applied['payload']);payload['xml_item_evidence']['snapshot']['values']['items'][0]['fields']['prod/vProd']['value']='999.00'
        changed=self.save(payload,row['operation_id'],applied['version']);self.assertFalse(changed['validation']['ready'])

    def test_documental_memory_keeps_observation_and_header_only_keeps_old_profile(self):
        docs=[self.document()];result=self.apply(docs);self.rule()
        preview=self.s.preview_operation_tax(self.c,result['operations'][0]['operation_id'])
        self.assertEqual(preview['snapshot']['profile'],'tributacao-parametrizada-v2')
        self.assertIn('xml_item_evidence',preview['snapshot'])
        second=self.apply([self.document(2)],self.config(item_mode='cabecalho'),key='header')
        self.assertEqual(self.s.preview_operation_tax(self.c,second['operations'][0]['operation_id'])['snapshot']['profile'],'tributacao-parametrizada-v1')

    def test_posted_evidence_and_memory_remain_historical_after_source_revision(self):
        docs=[self.document()];result=self.apply(docs);self.rule()
        operation_id=result['operations'][0]['operation_id']
        preview=self.s.preview_operation_tax(self.c,operation_id)
        calculated=self.s.apply_operation_tax(self.c,operation_id,preview['snapshot_hash'],'calc-history','Teste')['operation']
        self.post(calculated)
        posted=self.s.get_work_operation(self.c,operation_id)
        source=self.s.source_inbox(self.c)[0];evidence=copy.deepcopy(source['evidence']);evidence['issues'].append('Observação posterior sintética')
        with self.s.db:self.s._append_source_revision(self.c,source['input_id'],evidence,'Teste')
        historical=self.s.get_work_operation(self.c,operation_id)
        self.assertEqual(historical['payload'],posted['payload'])
        self.assertEqual(historical['snapshot_hash'],posted['snapshot_hash'])
        self.assertEqual(self.s.tax_operation_issues(self.c,historical),[])

    def test_closed_period_context_and_confirmation_are_enforced(self):
        docs=[self.document()];config=self.config();preview=self.s.preview_document_preparation(self.c,self.cycle['id'],docs,config)
        for confirmed in (False,1,'true'):
            with self.assertRaises(ValueError):self.s.apply_document_preparation(self.c,self.cycle['id'],docs,config,preview['snapshot_hash'],'bad','Teste','Teste',confirmed)
        self.s.db.execute("UPDATE work_cycles SET state='encerrada' WHERE id=?",(self.cycle['id'],));self.s.db.commit()
        with self.assertRaisesRegex(ValueError,'encerrada'):self.apply(docs)
        # Read-only item observation remains possible in a closed cycle.
        source=self.s._work_source(self.c,docs[0]['document_id'])
        self.assertEqual(len(self.s.document_item_values(self.c,docs[0]['document_id'],source['observations'][0]['id'])['snapshot']['values']['items']),2)

    def test_company_scope_preserves_preparation_history(self):
        docs=[self.document()];result=self.apply(docs)
        with self.assertRaises(ValueError):self.s.document_preparation_detail(self.other,result['id'])
        self.assertEqual(len(self.s.document_preparations(self.c,self.cycle['id'])),1)

    def test_outgoing_nfce_without_buyer_can_only_prepare_for_the_issuer(self):
        from test_fiscal_ledger import nfce
        from test_persistence import ISSUER
        self.s.db.execute('UPDATE companies SET cnpj=? WHERE id=?',(ISSUER,self.c));self.s.db.commit()
        policy=self.s.save_work_policy(self.c,self.plan,'saida','2026-08','Saída sintética',self.ids['1.1.1'],self.ids['2.1'],'Teste',True)
        root=ET.fromstring(nfce());root.find('.//{'+NS+'}infNFe').append(ET.fromstring(item_xml()).find('.//{'+NS+'}det'))
        source=self.s.receive_sources(self.c,[{'filename':'nfce.xml','content':ET.tostring(root)}],'nfce')['items'][0]
        doc=self.s.organize_source(self.c,source['input_id'],self.cycle['id'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
        result=self.apply([{'document_id':doc,'observation_id':None}],self.config(operation='saida',policy_id=policy['id']))
        fiscal=result['operations'][0]['payload']['fiscal']
        self.assertEqual((fiscal['operation'],fiscal['model'],fiscal['buyer']),('saida','65',''))

    def test_genuine_migration_16_to_current_preserves_originals_calculation_batches_and_locks(self):
        from src.module_closure import CHECKS
        doc=self.document()['document_id']
        payload=self.s.prepare_work_operation(self.c,self.cycle['id'],doc,policy_id=self.policy['id'])
        row=self.save(payload);self.rule()
        preview=self.s.preview_tax_batch(self.c,self.cycle['id'],[row['operation_id']])
        batch=self.s.apply_tax_batch(self.c,self.cycle['id'],[row['operation_id']],preview['snapshot_hash'],'old-batch','Teste',True)
        self.post(self.s.get_work_operation(self.c,row['operation_id']))
        preview=self.s.preview_tax_assessment(self.c,self.cycle['id']);assessment=self.s.create_tax_assessment(self.c,self.cycle['id'],preview['snapshot_hash'],'assessment','Teste')
        self.s.validate_tax_assessment(self.c,self.cycle['id'],assessment['id'],assessment['snapshot_hash'],'Teste',True)
        state=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Teste')
        before=[tuple(r) for r in self.s.db.execute('SELECT id,original,sha256 FROM files')]
        revisions=[tuple(r) for r in self.s.db.execute('SELECT * FROM work_revisions')]
        self.s.db.execute('DROP TABLE document_preparation_batches');self.s.db.execute('UPDATE schema_version SET version=16');self.s.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],18)
            self.assertEqual([tuple(r) for r in reopened.db.execute('SELECT id,original,sha256 FROM files')],before)
            self.assertEqual([tuple(r) for r in reopened.db.execute('SELECT * FROM work_revisions')],revisions)
            self.assertEqual(reopened.document_preparations(self.c,self.cycle['id']),[])
            self.assertEqual(reopened.tax_batch_detail(self.c,batch['id'])['snapshot'],batch['snapshot'])
            self.assertEqual(reopened.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
            self.assertEqual(reopened.db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__':unittest.main()
