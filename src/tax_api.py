"""Authenticated tax configuration, calculation and assessment contracts."""
from .accounting_store import identifier

TAX_GET = {'tax-config','tax-preview','tax-assessment-preview','tax-assessments'}
TAX_WRITE = {'tax-calculate'}
TAX_REVIEW = {'tax-rules','tax-codes','tax-templates','tax-template-copy','tax-assessments','tax-assessment-review'}
TAX_ROUTES = TAX_GET | TAX_WRITE | TAX_REVIEW


def dispatch_tax(store, method, route, data):
    from .local_app import _required, APIError
    req = lambda key: _required(data,key)
    company = identifier(req('company_id'))
    if method=='GET':
        if route=='tax-config':
            return store.tax_configuration(company)
        if route=='tax-preview':
            return store.preview_operation_tax(company,req('operation_id'))
        if route=='tax-assessment-preview':
            return store.preview_tax_assessment(company,req('cycle_id'))
        if route=='tax-assessments':
            return store.tax_assessments(company,req('cycle_id'))
    if method=='POST':
        if route=='tax-rules':
            return store.save_tax_rule(company,req('rule_key'),req('label'),req('spec'),req('state'),data.get('expected_version'),req('reason'))
        if route=='tax-codes':
            return store.save_tax_code(company,req('kind'),req('code'),req('data'),req('state'),data.get('expected_version'),req('reason'))
        if route=='tax-templates':
            return store.save_tax_template(company,req('rule_id'),req('rule_hash'),req('label'),data.get('expected_version'),req('reason'))
        if route=='tax-template-copy':
            return store.copy_tax_template(company,req('source_company_id'),req('template_id'),req('template_hash'),req('rule_key'),req('label'),req('reason'))
        if route=='tax-calculate':
            return store.apply_operation_tax(company,req('operation_id'),req('snapshot_hash'),req('request_key'),req('reason'))
        if route=='tax-assessments':
            return store.create_tax_assessment(company,req('cycle_id'),req('snapshot_hash'),req('request_key'),req('reason'))
        if route=='tax-assessment-review':
            return store.validate_tax_assessment(company,req('cycle_id'),req('assessment_id'),req('snapshot_hash'),req('reason'),data.get('confirmed'))
    raise APIError('Rota tributária não disponível',404)
