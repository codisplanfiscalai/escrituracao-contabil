"""Explicit one-to-one identity decisions for otherwise identical XML billing."""
import json
import re
from datetime import date
from decimal import Decimal, localcontext

from .accounting_store import digest, dump, identifier
from .reconciliation import XML_PROFILE

BILLING_ASSOCIATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS billing_associations (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 document_id INTEGER NOT NULL REFERENCES documents(id), period_id INTEGER NOT NULL REFERENCES periods(id),
 file_id INTEGER NOT NULL REFERENCES files(id), invoice_id INTEGER NOT NULL REFERENCES invoices(id),
 version INTEGER NOT NULL, source_fingerprint TEXT NOT NULL, target_fingerprint TEXT NOT NULL,
 snapshot TEXT NOT NULL, reason TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(document_id,file_id,version));
CREATE INDEX IF NOT EXISTS billing_associations_document ON billing_associations(document_id,file_id,version);
"""
RESOLVABLE_BILLING_ISSUES = frozenset({
    "nFat diverge da fatura já identificada; possível duplicidade exige associação manual",
    "nDup diverge das parcelas já identificadas; possível duplicidade exige associação manual",
    "Parcela sem título ou identificador inequívoco; nenhuma identidade fabricada",
})


def _require(condition, message):
    if not condition:
        raise ValueError("Associação de cobrança: " + message)


def _money(value):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]{2}", value) is not None,
             "valor monetário ausente ou inválido; não completar valores")
    return Decimal(value)


def _billing_values(invoice, parts):
    _require(isinstance(invoice.get("nFat"), str) and bool(invoice["nFat"].strip()), "nFat ausente")
    with localcontext() as context:
        context.prec = 50
        original, discount, net = (_money(invoice.get(field)) for field in ("vOrig", "vDesc", "vLiq"))
        _require(original - discount == net, "aritmética da fatura divergente")
        references = []
        for part in parts:
            reference = part.get("nDup")
            _require(isinstance(reference, str) and bool(reference.strip()), "nDup ausente")
            references.append(reference)
            _money(part.get("vDup"))
            due = part.get("dVenc")
            _require(isinstance(due, str), "vencimento ausente")
            try:
                parsed = date.fromisoformat(due)
            except ValueError:
                raise ValueError("Associação de cobrança: vencimento inválido") from None
            _require(parsed.isoformat() == due, "vencimento inválido")
        _require(len(references) == len(set(references)), "identificadores de parcelas repetidos na origem")
        if parts:
            _require(sum((_money(part["vDup"]) for part in parts), Decimal(0)) == net,
                     "soma das parcelas diverge do líquido da fatura")


def billing_resolution_map(snapshot):
    """Derive display/blocker annotations without changing raw observations."""
    result = {}
    observations = {row["id"]: row for row in snapshot["observations"]}
    for decision in snapshot.get("billing_associations", []):
        if not decision["current"] or not decision["valid"]:
            continue
        proposal = decision["snapshot"]["proposal"]
        links = [{"observation_id": proposal["invoice_observation_id"], "installment_id": None}, *proposal["installment_links"]]
        for link in links:
            observation = observations[link["observation_id"]]
            result[observation["id"]] = {
                "association_id": decision["id"], "version": decision["version"],
                "invoice_id": decision["invoice_id"], "installment_id": link["installment_id"],
                "resolved_issues": [issue for issue in observation["issues"] if issue in RESOLVABLE_BILLING_ISSUES],
            }
    return result


class BillingAssociationMixin:
    def _billing_targets(self, document_id, invoice_id):
        invoice = self.db.execute("SELECT id,document_id,reference,payload FROM invoices WHERE id=? AND document_id=?", (identifier(invoice_id), document_id)).fetchone()
        _require(invoice is not None, "fatura não pertence ao documento selecionado")
        invoice = dict(invoice)
        invoice["payload"] = json.loads(invoice["payload"])
        parts = [dict(row) for row in self.db.execute("SELECT id,invoice_id,reference,payload FROM installments WHERE invoice_id=? ORDER BY id", (invoice["id"],))]
        for part in parts:
            part["payload"] = json.loads(part["payload"])
        return {"invoice": invoice, "installments": parts}

    def _billing_history(self, company_id, document_id=None):
        query = "SELECT * FROM billing_associations WHERE company_id=?"
        params = [company_id]
        if document_id is not None:
            query += " AND document_id=?"
            params.append(document_id)
        rows = [dict(row) for row in self.db.execute(query + " ORDER BY id DESC", params)]
        for row in rows:
            row["snapshot"] = json.loads(row["snapshot"])
        return rows

    def _billing_applicability(self, decision, base_snapshot, current=True):
        result = dict(decision)
        blockers = []
        if not current:
            blockers.append("Decisão substituída por nova versão")
        if decision["source_fingerprint"] != digest(base_snapshot):
            blockers.append("Fontes do documento alteradas; gere nova prévia")
        try:
            targets = self._billing_targets(decision["document_id"], decision["invoice_id"])
            if digest(targets) != decision["target_fingerprint"]:
                blockers.append("Alvos canônicos alterados; gere nova prévia")
        except ValueError as exc:
            blockers.append(str(exc))
        result.update(current=current, valid=not blockers, blockers=blockers)
        return result

    def _billing_snapshot_decisions(self, company_id, document_id, base_snapshot):
        latest = {}
        for decision in self._billing_history(company_id, document_id):
            latest.setdefault(decision["file_id"], decision)
        return [self._billing_applicability(latest[file_id], base_snapshot) for file_id in sorted(latest)]

    def list_billing_associations(self, company_id, document_id=None):
        self._company(company_id)
        if document_id is not None:
            document_id = self._owned("documents", company_id, identifier(document_id))["id"]
        seen, snapshots, results = set(), {}, []
        for decision in self._billing_history(company_id, document_id):
            doc = decision["document_id"]
            if doc not in snapshots:
                snapshots[doc] = self._base_source_snapshot(company_id, doc)[0]
            key = (doc, decision["file_id"])
            results.append(self._billing_applicability(decision, snapshots[doc], key not in seen))
            seen.add(key)
        return results

    def _validate_billing_proposal(self, base, file_id, targets, installment_links):
        rows = [row for row in base["observations"] if row["file_id"] == file_id]
        _require(rows and all(row["source_kind"] == "XML" and row["profile"] == XML_PROFILE and row["file_status"] not in {"excluido", "rejeitado"} and row["period_id"] == base["period_id"] for row in rows), "fonte XML ativa do mesmo período é obrigatória")
        headers = [row for row in rows if row["entity_kind"] == "documento"]
        invoices = [row for row in rows if row["entity_kind"] == "fatura"]
        parts = [row for row in rows if row["entity_kind"] == "parcela"]
        _require(len(headers) == 1 and not headers[0]["issues"], "documento da fonte possui pendências não resolvíveis por associação")
        _require(len(invoices) == 1, "fonte deve conter exatamente uma fatura identificada")
        source_invoice = invoices[0]
        invoice = targets["invoice"]
        _billing_values(source_invoice["normalized"], [row["normalized"] for row in parts])
        _billing_values(invoice["payload"], [row["payload"] for row in targets["installments"]])
        _require(source_invoice["invoice_id"] in (None, invoice["id"]), "vínculo de fatura existente não pode ser trocado")
        _require(all(issue in RESOLVABLE_BILLING_ISSUES for row in [source_invoice, *parts] for issue in row["issues"]), "alertas de valores/aritmética ou de origem não podem ser resolvidos por associação")
        _require({key: value for key, value in source_invoice["normalized"].items() if key != "nFat"} == {key: value for key, value in invoice["payload"].items() if key != "nFat"}, "valores da fatura divergem do alvo")
        _require(isinstance(installment_links, list) and len(installment_links) == len(parts) == len(targets["installments"]), "informe todas as parcelas da fonte e do alvo uma única vez")
        normalized_links = []
        for link in installment_links:
            _require(isinstance(link, dict) and set(link) == {"observation_id", "installment_id"}, "cada vínculo deve conter observation_id e installment_id")
            normalized_links.append({"observation_id": identifier(link["observation_id"]), "installment_id": identifier(link["installment_id"])})
        source_ids = [link["observation_id"] for link in normalized_links]
        target_ids = [link["installment_id"] for link in normalized_links]
        _require(len(set(source_ids)) == len(source_ids) and set(source_ids) == {row["id"] for row in parts}, "observações de parcelas devem ter correspondência completa 1:1")
        _require(len(set(target_ids)) == len(target_ids) and set(target_ids) == {row["id"] for row in targets["installments"]}, "parcelas de destino devem ter correspondência completa 1:1")
        target_by_id = {row["id"]: row for row in targets["installments"]}
        source_by_id = {row["id"]: row for row in parts}
        enriched = []
        changed_identifier = source_invoice["normalized"]["nFat"] != invoice["payload"]["nFat"]
        for link in sorted(normalized_links, key=lambda row: row["observation_id"]):
            source, target = source_by_id[link["observation_id"]], target_by_id[link["installment_id"]]
            _require(source["invoice_id"] in (None, invoice["id"]) and source["installment_id"] in (None, target["id"]), "vínculo de parcela existente não pode ser trocado")
            _require({key: value for key, value in source["normalized"].items() if key != "nDup"} == {key: value for key, value in target["payload"].items() if key != "nDup"}, "valor ou vencimento da parcela diverge do alvo")
            changed_identifier |= source["normalized"]["nDup"] != target["payload"]["nDup"]
            enriched.append({**link, "source": source, "target": target})
        _require(changed_identifier, "nenhum identificador divergente para associar")
        # Require active native evidence for the canonical values; no fabricated
        # identity can become its own supporting evidence through this decision.
        active = [row for row in base["observations"] if row["source_kind"] == "XML" and row["profile"] == XML_PROFILE and row["file_status"] not in {"excluido", "rejeitado"} and row["period_id"] == base["period_id"] and not row["issues"]]
        _require(any(row["entity_kind"] == "fatura" and row["invoice_id"] == invoice["id"] and row["normalized"] == invoice["payload"] for row in active), "fatura canônica sem evidência XML ativa íntegra no contexto")
        for target in targets["installments"]:
            _require(any(row["entity_kind"] == "parcela" and row["installment_id"] == target["id"] and row["invoice_id"] == invoice["id"] and row["normalized"] == target["payload"] for row in active), "parcela canônica sem evidência XML ativa íntegra no contexto")
        return {"invoice_observation_id": source_invoice["id"], "invoice_id": invoice["id"],
                "installment_links": [{"observation_id": row["observation_id"], "installment_id": row["installment_id"]} for row in enriched]}, {"source": source_invoice, "target": invoice}, enriched

    def _billing_preview(self, company_id, document_id, period_id, file_id, invoice_id, installment_links):
        document = self._owned("documents", company_id, identifier(document_id))
        period = self._owned("periods", company_id, identifier(period_id))
        file = self._owned("files", company_id, identifier(file_id))
        _require(document["period_id"] == period["id"] == file["period_id"], "documento/arquivo devem pertencer ao mesmo contexto de período")
        base, source_fingerprint = self._base_source_snapshot(company_id, document["id"])
        _require(any(row["id"] == file["id"] for row in base["files"]), "arquivo não é fonte do documento")
        targets = self._billing_targets(document["id"], invoice_id)
        proposal, invoice, installments = self._validate_billing_proposal(base, file["id"], targets, installment_links)
        target_fingerprint = digest(targets)
        heads = [{"id": row["id"], "version": row["version"], "file_id": row["file_id"]} for row in self._billing_snapshot_decisions(company_id, document["id"], base)]
        fingerprint = digest({"source_fingerprint": source_fingerprint, "target_fingerprint": target_fingerprint, "proposal": proposal, "decisions": heads})
        preview = {"company_id": document["company_id"], "document_id": document["id"], "period_id": period["id"], "file_id": file["id"],
                   "invoice_id": targets["invoice"]["id"], "invoice_observation_id": proposal["invoice_observation_id"],
                   "source_fingerprint": source_fingerprint, "target_fingerprint": target_fingerprint,
                   "invoice": invoice, "installments": installments, "expected_fingerprint": fingerprint}
        return preview, {"sources": base, "targets": targets, "proposal": proposal}

    def preview_billing_association(self, company_id, document_id, period_id, file_id, invoice_id, installment_links):
        return self._billing_preview(company_id, document_id, period_id, file_id, invoice_id, installment_links)[0]

    def save_billing_association(self, company_id, document_id, period_id, file_id, invoice_id, installment_links, expected_fingerprint, reason, confirmed=False):
        from .persistence import _text
        reason = _text(reason, "motivo da associação de cobrança", 2000)
        _require(confirmed is True, "confirme explicitamente a prévia da associação")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            preview, snapshot = self._billing_preview(company_id, document_id, period_id, file_id, invoice_id, installment_links)
            _require(expected_fingerprint == preview["expected_fingerprint"], "prévia desatualizada; confira novamente a proposta e as fontes")
            version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM billing_associations WHERE document_id=? AND file_id=?", (preview["document_id"], preview["file_id"])).fetchone()[0]
            cur = self.db.execute("INSERT INTO billing_associations(company_id,document_id,period_id,file_id,invoice_id,version,source_fingerprint,target_fingerprint,snapshot,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (preview["company_id"], preview["document_id"], preview["period_id"], preview["file_id"], preview["invoice_id"], version, preview["source_fingerprint"], preview["target_fingerprint"], dump(snapshot), reason, self.actor, self._now()))
            self._audit(company_id, "cobranca_associada", {"association_id": cur.lastrowid, "document_id": preview["document_id"], "file_id": preview["file_id"], "invoice_id": preview["invoice_id"], "version": version, "expected_fingerprint": expected_fingerprint, "reason": reason})
            result = self._billing_history(company_id, preview["document_id"])[0]
            return self._billing_applicability(result, snapshot["sources"])
