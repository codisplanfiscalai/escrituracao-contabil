"""Authenticated tax configuration, calculation and assessment contracts."""
from .accounting_store import identifier

TAX_GET = {'tax-config','tax-preview','tax-assessment-preview','tax-assessments','tax-catalog-imports','tax-catalog-import','tax-catalog-original','tax-catalog-applications','tax-catalog-application','tax-catalog-codes','tax-code-history'}
TAX_WRITE = {'tax-calculate'}
TAX_REVIEW = {'tax-rules','tax-codes','tax-templates','tax-template-copy','tax-assessments','tax-assessment-review','tax-catalog-imports','tax-catalog-preview','tax-catalog-apply'}
TAX_ROUTES = TAX_GET | TAX_WRITE | TAX_REVIEW


def dispatch_tax(store, method, route, data):
    from .local_app import _required, APIError
    req = lambda key: _required(data,key)
    company = identifier(req('company_id'))
    if method=='GET':
        if route=='tax-config':
            return store.tax_configuration(company)
        if route=='tax-catalog-imports':
            return store.catalog_imports(company)
        if route=='tax-catalog-import':
            return store.catalog_import_detail(company,req('import_id'),query=data.get('query',''),offset=data.get('offset',0))
        if route=='tax-catalog-original':
            return store.catalog_import_original(company,req('import_id'))
        if route=='tax-catalog-applications':
            return store.catalog_applications(company,req('import_id'),summary=True)
        if route=='tax-catalog-application':
            return store.catalog_application(company,req('application_id'))
        if route in {'tax-catalog-codes','tax-code-history'}:
            return store.tax_code_page(company,kind=data.get('kind',''),query=data.get('query',''),offset=data.get('offset',0),
                                       code=req('code') if route=='tax-code-history' else None)
        if route=='tax-preview':
            return store.preview_operation_tax(company,req('operation_id'))
        if route=='tax-assessment-preview':
            return store.preview_tax_assessment(company,req('cycle_id'))
        if route=='tax-assessments':
            return store.tax_assessments(company,req('cycle_id'))
    if method=='POST':
        if route=='tax-catalog-imports':
            import base64,binascii
            encoded=req('content_base64')
            if not isinstance(encoded,str):raise ValueError('Conteúdo deve ser texto base64')
            try:content=base64.b64decode(encoded,validate=True)
            except (ValueError,binascii.Error):raise ValueError('Base64 de cadastro inválido') from None
            return store.receive_catalog_import(company,req('filename'),content,req('metadata'),req('request_key'),req('reason'))
        if route=='tax-catalog-preview':
            return store.preview_catalog_application(company,req('import_id'),req('codes'),req('application_from'))
        if route=='tax-catalog-apply':
            return store.apply_catalog_import(company,req('import_id'),req('codes'),req('application_from'),req('snapshot_hash'),req('request_key'),req('reason'),req('review_reference'),data.get('confirmed'),data.get('acknowledge_legacy'))
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
