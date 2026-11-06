"""Explicit gross-up groups. Rates and membership never imply legal incidence."""
from decimal import Decimal, localcontext
import re

GROSSUP_FIELDS = {'input_basis','denominator_components','residual_policy'}


def is_grossup(calc):
    return calc.get('method')=='por_dentro' or (calc.get('method')=='fcp' and calc.get('base_mode')=='por_dentro')


def validate_grossup_parameters(calc, own_component, own_rate):
    from .tax_engine import decimal_text, TAXES
    if calc['input_basis']!='liquido_sem_componentes_do_grupo':
        raise ValueError('Declare que a base líquida exclui os componentes do grupo por dentro')
    if calc['residual_policy'] not in {'bloquear','preservar_sem_rateio'}:
        raise ValueError('Declare a política para diferença de arredondamento do grupo')
    components=calc['denominator_components']
    if not isinstance(components,list) or not 1<=len(components)<=10:
        raise ValueError('Declare de 1 a 10 componentes e taxas no denominador')
    seen={}
    with localcontext() as context:
        context.prec=50
        for component in components:
            if not isinstance(component,dict) or set(component)!={'component','rate'}:
                raise ValueError('Cada componente do denominador exige identificador e taxa')
            key=component['component']
            if not isinstance(key,str) or (key not in TAXES and not re.fullmatch(r'FCP:[A-Z][A-Z0-9_]{0,29}',key)):
                raise ValueError('Denominador suporta ICMS/ISS/PIS/COFINS e modalidades FCP declaradas')
            if key.startswith('FCP:') and {'CBS','IBS'} & set(key.split(':')[1].split('_')):
                raise ValueError('CBS/IBS permanecem fora do cálculo')
            if key in seen:
                raise ValueError('Componente repetido no denominador')
            seen[key]=decimal_text(component['rate'],rate=True)
        if own_component not in seen or seen[own_component]!=decimal_text(own_rate,rate=True):
            raise ValueError('O componente calculado e sua taxa devem constar exatamente no denominador')
        total=sum(seen.values(),Decimal(0))
        if total>=100:
            raise ValueError('Soma das taxas por dentro deve ser menor que 100; denominador precisa ser positivo')
    return seen


def group_signature(spec):
    calc=spec['calculation']
    rates=tuple(sorted((c['component'],Decimal(c['rate'])) for c in calc['denominator_components']))
    return (rates,spec['base_field'],Decimal(calc['reduction_percent']),calc['base_rounding'],spec['rounding'],calc['input_basis'],calc['residual_policy'])


def validate_grossup_group(rules):
    from .tax_items import component_key
    by_key={component_key(rule['spec']):rule for rule in rules}
    for rule in rules:
        spec=rule['spec'];calc=spec['calculation']
        if not is_grossup(calc):continue
        declared=validate_grossup_parameters(calc,component_key(spec),spec['rate'])
        for key,rate in declared.items():
            peer=by_key.get(key)
            if not peer or not is_grossup(peer['spec']['calculation']):
                raise ValueError('Grupo por dentro exige regra aprovada e compatível para '+key)
            if Decimal(peer['spec']['rate'])!=rate or group_signature(peer['spec'])!=group_signature(spec):
                raise ValueError('Taxas, base, redução, componentes e arredondamento devem ser coerentes no grupo por dentro: '+key)


def grossup_steps(spec, declared_base):
    from .tax_items import component_key
    calc=spec['calculation']
    rates=validate_grossup_parameters(calc,component_key(spec),spec['rate'])
    with localcontext() as context:
        context.prec=50
        total=sum(rates.values(),Decimal(0));denominator=1-total/100
        reduced=declared_base*(1-Decimal(calc['reduction_percent'])/100)
        expanded=reduced/denominator
    return expanded,{'input_basis':calc['input_basis'],'reduced_net_base':format(reduced,'f'),
                     'denominator_rate_sum':format(total,'f'),'denominator':format(denominator,'f'),
                     'grossed_base_unrounded':format(expanded,'f'),'arithmetic_precision':50}


def reconcile_grossup_groups(rules, item, lines):
    from .tax_items import component_key
    groups={};by_key={line['component_key']:line for line in lines}
    with localcontext() as context:
        context.prec=50
        for rule in rules:
            spec=rule['spec'];calc=spec['calculation']
            if not is_grossup(calc):continue
            signature=group_signature(spec)
            if signature in groups:continue
            line=by_key[component_key(spec)]
            members=sorted(c['component'] for c in calc['denominator_components'])
            taxes=sum((Decimal(by_key[key]['amount']) for key in members),Decimal(0))
            net=Decimal(line['steps']['reduced_net_base']);gross=Decimal(line['base'])
            residual=gross-net-taxes
            if residual and calc['residual_policy']=='bloquear':
                raise ValueError('Diferença de arredondamento no grupo por dentro exige revisão ou política explícita de preservar sem rateio')
            groups[signature]={'item_id':item['id'],'components':members,'base_field':spec['base_field'],
                               'declared_net_base':line['steps']['declared_base'],'reduced_net_base':format(net,'f'),
                               'grossed_base':format(gross,'.2f'),'rounded_tax_sum':format(taxes,'.2f'),
                               'residual':format(residual,'f'),'residual_policy':calc['residual_policy'],
                               'formula':'residual = base_bruta_arredondada - base_liquida_reduzida - soma_tributos_arredondados',
                               'allocation_performed':False}
    return list(groups.values())
