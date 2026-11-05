"""One ledger with declared opening balances, continuity and versioned work exports."""

import hashlib
import io
import json
import zipfile
from decimal import Decimal, localcontext
from .accounting_store import digest, dump, identifier
from .accounting_books import _csv
from .work_domain import check_operation


class WorkBooksMixin:
    def _work_finance_at(self, company_id, competence):
        """Reconstruct dated financial effects; mark undated historical decisions."""
        reversals = {}
        cancellations = {}
        for row in self.db.execute(
            "SELECT r.payload,r.snapshot_hash,c.competence FROM work_revisions r JOIN work_operations o ON o.id=r.operation_id JOIN work_cycles c ON c.id=o.cycle_id WHERE o.company_id=? AND r.state='escriturado'",
            (company_id,),
        ):
            try:
                p = json.loads(row["payload"])
            except (ValueError, TypeError):
                raise ValueError("Snapshot financeiro histórico alterado.") from None
            if digest(p) != row["snapshot_hash"]:
                raise ValueError("Snapshot financeiro histórico alterado.")
            if p.get("reverse_settlement"):
                reversals[p["reverse_settlement"]["settlement_id"]] = row["competence"]
            for item in p.get("cancel_titles", []):
                cancellations[item["title_id"]] = row["competence"]
        results = []
        for row in self.db.execute(
            "SELECT t.id FROM finance_titles t JOIN periods p ON p.id=t.period_id WHERE t.company_id=? AND p.processing_competence<=? ORDER BY t.due_date,t.id",
            (company_id, competence),
        ):
            title = self._finance_title(company_id, row["id"])
            title.pop("snapshot_hash")
            warnings = []
            parts = []
            for part in title["settlements"]:
                if part["paid_date"][:7] > competence:
                    continue
                if (
                    part["reversed_at"]
                    and part["id"] in reversals
                    and reversals[part["id"]] > competence
                ):
                    part = {
                        **part,
                        "reversed_at": None,
                        "reversal_actor": None,
                        "reversal_reason": None,
                    }
                elif part["reversed_at"] and part["id"] not in reversals:
                    warnings.append(
                        "Estorno do processo anterior sem competência econômica: considerado o estado histórico disponível."
                    )
                parts.append(part)
            if (
                title["canceled_at"]
                and title["id"] in cancellations
                and cancellations[title["id"]] > competence
            ):
                title.update(
                    canceled_at=None, cancellation_actor=None, cancellation_reason=None
                )
            elif title["canceled_at"] and title["id"] not in cancellations:
                warnings.append(
                    "Cancelamento do processo anterior sem competência econômica: considerado o estado histórico disponível."
                )
            paid = sum(
                (Decimal(p["amount"]) for p in parts if not p["reversed_at"]),
                Decimal(0),
            )
            balance = (
                Decimal(0) if title["canceled_at"] else Decimal(title["amount"]) - paid
            )
            title.update(
                settlements=parts,
                paid=format(paid, ".2f"),
                balance=format(balance, ".2f"),
                status=(
                    "cancelado"
                    if title["canceled_at"]
                    else "quitado" if not balance else "parcial" if paid else "aberto"
                ),
                basis_competence=competence,
                warnings=sorted(set(warnings)),
            )
            title["snapshot_hash"] = digest(title)
            results.append(title)
        return results

    def work_books(self, company_id, cycle_id):
        if self.db.in_transaction:
            return self._work_books_snapshot(company_id, cycle_id)
        with self.db:
            self.db.execute("BEGIN")
            return self._work_books_snapshot(company_id, cycle_id)

    def _work_books_snapshot(self, company_id, cycle_id):
        cycle = self._work_cycle(company_id, cycle_id)
        company = self._company(company_id)
        baseline = self.db.execute(
            "SELECT * FROM work_balance_starts WHERE company_id=?", (company_id,)
        ).fetchone()
        starts = (
            baseline["competence"]
            if baseline and baseline["competence"] <= cycle["competence"]
            else None
        )
        rows = []
        sources = []
        fiscal = []
        for revision in self.db.execute(
            "SELECT r.*,o.cycle_id,o.document_id,c.competence FROM work_revisions r JOIN work_operations o ON o.id=r.operation_id JOIN work_cycles c ON c.id=o.cycle_id WHERE o.company_id=? AND r.state='escriturado' AND c.competence<=? ORDER BY c.competence,r.operation_id",
            (company_id, cycle["competence"]),
        ):
            p = json.loads(revision["payload"])
            if digest(p) != revision["snapshot_hash"]:
                raise ValueError("Snapshot histórico alterado.")
            if starts and revision["competence"] < starts:
                continue
            expected = check_operation(
                p,
                {
                    "competence": revision["competence"],
                    "plan_id": p["context"]["plan"]["id"],
                },
                p["accounts_snapshot"],
            )
            movements = [
                json.loads(row["payload"])
                for row in self.db.execute(
                    "SELECT payload FROM work_movements WHERE revision_id=? ORDER BY line",
                    (revision["id"],),
                )
            ]
            if not expected["ready"] or expected["entries"] != movements:
                raise ValueError("Movimentos não correspondem ao snapshot escriturado.")
            kind = p["fiscal"]["operation"]
            sources.append(
                {
                    "kind": "operacao",
                    "operation_id": revision["operation_id"],
                    "version": revision["version"],
                    "snapshot_hash": revision["snapshot_hash"],
                    "competence": revision["competence"],
                }
            )
            for line in movements:
                rows.append(
                    {
                        "origin": "operacao",
                        "operation_id": revision["operation_id"],
                        "revision_id": revision["id"],
                        "competence": revision["competence"],
                        "opening": kind == "abertura",
                        "date": line["date"],
                        "group": line["group"],
                        "side": line["side"],
                        "amount": line["amount"],
                        "memo": line["memo"],
                        "account_id": line["account"]["id"],
                        "account_code": line["account"]["code"],
                        "account_description": line["account"]["description"],
                        "nature": line["account"]["nature"],
                        "plan_id": line["account"]["plan_id"],
                        "source_hash": revision["snapshot_hash"],
                        "document_id": revision["document_id"],
                    }
                )
            if (
                kind in {"entrada", "saida", "servico_tomado", "servico_prestado"}
                and revision["competence"] == cycle["competence"]
            ):
                fiscal.append(
                    {
                        "operation_id": revision["operation_id"],
                        "document_id": revision["document_id"],
                        **p["fiscal"],
                        "reference": p["reference"],
                        "source_hash": p.get("source_hash"),
                        "snapshot_hash": revision["snapshot_hash"],
                    }
                )
        for entry in self.list_fiscal_entries(company_id):
            revision = entry["current"]
            if not revision or revision["state"] != "revisado":
                continue
            period = self._owned("periods", company_id, revision["period_id"])
            if period["processing_competence"] != cycle[
                "competence"
            ] or not self._fiscal_guard(company_id, period["id"], entry["document_id"]):
                continue
            expected_hash = digest(
                {
                    "data": revision["data"],
                    "period": period,
                    "source": revision["source_snapshot"],
                    "version": revision["version"],
                    "entry": entry["id"],
                }
            )
            if expected_hash != revision["snapshot_hash"]:
                raise ValueError("Ficha fiscal histórica alterada.")
            fiscal.append(
                {
                    **revision["data"],
                    "origin": "legado",
                    "entry_id": entry["id"],
                    "document_id": entry["document_id"],
                    "snapshot_hash": revision["snapshot_hash"],
                    "source_hash": revision["source_hash"],
                }
            )
            sources.append(
                {
                    "kind": "fiscal_legado",
                    "entry_id": entry["id"],
                    "snapshot_hash": revision["snapshot_hash"],
                }
            )
        # Closed legacy sources remain immutable; never recreate their journals.
        for period in self.list_periods(company_id):
            if period["processing_competence"] > cycle["competence"] or (
                starts and period["processing_competence"] < starts
            ):
                continue
            plan_ids = {
                row["plan_id"]
                for row in self.list_accounting_batches(company_id)
                if row["period_id"] == period["id"] and row["status"] == "fechado"
            }
            plan_ids |= {
                row["plan_id"]
                for row in self.list_manual_journals(company_id, period["id"])
                if row["status"] == "fechado"
            }
            for plan_id in sorted(plan_ids):
                book = self._accounting_books(company_id, period["id"], plan_id)
                sources.extend(
                    {
                        **source,
                        "origin": "legado",
                        "competence": period["processing_competence"],
                    }
                    for source in book["sources"]
                )
                for line in book["diary"]:
                    account = self.db.execute(
                        "SELECT nature FROM accounts WHERE id=?", (line["account_id"],)
                    ).fetchone()
                    rows.append(
                        {
                            "origin": "legado",
                            "operation_id": None,
                            "revision_id": None,
                            "competence": period["processing_competence"],
                            "opening": False,
                            "date": line["date"],
                            "group": line["group"],
                            "side": line["side"],
                            "amount": line["amount"],
                            "memo": line["memo"],
                            "account_id": line["account_id"],
                            "account_code": line["account_code"],
                            "account_description": line["account_description"],
                            "nature": account["nature"],
                            "plan_id": plan_id,
                            "source_hash": line["snapshot_hash"],
                            "document_id": line["document_id"],
                        }
                    )
        rows.sort(
            key=lambda row: (
                row["date"],
                row["origin"],
                row["operation_id"] or 0,
                row["account_id"],
            )
        )
        accounts = {}
        diary = []
        ledger = []
        with localcontext() as context:
            context.prec = 40
            for row in rows:
                account = accounts.setdefault(
                    row["account_id"],
                    {
                        "account_id": row["account_id"],
                        "code": row["account_code"],
                        "description": row["account_description"],
                        "nature": row["nature"],
                        "plan_id": row["plan_id"],
                        "opening": Decimal(0),
                        "debit": Decimal(0),
                        "credit": Decimal(0),
                    },
                )
                value = Decimal(row["amount"]) * (1 if row["side"] == "D" else -1)
                if row["competence"] < cycle["competence"] or row["opening"]:
                    account["opening"] += value
                else:
                    account["debit" if row["side"] == "D" else "credit"] += Decimal(
                        row["amount"]
                    )
                    diary.append({**row, "sequence": len(diary) + 1})
            running = {key: account["opening"] for key, account in accounts.items()}
            for row in diary:
                running[row["account_id"]] += Decimal(row["amount"]) * (
                    1 if row["side"] == "D" else -1
                )
                ledger.append(
                    {**row, "balance": format(running[row["account_id"]], ".2f")}
                )
            trial = [
                {
                    **a,
                    "opening": format(a["opening"], ".2f"),
                    "debit": format(a["debit"], ".2f"),
                    "credit": format(a["credit"], ".2f"),
                    "closing": format(a["opening"] + a["debit"] - a["credit"], ".2f"),
                }
                for a in sorted(
                    accounts.values(), key=lambda a: (a["plan_id"], a["code"])
                )
            ]
            totals = {
                key: format(sum((Decimal(a[key]) for a in trial), Decimal(0)), ".2f")
                for key in ["opening", "debit", "credit", "closing"]
            }
        if (
            totals["debit"] != totals["credit"]
            or totals["opening"] != "0.00"
            or totals["closing"] != "0.00"
        ):
            raise ValueError(
                "Livro desequilibrado; confira integridade dos movimentos."
            )
        titles = self._work_finance_at(company_id, cycle["competence"])
        result = {
            "profile": "escritura-operacional-v2",
            "company": company,
            "cycle": cycle,
            "opening_declared": bool(starts),
            "opening_competence": starts,
            "balance_convention": "debit_minus_credit",
            "diary": diary,
            "ledger": ledger,
            "trial_balance": trial,
            "fiscal_book": fiscal,
            "finance": titles,
            "sources": sources,
            "totals": totals,
            "prosoft_validated": False,
            "pva_validated": False,
            "tax_assessment_performed": False,
        }
        return {**result, "snapshot_hash": digest(result)}

    def create_work_export(self, company_id, cycle_id, expected_hash, reason):
        from .persistence import _text

        reason = _text(reason, "motivo da exportação", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            book = self.work_books(company_id, cycle_id)
            if book["snapshot_hash"] != expected_hash:
                raise ValueError(
                    "Conferência alterada; gere nova prévia antes de exportar."
                )
            if not book["sources"]:
                raise ValueError("Nenhum movimento escriturado para exportar.")
            old = self.db.execute(
                "SELECT id FROM work_exports WHERE cycle_id=? AND snapshot_hash=?",
                (identifier(cycle_id), expected_hash),
            ).fetchone()
            if old:
                return self._work_export(company_id, old["id"])
            movements = (
                "sequence",
                "date",
                "origin",
                "operation_id",
                "document_id",
                "plan_id",
                "account_code",
                "account_description",
                "group",
                "side",
                "amount",
                "memo",
                "source_hash",
            )
            text = (
                "origin",
                "account_code",
                "account_description",
                "group",
                "side",
                "memo",
                "source_hash",
            )
            files = {
                "escrituracao.json": (dump(book) + "\n").encode(),
                "diario.csv": _csv(book["diary"], movements, text),
                "razao.csv": _csv(
                    sorted(
                        book["ledger"],
                        key=lambda row: (
                            row["plan_id"],
                            row["account_code"],
                            row["sequence"],
                        ),
                    ),
                    movements + ("balance",),
                    text,
                ),
                "balancete.csv": _csv(
                    book["trial_balance"],
                    (
                        "plan_id",
                        "code",
                        "description",
                        "nature",
                        "opening",
                        "debit",
                        "credit",
                        "closing",
                    ),
                    ("code", "description", "nature"),
                ),
                "fiscal.csv": _csv(
                    book["fiscal_book"],
                    (
                        "operation_id",
                        "document_id",
                        "operation",
                        "model",
                        "number",
                        "series",
                        "issued_date",
                        "posting_date",
                        "total",
                        "cfop",
                        "cst",
                        "icms_base",
                        "icms_amount",
                        "iss_base",
                        "iss_amount",
                        "pis_base",
                        "pis_amount",
                        "cofins_base",
                        "cofins_amount",
                        "issuer",
                        "buyer",
                        "reference",
                        "source_hash",
                        "snapshot_hash",
                    ),
                    (
                        "operation",
                        "model",
                        "number",
                        "series",
                        "cfop",
                        "cst",
                        "issuer",
                        "buyer",
                        "reference",
                        "source_hash",
                        "snapshot_hash",
                    ),
                ),
                "financeiro.csv": _csv(
                    book["finance"],
                    (
                        "id",
                        "direction",
                        "reference",
                        "counterparty",
                        "due_date",
                        "amount",
                        "paid",
                        "balance",
                        "status",
                        "snapshot_hash",
                    ),
                    (
                        "direction",
                        "reference",
                        "counterparty",
                        "status",
                        "snapshot_hash",
                    ),
                ),
            }
            manifest = {
                "profile": book["profile"],
                "company_id": company_id,
                "cycle_id": identifier(cycle_id),
                "snapshot_hash": expected_hash,
                "opening_declared": book["opening_declared"],
                "prosoft_validated": False,
                "pva_validated": False,
                "csv_text_prefix": "'",
                "files": [
                    {
                        "name": name,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data),
                    }
                    for name, data in files.items()
                ],
            }
            files["manifest.json"] = (dump(manifest) + "\n").encode()
            output = io.BytesIO()
            with zipfile.ZipFile(
                output, "w", compression=zipfile.ZIP_DEFLATED
            ) as packed:
                for name, data in files.items():
                    packed.writestr(name, data)
            files["pacote-escrituracao.zip"] = output.getvalue()
            export_id = self.db.execute(
                "INSERT INTO work_exports(company_id,cycle_id,snapshot_hash,manifest_sha256,actor,reason,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    company_id,
                    identifier(cycle_id),
                    expected_hash,
                    hashlib.sha256(files["manifest.json"]).hexdigest(),
                    self.actor,
                    reason,
                    self._now(),
                ),
            ).lastrowid
            for name, data in files.items():
                self.db.execute(
                    "INSERT INTO work_export_files VALUES(?,?,?,?)",
                    (export_id, name, data, hashlib.sha256(data).hexdigest()),
                )
            self._audit(
                company_id,
                "pacote_operacional_preservado",
                {
                    "export_id": export_id,
                    "snapshot_hash": expected_hash,
                    "reason": reason,
                },
            )
            return self._work_export(company_id, export_id)

    def _work_export(self, company_id, export_id):
        self._company(company_id)
        row = self.db.execute(
            "SELECT * FROM work_exports WHERE company_id=? AND id=?",
            (company_id, identifier(export_id)),
        ).fetchone()
        if not row:
            raise ValueError("Exportação não pertence à empresa.")
        files = []
        for file in self.db.execute(
            "SELECT name,content,sha256 FROM work_export_files WHERE export_id=? ORDER BY name",
            (identifier(export_id),),
        ):
            if hashlib.sha256(file["content"]).hexdigest() != file["sha256"]:
                raise ValueError("Arquivo preservado alterado.")
            files.append(
                {
                    "name": file["name"],
                    "sha256": file["sha256"],
                    "size": len(file["content"]),
                }
            )
        return {**dict(row), "files": files}

    def work_exports(self, company_id, cycle_id):
        self._work_cycle(company_id, cycle_id)
        return [
            self._work_export(company_id, row["id"])
            for row in self.db.execute(
                "SELECT id FROM work_exports WHERE company_id=? AND cycle_id=? ORDER BY id DESC",
                (company_id, identifier(cycle_id)),
            )
        ]

    def work_export_file(self, company_id, export_id, name):
        export = self._work_export(company_id, export_id)
        if name not in {file["name"] for file in export["files"]}:
            raise ValueError("Arquivo de exportação indisponível.")
        row = self.db.execute(
            "SELECT content FROM work_export_files WHERE export_id=? AND name=?",
            (identifier(export_id), name),
        ).fetchone()
        media = (
            "application/zip"
            if name.endswith(".zip")
            else (
                "application/json"
                if name.endswith(".json")
                else "text/csv; charset=utf-8"
            )
        )
        return {"name": name, "content": bytes(row["content"]), "media_type": media}
