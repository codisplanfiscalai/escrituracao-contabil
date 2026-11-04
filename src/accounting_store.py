"""Explicit local document postings; no tax inference or external ledger writes."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, localcontext

ACCOUNTING_SCHEMA = """
CREATE TABLE IF NOT EXISTS document_reviews (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 document_id INTEGER NOT NULL REFERENCES documents(id), period_id INTEGER NOT NULL REFERENCES periods(id),
 version INTEGER NOT NULL, chosen_observation_id INTEGER NOT NULL REFERENCES source_observations(id),
 source_fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL, reason TEXT NOT NULL,
 actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(document_id,period_id,version));
CREATE TABLE IF NOT EXISTS accounting_batches (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), plan_id INTEGER NOT NULL REFERENCES plans(id),
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, version INTEGER NOT NULL,
 previous_batch_id INTEGER REFERENCES accounting_batches(id), status TEXT NOT NULL,
 snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL, reason TEXT NOT NULL,
 actor TEXT NOT NULL, created_at TEXT NOT NULL, review_actor TEXT, review_reason TEXT,
 reviewed_at TEXT, closed_at TEXT, UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS accounting_events (
 company_id INTEGER NOT NULL REFERENCES companies(id), document_id INTEGER NOT NULL REFERENCES documents(id),
 batch_id INTEGER NOT NULL REFERENCES accounting_batches(id), PRIMARY KEY(company_id,document_id));
CREATE TABLE IF NOT EXISTS accounting_batch_documents (
 batch_id INTEGER NOT NULL REFERENCES accounting_batches(id), document_id INTEGER NOT NULL REFERENCES documents(id),
 PRIMARY KEY(batch_id,document_id));
"""


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


def identifier(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise ValueError("Identificador deve ser inteiro positivo")
    return int(value)


def amount(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,2})?", value):
        raise ValueError("Valor deve ser texto decimal positivo, até 16 inteiros e duas casas; floats não são aceitos")
    result = Decimal(value)
    if result <= 0:
        raise ValueError("Valor deve ser positivo")
    return format(result, ".2f")


class AccountingMixin:
    def _base_source_snapshot(self, company_id, document_id):
        document = self._owned("documents", company_id, document_id)
        observations = [row for row in self.list_observations(company_id) if row["document_id"] == document["id"]]
        files = [dict(row) for row in self.db.execute(
            "SELECT f.id,f.period_id,f.sha256,f.status,s.conflict FROM document_sources s JOIN files f ON f.id=s.file_id WHERE s.document_id=? ORDER BY f.id", (document["id"],))]
        snapshot = {"document_id": document["id"], "business_key": document["business_key"],
                    "period_id": document["period_id"], "files": files, "observations": observations}
        return snapshot, digest(snapshot)

    def _source_snapshot(self, company_id, document_id):
        snapshot, fingerprint = self._base_source_snapshot(company_id, document_id)
        decisions = self._billing_snapshot_decisions(company_id, snapshot["document_id"], snapshot)
        if decisions:
            snapshot["billing_associations"] = decisions
            fingerprint = digest(snapshot)
        return snapshot, fingerprint

    def _source_blockers(self, snapshot, period_id):
        active = [row for row in snapshot["observations"] if row["file_status"] != "excluido"]
        blockers = []
        if snapshot["period_id"] != period_id or any(row["period_id"] != period_id for row in active):
            blockers.append("Contextos de período diferentes; associação de contexto não implementada")
        if not any(row["entity_kind"] == "documento" for row in active):
            blockers.append("Nenhuma observação documental ativa")
        indexed = {row["file_id"] for row in active}
        if any(row["status"] != "excluido" and row["id"] not in indexed for row in snapshot["files"]):
            blockers.append("Fonte vinculada ainda não analisada")
        allowed = {"Fatura com valores divergentes; primeira representação preservada",
                   "Parcela com valores divergentes; primeira representação preservada"}
        from .billing_association import billing_resolution_map
        resolutions = billing_resolution_map(snapshot)
        for row in active:
            resolution = resolutions.get(row["id"])
            if not resolution and ((row["entity_kind"] == "fatura" and row["invoice_id"] is None) or (row["entity_kind"] == "parcela" and row["installment_id"] is None)):
                blockers.append("Cobrança sem identidade inequívoca; seleção de fonte não resolve possível duplicidade")
            blockers.extend(message for message in row["issues"] if message not in allowed and (not resolution or message not in resolution["resolved_issues"]))
        return list(dict.fromkeys(blockers))

    def _review_status(self, company_id, document_id, period_id):
        snapshot, fingerprint = self._source_snapshot(company_id, document_id)
        blockers = self._source_blockers(snapshot, period_id)
        row = self.db.execute("SELECT * FROM document_reviews WHERE company_id=? AND document_id=? AND period_id=? ORDER BY version DESC LIMIT 1", (company_id, document_id, period_id)).fetchone()
        review = dict(row) if row else None
        if review:
            review["snapshot"] = json.loads(review["snapshot"])
            review["valid"] = review["source_fingerprint"] == fingerprint
            if not review["valid"]:
                blockers.append("Decisão caduca: fontes ou observações mudaram")
        else:
            blockers.append("Revisão documental explícita ausente")
        return {"source_fingerprint": fingerprint, "review": review,
                "readiness_for_accounting": not blockers, "accounting_blockers": blockers}

    def save_document_review(self, company_id, document_id, period_id, chosen_observation_id, expected_fingerprint, reason):
        from .persistence import _text
        reason = _text(reason, "motivo", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            document = self._owned("documents", company_id, identifier(document_id))
            period = self._owned("periods", company_id, identifier(period_id))
            if document["period_id"] != period["id"]:
                raise ValueError("Revisão deve usar o contexto canônico do documento")
            snapshot, fingerprint = self._source_snapshot(company_id, document["id"])
            if expected_fingerprint != fingerprint:
                raise ValueError("Prévia de fontes desatualizada; confira novamente")
            chosen_id = identifier(chosen_observation_id)
            chosen = next((row for row in snapshot["observations"] if row["id"] == chosen_id and row["entity_kind"] == "documento" and row["file_status"] != "excluido"), None)
            if not chosen or chosen["period_id"] != period["id"]:
                raise ValueError("Observação documental ativa do contexto é obrigatória")
            version = self.db.execute("SELECT COALESCE(MAX(version),0)+1 FROM document_reviews WHERE document_id=? AND period_id=?", (document["id"], period["id"])).fetchone()[0]
            cur = self.db.execute("INSERT INTO document_reviews(company_id,document_id,period_id,version,chosen_observation_id,source_fingerprint,snapshot,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                  (company_id, document["id"], period["id"], version, chosen_id, fingerprint, dump(snapshot), reason, self.actor, self._now()))
            self._audit(company_id, "documento_revisado", {"review_id": cur.lastrowid, "document_id": document["id"], "version": version, "reason": reason})
        return self._review_status(company_id, document["id"], period["id"])

    def list_document_reviews(self, company_id, document_id=None):
        self._company(company_id)
        if document_id is not None:
            document_id = self._owned("documents", company_id, identifier(document_id))["id"]
        rows = [dict(row) for row in self.db.execute("SELECT * FROM document_reviews WHERE company_id=? ORDER BY id DESC", (company_id,)) if document_id is None or row["document_id"] == document_id]
        for row in rows:
            row["snapshot"] = json.loads(row["snapshot"])
            latest = self._review_status(company_id, row["document_id"], row["period_id"])
            row["valid"] = row["source_fingerprint"] == latest["source_fingerprint"]
            row["current"] = row["id"] == latest["review"]["id"]
        return rows

    def _mapping_snapshot(self, company_id, plan_id, mapping_id, competence):
        row = self.db.execute("SELECT * FROM mappings WHERE id=? AND company_id=? AND plan_id=?", (identifier(mapping_id), company_id, plan_id)).fetchone()
        if not row:
            raise ValueError("Mapeamento não pertence ao plano e empresa selecionados")
        mapping = dict(row)
        current = self.db.execute("SELECT id FROM mappings WHERE company_id=? AND plan_id=? AND source_account=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>=?) ORDER BY version DESC LIMIT 1", (company_id, plan_id, mapping["source_account"], competence, competence)).fetchone()
        if not current or current["id"] != mapping["id"] or mapping["state"] != "aprovado":
            raise ValueError("Selecione a última versão aplicável de mapeamento aprovado e vigente nos movimentos")
        account = self.db.execute("SELECT * FROM accounts WHERE plan_id=? AND code=?", (plan_id, mapping["target_code"])).fetchone()
        if not account or account["kind"] != "analitica":
            raise ValueError("Destino deve ser conta analítica do plano selecionado")
        account = dict(account)
        account["attributes"] = json.loads(account["attributes"])
        return {"mapping": mapping, "account": account}

    def _posting_snapshot(self, company_id, period_id, plan_id, entries):
        from .persistence import _text
        company = self._company(company_id)
        period = self._owned("periods", company_id, period_id)
        plan = self._owned("plans", company_id, plan_id)
        if not isinstance(entries, list) or not 2 <= len(entries) <= 10000:
            raise ValueError("Informe de 2 a 10000 partidas explícitas")
        lines, documents, totals = [], {}, {}
        with localcontext() as ctx:
            ctx.prec = 40
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("Cada partida deve ser objeto")
                document_id = identifier(entry.get("document_id"))
                observation_id = identifier(entry.get("observation_id"))
                if document_id not in documents:
                    status = self._review_status(company_id, document_id, period["id"])
                    if not status["readiness_for_accounting"]:
                        raise ValueError("Documento bloqueado: " + "; ".join(status["accounting_blockers"]))
                    documents[document_id] = status["review"]
                review = documents[document_id]
                if observation_id != review["chosen_observation_id"]:
                    raise ValueError("Origem da partida deve ser a observação documental escolhida na revisão")
                posting_date = _text(entry.get("date"), "data", 10)
                try:
                    parsed = date.fromisoformat(posting_date)
                except ValueError:
                    raise ValueError("Data contábil inválida") from None
                if parsed.isoformat() != posting_date or posting_date[:7] != period["processing_competence"]:
                    raise ValueError("Data deve pertencer à competência dos movimentos")
                side = entry.get("side")
                if side not in ("D", "C"):
                    raise ValueError("Partida deve indicar D ou C")
                value = amount(entry.get("amount"))
                group = _text(entry.get("group"), "grupo", 100)
                memo = _text(entry.get("memo"), "histórico", 1000)
                mapping = self._mapping_snapshot(company_id, plan["id"], entry.get("mapping_id"), period["processing_competence"])
                lines.append({"line": len(lines)+1, "document_id": document_id, "observation_id": observation_id,
                              "review_id": review["id"], "group": group, "date": posting_date, "side": side,
                              "amount": value, "memo": memo, **mapping})
                key = (document_id, group)
                totals.setdefault(key, {"D": Decimal(0), "C": Decimal(0)})[side] += Decimal(value)
            for total in totals.values():
                if total["D"] != total["C"]:
                    raise ValueError("Débitos e créditos devem equilibrar por grupo e documento")
            for document_id, review in documents.items():
                chosen = next(row for row in review["snapshot"]["observations"] if row["id"] == review["chosen_observation_id"])
                origin_total = Decimal(amount(chosen["normalized"].get("total")))
                debit = sum((value["D"] for key, value in totals.items() if key[0] == document_id), Decimal(0))
                if debit != origin_total:
                    raise ValueError("Total das partidas do documento deve corresponder ao total da fonte escolhida")
            debit = sum((value["D"] for value in totals.values()), Decimal(0))
            credit = sum((value["C"] for value in totals.values()), Decimal(0))
        return {"engine": "explicit-document-v1", "company": company, "period": period, "plan": plan,
                "documents": [documents[key] for key in sorted(documents)], "entries": lines,
                "totals": {"debit": format(debit, ".2f"), "credit": format(credit, ".2f")},
                "groups": [{"document_id": key[0], "group": key[1], "debit": format(value["D"], ".2f"), "credit": format(value["C"], ".2f")} for key, value in sorted(totals.items())],
                "ready_for_export": False}

    def _batch(self, company_id, batch_id):
        self._company(company_id)
        row = self.db.execute("SELECT * FROM accounting_batches WHERE company_id=? AND id=?", (company_id, identifier(batch_id))).fetchone()
        if not row:
            raise ValueError("Lote não pertence à empresa selecionada ou não existe")
        result = dict(row)
        result["snapshot"] = json.loads(result["snapshot"])
        return result

    def _batch_blockers(self, batch):
        snap = batch["snapshot"]
        entries = [{key: line[key] for key in ("document_id", "observation_id", "group", "date", "side", "amount", "memo")} | {"mapping_id": line["mapping"]["id"]} for line in snap["entries"]]
        blockers = []
        try:
            current = self._posting_snapshot(batch["company_id"], batch["period_id"], batch["plan_id"], entries)
            if current != snap:
                blockers.append("Snapshot desatualizado; crie nova versão vinculada")
        except ValueError as exc:
            blockers.append(str(exc))
        for review in snap["documents"]:
            reservation = self.db.execute("SELECT batch_id FROM accounting_events WHERE company_id=? AND document_id=?", (batch["company_id"], review["document_id"])).fetchone()
            if not reservation or reservation["batch_id"] != batch["id"]:
                blockers.append("Evento reservado por outro lote; correção de fechado exige estorno/ajuste ainda não implementado")
                break
        return blockers

    def list_accounting_batches(self, company_id):
        self._company(company_id)
        result = []
        for row in self.db.execute("SELECT id FROM accounting_batches WHERE company_id=? ORDER BY id DESC", (company_id,)).fetchall():
            batch = self._batch(company_id, row["id"])
            batch["current_blockers"] = self._batch_blockers(batch)
            batch["ready_for_export"] = False
            result.append(batch)
        return result

    def create_accounting_batch(self, company_id, period_id, plan_id, request_key, entries, reason, previous_batch_id=None):
        from .persistence import _text
        request_key = _text(request_key, "identificador da tentativa", 100)
        reason = _text(reason, "motivo", 2000)
        period_id, plan_id = identifier(period_id), identifier(plan_id)
        previous_batch_id = identifier(previous_batch_id) if previous_batch_id is not None else None
        request_hash = digest({"period_id": period_id, "plan_id": plan_id, "entries": entries, "reason": reason, "previous_batch_id": previous_batch_id})
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self._company(company_id)
            existing = self.db.execute("SELECT id,request_hash FROM accounting_batches WHERE company_id=? AND request_key=?", (company_id, request_key)).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("Identificador de tentativa já utilizado com conteúdo diferente")
                self._audit(company_id, "lote_contabil_repetido", {"batch_id": existing["id"], "request_hash": request_hash})
                return self._batch(company_id, existing["id"])
            snapshot = self._posting_snapshot(company_id, period_id, plan_id, entries)
            doc_ids = {row["document_id"] for row in snapshot["documents"]}
            previous = self._batch(company_id, previous_batch_id) if previous_batch_id is not None else None
            if previous:
                if previous["status"] == "substituido" or {row["document_id"] for row in previous["snapshot"]["documents"]} != doc_ids:
                    raise ValueError("Correção deve substituir versão vigente com o mesmo conjunto de documentos")
            for document_id in doc_ids:
                old = self.db.execute("SELECT batch_id FROM accounting_events WHERE company_id=? AND document_id=?", (company_id, document_id)).fetchone()
                if old and (not previous or old["batch_id"] != previous["id"]):
                    raise ValueError("Documento já reservado/contabilizado em outro lote; use correção vinculada")
            now = self._now()
            cur = self.db.execute("INSERT INTO accounting_batches(company_id,period_id,plan_id,request_key,request_hash,version,previous_batch_id,status,snapshot,snapshot_hash,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (company_id, period_id, plan_id, request_key, request_hash, previous["version"]+1 if previous else 1, previous_batch_id, "previa", dump(snapshot), digest(snapshot), reason, self.actor, now))
            batch_id = cur.lastrowid
            if previous and previous["status"] != "fechado":
                self.db.execute("UPDATE accounting_batches SET status='substituido' WHERE id=?", (previous["id"],))
            for document_id in doc_ids:
                self.db.execute("INSERT INTO accounting_batch_documents VALUES(?,?)", (batch_id, document_id))
                if not previous or previous["status"] != "fechado":
                    self.db.execute("INSERT INTO accounting_events VALUES(?,?,?) ON CONFLICT(company_id,document_id) DO UPDATE SET batch_id=excluded.batch_id", (company_id, document_id, batch_id))
            self._audit(company_id, "previa_contabil_criada", {"batch_id": batch_id, "previous_batch_id": previous_batch_id, "snapshot_hash": digest(snapshot), "reason": reason})
        return self._batch(company_id, batch_id)

    def review_accounting_batch(self, company_id, batch_id, snapshot_hash, reason):
        return self._transition_batch(company_id, batch_id, snapshot_hash, reason, "revisado")

    def close_accounting_batch(self, company_id, batch_id, snapshot_hash, reason):
        return self._transition_batch(company_id, batch_id, snapshot_hash, reason, "fechado")

    def _transition_batch(self, company_id, batch_id, snapshot_hash, reason, target):
        from .persistence import _text
        reason = _text(reason, "motivo", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            batch = self._batch(company_id, batch_id)
            if snapshot_hash != batch["snapshot_hash"]:
                raise ValueError("Hash da prévia divergente; confira o snapshot")
            required = "previa" if target == "revisado" else "revisado"
            if batch["status"] != required:
                raise ValueError("Transição inválida: fechamento exige revisão explícita da prévia vigente")
            blockers = self._batch_blockers(batch)
            # A correction of a closed batch may be reviewed for inspection,
            # but never replaces its reserved event or becomes a closed posting.
            if target == "revisado":
                blockers = [item for item in blockers if not item.startswith("Evento reservado")]
            if blockers:
                raise ValueError("; ".join(blockers))
            if target == "revisado":
                self.db.execute("UPDATE accounting_batches SET status=?,review_actor=?,review_reason=?,reviewed_at=? WHERE id=?", (target, self.actor, reason, self._now(), batch["id"]))
            else:
                self.db.execute("UPDATE accounting_batches SET status=?,closed_at=? WHERE id=?", (target, self._now(), batch["id"]))
            self._audit(company_id, "lote_contabil_"+target, {"batch_id": batch["id"], "snapshot_hash": snapshot_hash, "reason": reason})
        return self._batch(company_id, batch["id"])
