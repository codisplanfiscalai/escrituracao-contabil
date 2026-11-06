"""API for the replacement bookkeeping application; legacy writers are retired."""

from .accounting_store import identifier

WORK_GET = {
    "nfe-events", "nfe-event-preview", "nfe-event-history", "nfe-document-events", "nfe-event-posting-proof",
    "work-module-state",
    "source-search",
    "work-archived-tabs",
    "work-attempt",
    "source-history",
    "source-impact",
    "source-inbox",
    "source-original",
    "work-cycles",
    "work-overview",
    "work-prepare",
    "work-operations",
    "work-operation",
    "work-policies",
    "work-tabs",
    "work-books",
    "work-exports",
    "work-export-file",
    "work-finance",
}
WORK_WRITE = {
    "source-remove",
    "work-plan",
    "source-receive",
    "source-organize",
    "source-discard",
    "work-cycles",
    "work-operations",
    "work-tabs",
    "work-settlement",
    "work-reversal",
    "work-resume",
}
WORK_REVIEW = {
    "nfe-event-review",
    "work-module-state",
    "work-policies",
    "work-review",
    "work-post",
    "work-cycle-state",
    "work-exports",
}
WORK_ROUTES = WORK_GET | WORK_WRITE | WORK_REVIEW
RETIRED_WRITES = {
    "files",
    "import-batches",
    "file-analysis",
    "file-removal",
    "manual-journals",
    "manual-review",
    "manual-close",
    "manual-reversal",
    "accounting-batches",
    "accounting-review",
    "accounting-close",
    "accounting-evidence",
    "accounting-book-exports",
    "fiscal-entries",
    "fiscal-review",
    "fiscal-period",
    "fiscal-workspaces",
    "document-reviews",
    "billing-associations",
    "finance-titles",
    "finance-settlements",
    "finance-reversal",
    "finance-cancel",
}


def dispatch_work(store, method, route, data):
    from .local_app import _required, APIError

    def req(key):
        return _required(data, key)

    company = identifier(req("company_id"))
    if method == "GET":
        if route == 'nfe-events':
            try:offset=int(data.get('offset',0))
            except (ValueError,TypeError):raise ValueError('Deslocamento inválido') from None
            return store.nfe_event_queue(company,data.get('query',''),offset)
        if route == 'nfe-event-preview':return store.nfe_event_preview(company,req('input_id'))
        if route == 'nfe-event-history':return store.nfe_event_history(company,req('input_id'))
        if route == 'nfe-document-events':return store.nfe_document_events(company,req('document_id'))
        if route == 'nfe-event-posting-proof':return store.nfe_event_posting_proof(company,req('operation_id'))
        if route == "work-module-state":
            return [store.module_period_overview(company, req("cycle_id"), module) for module in ("fiscal", "contabil")]
        if route == "source-search":
            return store.search_sources(company, **{key: data.get(key, "") for key in ("query", "kind", "issued_from", "issued_to", "direction")})
        if route == "work-attempt":
            row = store.db.execute(
                "SELECT r.operation_id,r.version FROM work_requests q JOIN work_revisions r ON r.id=q.revision_id WHERE q.company_id=? AND q.request_key=?",
                (company, str(req("request_key"))),
            ).fetchone()
            return (
                {
                    "submitted_version": row["version"],
                    "operation": store.get_work_operation(company, row["operation_id"]),
                }
                if row
                else None
            )
        if route == "source-history":
            return store.source_history(company, req("input_id"))
        if route == "source-impact":
            return store.source_impact(company, req("input_id"))
        if route == "source-inbox":
            return store.source_inbox(company)
        if route == "source-original":
            return store.source_original(company, req("input_id"))
        if route == "work-cycles":
            return store.work_cycles(company)
        if route == "work-overview":
            return store.work_overview(company, req("cycle_id"))
        if route == "work-prepare":
            return store.prepare_work_operation(
                company,
                req("cycle_id"),
                data.get("document_id") or None,
                data.get("observation_id") or None,
                data.get("policy_id") or None,
                data.get("operation") or None,
            )
        if route == "work-operations":
            return store.work_operations(company, req("cycle_id"))
        if route == "work-operation":
            return store.get_work_operation(company, req("operation_id"))
        if route == "work-policies":
            return store.work_policies(company)
        if route == "work-archived-tabs":
            return [
                t
                for t in store.work_tabs(company, req("cycle_id"), True)
                if t["closed"]
            ]
        if route == "work-tabs":
            return store.work_tabs(company, req("cycle_id"))
        if route == "work-books":
            return store.work_books(company, req("cycle_id"))
        if route == "work-exports":
            return store.work_exports(company, req("cycle_id"))
        if route == "work-export-file":
            return store.work_export_file(company, req("export_id"), req("name"))
        if route == "work-finance":
            cycle = store._work_cycle(company, req("cycle_id"))
            return [
                {
                    **store._finance_title(company, row["id"]),
                    "operation_id": row["operation_id"],
                }
                for row in store.db.execute(
                    "SELECT t.id,l.operation_id FROM finance_titles t LEFT JOIN work_title_links l ON l.title_id=t.id JOIN periods p ON p.id=t.period_id WHERE t.company_id=? AND p.processing_competence<=? ORDER BY t.due_date,t.id",
                    (company, cycle["competence"]),
                )
            ]
    if method == "POST":
        if route == 'nfe-event-review':
            return store.review_nfe_event(company,req('input_id'),req('snapshot_hash'),req('decision'),req('reason'),req('review_reference'),req('request_key'),data.get('confirmed'))
        if route == "work-module-state":
            return store.transition_module_period(company, req("cycle_id"), req("module"), req("target"), req("snapshot_hash"), req("reason"), data.get("checks"), data.get("evidence_reference", ""))
        if route == "source-remove":
            return store.remove_source(
                company,
                req("input_id"),
                req("impact_hash"),
                req("reason"),
                data.get("confirmed", False),
            )
        if route == "work-plan":
            return store.import_work_plan(
                company, req("filename"), req("content"), req("label"), req("reason")
            )
        if route == "source-receive":
            import base64, binascii

            inputs = req("inputs")
            if not isinstance(inputs, list):
                raise APIError("Entradas inválidas.")
            decoded = []
            for item in inputs:
                if not isinstance(item, dict) or not isinstance(
                    item.get("content_base64"), str
                ):
                    raise APIError("Arquivo sem conteúdo base64.")
                try:
                    content = base64.b64decode(item["content_base64"], validate=True)
                except (ValueError, binascii.Error):
                    raise APIError("Conteúdo base64 inválido.") from None
                decoded.append({"filename": item.get("filename"), "content": content})
            return store.receive_sources(company, decoded, req("request_key"))
        if route == "source-organize":
            return store.organize_source(
                company,
                req("input_id"),
                req("cycle_id"),
                req("snapshot_hash"),
                req("reason"),
                data.get("sped_profile") or None,
            )
        if route == "source-discard":
            return store.discard_source(
                company, req("input_id"), req("snapshot_hash"), req("reason")
            )
        if route == "work-cycles":
            return store.save_work_cycle(
                company,
                req("reference_competence"),
                req("competence"),
                data.get("plan_id"),
                req("reason"),
                data.get("expected_version"),
            )
        if route == "work-policies":
            return store.save_work_policy(
                company,
                req("plan_id"),
                req("operation"),
                req("reference_competence"),
                req("label"),
                req("debit_account_id"),
                req("credit_account_id"),
                req("reason"),
                data.get("approved", False),
            )
        if route == "work-operations":
            return store.save_work_operation(
                company,
                req("cycle_id"),
                req("payload"),
                req("reason"),
                req("request_key"),
                data.get("operation_id"),
                data.get("expected_version", 0),
            )
        if route == "work-review":
            return store.review_work_operation(
                company,
                req("operation_id"),
                req("snapshot_hash"),
                req("reason"),
                data.get("target", "revisado"),
            )
        if route == "work-post":
            return store.post_work_operation(
                company, req("operation_id"), req("snapshot_hash"), req("reason")
            )
        if route == "work-tabs":
            return store.save_work_tab(
                company,
                req("cycle_id"),
                req("title"),
                data.get("data", {}),
                data.get("tab_id"),
                data.get("expected_version", 0),
                data.get("closed", False),
                data.get("operation_id"),
            )
        if route == "work-settlement":
            return store.prepare_work_settlement(
                company,
                req("cycle_id"),
                req("title_id"),
                req("policy_id"),
                req("amount"),
                req("paid_date"),
                req("reference"),
            )
        if route == "work-reversal":
            return store.reverse_work_operation(
                company,
                req("operation_id"),
                req("cycle_id"),
                req("date"),
                req("snapshot_hash"),
                req("reason"),
                req("request_key"),
            )
        if route == "work-resume":
            return store.resume_work_legacy(
                company,
                req("cycle_id"),
                req("kind"),
                req("source_id"),
                req("snapshot_hash"),
                req("reason"),
                req("request_key"),
            )
        if route == "work-cycle-state":
            return store.transition_work_cycle(
                company,
                req("cycle_id"),
                req("target"),
                req("snapshot_hash"),
                req("reason"),
                data.get("acknowledge_errors", False),
            )
        if route == "work-exports":
            return store.create_work_export(
                company, req("cycle_id"), req("snapshot_hash"), req("reason")
            )
    raise APIError("Rota operacional não disponível.", 404)
