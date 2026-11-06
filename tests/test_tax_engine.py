"""Invented rates/codes solely for arithmetic, isolation and workflow tests."""
import copy
import unittest
import xml.etree.ElementTree as ET
import test_work_application as fixtures
from src.module_closure import CHECKS
from src.persistence import AccountingStore
from test_persistence import fake_xml, NS


class TaxEngineTests(unittest.TestCase):
    setUp = fixtures.WorkApplicationTests.setUp
    save = fixtures.WorkApplicationTests.save
    post = fixtures.WorkApplicationTests.post
    document = fixtures.WorkApplicationTests.document
    opening = fixtures.WorkApplicationTests.opening

    def rule(self, company=None, key='synthetic', version=0, state='aprovada', **spec):
        data = {'tax':'ICMS','rate':'2.5','base_field':'total','effect':'debito','operation':'entrada','model':'55',
                'valid_from':'2026-09-01','valid_to':'','rounding':'meio_para_cima','validation_reference':'Validação inteiramente sintética'}
        data.update(spec)
        return self.s.save_tax_rule(company or self.c,key,'Regra sintética',data,state,version,'Teste sintético')

    def calculate(self):
        self.rule()
        operation = self.save(self.document())
        preview = self.s.preview_operation_tax(self.c,operation['operation_id'])
        applied = self.s.apply_operation_tax(self.c,operation['operation_id'],preview['snapshot_hash'],'tax-1','Conferência sintética')
        return operation, preview, applied

    def test_decimal_calculation_trace_and_idempotent_application(self):
        original, preview, applied = self.calculate()
        memory = applied['calculation']['snapshot']
        self.assertEqual(memory['lines'][0]['unrounded'],'2.5075')
        self.assertEqual(memory['output']['icms_amount'],'2.51')
        self.assertEqual(memory['lines'][0]['rule']['version'],1)
        self.assertEqual(applied['operation']['version'],2)
        self.assertEqual(applied['operation']['state'],'rascunho')
        repeated = self.s.apply_operation_tax(self.c,original['operation_id'],preview['snapshot_hash'],'tax-1','Conferência sintética')
        self.assertTrue(repeated['duplicate'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],1)
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],0)
        self.post(applied['operation'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM work_movements').fetchone()[0],2)

    def test_no_rates_in_models_and_invalid_or_ambiguous_rules_are_blocked(self):
        config = self.s.tax_configuration(self.c)
        self.assertFalse(config['legal_defaults_loaded'])
        self.assertTrue(all(m['spec']['rate']=='' for m in config['structural_models']))
        for invalid in ({'rate':1.5},{'rate':''},{'rate':'100.1'},{'tax':'CBS'},{'rounding':''}):
            with self.assertRaises(ValueError):self.rule(**invalid)
        self.rule(key='a')
        self.rule(key='b')
        operation = self.save(self.document())
        with self.assertRaisesRegex(ValueError,'ambiguidade'):
            self.s.preview_operation_tax(self.c,operation['operation_id'])

    def test_changed_tax_value_or_rule_requires_new_calculation(self):
        _, _, applied = self.calculate()
        operation = applied['operation']
        payload = copy.deepcopy(operation['payload'])
        payload['fiscal']['icms_amount']='90.00'
        edited = self.save(payload,operation['operation_id'],operation['version'])
        self.assertTrue(any('depois do cálculo' in i['message'] for i in edited['validation']['issues']))
        self.rule(version=1,rate='3')
        current = self.s.get_work_operation(self.c,operation['operation_id'])
        self.assertFalse(current['validation']['ready'])
        with self.assertRaises(ValueError):self.post(current)

    def test_template_copy_is_draft_and_target_changes_do_not_touch_source(self):
        rule = self.rule()
        template = self.s.save_tax_template(self.c,rule['id'],rule['snapshot_hash'],'Modelo sintético',0,'Teste')
        copied = self.s.copy_tax_template(self.other,self.c,template['id'],template['snapshot_hash'],'copied','Cópia sintética','Teste')
        self.assertEqual(copied['state'],'rascunho')
        self.assertEqual(copied['source']['source_company_id'],self.c)
        spec = {**copied['spec'],'rate':'7','validation_reference':'Validação da empresa destinatária'}
        self.s.save_tax_rule(self.other,'copied','Cópia sintética',spec,'aprovada',1,'Ajuste local')
        self.assertEqual(self.s._tax_rule(self.c,rule['id'])['spec']['rate'],'2.5')
        self.assertEqual(self.s.tax_templates(self.c)[0]['snapshot']['rule']['spec']['rate'],'2.5')
        self.assertEqual(self.s.tax_templates(self.other),[])

    def test_explicit_rounding_and_future_rule_do_not_change_past_facts(self):
        _,_,applied = self.calculate()
        self.rule(version=1,rounding='truncar')
        preview = self.s.preview_operation_tax(self.c,applied['operation']['operation_id'])
        self.assertEqual(preview['snapshot']['output']['icms_amount'],'2.50')
        self.rule(version=2,rate='9',valid_from='2026-10-01',valid_to='2026-10-31')
        preview = self.s.preview_operation_tax(self.c,applied['operation']['operation_id'])
        self.assertEqual(preview['snapshot']['output']['icms_amount'],'2.50')
        self.assertEqual(self.s._matching_tax_rules(self.c,{'operation':'entrada','model':'55','posting_date':'2026-11-01'}),[])

    def test_company_catalogs_vigency_and_references_are_mandatory(self):
        data = {'description':'Código sintético','valid_from':'2026-01-01','valid_to':'2026-09-30','source_reference':'Tabela sintética sem validade legal'}
        for kind,code in [('cfop','1102'),('ncm','00000000'),('service','SYN-1'),('revenue','0000')]:
            self.s.save_tax_code(self.c,kind,code,data,'ativo',0,'Teste')
        rule = self.rule(cfop='1102',ncm='00000000',service_code='SYN-1',revenue_code='0000')
        self.assertEqual(rule['spec']['revenue_code'],'0000')
        self.assertEqual(self.s.tax_catalog(self.other),[])
        with self.assertRaisesRegex(ValueError,'versão ativa'):
            self.rule(company=self.other,cfop='1102')
        with self.assertRaises(ValueError):self.s.resolve_tax_code(self.c,'ncm','00000000','2026-10-01')
        self.assertEqual(self.s.resolve_tax_code(self.c,'cfop','1102','2026-09-15')['version'],1)

    def test_assessment_sums_posted_facts_and_gates_fiscal_closure(self):
        _, _, applied = self.calculate()
        self.post(applied['operation'])
        state = self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.assertTrue(any('apuração parametrizada' in message for message in state['blockers']))
        preview = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertEqual(preview['snapshot']['blockers'],[])
        self.assertEqual(preview['snapshot']['totals'][0]['saldo_aritmetico'],'2.51')
        assessment = self.s.create_tax_assessment(self.c,self.cycle['id'],preview['snapshot_hash'],'assessment-1','Teste')
        reviewed = self.s.validate_tax_assessment(self.c,self.cycle['id'],assessment['id'],assessment['snapshot_hash'],'Conferência',True)
        self.assertEqual(reviewed['state'],'validada')
        state = self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.assertEqual(state['blockers'],[])
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Fechamento',{key:True for key in CHECKS['fiscal']},'Apuração parametrizada validada')
        with self.assertRaisesRegex(ValueError,'fiscal encerrado'):
            self.rule(version=1,rate='3')

    def test_manual_values_preserved_and_unclassified_tax_blocks_validation(self):
        payload = self.document()
        payload['fiscal']['icms_amount']='9.99'
        self.post(self.save(payload))
        preview = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertTrue(preview['snapshot']['blockers'])
        self.rule()
        preview = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertEqual(preview['snapshot']['lines'][0]['amount'],'9.99')
        self.assertEqual(preview['snapshot']['lines'][0]['origin'],'valor_informado_preservado_sem_recalculo')

    def test_schema_12_migration_preserves_previous_module_lock(self):
        state = self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Referência externa')
        for table in ('tax_assessment_versions','tax_calculations','tax_template_versions','tax_rule_versions','tax_catalog_versions'):
            self.s.db.execute('DROP TABLE '+table)
        self.s.db.execute('UPDATE schema_version SET version=12')
        self.s.db.commit()
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.db.execute('SELECT version FROM schema_version').fetchone()[0],16)
            self.assertEqual(reopened.module_period_state(self.c,'2026-09','fiscal')['state'],'encerrada')
            self.assertEqual(reopened.tax_rules(self.c),[])

    def test_removing_calculation_requires_explicit_manual_exception(self):
        _,_,applied = self.calculate()
        row = applied['operation']
        payload = copy.deepcopy(row['payload'])
        del payload['tax_calculation']
        with self.assertRaises(ValueError):self.save(payload,row['operation_id'],row['version'])
        payload['tax_override_reason']='Exceção sintética revisada'
        edited = self.save(payload,row['operation_id'],row['version'])
        self.assertTrue(edited['validation']['ready'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],1)

    def test_mixed_ncm_source_cannot_apply_one_item_rule_to_whole_document(self):
        data = {'description':'NCM sintético','valid_from':'2026-01-01','valid_to':'','source_reference':'Fixture'}
        self.s.save_tax_code(self.c,'ncm','00000000',data,'ativo',0,'Teste')
        self.rule(ncm='00000000')
        root = ET.fromstring(fake_xml())
        info = root.find('.//{'+NS+'}infNFe')
        for index,ncm in enumerate(['00000000','00000001'],1):
            detail = ET.SubElement(info,'{'+NS+'}det',{'nItem':str(index)})
            product = ET.SubElement(detail,'{'+NS+'}prod')
            for key,value in {'cProd':'SYN-'+str(index),'xProd':'Item sintético','NCM':ncm,'uCom':'UN'}.items():
                ET.SubElement(product,'{'+NS+'}'+key).text=value
        source = self.s.receive_sources(self.c,[{'filename':'Mixed.xml','content':ET.tostring(root)}],'mixed')['items'][0]
        organized = self.s.organize_source(self.c,source['input_id'],self.cycle['id'],source['snapshot_hash'],'Teste')
        payload = self.s.prepare_work_operation(self.c,self.cycle['id'],organized['evidence']['document_ids'][0],policy_id=self.policy['id'])
        payload['fiscal']['ncm']='00000000'
        row = self.save(payload)
        with self.assertRaisesRegex(ValueError,'todos os itens'):
            self.s.preview_operation_tax(self.c,row['operation_id'])

    def test_taxed_reversal_needs_explicit_linked_adjustment_and_effect(self):
        _,_,applied = self.calculate()
        original = self.post(applied['operation'])
        reversal = self.s.reverse_work_operation(self.c,original['operation_id'],self.cycle['id'],'2026-09-20',original['snapshot_hash'],'Estorno sintético','reversal-tax')
        self.post(reversal)
        preview = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertTrue(any('ajuste fiscal explícito' in text for text in preview['snapshot']['blockers']))
        self.rule(key='adjustment',operation='ajuste',model='',effect='credito',base_field='icms_base')
        payload = self.s.prepare_work_operation(self.c,self.cycle['id'],operation='ajuste')
        payload.update(reference='Ajuste tributário sintético',tax_adjustment_of=original['operation_id'],tax_adjustment_reason='Conferência explícita sem inferência legal')
        payload['fiscal'].update(posting_date='2026-09-20',total='2.51',icms_base='100.30')
        payload['entries']=[{'account_id':self.ids[code],'side':side,'date':'2026-09-20','group':'principal','amount':'2.51','memo':'Ajuste sintético'} for code,side in [('1.1.1','D'),('2.1','C')]]
        row = self.save(payload)
        preview = self.s.preview_operation_tax(self.c,row['operation_id'])
        applied = self.s.apply_operation_tax(self.c,row['operation_id'],preview['snapshot_hash'],'tax-adjustment','Ajuste sintético')
        self.post(applied['operation'])
        assessed = self.s.preview_tax_assessment(self.c,self.cycle['id'])
        self.assertEqual(assessed['snapshot']['blockers'],[])
        self.assertEqual(assessed['snapshot']['totals'][0]['saldo_aritmetico'],'0.00')

    def test_global_closure_cannot_bypass_parametrized_assessment(self):
        _,_,applied = self.calculate()
        self.post(applied['operation'])
        self.opening()
        overview = self.s.work_overview(self.c,self.cycle['id'])
        with self.assertRaisesRegex(ValueError,'apuração parametrizada'):
            self.s.transition_work_cycle(self.c,self.cycle['id'],'encerrada',overview['snapshot_hash'],'Teste de bloqueio')


if __name__=='__main__':unittest.main()
