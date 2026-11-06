"""Explicit company policies and arithmetic; no statutory rates or tax treatment.

Rules require the operator to provide scope, rate, basis, effect and rounding.
CBS/IBS remain outside this engine; special components use declared profiles only.
"""
import copy
import json
import re
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext
import calendar
from .tax_items import SPECIAL_TAXES, ITEM_BASES, ITEM_MEMORY_PROFILES, calculation_spec, component_key, validate_items, calculate_item_group
from .tax_grossup import is_grossup

from .accounting_store import digest, dump, identifier

TAXES = {'ICMS': 'icms', 'ISS': 'iss', 'PIS': 'pis', 'COFINS': 'cofins'}
ROUNDINGS = {'meio_para_cima': ROUND_HALF_UP, 'truncar': ROUND_DOWN}
BASES = {'total', 'icms_base', 'iss_base', 'pis_base', 'cofins_base'}
SPEC_FIELDS = {'tax', 'rate', 'base_field', 'effect', 'operation', 'model', 'cfop', 'ncm', 'service_code', 'revenue_code',
               'valid_from', 'valid_to', 'rounding', 'validation_reference'}
EXTENDED_FIELDS = {'calculation', 'item_treatment'}
TAX_SCHEMA = """
CREATE TABLE IF NOT EXISTS tax_rule_versions (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 rule_key TEXT NOT NULL, label TEXT NOT NULL, version INTEGER NOT NULL, state TEXT NOT NULL,
 spec TEXT NOT NULL, source TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,rule_key,version));
CREATE TABLE IF NOT EXISTS tax_template_versions (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 label TEXT NOT NULL, version INTEGER NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,label,version));
CREATE TABLE IF NOT EXISTS tax_calculations (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), operation_id INTEGER NOT NULL REFERENCES work_operations(id),
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS tax_assessment_versions (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), version INTEGER NOT NULL,
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, state TEXT NOT NULL,
 snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL, actor TEXT NOT NULL,
 reason TEXT NOT NULL, created_at TEXT NOT NULL, review_actor TEXT, review_reason TEXT, reviewed_at TEXT,
 UNIQUE(company_id,request_key), UNIQUE(cycle_id,version));
"""


def decimal_text(value, *, rate=False):
    pattern = r'(?:0|[1-9][0-9]{0,14})(?:\.[0-9]{1,6})?' if rate else r'(?:0|[1-9][0-9]{0,14})(?:\.[0-9]{1,2})?'
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError('Informe texto decimal não negativo; floats e valores presumidos não são aceitos')
    result = Decimal(value)
    if rate and result > 100:
        raise ValueError('O motor percentual aceita taxa explícita entre 0 e 100')
    return result


def rule_spec(data):
    from .persistence import _text
    if not isinstance(data, dict) or set(data) - (SPEC_FIELDS | EXTENDED_FIELDS):
        raise ValueError('Campos desconhecidos na regra tributária')
    spec = {key: _text(data.get(key, ''), key, 1000 if key == 'validation_reference' else 100, False) for key in SPEC_FIELDS}
    issues = []
    for key, allowed in [('tax', set(TAXES) | SPECIAL_TAXES), ('base_field', ITEM_BASES if 'calculation' in data else BASES), ('effect', {'debito','credito','informativo'}),
                         ('operation', {'entrada','saida','servico_tomado','servico_prestado','ajuste'}), ('rounding', ROUNDINGS)]:
        if spec[key] not in allowed:
            issues.append('Defina ' + key)
    try:
        decimal_text(spec['rate'], rate=True)
    except ValueError as error:
        issues.append(str(error))
    for key in ('valid_from', 'valid_to'):
        value = spec[key]
        try:
            if not value and key == 'valid_to':
                continue
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) or date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except ValueError:
            issues.append('Defina ' + key + ' em AAAA-MM-DD')
    if spec['valid_from'] and spec['valid_to'] and spec['valid_from'] > spec['valid_to']:
        issues.append('Vigência invertida')
    if spec['model'] and spec['model'] not in {'55','65','SERVICO'}:
        issues.append('Modelo não suportado')
    if spec['cfop'] and not re.fullmatch(r'[1-7][0-9]{3}', spec['cfop']):
        issues.append('CFOP deve ter quatro dígitos; enquadramento não verificado')
    if not spec['validation_reference']:
        issues.append('Informe referência da validação pelo responsável')
    if 'item_treatment' in data:
        spec['item_treatment'] = _text(data['item_treatment'],'Tratamento declarado do item',100,False)
    if 'calculation' in data:
        spec['calculation'] = copy.deepcopy(data['calculation'])
        try:
            calculation_spec(spec['calculation'],spec['tax'],spec['rate'])
            if is_grossup(spec['calculation']) and spec['base_field']!='net_base':
                raise ValueError('Cálculo por dentro exige o campo net_base, líquido sem os componentes declarados; não presume base a partir do total')
        except ValueError as error:
            issues.append(str(error))
    elif spec['tax'] in SPECIAL_TAXES or spec.get('item_treatment'):
        issues.append('Componente especial ou tratamento de item exige perfil de cálculo por item')
    return spec, issues


class TaxEngineMixin:
    def _assert_tax_validity_open(self, company_id, valid_from, valid_to):
        for cycle in self.work_cycles(company_id):
            year, month = map(int,cycle['competence'].split('-'))
            last = f'{year:04d}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}'
            if valid_from<=last and (not valid_to or valid_to>=cycle['competence']+'-01'):
                if cycle['state']!='aberta':
                    raise ValueError('Parametrização alcança competência encerrada; reabra antes de alterar')
                self.assert_module_period_open(company_id,cycle['competence'],{'fiscal'})

    def _tax_rule(self, company_id, rule_id):
        self._company(identifier(company_id))
        row = self.db.execute('SELECT * FROM tax_rule_versions WHERE company_id=? AND id=?', (company_id, identifier(rule_id))).fetchone()
        if not row:
            raise ValueError('Regra não pertence à empresa')
        result = dict(row)
        result['spec'], result['source'] = json.loads(result['spec']), json.loads(result['source'])
        proof = {key: result[key] for key in ('rule_key','label','version','state','spec','source')}
        if digest(proof) != result['snapshot_hash']:
            raise ValueError('Regra tributária alterada')
        result['issues'] = rule_spec(result['spec'])[1]
        return result

    def tax_rules(self, company_id):
        self._company(identifier(company_id))
        return [self._tax_rule(company_id, r['id']) for r in self.db.execute('SELECT id FROM tax_rule_versions WHERE company_id=? ORDER BY id DESC', (company_id,))]

    def _tax_rule_current(self, company_id, key):
        return self.db.execute('SELECT * FROM tax_rule_versions WHERE company_id=? AND rule_key=? ORDER BY version DESC LIMIT 1', (company_id,key)).fetchone()

    def save_tax_rule(self, company_id, key, label, data, state, expected_version, reason, *, source=None, _in_transaction=False):
        from .persistence import _text
        from .company_profiles import expected_version as version_check
        key, label = _text(key,'Identificador da regra',80), _text(label,'Nome da regra',200)
        reason = _text(reason,'Motivo',2000)
        version_check(expected_version)
        spec, issues = rule_spec(data)
        if state not in {'rascunho','aprovada','inativa'} or (state != 'rascunho' and issues):
            raise ValueError('; '.join(issues) or 'Estado da regra inválido')
        with self._import_transaction(_in_transaction):
            if not _in_transaction:
                self.db.execute('BEGIN IMMEDIATE')
            self._company(identifier(company_id))
            previous = self._tax_rule_current(company_id,key)
            if expected_version != (previous['version'] if previous else 0):
                raise ValueError('Regra alterada; recarregue antes de salvar')
            if state != 'rascunho':
                self._assert_tax_validity_open(company_id,spec['valid_from'],spec['valid_to'])
            if state == 'aprovada':
                self._tax_code_references(company_id,spec,spec['valid_from'])
            origin = source if source is not None else json.loads(previous['source']) if previous else {}
            version = expected_version + 1
            proof = {'rule_key':key,'label':label,'version':version,'state':state,'spec':spec,'source':origin}
            rule_id = self.db.execute('INSERT INTO tax_rule_versions(company_id,rule_key,label,version,state,spec,source,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (company_id,key,label,version,state,dump(spec),dump(origin),digest(proof),self.actor,reason,self._now())).lastrowid
            self._audit(company_id,'regra_tributaria_versionada',{'rule_id':rule_id,'rule_key':key,'version':version,'state':state,'reason':reason})
        return self._tax_rule(company_id,rule_id)

    def _matching_tax_rules(self, company_id, fiscal, *, scope='documento'):
        day = fiscal.get('posting_date','')
        if not isinstance(day,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):
            raise ValueError('Informe data de escrituração para selecionar vigência das regras')
        date.fromisoformat(day)
        latest = {}
        for rule in self.tax_rules(company_id):
            spec = rule['spec']
            if rule['rule_key'] not in latest and rule['state'] != 'rascunho' and spec['valid_from'] <= day:
                latest[rule['rule_key']] = rule
        matches = []
        for rule in latest.values():
            spec = rule['spec']
            if rule['state'] != 'aprovada' or (spec['valid_to'] and day > spec['valid_to']):
                continue
            if ('item' if 'calculation' in spec else 'documento') != scope:
                continue
            if spec['operation'] != fiscal.get('operation') or (spec['model'] and spec['model'] != fiscal.get('model')) or any(spec[field] and spec[field] != fiscal.get(field) for field in ('cfop','ncm','service_code')):
                continue
            if spec.get('item_treatment') and spec['item_treatment'] != fiscal.get('treatment'):
                continue
            rule['catalog_references'] = self._tax_code_references(company_id,spec,day)
            matches.append(rule)
        if len({component_key(r['spec']) for r in matches}) != len(matches):
            raise ValueError('Mais de uma regra aplicável ao mesmo tributo; resolva a ambiguidade')
        return sorted(matches,key=lambda r:component_key(r['spec']))

    def _tax_code_references(self, company_id, spec, day):
        from .tax_catalog import CODE_FIELDS
        return {field:self.resolve_tax_code(company_id,kind,spec[field],day) for field,kind in CODE_FIELDS.items() if spec.get(field)}

    def _tax_preview(self, company_id, revision):
        payload=revision['payload']
        self.assert_xml_item_evidence(company_id,payload)
        fiscal = copy.deepcopy(payload.get('fiscal') or {})
        if 'tax_items' in revision['payload']:
            return self._tax_items_preview(company_id,revision,fiscal)
        rules = self._matching_tax_rules(company_id,fiscal)
        if not rules:
            raise ValueError('Nenhuma regra tributária aprovada e aplicável; nenhum valor foi presumido')
        lines, output = [], {}
        with localcontext() as context:
            context.prec = 40
            for rule in rules:
                spec = rule['spec']
                if spec['ncm'] and revision['payload'].get('document_id'):
                    source = self._work_source(company_id,revision['payload']['document_id'])
                    observation = next((o for o in source['observations'] if o['id']==revision['payload'].get('observation_id')),None)
                    raw = observation.get('raw') if observation else None
                    products = raw.get('products',[]) if isinstance(raw,dict) else []
                    if products and any(not isinstance(p,dict) or not isinstance(p.get('data',p),dict) or p.get('data',p).get('ncm')!=spec['ncm'] for p in products):
                        raise ValueError('NCM da regra não representa todos os itens observados; cálculo tributário por item ainda não suportado')
                base = decimal_text(fiscal.get(spec['base_field']))
                rate = decimal_text(spec['rate'],rate=True)
                raw = base * rate / Decimal('100')
                amount = raw.quantize(Decimal('.01'),rounding=ROUNDINGS[spec['rounding']])
                prefix = TAXES[spec['tax']]
                output[prefix+'_base'], output[prefix+'_amount'] = format(base,'.2f'), format(amount,'.2f')
                lines.append({'tax':spec['tax'],'base_field':spec['base_field'],'base':format(base,'.2f'),'rate':spec['rate'],
                              'formula':'base * rate / 100','unrounded':format(raw,'f'),'amount':format(amount,'.2f'),
                              'effect':spec['effect'],'rounding':spec['rounding'],'revenue_code':spec['revenue_code'],'rule':rule})
        snapshot = {'profile':'tributacao-parametrizada-v2' if 'xml_item_evidence' in payload else 'tributacao-parametrizada-v1','company_id':identifier(company_id), 'cycle_id':revision['cycle_id'],
                    'operation_id':revision['operation_id'],'input_version':revision['version'],'input_hash':revision['snapshot_hash'],
                    'input_fiscal':fiscal,'document_id':revision['payload'].get('document_id'),'source_hash':revision['payload'].get('source_hash'),
                    'reference':revision['payload'].get('reference'),
                    'tax_adjustment_of':revision['payload'].get('tax_adjustment_of'),
                    'tax_adjustment_reason':revision['payload'].get('tax_adjustment_reason'),'lines':lines,'output':output}
        if 'xml_item_evidence' in payload:snapshot['xml_item_evidence']=copy.deepcopy(payload['xml_item_evidence'])
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def _tax_items_preview(self, company_id, revision, fiscal):
        payload = revision['payload']
        products = []
        if payload.get('document_id'):
            source = self._work_source(company_id,payload['document_id'])
            observation = next((o for o in source['observations'] if o['id']==payload.get('observation_id')),None)
            if not observation or observation['file_status']=='excluido' or source['source_hash']!=payload.get('source_hash'):
                raise ValueError('Fonte dos itens ausente ou alterada; confira novamente')
            products = observation['raw'].get('products',[])
        items = copy.deepcopy(payload['tax_items'])
        validate_items(items,fiscal,products)
        if self._matching_tax_rules(company_id,fiscal):
            raise ValueError('Há regras documentais aplicáveis; adapte explicitamente para itens antes de combinar tratamentos')
        lines, output, components, grossup_groups = [], {}, {}, []
        with localcontext() as context:
            context.prec = 50
            for item in items:
                facts = {**fiscal,**{k:item[k] for k in ('cfop','ncm','service_code','treatment')}}
                rules = self._matching_tax_rules(company_id,facts,scope='item')
                if {component_key(r['spec']) for r in rules} != set(item['taxes']):
                    raise ValueError('Item '+item['id']+': componentes declarados não correspondem exatamente às regras aprovadas aplicáveis')
                try:
                    item_lines,item_groups=calculate_item_group(rules,item)
                except ValueError as error:
                    raise ValueError('Item '+item['id']+': '+str(error)) from None
                grossup_groups.extend(item_groups)
                for line in item_lines:
                    lines.append(line)
                    key = line['component_key']
                    group = components.setdefault(key,{'component_key':key,'tax':line['tax'],'base':Decimal(0),'amount':Decimal(0)})
                    group['base'] += Decimal(line['base'])
                    group['amount'] += Decimal(line['amount'])
            for key,group in components.items():
                group.update(base=format(group['base'],'.2f'),amount=format(group['amount'],'.2f'))
                decimal_text(group['base'])
                decimal_text(group['amount'])
                if key in TAXES:
                    output[TAXES[key]+'_base'],output[TAXES[key]+'_amount']=group['base'],group['amount']
        # Values not covered by this item memory cannot silently survive a prior document calculation.
        if any(fiscal.get(prefix+'_amount') not in (None,'') and tax not in components for tax,prefix in TAXES.items()):
            raise ValueError('Há valores documentais sem cobertura nos itens; reconcilie explicitamente antes de calcular')
        extended=any(line['parameters']['method'] in {'fcp','por_dentro'} for line in lines)
        snapshot = {'profile':'tributacao-itens-v4' if 'xml_item_evidence' in payload else 'tributacao-itens-v3' if extended else 'tributacao-itens-v2','company_id':identifier(company_id),'cycle_id':revision['cycle_id'],
                    'operation_id':revision['operation_id'],'input_version':revision['version'],'input_hash':revision['snapshot_hash'],
                    'input_fiscal':fiscal,'input_items':items,'document_id':payload.get('document_id'),
                    'source_hash':payload.get('source_hash'),'observation_id':payload.get('observation_id'),
                    'reference':payload.get('reference'),'tax_adjustment_of':payload.get('tax_adjustment_of'),
                    'tax_adjustment_reason':payload.get('tax_adjustment_reason'),'lines':lines,'output':output,
                    'component_output':sorted(components.values(),key=lambda g:g['component_key']),
                    'reconciliation':{'source_locators':[p['locator'] for p in products],
                                      'item_values_origin':('Valores atuais e rateios declarados; evidência XML observada separada, cópias propostas sujeitas à conferência' if 'xml_item_evidence' in payload else 'Valores e rateios declarados; não extraídos automaticamente dos produtos XML'),
                                      'rounding':'Base em centavos antes da taxa; tributo arredondado por item antes da soma'}}
        if extended:snapshot['grossup_groups']=grossup_groups
        if 'xml_item_evidence' in payload:snapshot['xml_item_evidence']=copy.deepcopy(payload['xml_item_evidence'])
        return {'snapshot':snapshot,'snapshot_hash':digest(snapshot)}

    def preview_operation_tax(self, company_id, operation_id):
        revision = self._work_revision(company_id,operation_id)
        if revision['state'] not in {'rascunho','revisado'}:
            raise ValueError('Cálculo exige operação salva ainda não escriturada')
        return self._tax_preview(company_id,revision)

    def _tax_calculation(self, company_id, calculation_id):
        row = self.db.execute('SELECT * FROM tax_calculations WHERE company_id=? AND id=?',(company_id,identifier(calculation_id))).fetchone()
        if not row:
            raise ValueError('Memória de cálculo não pertence à empresa')
        result = dict(row)
        result['snapshot'] = json.loads(result['snapshot'])
        if digest(result['snapshot']) != result['snapshot_hash']:
            raise ValueError('Memória de cálculo alterada')
        return result

    def apply_operation_tax(self, company_id, operation_id, expected_hash, request_key, reason, *, _in_transaction=False):
        from .persistence import _text
        reason, request_key = _text(reason,'Motivo do cálculo',2000), _text(request_key,'Tentativa',80)
        request_hash = digest([identifier(operation_id),expected_hash,reason])
        if _in_transaction and not self.db.in_transaction:
            raise ValueError('Aplicação tributária interna exige transação ativa')
        with self._import_transaction(_in_transaction):
            if not _in_transaction:self.db.execute('BEGIN IMMEDIATE')
            previous = self.db.execute('SELECT id,request_hash FROM tax_calculations WHERE company_id=? AND request_key=?',(company_id,request_key)).fetchone()
            if previous:
                if previous['request_hash'] != request_hash:
                    raise ValueError('Tentativa tributária já usada com outro conteúdo')
                return {'calculation':self._tax_calculation(company_id,previous['id']),'operation':self.get_work_operation(company_id,operation_id),'duplicate':True}
            revision = self._work_revision(company_id,operation_id)
            if revision['state'] not in {'rascunho','revisado'}:
                raise ValueError('Operação efetivada não pode ser recalculada')
            cycle = self._work_cycle(company_id,revision['cycle_id'])
            self.assert_operation_modules_open(company_id,cycle,revision['payload'])
            preview = self._tax_preview(company_id,revision)
            if expected_hash != preview['snapshot_hash']:
                raise ValueError('Prévia tributária alterada; calcule novamente')
            calc_id = self.db.execute('INSERT INTO tax_calculations(company_id,cycle_id,operation_id,request_key,request_hash,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (company_id,cycle['id'],operation_id,request_key,request_hash,dump(preview['snapshot']),expected_hash,self.actor,reason,self._now())).lastrowid
            payload = copy.deepcopy(revision['payload'])
            payload['fiscal'].update(preview['snapshot']['output'])
            if preview['snapshot'].get('profile') in ITEM_MEMORY_PROFILES:
                payload['tax_components'] = copy.deepcopy(preview['snapshot']['component_output'])
            else:
                payload.pop('tax_components',None)
            payload['tax_calculation'] = {'id':calc_id,'snapshot_hash':expected_hash,'memory':preview['snapshot']}
            result = self.save_work_operation(company_id,cycle['id'],payload,reason,'taxcalc:'+request_key,operation_id,revision['version'],_in_transaction=True)
            self._audit(company_id,'tributacao_aplicada_em_rascunho',{'calculation_id':calc_id,'operation_id':operation_id,'reason':reason})
        return {'calculation':self._tax_calculation(company_id,calc_id),'operation':result,'duplicate':False}

    def tax_operation_issues(self, company_id, revision):
        payload = revision['payload']
        proof = payload.get('tax_calculation')
        try:
            self.assert_xml_item_evidence(company_id,payload,current=revision['state']!='escriturado')
            if payload.get('tax_adjustment_of'):
                from .persistence import _text
                original = self._work_revision(company_id,payload['tax_adjustment_of'])
                if original['state']!='escriturado' or payload.get('fiscal',{}).get('operation')!='ajuste' or original['operation_id']==revision['operation_id']:
                    raise ValueError('Ajuste tributário exige origem escriturada da mesma empresa e natureza ajuste')
                _text(payload.get('tax_adjustment_reason'),'Motivo do ajuste tributário',2000)
            if not proof:
                if 'tax_items' in payload or 'tax_components' in payload:
                    raise ValueError('Itens e componentes tributários exigem cálculo com memória antes de conferir')
                return []  # Historical/manual tax facts retain their own declared provenance.
            if not isinstance(proof,dict):
                raise ValueError('Referência da memória de cálculo inválida')
            record = self._tax_calculation(company_id,proof.get('id'))
            memory = record['snapshot']
            if record['operation_id'] != revision['operation_id'] or record['cycle_id'] != revision['cycle_id'] or proof != {'id':record['id'],'snapshot_hash':record['snapshot_hash'],'memory':memory}:
                raise ValueError('Memória de cálculo não corresponde à operação')
            expected_fiscal = {**memory['input_fiscal'],**memory['output']}
            if payload.get('fiscal') != expected_fiscal or any(payload.get(k) != memory.get(k) for k in ('document_id','source_hash','reference','tax_adjustment_of','tax_adjustment_reason','xml_item_evidence')):
                raise ValueError('Dados fiscais alterados depois do cálculo; gere nova memória')
            item_mode = memory.get('profile') in ITEM_MEMORY_PROFILES
            if item_mode:
                if payload.get('tax_items')!=memory['input_items'] or payload.get('tax_components')!=memory['component_output'] or payload.get('observation_id')!=memory.get('observation_id'):
                    raise ValueError('Itens ou componentes alterados depois do cálculo; gere nova memória')
            elif 'tax_items' in payload or 'tax_components' in payload:
                raise ValueError('A memória documental não cobre itens e componentes adicionais')
            if revision['state'] != 'escriturado':
                if item_mode:
                    original = {**revision,'version':memory['input_version'],'snapshot_hash':memory['input_hash'],
                                'payload':{**payload,'fiscal':memory['input_fiscal']}}
                    if self._tax_preview(company_id,original)['snapshot_hash'] != record['snapshot_hash']:
                        raise ValueError('Regras ou itens aplicáveis mudaram; recalcule antes de conferir')
                else:
                    current = self._matching_tax_rules(company_id,memory['input_fiscal'])
                    if [digest(r) for r in current] != [digest(line['rule']) for line in memory['lines']]:
                        raise ValueError('Regras aplicáveis mudaram; recalcule antes de conferir')
            return []
        except (ValueError,KeyError,TypeError) as error:
            return [{'field':'tax_calculation','message':str(error),'severity':'bloqueio'}]

    def tax_templates(self, company_id):
        self._company(identifier(company_id))
        results = []
        for row in self.db.execute('SELECT * FROM tax_template_versions WHERE company_id=? ORDER BY id DESC',(company_id,)):
            value = dict(row)
            value['snapshot'] = json.loads(value['snapshot'])
            if digest(value['snapshot']) != value['snapshot_hash']:
                raise ValueError('Modelo tributário alterado')
            results.append(value)
        return results

    def save_tax_template(self, company_id, rule_id, rule_hash, label, expected_version, reason):
        from .persistence import _text
        from .company_profiles import expected_version as version_check
        label, reason = _text(label,'Nome do modelo',200), _text(reason,'Motivo do modelo',2000)
        version_check(expected_version)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rule = self._tax_rule(company_id,rule_id)
            if rule['snapshot_hash']!=rule_hash or rule['state']!='aprovada':
                raise ValueError('Selecione uma versão aprovada e atual da regra para o modelo')
            current = self.db.execute('SELECT version FROM tax_template_versions WHERE company_id=? AND label=? ORDER BY version DESC LIMIT 1',(company_id,label)).fetchone()
            if expected_version!=(current['version'] if current else 0):
                raise ValueError('Modelo alterado; recarregue a versão')
            snapshot = {'source_company_id':identifier(company_id),'rule':rule,'label':label,'version':expected_version+1}
            template_id = self.db.execute('INSERT INTO tax_template_versions(company_id,label,version,snapshot,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (company_id,label,expected_version+1,dump(snapshot),digest(snapshot),self.actor,reason,self._now())).lastrowid
            self._audit(company_id,'modelo_tributario_versionado',{'template_id':template_id,'rule_id':rule_id,'reason':reason})
        return next(t for t in self.tax_templates(company_id) if t['id']==template_id)

    def copy_tax_template(self, company_id, source_company_id, template_id, template_hash, key, label, reason):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            self._company(identifier(company_id))
            template = next((t for t in self.tax_templates(source_company_id) if t['id']==identifier(template_id)),None)
            if not template or template['snapshot_hash']!=template_hash:
                raise ValueError('Modelo de origem não disponível ou alterado')
            origin = {'source_company_id':identifier(source_company_id),'template_id':template['id'],
                      'template_version':template['version'],'template_hash':template_hash}
            spec = copy.deepcopy(template['snapshot']['rule']['spec'])
            spec['validation_reference'] = ''
            result = self.save_tax_rule(company_id,key,label,spec,'rascunho',0,reason,source=origin,_in_transaction=True)
            self._audit(company_id,'modelo_tributario_copiado',{'rule_id':result['id'],'source':origin})
        return result

    def tax_configuration(self, company_id):
        from .tax_sources import CATALOG_SOURCES
        page = self.tax_code_page(company_id)
        structural = []
        for label, basis in [('Percentual sobre total declarado','total'),('Percentual sobre base ICMS declarada','icms_base'),('Percentual sobre base ISS declarada','iss_base')]:
            spec = {key:'' for key in SPEC_FIELDS}
            spec['base_field'] = basis
            structural.append({'label':label,'spec':spec,'state':'rascunho','requires_validation':True})
        for label,method,tax,extra in [
            ('Percentual por item','percentual','',{}),
            ('ST por item com margem e dedução declaradas','st','ICMS_ST',{'margin_percent':'','deduction_field':'st_deduction','negative_policy':''}),
            ('DIFAL por diferença de taxas declaradas','difal','ICMS_DIFAL',{'origin_rate':'','negative_policy':''}),
            ('Retenção por item e tributo declarado','retencao','RETENCAO',{'component_code':''})]:
            spec = {key:'' for key in SPEC_FIELDS}
            spec.update(tax=tax,item_treatment='',calculation={'scope':'item','method':method,'reduction_percent':'','base_rounding':'',**extra})
            structural.append({'label':label,'spec':spec,'state':'rascunho','requires_validation':True})
        for label,method,tax,basis,extra in [
            ('FCP por item com modalidade e base declaradas','fcp','FCP','',{'component_code':'','base_mode':''}),
            ('Por dentro com grupo e base líquida declarados','por_dentro','','net_base',{'input_basis':'','denominator_components':[],'residual_policy':''})]:
            spec={key:'' for key in SPEC_FIELDS}
            spec.update(tax=tax,base_field=basis,item_treatment='',calculation={'scope':'item','method':method,'reduction_percent':'','base_rounding':'',**extra})
            structural.append({'label':label,'spec':spec,'state':'rascunho','requires_validation':True})
        return {'rules':self.tax_rules(company_id),'templates':self.tax_templates(company_id),
                'catalog':page['items'],'catalog_page':{key:value for key,value in page.items() if key!='items'},'structural_models':structural,
                'supported_taxes':list(TAXES)+sorted(SPECIAL_TAXES),'item_base_fields':sorted(ITEM_BASES),
                'catalog_sources':CATALOG_SOURCES,'legal_defaults_loaded':False}
