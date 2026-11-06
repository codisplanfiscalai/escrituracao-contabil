"""Invented item classifications and rates; no real tax documents or legal claims."""
import copy
import unittest
import xml.etree.ElementTree as ET
import test_work_application as fixtures
import test_tax_engine as tax_fixtures
from test_persistence import fake_xml, NS
from src.persistence import AccountingStore


class TaxItemTests(unittest.TestCase):
    setUp = fixtures.WorkApplicationTests.setUp
    save = fixtures.WorkApplicationTests.save
    post = fixtures.WorkApplicationTests.post
    document = fixtures.WorkApplicationTests.document
    rule = tax_fixtures.TaxEngineTests.rule

    def calc(self, method='percentual', **extra):
        return {'scope':'item','method':method,'reduction_percent':'0',
                'base_rounding':'centavos_antes_da_taxa',**extra}

    def item(self, key='A', total='100.30', taxes=None, **extra):
        return {'id':key,'description':'Item sintético '+key,'cfop':'','ncm':'','service_code':'','treatment':'',
                'source_reference':'Valores e classificação declarados para teste','source_locator':'',
                'taxes':['ICMS'] if taxes is None else taxes,'no_tax_reason':'','values':{'total':total},**extra}

    def operation(self, items):
        payload=self.document()
        payload['tax_items']=items
        return self.save(payload)

    def apply(self, operation, key='item-calc'):
        preview=self.s.preview_operation_tax(self.c,operation['operation_id'])
        result=self.s.apply_operation_tax(self.c,operation['operation_id'],preview['snapshot_hash'],key,'Teste sintético')
        return preview,result

    def test_mixed_treatments_reduction_rounding_and_assessment_item_provenance(self):
        self.rule(key='a',rate='2.5',item_treatment='A',calculation=self.calc(reduction_percent='10'))
        self.rule(key='b',rate='7',effect='credito',item_treatment='B',calculation=self.calc())
        items=[self.item(total='60.00',treatment='A'),self.item('B','40.30',treatment='B')]
        operation=self.operation(items)
        self.assertFalse(operation['validation']['ready'])
        preview,result=self.apply(operation)
        memory=preview['snapshot']
        self.assertEqual(memory['output'],{'icms_base':'94.30','icms_amount':'4.17'})
        self.assertEqual([l['amount'] for l in memory['lines']],['1.35','2.82'])
        self.assertEqual(memory['lines'][0]['steps']['unrounded_base'],'54.000')
        self.assertEqual(result['operation']['payload']['tax_items'],items)
        self.post(result['operation'])
        assessment=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual(assessment['blockers'],[])
        self.assertEqual(assessment['totals'][0]['saldo_aritmetico'],'-1.47')
        self.assertEqual([l['item_id'] for l in assessment['lines']],['A','B'])
        self.assertEqual(assessment['lines'][0]['parameters']['reduction_percent'],'10')

    def test_st_difal_and_retention_are_separate_and_do_not_net_finance_or_journal(self):
        self.rule(key='st',tax='ICMS_ST',rate='10',calculation=self.calc('st',margin_percent='50',deduction_field='st_deduction',negative_policy='bloquear'))
        self.rule(key='difal',tax='ICMS_DIFAL',rate='12',calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        self.rule(key='retain',tax='RETENCAO',rate='2',effect='informativo',calculation=self.calc('retencao',component_code='TESTE'))
        item=self.item(taxes=['ICMS_ST','ICMS_DIFAL','RETENCAO:TESTE'],values={'total':'100.30','st_deduction':'5.00'})
        operation=self.operation([item])
        preview,result=self.apply(operation)
        self.assertEqual(preview['snapshot']['output'],{})
        totals={c['component_key']:c['amount'] for c in result['operation']['payload']['tax_components']}
        self.assertEqual(totals,{'ICMS_ST':'10.05','ICMS_DIFAL':'8.02','RETENCAO:TESTE':'2.01'})
        self.assertEqual(operation['payload']['entries'],result['operation']['payload']['entries'])
        self.assertEqual(operation['payload']['finance'],result['operation']['payload']['finance'])
        self.post(result['operation'])
        totals=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['totals']
        self.assertEqual({r['tax'] for r in totals},{'ICMS_ST','ICMS_DIFAL','RETENCAO'})
        self.assertEqual(next(r for r in totals if r['tax']=='RETENCAO')['component_key'],'RETENCAO:TESTE')

    def test_negative_result_is_blocked_or_zeroed_only_when_declared(self):
        self.rule(tax='ICMS_DIFAL',rate='4',calculation=self.calc('difal',origin_rate='12',negative_policy='bloquear'))
        operation=self.operation([self.item(taxes=['ICMS_DIFAL'])])
        with self.assertRaisesRegex(ValueError,'negativo'):
            self.s.preview_operation_tax(self.c,operation['operation_id'])
        self.rule(version=1,tax='ICMS_DIFAL',rate='4',calculation=self.calc('difal',origin_rate='12',negative_policy='zerar'))
        preview,_=self.apply(operation)
        line=preview['snapshot']['lines'][0]
        self.assertEqual(line['amount'],'0.00')
        self.assertEqual(line['steps']['before_negative_policy'],'-8.024')

    def test_item_rounding_precedes_sum_and_reduction_base_rounding_is_explicit(self):
        self.rule(rate='2',calculation=self.calc())
        # Both items independently round up; rounding the document would yield a different amount.
        operation=self.operation([self.item(total='50.15'),self.item('B','50.15')])
        preview,_=self.apply(operation)
        self.assertEqual(preview['snapshot']['output']['icms_amount'],'2.00')
        self.rule(version=1,rate='50',calculation=self.calc(reduction_percent='99'))
        preview=self.s.preview_operation_tax(self.c,operation['operation_id'])
        self.assertEqual(preview['snapshot']['lines'][0]['base'],'0.50')
        self.assertEqual(preview['snapshot']['output']['icms_amount'],'0.50')

    def test_missing_coverage_ambiguity_and_document_item_overlap_are_blocked(self):
        self.rule(calculation=self.calc())
        for items in ([self.item(taxes=['PIS'])],[self.item(taxes=[],no_tax_reason='Exclusão declarada')]):
            op=self.operation_once(items)
            with self.assertRaisesRegex(ValueError,'componentes declarados'):
                self.s.preview_operation_tax(self.c,op['operation_id'])
        self.rule(key='ambiguous',calculation=self.calc())
        op=self.operation_once([self.item()])
        with self.assertRaisesRegex(ValueError,'ambiguidade'):
            self.s.preview_operation_tax(self.c,op['operation_id'])
        self.rule(key='ambiguous',version=1,state='inativa',calculation=self.calc())
        self.rule(key='legacy')
        with self.assertRaisesRegex(ValueError,'documentais'):
            self.s.preview_operation_tax(self.c,op['operation_id'])

    def operation_once(self, items):
        # Reuse one source/operation across incomplete draft variants.
        row=self.s.db.execute('SELECT id FROM work_operations WHERE company_id=?',(self.c,)).fetchone()
        if not row:
            return self.operation(items)
        old=self.s.get_work_operation(self.c,row['id'])
        payload=copy.deepcopy(old['payload']);payload['tax_items']=items
        return self.save(payload,old['operation_id'],old['version'])

    def test_item_validation_no_silent_omissions_and_no_unsupported_codes(self):
        self.rule(calculation=self.calc())
        invalid=[[],[self.item(total='100.29')],[self.item(),self.item()],
                 [self.item(values={'total':100.30})],[self.item(taxes=['CBS'])],[self.item(taxes=['RETENCAO:CBS'])],
                 [self.item(taxes=[],no_tax_reason='')],[self.item(source_reference='')],
                 [self.item(values={'total':'100.30','invented':'1.00'})]]
        for items in invalid:
            op=self.operation_once(items)
            with self.assertRaises(ValueError):self.s.preview_operation_tax(self.c,op['operation_id'])
            self.assertFalse(op['validation']['ready'])

    def test_item_component_and_rule_changes_invalidate_memory_and_posting(self):
        self.rule(calculation=self.calc())
        operation=self.operation([self.item()])
        preview,result=self.apply(operation)
        repeated=self.s.apply_operation_tax(self.c,operation['operation_id'],preview['snapshot_hash'],'item-calc','Teste sintético')
        self.assertTrue(repeated['duplicate'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],1)
        current=result['operation']
        for field in ('tax_items','tax_components'):
            payload=copy.deepcopy(current['payload'])
            payload[field][0]['id' if field=='tax_items' else 'amount']='alterado'
            edited=self.save(payload,current['operation_id'],current['version'])
            self.assertFalse(edited['validation']['ready'])
            with self.assertRaises(ValueError):self.post(edited)
            current=self.save(copy.deepcopy(result['operation']['payload']),edited['operation_id'],edited['version'])
        self.rule(version=1,rate='3',calculation=self.calc())
        current=self.s.get_work_operation(self.c,current['operation_id'])
        self.assertFalse(current['validation']['ready'])
        with self.assertRaises(ValueError):self.post(current)

    def test_profiles_require_explicit_parameters_and_reject_formulas_and_defaults(self):
        invalid=[self.calc(reduction_percent=0),self.calc(reduction_percent='101'),
                 self.calc('st'),self.calc('difal',origin_rate='4'),
                 self.calc('difal',origin_rate='4',negative_policy=[]),
                 self.calc('retencao',component_code=''),self.calc(base_rounding=''),
                 {**self.calc(),'formula':'eval()'},self.calc('st',margin_percent='1000.1',deduction_field='st_deduction',negative_policy='zerar')]
        for calc in invalid:
            with self.assertRaises(ValueError):self.rule(calculation=calc)
        with self.assertRaises(ValueError):self.rule(tax='ICMS_ST')
        with self.assertRaises(ValueError):self.rule(tax='ICMS_ST',calculation=self.calc())
        for code in ('CBS','IBS','TESTE_CBS'):
            with self.assertRaisesRegex(ValueError,'CBS/IBS'):
                self.rule(tax='RETENCAO',calculation=self.calc('retencao',component_code=code))
        self.rule(tax='ICMS_ST',calculation=self.calc('st',margin_percent='150.123456',deduction_field='st_deduction',negative_policy='bloquear'))

    def test_source_item_locator_ncm_and_completeness_are_checked(self):
        root=ET.fromstring(fake_xml());info=root.find('.//n:infNFe',{'n':NS})
        for index,ncm in enumerate(['00000000','00000001'],1):
            det=ET.SubElement(info,'{'+NS+'}det',nItem=str(index));prod=ET.SubElement(det,'{'+NS+'}prod')
            ET.SubElement(prod,'{'+NS+'}NCM').text=ncm
        source=self.s.receive_sources(self.c,[{'filename':'itens-sinteticos.xml','content':ET.tostring(root)}],'item-source')['items'][0]
        doc=self.s.organize_source(self.c,source['input_id'],self.cycle['id'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
        payload=self.s.prepare_work_operation(self.c,self.cycle['id'],doc,policy_id=self.policy['id'])
        for ncm in ('00000000','00000001'):
            self.s.save_tax_code(self.c,'ncm',ncm,{'description':'Sintético','valid_from':'2026-01-01','valid_to':'','source_reference':'Fixture'},'ativo',0,'Teste')
        self.rule(key='a',ncm='00000000',calculation=self.calc())
        self.rule(key='b',ncm='00000001',rate='7',calculation=self.calc())
        payload['tax_items']=[self.item(total='60.00',ncm='00000000',source_locator='infNFe/det[1]/prod'),self.item('B','40.30',ncm='00000001',source_locator='infNFe/det[2]/prod')]
        op=self.save(payload);preview,result=self.apply(op)
        self.assertEqual(preview['snapshot']['output']['icms_amount'],'4.32')
        payload=copy.deepcopy(result['operation']['payload']);payload['tax_items'][1]['ncm']='00000000'
        edited=self.save(payload,result['operation']['operation_id'],result['operation']['version'])
        with self.assertRaisesRegex(ValueError,'diverge da fonte'):self.s.preview_operation_tax(self.c,edited['operation_id'])

    def test_company_templates_preserve_profiles_but_need_new_validation(self):
        rule=self.rule(tax='RETENCAO',calculation=self.calc('retencao',component_code='TESTE'))
        template=self.s.save_tax_template(self.c,rule['id'],rule['snapshot_hash'],'Perfil sintético',0,'Teste')
        copied=self.s.copy_tax_template(self.other,self.c,template['id'],template['snapshot_hash'],'copy','Cópia','Teste')
        self.assertEqual(copied['spec']['calculation'],rule['spec']['calculation'])
        self.assertEqual(copied['state'],'rascunho')
        self.assertEqual(copied['spec']['validation_reference'],'')
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.tax_rules(self.c)[0]['spec'],rule['spec'])

    def test_retention_identifiers_stay_separate_and_explicit_no_tax_item_is_preserved(self):
        for code,rate in [('A','2'),('B','3')]:
            self.rule(key=code,tax='RETENCAO',rate=rate,item_treatment='tributado',calculation=self.calc('retencao',component_code=code))
        operation=self.operation([self.item(total='60.00',treatment='tributado',taxes=['RETENCAO:A','RETENCAO:B']),
                                  self.item('B','40.30',treatment='sem_componentes',taxes=[],no_tax_reason='Exclusão declarada e conferida no teste')])
        _,result=self.apply(operation)
        self.post(result['operation'])
        assessment=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual(assessment['blockers'],[])
        self.assertEqual({g['component_key']:g['debito'] for g in assessment['totals']},{'RETENCAO:A':'1.20','RETENCAO:B':'1.80'})
        self.assertEqual(result['calculation']['snapshot']['input_items'][1]['no_tax_reason'],'Exclusão declarada e conferida no teste')

    def test_special_component_reversal_requires_matching_explicit_adjustment(self):
        self.rule(tax='ICMS_DIFAL',rate='12',calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        _,result=self.apply(self.operation([self.item(taxes=['ICMS_DIFAL'])]))
        original=self.post(result['operation'])
        reversed_row=self.s.reverse_work_operation(self.c,original['operation_id'],self.cycle['id'],'2026-09-20',original['snapshot_hash'],'Teste','special-reversal')
        self.post(reversed_row)
        self.assertTrue(self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['blockers'])
        self.rule(key='adjust',tax='ICMS_DIFAL',rate='12',operation='ajuste',model='',effect='credito',calculation=self.calc('difal',origin_rate='4',negative_policy='bloquear'))
        payload=self.s.prepare_work_operation(self.c,self.cycle['id'],operation='ajuste')
        payload.update(reference='Ajuste declarado',tax_adjustment_of=original['operation_id'],tax_adjustment_reason='Revisão sintética explícita',tax_items=[self.item(taxes=['ICMS_DIFAL'])])
        payload['fiscal'].update(posting_date='2026-09-20',total='100.30')
        payload['entries']=[{'account_id':self.ids[code],'side':side,'date':'2026-09-20','group':'principal','amount':'100.30','memo':'Ajuste sintético'} for code,side in [('1.1.1','D'),('2.1','C')]]
        _,applied=self.apply(self.save(payload),key='adjustment-calc')
        self.post(applied['operation'])
        assessment=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual(assessment['blockers'],[])
        self.assertEqual(assessment['totals'][0]['saldo_aritmetico'],'0.00')

    def test_fiscal_lock_covers_item_only_adjustments_without_document_header(self):
        from src.module_closure import CHECKS, operation_modules
        state=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Conferência sintética')
        payload=self.s.prepare_work_operation(self.c,self.cycle['id'],operation='ajuste')
        payload.update(reference='Ajuste de componente',tax_items=[self.item(taxes=['ICMS_DIFAL'])])
        payload['fiscal'].update(posting_date='2026-09-20',total='100.30')
        self.assertIn('fiscal',operation_modules(payload))
        with self.assertRaisesRegex(ValueError,'fiscal encerrado'):self.save(payload)
        for key in ('tax_components','tax_calculation','tax_adjustment_of'):
            minimal={'fiscal':{'operation':'ajuste'},key:[]}
            self.assertIn('fiscal',operation_modules(minimal))


if __name__=='__main__':unittest.main()
