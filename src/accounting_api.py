"""Rotas contábeis compartilhadas pela aplicação local e pelo portal autenticado."""

ACCOUNTING_GET = {'manual-journals','accounting-books','accounting-book-exports','accounting-book-file','accounting-report'}
ACCOUNTING_WRITE = {'manual-journals','manual-reversal'}
ACCOUNTING_REVIEW = {'manual-review','manual-close','accounting-book-exports'}
ACCOUNTING_ROUTES = ACCOUNTING_GET | ACCOUNTING_WRITE | ACCOUNTING_REVIEW


def dispatch_accounting(store, method, route, data):
    from .local_app import _required
    from .accounting_store import identifier
    company = identifier(_required(data,'company_id'))
    if method == 'GET':
        if route == 'accounting-report':
            from .work_reports import report_from_request
            return report_from_request(store, data)
        if route == 'manual-journals':
            return store.list_manual_journals(company,data.get('period_id') or None,data.get('journal_id') or None)
        if route == 'accounting-books':
            return store.accounting_books(company,_required(data,'period_id'),_required(data,'plan_id'))
        if route == 'accounting-book-exports':
            return store.list_book_exports(company)
        if route == 'accounting-book-file':
            return store.read_book_artifact(company,_required(data,'export_id'),_required(data,'name'))
    if method == 'POST':
        if route == 'manual-journals':
            return store.save_manual_journal(company,_required(data,'period_id'),_required(data,'plan_id'),
                _required(data,'entries'),_required(data,'reference'),_required(data,'reason'),_required(data,'request_key'),
                data.get('journal_id'),data.get('expected_version',0))
        if route in ('manual-review','manual-close'):
            return store.transition_manual_journal(company,_required(data,'journal_id'),_required(data,'snapshot_hash'),
                _required(data,'reason'),'revisado' if route == 'manual-review' else 'fechado')
        if route == 'manual-reversal':
            return store.reverse_manual_journal(company,_required(data,'journal_id'),_required(data,'period_id'),
                _required(data,'date'),_required(data,'reason'),_required(data,'snapshot_hash'))
        if route == 'accounting-book-exports':
            return store.create_book_export(company,_required(data,'period_id'),_required(data,'plan_id'),
                _required(data,'book_hash'),_required(data,'reason'))
    from .local_app import APIError
    raise APIError('Rota ou método não disponível.',404)
