"""Synthetic declared FCP and gross-up profiles; no statutory rates or incidence."""
import copy
import unittest
import test_work_application as fixtures
import test_tax_engine as taxes
import test_tax_items as items
from test_persistence import fake_xml
from src.persistence import AccountingStore
from src.module_closure import CHECKS


class FCPGrossupTests(unittest.TestCase):
    setUp=fixtures.WorkApplicationTests.setUp
    save=fixtures.WorkApplicationTests.save
    post=fixtures.WorkApplicationTests.post
    rule=taxes.TaxEngineTests.rule
    item=items.TaxItemTests.item
    calc=items.TaxItemTests.calc
    apply=items.TaxItemTests.apply

    def fcp(self, code='TESTE', *, mode='declarada', **extra):
        return self.calc('fcp',component_code=code,base_mode=mode,**extra)

    def inside(self, rates=None, *, method='por_dentro', **extra):
        values={'input_basis':'liquido_sem_componentes_do_grupo','denominator_components':rates or [{'component':'ICMS','rate':'18'}],
                'residual_policy':'bloquear',**extra}
        return self.fcp(mode='por_dentro',**values) if method=='fcp' else self.calc('por_dentro',**values)

    def operation(self, declared_items, total='125.00'):
        source=self.s.receive_sources(self.c,[{'filename':'grossup-synthetic.xml','content':fake_xml(total=total,billing=False)}],'grossup-source')['items'][0]
        doc=self.s.organize_source(self.c,source['input_id'],self.cycle['id'],source['snapshot_hash'],'Teste')['evidence']['document_ids'][0]
        payload=self.s.prepare_work_operation(self.c,self.cycle['id'],doc,policy_id=self.policy['id'])
        payload['tax_items']=declared_items
        return self.save(payload)

    def group_rules(self, *, rounding='meio_para_cima', policy='bloquear', reduction='0', own_rate='18', fcp_rate='2'):
        rates=[{'component':'ICMS','rate':own_rate},{'component':'FCP:TESTE','rate':fcp_rate}]
        self.rule(key='own',rate=own_rate,base_field='net_base',rounding=rounding,calculation=self.inside(rates,residual_policy=policy,reduction_percent=reduction))
        self.rule(key='fcp',tax='FCP',rate=fcp_rate,base_field='net_base',rounding=rounding,calculation=self.inside(rates,method='fcp',residual_policy=policy,reduction_percent=reduction))

    def test_fcp_modalities_stay_separate_and_do_not_infer_finance_or_accounting(self):
        self.rule(key='a',tax='FCP',rate='2',base_field='fcp_base',calculation=self.fcp('A'))
        self.rule(key='b',tax='FCP',rate='3',base_field='fcp_base',effect='informativo',calculation=self.fcp('B'))
        operation=self.operation([self.item(total='125.00',taxes=['FCP:A','FCP:B'],values={'total':'125.00','fcp_base':'125.00'})])
        preview,result=self.apply(operation)
        self.assertEqual(preview['snapshot']['profile'],'tributacao-itens-v3')
        self.assertEqual(preview['snapshot']['output'],{})
        self.assertEqual({c['component_key']:c['amount'] for c in result['operation']['payload']['tax_components']},{'FCP:A':'2.50','FCP:B':'3.75'})
        for key in ('entries','finance'):self.assertEqual(result['operation']['payload'][key],operation['payload'][key])
        self.post(result['operation'])
        groups=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']['totals']
        self.assertEqual({g['component_key'] for g in groups},{'FCP:A','FCP:B'})

    def test_grossup_group_trace_reconciles_net_base_components_and_assessment(self):
        self.group_rules()
        operation=self.operation([self.item(total='125.00',taxes=['ICMS','FCP:TESTE'],values={'total':'125.00','net_base':'100.00'})])
        preview,result=self.apply(operation)
        snapshot=preview['snapshot']
        self.assertEqual(snapshot['output'],{'icms_base':'125.00','icms_amount':'22.50'})
        lines={line['component_key']:line for line in snapshot['lines']}
        self.assertEqual(lines['FCP:TESTE']['amount'],'2.50')
        self.assertEqual(lines['ICMS']['steps']['denominator'],'0.8')
        group=snapshot['grossup_groups'][0]
        self.assertEqual(group['grossed_base'],'125.00')
        self.assertEqual(group['rounded_tax_sum'],'25.00')
        self.assertEqual(group['residual'],'0.00')
        self.assertFalse(group['allocation_performed'])
        self.post(result['operation'])
        assessment=self.s.preview_tax_assessment(self.c,self.cycle['id'])['snapshot']
        self.assertEqual(assessment['blockers'],[])
        self.assertEqual(assessment['grossup_groups'][0]['calculation_id'],result['calculation']['id'])

    def test_single_component_grossup_is_explicit_and_repeating_division_is_traced(self):
        self.rule(rate='18',base_field='net_base',calculation=self.inside())
        operation=self.operation([self.item(total='125.00',values={'total':'125.00','net_base':'100.00'})])
        preview,_=self.apply(operation)
        line=preview['snapshot']['lines'][0]
        self.assertEqual(line['base'],'121.95')
        self.assertEqual(line['amount'],'21.95')
        self.assertEqual(line['steps']['arithmetic_precision'],50)
        self.assertTrue(line['steps']['grossed_base_unrounded'].startswith('121.951219512'))

    def test_reduction_is_explicitly_before_grossup(self):
        self.group_rules(reduction='10')
        operation=self.operation([self.item(total='125.00',taxes=['ICMS','FCP:TESTE'],values={'total':'125.00','net_base':'100.00'})])
        preview,_=self.apply(operation)
        group=preview['snapshot']['grossup_groups'][0]
        self.assertEqual(group['grossed_base'],'112.50')
        self.assertEqual(group['rounded_tax_sum'],'22.50')
        self.assertEqual(preview['snapshot']['lines'][0]['steps']['reduced_net_base'],'90.000')

    def test_invalid_or_incomplete_parameters_cannot_be_approved(self):
        invalid=[self.fcp(code=''),self.fcp(mode=''),self.fcp('CBS'),self.calc('por_dentro'),
                 self.inside(input_basis=''),self.inside(residual_policy=''),
                 self.inside(denominator_components=[]),self.inside(denominator_components=[{'component':'ICMS','rate':18}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'100'}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'18'},{'component':'FCP:A','rate':'82'}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'18'},{'component':'ICMS','rate':'1'}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'17'}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'18'},{'component':'CBS','rate':'1'}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'18'},{'component':'FCP:CBS','rate':'1'}]),
                 self.inside(denominator_components=[{'component':'ICMS','rate':'18','formula':'run()'}])]
        for profile in invalid:
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):self.rule(rate='18',tax='FCP' if profile['method']=='fcp' else 'ICMS',base_field='net_base',calculation=profile)
        with self.assertRaisesRegex(ValueError,'net_base'):self.rule(rate='18',calculation=self.inside())
        with self.assertRaises(ValueError):self.rule(tax='FCP',calculation=self.calc())
        with self.assertRaisesRegex(ValueError,'menor que 100'):
            self.rule(rate='100',base_field='net_base',calculation=self.inside([{'component':'ICMS','rate':'100'}]))

    def test_missing_liquid_base_or_fcp_base_blocks_without_inference_from_total(self):
        self.rule(rate='18',base_field='net_base',calculation=self.inside())
        operation=self.operation([self.item(total='125.00')])
        with self.assertRaises(ValueError):self.s.preview_operation_tax(self.c,operation['operation_id'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)
        self.rule(version=1,state='inativa',rate='18',base_field='net_base',calculation=self.inside())
        self.rule(key='fcp',tax='FCP',rate='2',base_field='fcp_base',calculation=self.fcp())
        payload=copy.deepcopy(operation['payload']);payload['tax_items'][0]['taxes']=['FCP:TESTE']
        changed=self.save(payload,operation['operation_id'],operation['version'])
        with self.assertRaises(ValueError):self.s.preview_operation_tax(self.c,changed['operation_id'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)

    def test_missing_or_incoherent_peer_rule_is_blocked(self):
        rates=[{'component':'ICMS','rate':'18'},{'component':'FCP:TESTE','rate':'2'}]
        self.rule(key='own',rate='18',base_field='net_base',calculation=self.inside(rates))
        operation=self.operation([self.item(total='125.00',values={'total':'125.00','net_base':'100.00'})])
        with self.assertRaisesRegex(ValueError,'regra aprovada'):self.s.preview_operation_tax(self.c,operation['operation_id'])
        self.rule(key='fcp',tax='FCP',rate='2',base_field='fcp_base',calculation=self.fcp())
        payload=copy.deepcopy(operation['payload']);payload['tax_items'][0]['taxes'].append('FCP:TESTE');payload['tax_items'][0]['values']['fcp_base']='125.00'
        edited=self.save(payload,operation['operation_id'],operation['version'])
        with self.assertRaisesRegex(ValueError,'compatível'):self.s.preview_operation_tax(self.c,edited['operation_id'])
        self.rule(key='fcp',version=1,tax='FCP',rate='2',base_field='net_base',calculation=self.inside(rates,method='fcp',reduction_percent='5'))
        with self.assertRaisesRegex(ValueError,'coerentes'):self.s.preview_operation_tax(self.c,edited['operation_id'])

    def test_rounding_residual_requires_policy_and_never_changes_other_values(self):
        self.group_rules(rounding='truncar')
        operation=self.operation([self.item(total='125.00',taxes=['ICMS','FCP:TESTE'],values={'total':'125.00','net_base':'100.30'})])
        with self.assertRaisesRegex(ValueError,'arredondamento'):self.s.preview_operation_tax(self.c,operation['operation_id'])
        rates=[{'component':'ICMS','rate':'18'},{'component':'FCP:TESTE','rate':'2'}]
        self.rule(key='own',version=1,rate='18',base_field='net_base',rounding='truncar',calculation=self.inside(rates,residual_policy='preservar_sem_rateio'))
        self.rule(key='fcp',version=1,tax='FCP',rate='2',base_field='net_base',rounding='truncar',calculation=self.inside(rates,method='fcp',residual_policy='preservar_sem_rateio'))
        preview,result=self.apply(operation)
        group=preview['snapshot']['grossup_groups'][0]
        self.assertEqual(group['residual'],'0.01')
        self.assertEqual(group['rounded_tax_sum'],'25.06')
        self.assertEqual(preview['snapshot']['output']['icms_amount'],'22.56')
        self.assertFalse(group['allocation_performed'])
        self.assertEqual(operation['payload']['entries'],result['operation']['payload']['entries'])

    def test_changed_group_rule_or_item_invalidates_memory_and_idempotency_remains(self):
        self.group_rules()
        operation=self.operation([self.item(total='125.00',taxes=['ICMS','FCP:TESTE'],values={'total':'125.00','net_base':'100.00'})])
        preview,result=self.apply(operation)
        duplicate=self.s.apply_operation_tax(self.c,operation['operation_id'],preview['snapshot_hash'],'item-calc','Teste sintético')
        self.assertTrue(duplicate['duplicate'])
        payload=copy.deepcopy(result['operation']['payload']);payload['tax_items'][0]['values']['net_base']='101.00'
        changed=self.save(payload,operation['operation_id'],result['operation']['version'])
        self.assertFalse(changed['validation']['ready'])
        with self.assertRaises(ValueError):self.post(changed)
        restored=self.save(copy.deepcopy(result['operation']['payload']),operation['operation_id'],changed['version'])
        self.assertTrue(restored['validation']['ready'])
        rates=[{'component':'ICMS','rate':'18'},{'component':'FCP:TESTE','rate':'2'}]
        self.rule(key='fcp',version=1,tax='FCP',rate='2',base_field='net_base',calculation=self.inside(rates,method='fcp',residual_policy='preservar_sem_rateio'))
        current=self.s.get_work_operation(self.c,operation['operation_id'])
        self.assertFalse(current['validation']['ready'])

    def test_templates_are_drafts_in_other_company_and_v2_memory_keeps_shape(self):
        rule=self.rule(tax='FCP',rate='2',base_field='fcp_base',calculation=self.fcp())
        template=self.s.save_tax_template(self.c,rule['id'],rule['snapshot_hash'],'FCP sintético',0,'Teste')
        copied=self.s.copy_tax_template(self.other,self.c,template['id'],template['snapshot_hash'],'copy','Cópia','Teste')
        self.assertEqual(copied['state'],'rascunho');self.assertEqual(copied['spec']['validation_reference'],'')
        self.assertEqual(copied['spec']['calculation'],rule['spec']['calculation'])
        self.rule(version=1,tax='FCP',rate='2',state='inativa',base_field='fcp_base',calculation=self.fcp())
        self.rule(key='legacy',rate='2.5',calculation=self.calc())
        operation=self.operation([self.item(total='125.00')]);preview,result=self.apply(operation)
        self.assertEqual(preview['snapshot']['profile'],'tributacao-itens-v2')
        self.assertNotIn('grossup_groups',preview['snapshot'])
        self.assertNotIn('denominator',preview['snapshot']['lines'][0]['steps'])
        with AccountingStore(self.path) as reopened:
            self.assertTrue(reopened.get_work_operation(self.c,operation['operation_id'])['validation']['ready'])
            self.assertEqual(reopened.get_work_operation(self.c,operation['operation_id'])['payload'],result['operation']['payload'])

    def test_fcp_only_posted_assessment_gates_fiscal_closure(self):
        self.rule(tax='FCP',rate='2',base_field='fcp_base',calculation=self.fcp())
        operation=self.operation([self.item(total='125.00',taxes=['FCP:TESTE'],values={'total':'125.00','fcp_base':'125.00'})])
        _,result=self.apply(operation);self.post(result['operation'])
        state=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.assertTrue(any('apuração parametrizada' in b for b in state['blockers']))
        preview=self.s.preview_tax_assessment(self.c,self.cycle['id'])
        assessment=self.s.create_tax_assessment(self.c,self.cycle['id'],preview['snapshot_hash'],'assessment-fcp','Teste')
        self.s.validate_tax_assessment(self.c,self.cycle['id'],assessment['id'],assessment['snapshot_hash'],'Teste',True)
        state=self.s.module_period_overview(self.c,self.cycle['id'],'fiscal')
        self.s.transition_module_period(self.c,self.cycle['id'],'fiscal','encerrada',state['snapshot_hash'],'Teste',{k:True for k in CHECKS['fiscal']},'Conferência sintética')
        with self.assertRaisesRegex(ValueError,'encerrado'):self.rule(version=1,tax='FCP',rate='3',base_field='fcp_base',calculation=self.fcp())

    def test_near_singular_result_outside_supported_money_range_is_blocked(self):
        self.rule(rate='99.999999',base_field='net_base',calculation=self.inside([{'component':'ICMS','rate':'99.999999'}],residual_policy='preservar_sem_rateio'))
        operation=self.operation([self.item(total='125.00',values={'total':'125.00','net_base':'999999999999999'})])
        with self.assertRaises(ValueError):self.s.preview_operation_tax(self.c,operation['operation_id'])
        self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM tax_calculations').fetchone()[0],0)

    def test_group_model_in_another_company_does_not_resolve_peers_from_source(self):
        self.group_rules()
        original=next(r for r in self.s.tax_rules(self.c) if r['rule_key']=='own')
        template=self.s.save_tax_template(self.c,original['id'],original['snapshot_hash'],'Grupo sintético',0,'Teste')
        copied=self.s.copy_tax_template(self.other,self.c,template['id'],template['snapshot_hash'],'own','Cópia sintética','Teste')
        spec=copy.deepcopy(copied['spec']);spec['validation_reference']='Revisão do destino'
        self.s.save_tax_rule(self.other,'own','Cópia sintética',spec,'aprovada',1,'Teste')
        cycle=self.s.save_work_cycle(self.other,'2026-08','2026-09',None,'Teste')
        payload=self.s.prepare_work_operation(self.other,cycle['id'],operation='entrada')
        payload.update(reference='Grupo de outra empresa',tax_items=[self.item(total='125.00',values={'total':'125.00','net_base':'100.00'})])
        payload['fiscal'].update(posting_date='2026-09-15',issued_date='2026-09-15',model='55',number='1',total='125.00')
        row=self.s.save_work_operation(self.other,cycle['id'],payload,'Teste','other-company-operation')
        with self.assertRaisesRegex(ValueError,'regra aprovada'):self.s.preview_operation_tax(self.other,row['operation_id'])
        self.assertEqual(self.s._tax_rule(self.c,original['id'])['spec'],original['spec'])


if __name__=='__main__':unittest.main()
