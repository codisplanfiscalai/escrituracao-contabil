"""Declared item arithmetic profiles; no legal classification or official rates."""
import copy
import re
from decimal import Decimal, localcontext
from .tax_grossup import GROSSUP_FIELDS, is_grossup, validate_grossup_parameters, validate_grossup_group, grossup_steps, reconcile_grossup_groups

SPECIAL_TAXES = {'ICMS_ST', 'ICMS_DIFAL', 'RETENCAO', 'FCP'}
ITEM_BASES = {'total', 'icms_base', 'iss_base', 'pis_base', 'cofins_base', 'st_base', 'difal_base', 'retention_base','fcp_base','net_base'}
METHOD_TAX = {'st': 'ICMS_ST', 'difal': 'ICMS_DIFAL', 'retencao': 'RETENCAO','fcp':'FCP'}
CALC_FIELDS = {'scope', 'method', 'reduction_percent', 'base_rounding', 'margin_percent',
               'origin_rate', 'deduction_field', 'negative_policy', 'component_code','base_mode'} | GROSSUP_FIELDS
ITEM_MEMORY_PROFILES = {'tributacao-itens-v2','tributacao-itens-v3'}


def component_key(spec):
    return spec['tax'] + (':' + spec['calculation']['component_code'] if spec['tax'] in {'RETENCAO','FCP'} else '')


def calculation_spec(value, tax, rate):
    from .tax_engine import decimal_text
    if not isinstance(value, dict) or set(value) - CALC_FIELDS:
        raise ValueError('Perfil de cálculo por item inválido')
    if any(not isinstance(parameter,str) or len(parameter)>100 for key,parameter in value.items() if key!='denominator_components'):
        raise ValueError('Parâmetros do perfil devem ser textos explícitos de até 100 caracteres')
    required = {'scope', 'method', 'reduction_percent', 'base_rounding'}
    method = value.get('method')
    if method == 'st':
        required |= {'margin_percent', 'deduction_field', 'negative_policy'}
    elif method == 'difal':
        required |= {'origin_rate', 'negative_policy'}
    elif method == 'retencao':
        required.add('component_code')
    elif method == 'fcp':
        required |= {'component_code','base_mode'}
        if value.get('base_mode') not in {'declarada','por_dentro'}:
            raise ValueError('Declare se a base FCP é informada ou recomposta por dentro')
    elif method == 'por_dentro':
        pass
    elif method != 'percentual':
        raise ValueError('Selecione o método de cálculo por item')
    if is_grossup(value):required |= GROSSUP_FIELDS
    if set(value) != required or value.get('scope') != 'item' or value.get('base_rounding') != 'centavos_antes_da_taxa':
        raise ValueError('Preencha somente os parâmetros exigidos pelo perfil e declare o arredondamento da base')
    if METHOD_TAX.get(method, tax) != tax or (tax in SPECIAL_TAXES and METHOD_TAX.get(method) != tax):
        raise ValueError('Método incompatível com o componente tributário')
    decimal_text(value['reduction_percent'], rate=True)
    if method == 'st':
        if not isinstance(value['margin_percent'],str) or not re.fullmatch(r'(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,6})?',value['margin_percent']):
            raise ValueError('Margem deve ser texto decimal com até seis casas')
        margin = Decimal(value['margin_percent'])
        if margin > 1000:
            raise ValueError('Margem suportada: 0 a 1000 por cento')
        if value['deduction_field'] != 'st_deduction':
            raise ValueError('Informe a dedução própria em st_deduction de cada item, inclusive zero')
    if method == 'difal':
        decimal_text(value['origin_rate'], rate=True)
    if method in {'st', 'difal'} and value['negative_policy'] not in {'bloquear', 'zerar'}:
        raise ValueError('Declare o tratamento de resultado negativo: bloquear ou zerar')
    if method in {'retencao','fcp'} and (not isinstance(value['component_code'], str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,29}', value['component_code'])):
        raise ValueError('Identifique explicitamente o tributo retido ou a modalidade FCP, sem enquadramento automático')
    if method in {'retencao','fcp'} and {'CBS','IBS'} & set(value['component_code'].split('_')):
        raise ValueError('CBS/IBS permanecem fora do cálculo, inclusive por componente declarado')
    if is_grossup(value):
        key=tax+(':'+value['component_code'] if tax=='FCP' else '')
        validate_grossup_parameters(value,key,rate)
    return copy.deepcopy(value)


def validate_items(items, fiscal, products):
    from .persistence import _text
    from .tax_engine import decimal_text, TAXES
    if not isinstance(items, list) or not 1 <= len(items) <= 200:
        raise ValueError('Informe de 1 a 200 itens tributários')
    identifiers, locators, total = set(), set(), Decimal(0)
    observed = {p['locator']: p['data'] for p in products}
    for item in items:
        if not isinstance(item, dict) or set(item) != {'id', 'description', 'cfop', 'ncm', 'service_code', 'treatment', 'source_reference', 'source_locator', 'taxes', 'no_tax_reason', 'values'}:
            raise ValueError('Item exige identificação, classificações, origem, componentes e valores explícitos')
        key = _text(item['id'], 'Identificador do item', 80)
        if key in identifiers:
            raise ValueError('Identificador de item repetido')
        identifiers.add(key)
        for field in ('description', 'source_reference'):
            _text(item[field], field, 1000)
        for field, limit in [('treatment',100), ('no_tax_reason',1000), ('source_locator',200), ('cfop',4), ('ncm',8), ('service_code',30)]:
            _text(item[field], field, limit, False)
        if item['cfop'] and not re.fullmatch(r'[1-7][0-9]{3}',item['cfop']):
            raise ValueError('CFOP do item exige quatro dígitos')
        if item['ncm'] and not re.fullmatch(r'[0-9]{8}',item['ncm']):
            raise ValueError('NCM do item exige oito dígitos')
        taxes = item['taxes']
        if not isinstance(taxes,list) or any(not isinstance(t,str) for t in taxes) or len(taxes)!=len(set(taxes)) or len(taxes)>20:
            raise ValueError('Componentes do item devem ser uma lista sem repetições, até 20')
        if any(t not in set(TAXES) | (SPECIAL_TAXES - {'RETENCAO','FCP'}) and not re.fullmatch(r'(?:RETENCAO|FCP):[A-Z][A-Z0-9_]{0,29}',t) for t in taxes):
            raise ValueError('Componente do item não suportado; CBS/IBS fora do cálculo')
        if any(t.startswith(('RETENCAO:','FCP:')) and {'CBS','IBS'} & set(t.split(':',1)[1].split('_')) for t in taxes):
            raise ValueError('CBS/IBS permanecem fora do cálculo, inclusive por retenção')
        if not taxes and not item['no_tax_reason'].strip():
            raise ValueError('Item sem componentes exige motivo explícito')
        if not isinstance(item['values'],dict) or set(item['values']) - (ITEM_BASES | {'st_deduction'}):
            raise ValueError('Campos de valores do item não suportados')
        for value in item['values'].values():
            decimal_text(value)
        total += decimal_text(item['values'].get('total'))
        locator = item['source_locator']
        if products:
            if locator not in observed or locator in locators:
                raise ValueError('Vincule cada item uma única vez a um localizador da fonte selecionada')
            locators.add(locator)
            if observed[locator].get('ncm') and observed[locator]['ncm'] != item['ncm']:
                raise ValueError('NCM do item diverge da fonte; registre a correção antes do cálculo')
        elif locator:
            raise ValueError('A fonte selecionada não fornece esse localizador de item')
    if products and locators != set(observed):
        raise ValueError('Há itens da fonte selecionada sem correspondência declarada')
    if total != decimal_text(fiscal.get('total')):
        raise ValueError('A soma dos totais líquidos atribuídos aos itens deve conferir com o documento; rateios não são presumidos')


def calculate_item(rule, item):
    from .tax_engine import decimal_text, ROUNDINGS
    spec, calc = rule['spec'], rule['spec']['calculation']
    rounding = ROUNDINGS[spec['rounding']]
    with localcontext() as context:
        context.prec = 50
        base = decimal_text(item['values'].get(spec['base_field']))
        reduction = decimal_text(calc['reduction_percent'],rate=True)
        rate = decimal_text(spec['rate'],rate=True)
        expanded = base
        extra_steps={}
        if is_grossup(calc):
            expanded,extra_steps=grossup_steps(spec,base)
            unrounded_base=expanded
        else:
            if calc['method'] == 'st':
                expanded *= 1 + Decimal(calc['margin_percent']) / 100
            unrounded_base = expanded * (1 - reduction / 100)
        effective_base = unrounded_base.quantize(Decimal('.01'),rounding=rounding)
        effective_rate = rate - decimal_text(calc['origin_rate'],rate=True) if calc['method']=='difal' else rate
        gross = effective_base * effective_rate / 100
        deduction = decimal_text(item['values'].get(calc['deduction_field'])) if calc['method']=='st' else Decimal(0)
        raw = gross - deduction
        adjusted = raw
        if raw < 0:
            if calc.get('negative_policy') != 'zerar':
                raise ValueError('Resultado negativo exige revisão ou política explícita de zerar')
            adjusted = Decimal(0)
        amount = adjusted.quantize(Decimal('.01'),rounding=rounding)
        if amount == 0:
            amount = abs(amount)
    formulas = {'percentual':'base_reduzida_arredondada * taxa / 100', 'retencao':'base_reduzida_arredondada * taxa_retida / 100',
                'st':'arredondar(base * (1 + margem / 100) * (1 - reducao / 100)) * taxa / 100 - deducao_declarada',
                'difal':'base_reduzida_arredondada * (taxa_destino - taxa_origem) / 100',
                'fcp':'base_reduzida_arredondada * taxa_FCP_declarada / 100',
                'por_dentro':'arredondar(base_liquida * (1 - reducao / 100) / (1 - soma_taxas_do_grupo / 100)) * taxa / 100'}
    formula=formulas['por_dentro'] if is_grossup(calc) else formulas[calc['method']]
    return {'item_id':item['id'],'item_source':{'reference':item['source_reference'],'locator':item['source_locator']},
            'tax':spec['tax'],'component_key':component_key(spec),'base_field':spec['base_field'],
            'base':format(effective_base,'.2f'),'rate':spec['rate'],'amount':format(amount,'.2f'),
            'formula':formula,'parameters':copy.deepcopy(calc),
            'steps':{'declared_base':format(base,'f'),'expanded_base':format(expanded,'f'),'unrounded_base':format(unrounded_base,'f'),
                     'effective_rate':format(effective_rate,'f'),'gross':format(gross,'f'),'deduction':format(deduction,'f'),
                     'before_negative_policy':format(raw,'f'),**extra_steps},'unrounded':format(adjusted,'f'),
            'effect':spec['effect'],'rounding':spec['rounding'],'revenue_code':spec['revenue_code'],'rule':rule}


def calculate_item_group(rules, item):
    validate_grossup_group(rules)
    lines=[calculate_item(rule,item) for rule in rules]
    return lines,reconcile_grossup_groups(rules,item,lines)
