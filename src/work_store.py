"""Application service for the redesigned competence → operation → books journey."""

import copy
import hashlib
import json
from decimal import Decimal
from .accounting_store import amount, digest, dump, identifier
from .work_domain import check_operation, OPERATIONS


class WorkStoreMixin:
    def _work_cycle(self, company_id, cycle_id):
        self._company(company_id)
        row = self.db.execute(
            "SELECT * FROM work_cycles WHERE company_id=? AND id=?",
            (company_id, identifier(cycle_id)),
        ).fetchone()
        if not row:
            raise ValueError("Competência não pertence à empresa.")
        result = dict(row)
        result["period"] = self._owned("periods", company_id, row["period_id"])
        result["plan"] = (
            self._owned("plans", company_id, row["plan_id"]) if row["plan_id"] else None
        )
        return result

    def work_cycles(self, company_id):
        self._company(company_id)
        return [
            self._work_cycle(company_id, row["id"])
            for row in self.db.execute(
                "SELECT id FROM work_cycles WHERE company_id=? ORDER BY competence DESC",
                (company_id,),
            )
        ]

    def save_work_cycle(
        self, company_id, reference, competence, plan_id, reason, expected_version=None
    ):
        from .persistence import _month, _text

        reference, competence = _month(reference), _month(competence)
        reason = _text(reason, "motivo", 2000)
        plan_id = identifier(plan_id) if plan_id else None
        if expected_version is not None and (
            type(expected_version) is not int or expected_version < 1
        ):
            raise ValueError(
                "Versão esperada da competência deve ser inteiro positivo; booleanos não são versões."
            )
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self._company(company_id)
            self.assert_module_period_open(company_id, competence, {"fiscal", "contabil"})
            if plan_id:
                self._owned("plans", company_id, plan_id)
            row = self.db.execute(
                "SELECT * FROM work_cycles WHERE company_id=? AND competence=?",
                (company_id, competence),
            ).fetchone()
            if row:
                if row["state"] != "aberta":
                    raise ValueError(
                        "Competência encerrada: crie reabertura motivada antes de alterar parâmetros."
                    )
                if expected_version != row["version"]:
                    raise ValueError(
                        "Configuração desatualizada; recarregue a competência."
                    )
            period = self.db.execute(
                "SELECT id FROM periods WHERE company_id=? AND reference_competence=? AND processing_competence=?",
                (company_id, reference, competence),
            ).fetchone()
            period_id = (
                period["id"]
                if period
                else self.db.execute(
                    "INSERT INTO periods(company_id,reference_competence,processing_competence) VALUES(?,?,?)",
                    (company_id, reference, competence),
                ).lastrowid
            )
            if row:
                self.db.execute(
                    "UPDATE work_cycles SET period_id=?,plan_id=?,version=version+1,actor=?,reason=? WHERE id=?",
                    (period_id, plan_id, self.actor, reason, row["id"]),
                )
                cycle_id = row["id"]
            else:
                cycle_id = self.db.execute(
                    "INSERT INTO work_cycles(company_id,competence,period_id,plan_id,actor,reason,created_at) VALUES(?,?,?,?,?,?,?)",
                    (
                        company_id,
                        competence,
                        period_id,
                        plan_id,
                        self.actor,
                        reason,
                        self._now(),
                    ),
                ).lastrowid
            self._audit(
                company_id,
                "competencia_operacional_configurada",
                {
                    "cycle_id": cycle_id,
                    "reference": reference,
                    "competence": competence,
                    "plan_id": plan_id,
                    "reason": reason,
                },
            )
        return self._work_cycle(company_id, cycle_id)

    def _work_legacy_document_reservation(self, company_id, document_id):
        row = self.db.execute(
            "SELECT batch_id FROM accounting_events WHERE company_id=? AND document_id=?",
            (company_id, document_id),
        ).fetchone()
        if row:
            return {"kind": "contabil", "id": row["batch_id"]}
        for entry in self.list_fiscal_entries(company_id):
            if (
                entry["document_id"] == document_id
                and entry["current"]
                and entry["current"]["state"] == "revisado"
                and self._fiscal_guard(
                    company_id, entry["current"]["period_id"], document_id
                )
            ):
                return {"kind": "fiscal", "id": entry["id"]}
        return None

    def _verify_work_originals(self, company_id, document_id):
        """Verify immutable proof bytes at review/post, without rewriting history."""
        if document_id is None:
            return
        self._owned("documents", company_id, document_id)
        for row in self.db.execute(
            "SELECT f.id,f.original,f.sha256,f.size FROM files f JOIN document_sources s ON s.file_id=f.id WHERE s.document_id=? AND f.company_id=? AND f.status!='excluido'",
            (document_id, company_id),
        ):
            content = bytes(row["original"])
            if (
                len(content) != row["size"]
                or hashlib.sha256(content).hexdigest() != row["sha256"]
            ):
                raise ValueError(
                    "Integridade do original divergente no arquivo #"
                    + str(row["id"])
                    + "; confira a cópia preservada antes de escriturar."
                )

    def _work_source(self, company_id, document_id):
        from .reconciliation import differences

        document = self._owned("documents", company_id, identifier(document_id))
        snapshot, fingerprint = self._base_source_snapshot(company_id, document_id)
        active = [
            row for row in snapshot["observations"] if row["file_status"] != "excluido"
        ]
        observations = [row for row in active if row["entity_kind"] == "documento"]
        parts = []
        for row in active:
            if row["entity_kind"] == "parcela" and row["installment_id"]:
                raw = row["normalized"]
                parts.append(
                    {
                        "id": row["installment_id"],
                        "file_id": row["file_id"],
                        "reference": raw.get("nDup", ""),
                        "due_date": raw.get("dVenc", ""),
                        "amount": raw.get("vDup", ""),
                        "issues": row["issues"],
                    }
                )
        return {
            "document_id": document["id"],
            "business_key": document["business_key"],
            "period_id": document["period_id"],
            "source_hash": digest(
                {
                    "canonical_source": fingerprint,
                    "evidence": [
                        (row["id"], row["snapshot_hash"])
                        for row in self.db.execute(
                            "SELECT r.id,r.snapshot_hash FROM source_revisions r JOIN source_inputs i ON i.id=r.input_id JOIN document_sources d ON d.file_id=i.file_id WHERE d.document_id=? ORDER BY r.id",
                            (identifier(document_id),),
                        )
                    ],
                }
            ),
            "observations": observations,
            "installments": parts,
            "differences": differences(observations),
            "files": snapshot["files"],
            "billing_issues": [
                {
                    "file_id": row["file_id"],
                    "locator": row["locator"],
                    "messages": row["issues"],
                }
                for row in active
                if row["entity_kind"] != "documento" and row["issues"]
            ],
        }

    def work_policies(self, company_id):
        self._company(company_id)
        return [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM work_policies WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            )
        ]

    def save_work_policy(
        self,
        company_id,
        plan_id,
        operation,
        reference,
        label,
        debit,
        credit,
        reason,
        approved=False,
    ):
        from .persistence import _month, _text

        reference = _month(reference)
        label = _text(label, "nome da política", 300)
        reason = _text(reason, "motivo", 2000)
        plan_id = identifier(plan_id)
        debit, credit = identifier(debit), identifier(credit)
        if not isinstance(operation, str) or operation not in OPERATIONS:
            raise ValueError("Natureza de operação inválida.")
        if not isinstance(approved, bool):
            raise ValueError("Aprovação deve ser booleana.")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self._owned("plans", company_id, plan_id)
            accounts = {
                row["id"]: row for row in self.list_accounts(company_id, plan_id)
            }
            if any(
                value not in accounts or accounts[value]["kind"] != "analitica"
                for value in (debit, credit)
            ):
                raise ValueError(
                    "A política exige contas analíticas do plano da empresa."
                )
            if debit == credit:
                raise ValueError(
                    "Débito e crédito da política devem ser contas diferentes."
                )
            version = self.db.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM work_policies WHERE company_id=? AND plan_id=? AND operation=? AND reference_competence=?",
                (company_id, plan_id, operation, reference),
            ).fetchone()[0]
            ident = self.db.execute(
                "INSERT INTO work_policies(company_id,plan_id,operation,reference_competence,version,state,debit_account_id,credit_account_id,label,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    company_id,
                    plan_id,
                    operation,
                    reference,
                    version,
                    "aprovada" if approved else "rascunho",
                    debit,
                    credit,
                    label,
                    self.actor,
                    reason,
                    self._now(),
                ),
            ).lastrowid
            self._audit(
                company_id,
                "politica_contabil_versionada",
                {
                    "policy_id": ident,
                    "version": version,
                    "approved": approved,
                    "reason": reason,
                },
            )
        return next(row for row in self.work_policies(company_id) if row["id"] == ident)

    def _work_policy(self, company_id, cycle, policy_id, operation):
        if not policy_id:
            return None
        row = next(
            (
                row
                for row in self.work_policies(company_id)
                if str(row["id"]) == str(policy_id)
            ),
            None,
        )
        if (
            not row
            or row["state"] != "aprovada"
            or (row["plan_id"], row["reference_competence"], row["operation"])
            != (cycle["plan_id"], cycle["period"]["reference_competence"], operation)
        ):
            raise ValueError(
                "Política não aprovada ou fora do plano/referência/natureza selecionados."
            )
        latest = max(
            value["version"]
            for value in self.work_policies(company_id)
            if (value["plan_id"], value["operation"], value["reference_competence"])
            == (row["plan_id"], row["operation"], row["reference_competence"])
        )
        if row["version"] != latest:
            raise ValueError("Política substituída; confira a versão vigente.")
        return row

    def prepare_work_operation(
        self,
        company_id,
        cycle_id,
        document_id=None,
        observation_id=None,
        policy_id=None,
        operation=None,
    ):
        cycle = self._work_cycle(company_id, cycle_id)
        company = self._company(company_id)
        source = self._work_source(company_id, document_id) if document_id else None
        if source:
            period = self._owned("periods", company_id, source["period_id"])
            if period["processing_competence"] != cycle["competence"]:
                raise ValueError(
                    "Documento pertence a outra competência dos movimentos."
                )
            chosen = next(
                (
                    row
                    for row in source["observations"]
                    if str(row["id"]) == str(observation_id)
                ),
                None,
            )
            if not chosen and len(source["observations"]) == 1:
                chosen = source["observations"][0]
            if not chosen:
                raise ValueError(
                    "Selecione explicitamente uma fonte entre as origens disponíveis."
                )
            raw = chosen["raw"]
            normalized = chosen["normalized"]
            proposed = operation or (
                "saida"
                if company["cnpj"] and normalized.get("issuer") == company["cnpj"]
                else (
                    "entrada"
                    if company["cnpj"] and normalized.get("buyer") == company["cnpj"]
                    else ""
                )
            )
            issued = normalized.get("issued_date", "")
            fiscal = {
                "operation": proposed,
                "model": raw.get("model", "55"),
                "number": normalized.get("number", ""),
                "series": normalized.get("series", ""),
                "issued_date": issued,
                "posting_date": issued if issued[:7] == cycle["competence"] else "",
                "total": normalized.get("total", ""),
                "issuer": normalized.get("issuer", ""),
                "buyer": normalized.get("buyer", ""),
                "key": source["business_key"],
            }
            parts = [
                row
                for row in source["installments"]
                if row["file_id"] == chosen["file_id"] and not row["issues"]
            ]
            counterparty = (
                (raw.get("issuer_name") or normalized.get("issuer", ""))
                if proposed in {"entrada", "servico_tomado"}
                else (raw.get("buyer_name") or normalized.get("buyer", ""))
            )
            finance = {
                "mode": "origem" if parts else "sem_cobranca",
                "direction": (
                    "pagar" if proposed in {"entrada", "servico_tomado"} else "receber"
                ),
                "counterparty": counterparty,
                "installments": [
                    {
                        "reference": p["reference"],
                        "due_date": p["due_date"],
                        "amount": p["amount"],
                        "installment_id": p["id"],
                    }
                    for p in parts
                ],
            }
        else:
            chosen = None
            fiscal = {
                "operation": operation or "ajuste",
                "model": "",
                "number": "",
                "issued_date": "",
                "posting_date": "",
                "total": "",
            }
            finance = {
                "mode": "sem_cobranca",
                "direction": "pagar",
                "counterparty": "",
                "installments": [],
            }
        policy = (
            self._work_policy(company_id, cycle, policy_id, fiscal["operation"])
            if policy_id
            else None
        )
        entries = (
            [
                {
                    "account_id": account,
                    "side": side,
                    "date": fiscal["posting_date"],
                    "group": "principal",
                    "amount": fiscal["total"],
                    "memo": str(fiscal.get("number") or "Operação manual"),
                }
                for side, account in [
                    ("D", policy["debit_account_id"]),
                    ("C", policy["credit_account_id"]),
                ]
            ]
            if policy
            else [
                {
                    "account_id": "",
                    "side": side,
                    "date": fiscal["posting_date"],
                    "group": "principal",
                    "amount": fiscal["total"],
                    "memo": "",
                }
                for side in ["D", "C"]
            ]
        )
        return {
            "reference": ("Documento " + str(fiscal["number"])) if source else "",
            "document_id": source["document_id"] if source else None,
            "observation_id": chosen["id"] if chosen else None,
            "source_hash": source["source_hash"] if source else None,
            "acknowledge_differences": False,
            "policy_id": policy_id,
            "fiscal": fiscal,
            "entries": entries,
            "finance": finance,
            "notes": "",
        }

    def _work_revision(self, company_id, operation_id, version=None):
        self._company(company_id)
        query = "SELECT r.*,o.company_id,o.cycle_id,o.document_id,o.reversal_of FROM work_revisions r JOIN work_operations o ON o.id=r.operation_id WHERE o.company_id=? AND o.id=?"
        values = [company_id, identifier(operation_id)]
        if version is not None:
            query += " AND r.version=?"
            values.append(identifier(version))
        row = self.db.execute(
            query + " ORDER BY r.version DESC LIMIT 1", values
        ).fetchone()
        if not row:
            raise ValueError("Operação não pertence à empresa.")
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        if digest(result["payload"]) != result["snapshot_hash"]:
            raise ValueError("Snapshot da operação alterado.")
        return result

    def work_operations(self, company_id, cycle_id):
        cycle = self._work_cycle(company_id, cycle_id)
        return [
            self.get_work_operation(company_id, row["id"])
            for row in self.db.execute(
                "SELECT id FROM work_operations WHERE cycle_id=? ORDER BY id DESC",
                (cycle["id"],),
            )
        ]

    def _work_validation(self, company_id, revision):
        cycle = self._work_cycle(company_id, revision["cycle_id"])
        payload = revision["payload"]
        if revision["state"] == "escriturado":
            result = check_operation(
                payload,
                {
                    "competence": cycle["competence"],
                    "plan_id": payload["context"]["plan"]["id"],
                },
                payload["accounts_snapshot"],
            )
            result["issues"].extend(self.tax_operation_issues(company_id, revision))
            result["ready"] = not result["issues"]
            return result

        accounts = (
            {
                str(row["id"]): row
                for row in self.list_accounts(company_id, cycle["plan_id"])
            }
            if cycle["plan_id"]
            else {}
        )
        source = (
            self._work_source(company_id, revision["document_id"])
            if revision["document_id"]
            else None
        )
        result = check_operation(payload, cycle, accounts, source)
        if any(
            accounts.get(key) != value
            for key, value in payload.get("accounts_snapshot", {}).items()
        ):
            result["issues"].append(
                {
                    "field": "entries",
                    "message": "Contas do plano alteradas; salve nova versão para conferir.",
                    "severity": "bloqueio",
                }
            )
        finance = (
            payload.get("finance") if isinstance(payload.get("finance"), dict) else {}
        )
        installments = (
            finance.get("installments")
            if isinstance(finance.get("installments"), list)
            else []
        )
        if finance.get("mode") != "sem_cobranca":
            for part in installments:
                if not isinstance(part, dict) or not part.get("existing_title_id"):
                    continue
                try:
                    title = self._finance_title(company_id, part["existing_title_id"])
                    linked = self.db.execute(
                        "SELECT operation_id FROM work_title_links WHERE title_id=?",
                        (title["id"],),
                    ).fetchone()
                    if (
                        title["canceled_at"]
                        or title["amount"] != amount(part.get("amount"))
                        or title["direction"] != finance.get("direction")
                        or title["due_date"] != part.get("due_date")
                        or linked
                    ):
                        raise ValueError(
                            "Título existente incompatível ou já vinculado a outra operação."
                        )
                except (ValueError, KeyError, TypeError) as error:
                    result["issues"].append(
                        {
                            "field": "finance.installments",
                            "message": str(error),
                            "severity": "bloqueio",
                        }
                    )
        for name in ["settlement", "reverse_settlement"]:
            operation = payload.get(name)
            if operation:
                try:
                    title = self._finance_title(company_id, operation["title_id"])
                    if title["snapshot_hash"] != operation["expected_hash"]:
                        raise ValueError(
                            "Título alterado; atualize a operação financeira."
                        )
                    if name == "settlement" and (
                        title["canceled_at"]
                        or payload["fiscal"]["operation"]
                        != (
                            "pagamento"
                            if title["direction"] == "pagar"
                            else "recebimento"
                        )
                        or payload["finance"].get("mode") != "sem_cobranca"
                        or Decimal(amount(operation["amount"]))
                        > Decimal(title["balance"])
                        or operation["amount"] != payload["fiscal"]["total"]
                        or operation["paid_date"] != payload["fiscal"]["posting_date"]
                    ):
                        raise ValueError(
                            "Liquidação incompatível com saldo, data ou valor da operação."
                        )
                    if name == "reverse_settlement" and not payload.get("reversal"):
                        raise ValueError(
                            "Estorno financeiro exige estorno contábil vinculado."
                        )
                    if name == "reverse_settlement" and not any(
                        row["id"] == operation["settlement_id"]
                        and not row["reversed_at"]
                        for row in title["settlements"]
                    ):
                        raise ValueError("Baixa indisponível para estorno.")
                except (ValueError, KeyError, TypeError) as error:
                    result["issues"].append(
                        {"field": name, "message": str(error), "severity": "bloqueio"}
                    )
        for canceled in payload.get("cancel_titles", []):
            try:
                title = self._finance_title(company_id, canceled["title_id"])
                if (
                    not payload.get("reversal")
                    or title["snapshot_hash"] != canceled["expected_hash"]
                    or title["canceled_at"]
                    or any(not p["reversed_at"] for p in title["settlements"])
                ):
                    raise ValueError(
                        "Título alterado ou com liquidação ativa; estorne a liquidação antes do reconhecimento."
                    )
            except (ValueError, KeyError, TypeError) as error:
                result["issues"].append(
                    {
                        "field": "cancel_titles",
                        "message": str(error),
                        "severity": "bloqueio",
                    }
                )
        if payload.get("fiscal", {}).get("operation") in (
            "pagamento",
            "recebimento",
        ) and not payload.get("settlement"):
            result["issues"].append(
                {
                    "field": "settlement",
                    "message": "Liquidação exige título vinculado.",
                    "severity": "bloqueio",
                }
            )
        if payload.get("fiscal", {}).get("operation") == "abertura":
            if payload["fiscal"].get("posting_date") != cycle["competence"] + "-01":
                result["issues"].append(
                    {
                        "field": "fiscal.posting_date",
                        "message": "A abertura deve representar o início da competência (dia 01).",
                        "severity": "bloqueio",
                    }
                )
            baseline = self.db.execute(
                "SELECT revision_id FROM work_balance_starts WHERE company_id=?",
                (company_id,),
            ).fetchone()
            if baseline and baseline["revision_id"] != revision["id"]:
                result["issues"].append(
                    {
                        "field": "opening",
                        "message": "Abertura já estabelecida; use ajuste para diferenças posteriores.",
                        "severity": "bloqueio",
                    }
                )

        if payload.get("context", {}).get("cycle_version") != cycle["version"]:
            result["issues"].append(
                {
                    "field": "context",
                    "message": "Parâmetros da competência alterados; salve e confira uma nova versão.",
                    "severity": "bloqueio",
                }
            )
        try:
            policy = self._work_policy(
                company_id,
                cycle,
                payload.get("policy_id"),
                payload.get("fiscal", {}).get("operation"),
            )
            if policy and any(
                str(line.get("account_id"))
                != str(
                    policy["debit_account_id"]
                    if line.get("side") == "D"
                    else policy["credit_account_id"]
                )
                for line in payload.get("entries", [])
                if isinstance(line, dict)
            ):
                raise ValueError(
                    "Partidas divergem da política selecionada; corrija ou use partidas manuais explícitas."
                )
        except ValueError as error:
            result["issues"].append(
                {"field": "policy_id", "message": str(error), "severity": "bloqueio"}
            )
        reversal = payload.get("reversal")
        if revision.get("reversal_of") or reversal:
            try:
                if not reversal or revision.get("reversal_of") != identifier(
                    reversal["operation_id"]
                ):
                    raise ValueError("Vínculo de estorno inválido.")
                original = self._work_revision(company_id, reversal["operation_id"])
                link = self.db.execute(
                    "SELECT s.id,s.title_id FROM work_settlement_links l JOIN finance_settlements s ON s.id=l.settlement_id WHERE l.operation_id=?",
                    (original["operation_id"],),
                ).fetchone()
                reverse = payload.get("reverse_settlement")
                if bool(link) != bool(reverse) or (
                    link
                    and (reverse.get("settlement_id"), reverse.get("title_id"))
                    != (link["id"], link["title_id"])
                ):
                    raise ValueError(
                        "Estorno deve preservar o vínculo da liquidação original."
                    )
                expected_lines = [
                    {
                        **line,
                        "side": "C" if line["side"] == "D" else "D",
                        "date": payload["fiscal"]["posting_date"],
                    }
                    for line in original["payload"]["entries"]
                ]
                if (
                    original["state"] != "escriturado"
                    or original["snapshot_hash"] != reversal["snapshot_hash"]
                    or expected_lines != payload["entries"]
                    or payload["finance"].get("mode") != "sem_cobranca"
                    or payload["fiscal"]["operation"] != "ajuste"
                    or set(c["title_id"] for c in payload.get("cancel_titles", []))
                    != set(
                        r["title_id"]
                        for r in self.db.execute(
                            "SELECT title_id FROM work_title_links WHERE operation_id=?",
                            (original["operation_id"],),
                        )
                    )
                ):
                    raise ValueError(
                        "Estorno deve inverter integralmente as partidas originais."
                    )
            except (ValueError, KeyError, TypeError) as error:
                result["issues"].append(
                    {"field": "reversal", "message": str(error), "severity": "bloqueio"}
                )
        result["issues"].extend(self.tax_operation_issues(company_id, revision))
        result["ready"] = not result["issues"]
        return result

    def get_work_operation(self, company_id, operation_id):
        revision = self._work_revision(company_id, operation_id)
        result = {**revision, "validation": self._work_validation(company_id, revision)}
        result["history"] = [
            dict(row)
            for row in self.db.execute(
                "SELECT version,state,snapshot_hash,actor,reason,created_at,review_actor,review_reason,reviewed_at,posted_at FROM work_revisions WHERE operation_id=? ORDER BY version DESC",
                (revision["operation_id"],),
            )
        ]
        result["titles"] = [
            self._finance_title(company_id, row["title_id"])
            for row in self.db.execute(
                "SELECT title_id FROM work_title_links WHERE operation_id=?",
                (revision["operation_id"],),
            )
        ]
        return result

    def save_work_operation(
        self,
        company_id,
        cycle_id,
        payload,
        reason,
        request_key,
        operation_id=None,
        expected_version=0,
        *,
        _in_transaction=False,
    ):
        from .persistence import _text

        reason = _text(reason, "motivo", 2000)
        request_key = _text(request_key, "tentativa", 100)
        if not isinstance(payload, dict) or len(dump(payload)) > 2 * 1024 * 1024:
            raise ValueError("Ficha inválida ou maior que 2 MiB.")
        if any(
            key in payload and not isinstance(payload[key], dict)
            for key in ["fiscal", "finance"]
        ) or ("entries" in payload and not isinstance(payload["entries"], list)):
            raise ValueError(
                "Ficha exige objetos fiscal/financeiro e lista de partidas; campos podem estar incompletos."
            )
        if type(expected_version) != int or expected_version < 0:
            raise ValueError("Versão esperada inválida.")
        fingerprint = digest(
            {
                "cycle_id": identifier(cycle_id),
                "payload": payload,
                "reason": reason,
                "operation_id": operation_id,
                "expected_version": expected_version,
            }
        )
        with self._import_transaction(_in_transaction):
            if not _in_transaction:
                self.db.execute("BEGIN IMMEDIATE")
            cycle = self._work_cycle(company_id, cycle_id)
            if cycle["state"] != "aberta":
                raise ValueError(
                    "Competência encerrada; nenhuma nova operação será gravada."
                )
            old = self.db.execute(
                "SELECT * FROM work_requests WHERE company_id=? AND request_key=?",
                (company_id, request_key),
            ).fetchone()
            if old:
                if old["request_hash"] != fingerprint:
                    raise ValueError("Tentativa já utilizada com outro conteúdo.")
                row = self.db.execute(
                    "SELECT operation_id,version FROM work_revisions WHERE id=?",
                    (old["revision_id"],),
                ).fetchone()
                return self._work_revision(
                    company_id, row["operation_id"], row["version"]
                )
            previous = (
                self._work_revision(company_id, operation_id) if operation_id else None
            )
            self.assert_operation_modules_open(company_id, cycle, payload)
            if previous:
                self.assert_operation_modules_open(company_id, cycle, previous["payload"])
                if previous["payload"].get("tax_calculation") and not payload.get("tax_calculation"):
                    _text(payload.get("tax_override_reason"), "Motivo para substituir cálculo por valores informados", 2000)
            if previous and (
                previous["state"] in {"escriturado", "dispensado"}
                or previous["cycle_id"] != cycle["id"]
            ):
                raise ValueError(
                    "Operação efetivada ou de outra competência não permite edição; registre ajuste vinculado."
                )
            if expected_version != (previous["version"] if previous else 0):
                raise ValueError("Versão desatualizada; recarregue a ficha.")
            document_id = (
                identifier(payload["document_id"])
                if payload.get("document_id")
                else None
            )
            if previous and document_id != previous["document_id"]:
                raise ValueError("A edição deve preservar o vínculo documental.")
            if document_id:
                source = self._work_source(company_id, document_id)
                if (
                    self._owned("periods", company_id, source["period_id"])[
                        "processing_competence"
                    ]
                    != cycle["competence"]
                ):
                    raise ValueError("Documento fora da competência dos movimentos.")
                if self._work_legacy_document_reservation(company_id, document_id):
                    raise ValueError(
                        "Documento já escriturado no histórico anterior; não duplicar o efeito."
                    )
                existing = self.db.execute(
                    "SELECT id FROM work_operations WHERE company_id=? AND document_id=?",
                    (company_id, document_id),
                ).fetchone()
                if existing and (
                    not previous or existing["id"] != previous["operation_id"]
                ):
                    raise ValueError(
                        "Documento já possui operação canônica; abra a ficha existente."
                    )
            target = copy.deepcopy(payload)
            target["context"] = {
                "company": self._company(company_id),
                "cycle_id": cycle["id"],
                "cycle_version": cycle["version"],
                "competence": cycle["competence"],
                "reference_competence": cycle["period"]["reference_competence"],
                "plan": cycle["plan"],
            }
            current_accounts = (
                {
                    str(row["id"]): row
                    for row in self.list_accounts(company_id, cycle["plan_id"])
                }
                if cycle["plan_id"]
                else {}
            )
            target["accounts_snapshot"] = {
                str(line.get("account_id")): current_accounts[
                    str(line.get("account_id"))
                ]
                for line in target.get("entries", [])
                if isinstance(line, dict)
                and str(line.get("account_id")) in current_accounts
            }
            target["policy_snapshot"] = (
                self._work_policy(
                    company_id,
                    cycle,
                    target.get("policy_id"),
                    target.get("fiscal", {}).get("operation"),
                )
                if target.get("policy_id")
                else None
            )
            if not previous:
                operation_id = self.db.execute(
                    "INSERT INTO work_operations(company_id,cycle_id,document_id,created_at) VALUES(?,?,?,?)",
                    (company_id, cycle["id"], document_id, self._now()),
                ).lastrowid
            else:
                self.db.execute(
                    "UPDATE work_revisions SET state='substituido' WHERE id=?",
                    (previous["id"],),
                )
            version = previous["version"] + 1 if previous else 1
            revision_id = self.db.execute(
                "INSERT INTO work_revisions(operation_id,version,state,payload,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    version,
                    "rascunho",
                    dump(target),
                    digest(target),
                    self.actor,
                    reason,
                    self._now(),
                ),
            ).lastrowid
            self.db.execute(
                "INSERT INTO work_requests VALUES(?,?,?,?)",
                (company_id, request_key, fingerprint, revision_id),
            )
            self._audit(
                company_id,
                "operacao_versionada",
                {
                    "operation_id": operation_id,
                    "version": version,
                    "snapshot_hash": digest(target),
                    "reason": reason,
                },
            )
        return self.get_work_operation(company_id, operation_id)

    def review_work_operation(
        self, company_id, operation_id, expected_hash, reason, target="revisado"
    ):
        from .persistence import _text

        reason = _text(reason, "motivo da conferência", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            revision = self._work_revision(company_id, operation_id)
            cycle = self._work_cycle(company_id, revision["cycle_id"])
            if cycle["state"] != "aberta":
                raise ValueError("Competência encerrada.")
            self.assert_operation_modules_open(company_id, cycle, revision["payload"])
            if (
                revision["snapshot_hash"] != expected_hash
                or digest(revision["payload"]) != expected_hash
            ):
                raise ValueError("Versão alterada; confira novamente.")
            if (
                target not in {"revisado", "dispensado"}
                or revision["state"] != "rascunho"
            ):
                raise ValueError("Transição de conferência inválida.")
            if target == "revisado":
                validation = self._work_validation(company_id, revision)
                if not validation["ready"]:
                    raise ValueError(
                        "; ".join(issue["message"] for issue in validation["issues"])
                    )
            if target == "revisado":
                self._verify_work_originals(company_id, revision["document_id"])
            self.db.execute(
                "UPDATE work_revisions SET state=?,review_actor=?,review_reason=?,reviewed_at=? WHERE id=?",
                (target, self.actor, reason, self._now(), revision["id"]),
            )
            self._audit(
                company_id,
                "operacao_" + target,
                {
                    "operation_id": revision["operation_id"],
                    "snapshot_hash": expected_hash,
                    "reason": reason,
                },
            )
        return self.get_work_operation(company_id, operation_id)

    def post_work_operation(self, company_id, operation_id, expected_hash, reason):
        from .persistence import _text

        reason = _text(reason, "motivo da escrituração", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            revision = self._work_revision(company_id, operation_id)
            cycle = self._work_cycle(company_id, revision["cycle_id"])
            if (
                revision["snapshot_hash"] != expected_hash
                or digest(revision["payload"]) != expected_hash
            ):
                raise ValueError("Snapshot alterado; confira novamente.")
            if revision["state"] == "escriturado":
                return self.get_work_operation(company_id, operation_id)
            self.assert_operation_modules_open(company_id, cycle, revision["payload"])
            if (
                cycle["state"] != "aberta"
                or revision["state"] != "revisado"
                or not revision["reviewed_at"]
            ):
                raise ValueError("Confira a versão completa antes de escriturar.")
            validation = self._work_validation(company_id, revision)
            if not validation["ready"]:
                raise ValueError(
                    "; ".join(issue["message"] for issue in validation["issues"])
                )
            self._verify_work_originals(company_id, revision["document_id"])
            if revision["document_id"] and self._work_legacy_document_reservation(
                company_id, revision["document_id"]
            ):
                raise ValueError(
                    "Documento reservado pelo histórico fiscal/contábil anterior."
                )
            for line in validation["entries"]:
                self.db.execute(
                    "INSERT INTO work_movements VALUES(?,?,?)",
                    (revision["id"], line["line"], dump(line)),
                )

            settlement = revision["payload"].get("settlement")
            if settlement:
                key = "work-settlement:" + str(revision["operation_id"])
                data = {
                    "amount": amount(settlement["amount"]),
                    "paid_date": settlement["paid_date"],
                    "reference": settlement["reference"],
                    "reason": reason,
                }
                settlement_id = self.db.execute(
                    "INSERT INTO finance_settlements(title_id,amount,paid_date,reference,reason,request_key,request_hash,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        identifier(settlement["title_id"]),
                        data["amount"],
                        data["paid_date"],
                        data["reference"],
                        reason,
                        key,
                        digest(data),
                        self.actor,
                        self._now(),
                    ),
                ).lastrowid
                self.db.execute(
                    "INSERT INTO work_settlement_links VALUES(?,?)",
                    (revision["operation_id"], settlement_id),
                )
            reverse = revision["payload"].get("reverse_settlement")
            if reverse:
                self.db.execute(
                    "UPDATE finance_settlements SET reversed_at=?,reversal_actor=?,reversal_reason=? WHERE id=?",
                    (self._now(), self.actor, reason, reverse["settlement_id"]),
                )
            if revision["payload"]["fiscal"]["operation"] == "abertura":
                self.db.execute(
                    "INSERT INTO work_balance_starts VALUES(?,?,?,?,?)",
                    (
                        company_id,
                        revision["id"],
                        cycle["competence"],
                        revision["payload"].get("opening_zero") is True,
                        reason,
                    ),
                )
            for title in revision["payload"].get("cancel_titles", []):
                self.db.execute(
                    "UPDATE finance_titles SET canceled_at=?,cancellation_actor=?,cancellation_reason=? WHERE id=?",
                    (self._now(), self.actor, reason, title["title_id"]),
                )
            finance = revision["payload"]["finance"]
            if finance["mode"] != "sem_cobranca":
                for part in finance["installments"]:
                    if part.get("existing_title_id"):
                        title = self._finance_title(
                            company_id, part["existing_title_id"]
                        )
                        if (
                            title["canceled_at"]
                            or title["amount"] != amount(part["amount"])
                            or title["direction"] != finance["direction"]
                            or title["due_date"] != part["due_date"]
                        ):
                            raise ValueError(
                                "Título existente não corresponde ao valor/direção ou está cancelado."
                            )
                        title_id = title["id"]
                    else:
                        data = {
                            "period_id": cycle["period_id"],
                            "direction": finance["direction"],
                            "reference": revision["payload"]["reference"]
                            + " / "
                            + part["reference"],
                            "counterparty": finance["counterparty"],
                            "due_date": part["due_date"],
                            "amount": amount(part["amount"]),
                            "reason": reason,
                        }
                        key = (
                            "work:"
                            + str(revision["operation_id"])
                            + ":"
                            + part["reference"]
                        )
                        title_id = self.db.execute(
                            "INSERT INTO finance_titles(company_id,period_id,direction,reference,counterparty,due_date,amount,request_key,request_hash,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (
                                company_id,
                                data["period_id"],
                                data["direction"],
                                data["reference"],
                                data["counterparty"],
                                data["due_date"],
                                data["amount"],
                                key,
                                digest(data),
                                reason,
                                self.actor,
                                self._now(),
                            ),
                        ).lastrowid
                    installment_id = (
                        identifier(part["installment_id"])
                        if finance["mode"] == "origem"
                        else None
                    )
                    self.db.execute(
                        "INSERT INTO work_title_links VALUES(?,?,?,?)",
                        (
                            revision["operation_id"],
                            title_id,
                            installment_id,
                            part["reference"],
                        ),
                    )
            self.db.execute(
                "UPDATE work_revisions SET state='escriturado',posted_at=? WHERE id=?",
                (self._now(), revision["id"]),
            )
            self._audit(
                company_id,
                "operacao_escriturada",
                {
                    "operation_id": revision["operation_id"],
                    "revision_id": revision["id"],
                    "snapshot_hash": expected_hash,
                    "movements": len(validation["entries"]),
                    "reason": reason,
                },
            )
        return self.get_work_operation(company_id, operation_id)

    def work_overview(self, company_id, cycle_id):
        cycle = self._work_cycle(company_id, cycle_id)
        periods = [
            p
            for p in self.list_periods(company_id)
            if p["processing_competence"] == cycle["competence"]
        ]
        ids = {p["id"] for p in periods}
        operations = self.work_operations(company_id, cycle_id)
        by_document = {o["document_id"]: o for o in operations if o["document_id"]}
        documents = []
        for doc in self.list_documents(company_id):
            if doc["period_id"] not in ids:
                continue
            source = self._work_source(company_id, doc["id"])
            old = self._work_legacy_document_reservation(company_id, doc["id"])
            op = by_document.get(doc["id"])
            documents.append(
                {
                    "id": doc["id"],
                    "number": doc["payload"].get("number"),
                    "model": doc["payload"].get("model"),
                    "total": doc["payload"].get("total"),
                    "key": doc["business_key"],
                    "source": source,
                    "operation_id": op["operation_id"] if op else None,
                    "state": op["state"] if op else "legado" if old else "a_escriturar",
                    "legacy_reservation": old,
                }
            )
        imports = [
            b for b in self.list_import_batches(company_id) if b["period_id"] in ids
        ]
        files = [f for f in self.list_files(company_id) if f["period_id"] in ids]
        pending = [d for d in documents if d["state"] == "a_escriturar"]
        blocked = [
            o
            for o in operations
            if o["state"] not in {"escriturado", "dispensado"}
            and not o["validation"]["ready"]
        ]
        evidence = [
            r
            for r in self.source_inbox(company_id)
            if r["evidence"].get("cycle_id") == cycle["id"]
        ]
        open_forms = [
            dict(r)
            for r in self.db.execute(
                "SELECT id,version FROM work_tabs WHERE company_id=? AND cycle_id=? AND operation_id IS NULL AND closed=0",
                (company_id, cycle["id"]),
            )
        ]
        legacy = self.work_legacy(company_id, cycle_id)
        counts = {
            "legacy_pending": sum(r["can_resume"] for r in legacy),
            "documents": len(documents),
            "open_forms": len(open_forms),
            "pending_documents": len(pending),
            "drafts": sum(o["state"] == "rascunho" for o in operations),
            "reviewed": sum(o["state"] == "revisado" for o in operations),
            "posted": sum(o["state"] == "escriturado" for o in operations),
            "blocked": len(blocked),
            "rejected_inputs": sum(b["counts"].get("rejeitado", 0) for b in imports)
            + sum(
                not r["evidence"].get("document_ids")
                and r["evidence"]["state"] != "descartado"
                for r in evidence
            ),
        }
        next_action = (
            "recepcao"
            if not files
            else (
                "escrituracao"
                if pending or counts["drafts"]
                else "conferencia" if counts["reviewed"] else "livros"
            )
        )
        return {
            "cycle": cycle,
            "documents": documents,
            "operations": operations,
            "imports": imports,
            "files": files,
            "counts": counts,
            "next_action": next_action,
            "policies": self.work_policies(company_id),
            "legacy": legacy,
            "snapshot_hash": digest(
                {
                    "cycle": cycle,
                    "legacy": [
                        (
                            r["kind"],
                            r["id"],
                            r["state"],
                            r["snapshot_hash"],
                            r["operation_id"],
                        )
                        for r in legacy
                    ],
                    "evidence": [(r["input_id"], r["snapshot_hash"]) for r in evidence],
                    "forms": [(r["id"], r["version"]) for r in open_forms],
                    "sources": [
                        (d["id"], d["source"]["source_hash"]) for d in documents
                    ],
                    "operations": [
                        (
                            o["operation_id"],
                            o["version"],
                            o["state"],
                            o["snapshot_hash"],
                        )
                        for o in operations
                    ],
                }
            ),
        }

    def work_legacy(self, company_id, cycle_id):
        cycle = self._work_cycle(company_id, cycle_id)
        ids = {
            p["id"]
            for p in self.list_periods(company_id)
            if p["processing_competence"] == cycle["competence"]
        }
        result = []
        for kind, rows in [
            ("manual", self.list_manual_journals(company_id)),
            ("documental", self.list_accounting_batches(company_id)),
            ("fiscal", self.list_fiscal_entries(company_id)),
        ]:
            for row in rows:
                data = row["current"] if kind == "fiscal" else row
                if not data or data["period_id"] not in ids:
                    continue
                ident = row["journal_id"] if kind == "manual" else row["id"]
                state = data.get("status") or data.get("state")
                linked = self.db.execute(
                    "SELECT operation_id FROM work_legacy_links WHERE kind=? AND source_id=?",
                    (kind, ident),
                ).fetchone()
                result.append(
                    {
                        "kind": kind,
                        "id": ident,
                        "state": state,
                        "version": data["version"],
                        "snapshot_hash": data["snapshot_hash"],
                        "operation_id": linked["operation_id"] if linked else None,
                        "can_resume": not linked
                        and cycle["state"] == "aberta"
                        and kind != "documental"
                        and not (
                            kind == "fiscal"
                            and self._fiscal_guard(
                                company_id, data["period_id"], row["document_id"]
                            )
                        )
                        and state in {"previa", "revisado", "rascunho"},
                        "snapshot": data.get("snapshot") or data.get("data"),
                    }
                )
        for row in self.db.execute(
            "SELECT * FROM fiscal_workspaces WHERE company_id=? AND actor=? ORDER BY id",
            (company_id, self.actor),
        ):
            if row["period_id"] not in ids:
                continue
            data = dict(row)
            data["data"] = json.loads(data["data"])
            linked = self.db.execute(
                "SELECT operation_id FROM work_legacy_links WHERE kind='guia_fiscal' AND source_id=?",
                (row["id"],),
            ).fetchone()
            result.append(
                {
                    "kind": "guia_fiscal",
                    "id": row["id"],
                    "state": "encerrada" if row["closed"] else "rascunho",
                    "version": row["version"],
                    "snapshot_hash": digest(data),
                    "operation_id": linked["operation_id"] if linked else None,
                    "can_resume": not linked
                    and not row["closed"]
                    and cycle["state"] == "aberta",
                    "snapshot": data,
                }
            )
        return result

    def resume_work_legacy(
        self, company_id, cycle_id, kind, source_id, expected_hash, reason, request_key
    ):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            selected = next(
                (
                    row
                    for row in self.work_legacy(company_id, cycle_id)
                    if row["kind"] == kind and row["id"] == identifier(source_id)
                ),
                None,
            )
            if (
                not selected
                or not selected["can_resume"]
                or selected["snapshot_hash"] != expected_hash
            ):
                raise ValueError(
                    "Registro anterior fechado, retomado ou alterado; consulte seu histórico."
                )
            if kind == "documental":
                raise ValueError(
                    "Lote documental antigo não será convertido sem associação por documento; abra cada operação da fila."
                )
            if kind == "manual":
                old = self._manual_revision(company_id, source_id)
                payload = self.prepare_work_operation(
                    company_id, cycle_id, operation="ajuste"
                )
                snapshot = old["snapshot"]
                payload["reference"] = snapshot["reference"]
                payload["fiscal"]["posting_date"] = snapshot["entries"][0]["date"]
                payload["fiscal"]["total"] = snapshot["totals"]["debit"]
                payload["entries"] = [
                    {
                        k: v
                        for k, v in {
                            **line,
                            "account_id": line["account"]["id"],
                        }.items()
                        if k != "account"
                    }
                    for line in snapshot["entries"]
                ]
            elif kind == "guia_fiscal":
                raw = selected["snapshot"]["data"]
                fields = (
                    raw.get("data")
                    if isinstance(raw.get("data"), dict)
                    else (
                        raw.get("fields")
                        if isinstance(raw.get("fields"), dict)
                        else raw
                    )
                )
                document_id = raw.get("document_id") or fields.get("document_id")
                payload = self.prepare_work_operation(
                    company_id,
                    cycle_id,
                    document_id=document_id,
                    observation_id=raw.get("observation_id"),
                )
                payload["reference"] = selected["snapshot"]["title"]
                keys = {
                    "operation",
                    "model",
                    "number",
                    "series",
                    "key",
                    "issued_date",
                    "entry_date",
                    "posting_date",
                    "issuer",
                    "buyer",
                    "total",
                    "notes",
                    "participant_id",
                    "service_code",
                    "municipality",
                    "iss_base",
                    "iss_amount",
                }
                payload["fiscal"].update({k: v for k, v in fields.items() if k in keys})
                payload["notes"] = raw.get("notes", fields.get("notes", ""))
                payload["legacy_workspace"] = {
                    "id": identifier(source_id),
                    "version": selected["version"],
                    "snapshot_hash": expected_hash,
                    "original": raw,
                }
                for line in payload["entries"]:
                    line.update(
                        date=payload["fiscal"].get("posting_date", ""),
                        amount=payload["fiscal"].get("total", ""),
                    )
            else:
                old = (
                    self.get_fiscal_entry(company_id, source_id)
                    if hasattr(self, "get_fiscal_entry")
                    else next(
                        row
                        for row in self.list_fiscal_entries(company_id)
                        if row["id"] == identifier(source_id)
                    )
                )
                payload = (
                    self.prepare_work_operation(
                        company_id, cycle_id, document_id=old.get("document_id")
                    )
                    if old.get("document_id")
                    else self.prepare_work_operation(company_id, cycle_id)
                )
                payload["fiscal"] = old["current"]["data"]
                payload["reference"] = "Retomada fiscal #" + str(source_id)
            saved = self.save_work_operation(
                company_id, cycle_id, payload, reason, request_key, _in_transaction=True
            )
            self.db.execute(
                "INSERT INTO work_legacy_links VALUES(?,?,?,?,?)",
                (
                    kind,
                    identifier(source_id),
                    company_id,
                    saved["operation_id"],
                    expected_hash,
                ),
            )
            self._audit(
                company_id,
                "rascunho_anterior_retomado",
                {
                    "kind": kind,
                    "source_id": source_id,
                    "operation_id": saved["operation_id"],
                    "reason": reason,
                },
            )
            return saved

    def save_work_tab(
        self,
        company_id,
        cycle_id,
        title,
        data,
        tab_id=None,
        expected_version=0,
        closed=False,
        operation_id=None,
    ):
        from .persistence import _text

        self._work_cycle(company_id, cycle_id)
        title = _text(title, "nome da guia", 300)
        if (
            not isinstance(data, dict)
            or len(dump(data)) > 2 * 1024 * 1024
            or type(expected_version) != int
            or type(closed) != bool
        ):
            raise ValueError("Rascunho inválido ou grande demais.")
        if operation_id and self._work_revision(company_id, operation_id)[
            "cycle_id"
        ] != identifier(cycle_id):
            raise ValueError("Operação fora da competência da guia.")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            if tab_id:
                old = self.db.execute(
                    "SELECT * FROM work_tabs WHERE id=? AND company_id=? AND cycle_id=? AND actor=?",
                    (identifier(tab_id), company_id, identifier(cycle_id), self.actor),
                ).fetchone()
                if not old or old["version"] != expected_version:
                    raise ValueError("Guia alterada; recarregue antes de sobrescrever.")
                if json.loads(old["data"]).get("payload") != data.get("payload"):
                    self.assert_operation_modules_open(company_id, self._work_cycle(company_id, cycle_id), data.get("payload") or {})
                    self.assert_operation_modules_open(company_id, self._work_cycle(company_id, cycle_id), json.loads(old["data"]).get("payload") or {})
                self.db.execute(
                    "UPDATE work_tabs SET title=?,data=?,version=version+1,closed=?,updated_at=?,operation_id=? WHERE id=?",
                    (title, dump(data), closed, self._now(), operation_id, old["id"]),
                )
            else:
                if expected_version != 0:
                    raise ValueError("Nova guia exige versão zero.")
                self.assert_operation_modules_open(company_id, self._work_cycle(company_id, cycle_id), data.get("payload") or {})
                tab_id = self.db.execute(
                    "INSERT INTO work_tabs(company_id,cycle_id,actor,operation_id,title,data,version,closed,updated_at) VALUES(?,?,?,?,?,?,1,?,?)",
                    (
                        company_id,
                        identifier(cycle_id),
                        self.actor,
                        operation_id,
                        title,
                        dump(data),
                        closed,
                        self._now(),
                    ),
                ).lastrowid
        return next(
            row
            for row in self.work_tabs(company_id, cycle_id, True)
            if row["id"] == identifier(tab_id)
        )

    def work_tabs(self, company_id, cycle_id, include_closed=False):
        self._work_cycle(company_id, cycle_id)
        rows = [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM work_tabs WHERE company_id=? AND cycle_id=? AND actor=? AND (? OR closed=0) ORDER BY id",
                (company_id, identifier(cycle_id), self.actor, include_closed),
            )
        ]
        for row in rows:
            row["data"] = json.loads(row["data"])
        return rows

    def prepare_work_settlement(
        self, company_id, cycle_id, title_id, policy_id, value, paid_date, reference
    ):
        title = self._finance_title(company_id, title_id)
        if title["canceled_at"] or Decimal(amount(value)) > Decimal(title["balance"]):
            raise ValueError("Valor supera o saldo ou título cancelado.")
        nature = "pagamento" if title["direction"] == "pagar" else "recebimento"
        proposal = self.prepare_work_operation(
            company_id, cycle_id, policy_id=policy_id, operation=nature
        )
        proposal["reference"] = reference
        proposal["fiscal"]["posting_date"] = paid_date
        proposal["fiscal"]["total"] = amount(value)
        for line in proposal["entries"]:
            line.update(date=paid_date, amount=amount(value), memo=reference)
        proposal["settlement"] = {
            "title_id": title["id"],
            "expected_hash": title["snapshot_hash"],
            "amount": amount(value),
            "paid_date": paid_date,
            "reference": reference,
        }
        return proposal

    def reverse_work_operation(
        self,
        company_id,
        operation_id,
        cycle_id,
        posted_date,
        expected_hash,
        reason,
        request_key,
    ):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            original = self._work_revision(company_id, operation_id)
            if (
                original["state"] != "escriturado"
                or original["snapshot_hash"] != expected_hash
                or digest(original["payload"]) != expected_hash
            ):
                raise ValueError("Estorno exige operação escriturada íntegra.")
            if original["reversal_of"]:
                raise ValueError(
                    "Estorno de estorno não é permitido; registre ajuste explícito."
                )
            if self.db.execute(
                "SELECT 1 FROM work_operations WHERE reversal_of=?",
                (identifier(operation_id),),
            ).fetchone():
                raise ValueError("Operação já possui estorno vinculado.")
            payload = self.prepare_work_operation(
                company_id, cycle_id, operation="ajuste"
            )
            if original["payload"]["fiscal"]["operation"] == "abertura":
                raise ValueError(
                    "Abertura estabelecida não admite estorno; registre ajuste explícito."
                )
            payload["cancel_titles"] = []
            for row in self.db.execute(
                "SELECT title_id FROM work_title_links WHERE operation_id=?",
                (identifier(operation_id),),
            ):
                title = self._finance_title(company_id, row["title_id"])
                if title["canceled_at"] or any(
                    not p["reversed_at"] for p in title["settlements"]
                ):
                    raise ValueError(
                        "Estorne as liquidações antes de estornar o reconhecimento."
                    )
                payload["cancel_titles"].append(
                    {"title_id": title["id"], "expected_hash": title["snapshot_hash"]}
                )
            payload["reversal"] = {
                "operation_id": identifier(operation_id),
                "snapshot_hash": expected_hash,
            }
            payload["reference"] = "Estorno da operação #" + str(operation_id)
            payload["fiscal"].update(
                posting_date=posted_date, total=original["payload"]["fiscal"]["total"]
            )
            payload["entries"] = [
                {
                    **line,
                    "side": "C" if line["side"] == "D" else "D",
                    "date": posted_date,
                }
                for line in original["payload"]["entries"]
            ]
            if any(
                posted_date < line["date"] for line in original["payload"]["entries"]
            ):
                raise ValueError(
                    "Estorno não pode anteceder o reconhecimento original."
                )
            link = self.db.execute(
                "SELECT settlement_id FROM work_settlement_links WHERE operation_id=?",
                (identifier(operation_id),),
            ).fetchone()
            if link:
                settlement = self.db.execute(
                    "SELECT title_id FROM finance_settlements WHERE id=?",
                    (link["settlement_id"],),
                ).fetchone()
                title = self._finance_title(company_id, settlement["title_id"])
                payload["reverse_settlement"] = {
                    "title_id": title["id"],
                    "settlement_id": link["settlement_id"],
                    "expected_hash": title["snapshot_hash"],
                }
            saved = self.save_work_operation(
                company_id, cycle_id, payload, reason, request_key, _in_transaction=True
            )
            self.db.execute(
                "UPDATE work_operations SET reversal_of=? WHERE id=?",
                (identifier(operation_id), saved["operation_id"]),
            )
            self._audit(
                company_id,
                "estorno_operacional_preparado",
                {
                    "original_id": operation_id,
                    "operation_id": saved["operation_id"],
                    "reason": reason,
                },
            )
            return self.get_work_operation(company_id, saved["operation_id"])

    def transition_work_cycle(
        self,
        company_id,
        cycle_id,
        target,
        expected_hash,
        reason,
        acknowledge_errors=False,
    ):
        from .persistence import _text

        reason = _text(reason, "motivo", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            overview = self.work_overview(company_id, cycle_id)
            cycle = overview["cycle"]
            if overview["snapshot_hash"] != expected_hash:
                raise ValueError("Competência alterada; confira novamente.")
            previous_export = self.db.execute(
                "SELECT 1 FROM fiscal_period_states WHERE company_id=? AND competence=? AND state='exportado'",
                (company_id, cycle["competence"]),
            ).fetchone()
            if previous_export and target == "aberta":
                raise ValueError(
                    "Competência exportada no histórico: preserve o fechamento e registre ajustes em competência aberta."
                )
            if target not in {"aberta", "encerrada"} or cycle["state"] == target:
                raise ValueError("Transição inválida.")
            if target == "encerrada":
                assessment = self.tax_assessment_readiness(company_id, cycle_id)
                if assessment["required"] and not assessment["ready"]:
                    raise ValueError(assessment["message"])
                if any(
                    overview["counts"][key]
                    for key in ["pending_documents", "drafts", "reviewed", "open_forms"]
                ):
                    raise ValueError(
                        "Resolva ou dispense as operações pendentes antes de encerrar."
                    )
                if (
                    overview["counts"]["rejected_inputs"]
                    or overview["counts"]["legacy_pending"]
                ) and acknowledge_errors is not True:
                    raise ValueError(
                        "Reconheça os arquivos rejeitados e rascunhos anteriores não retomados antes de encerrar o recorte."
                    )
                if not self.db.execute(
                    "SELECT 1 FROM work_balance_starts WHERE company_id=? AND competence<=?",
                    (company_id, cycle["competence"]),
                ).fetchone():
                    raise ValueError(
                        "Declare os saldos iniciais ou confirme saldo inicial zero antes de encerrar."
                    )
            self.db.execute(
                "UPDATE work_cycles SET state=?,reason=?,actor=? WHERE id=?",
                (target, reason, self.actor, cycle["id"]),
            )
            self._audit(
                company_id,
                "competencia_" + target,
                {
                    "cycle_id": cycle["id"],
                    "snapshot_hash": expected_hash,
                    "reason": reason,
                    "acknowledge_errors": acknowledge_errors,
                },
            )
        return self._work_cycle(company_id, cycle_id)

    def import_work_plan(self, company_id, filename, content, label, reason):
        import csv, hashlib, io
        from .persistence import _text

        filename = _text(filename, "nome do arquivo", 255)
        reason = _text(reason, "motivo", 2000)
        if not isinstance(content, str) or len(content.encode()) > 10 * 1024 * 1024:
            raise ValueError("Plano CSV inválido ou acima de 10 MiB.")
        lines = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=";")
        required = {"codigo", "descricao", "tipo", "natureza", "superior"}
        if not required <= set(lines.fieldnames or []):
            raise ValueError(
                "Use CSV com codigo;descricao;tipo;natureza;superior. Classificador e acesso são colunas opcionais preservadas."
            )
        accounts = []
        for row in lines:
            accounts.append(
                {
                    "code": row["codigo"],
                    "description": row["descricao"],
                    "kind": row["tipo"],
                    "nature": row["natureza"],
                    "parent_code": row["superior"] or None,
                    "attributes": {
                        key: value for key, value in row.items() if key not in required
                    },
                }
            )
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            plan = self.import_plan(company_id, label, accounts, _in_transaction=True)
            self.db.execute(
                "INSERT INTO work_config_sources(company_id,kind,filename,content,sha256,plan_id,actor,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    company_id,
                    "plano",
                    filename,
                    content.encode(),
                    hashlib.sha256(content.encode()).hexdigest(),
                    plan["id"],
                    self.actor,
                    self._now(),
                ),
            )
            self._audit(
                company_id,
                "plano_csv_recebido",
                {"plan_id": plan["id"], "filename": filename, "reason": reason},
            )
        return plan
