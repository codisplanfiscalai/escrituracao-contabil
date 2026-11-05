"""Títulos e baixas locais explícitos, sem integração bancária ou contábil automática."""

from datetime import date
from decimal import Decimal, localcontext
from .accounting_store import amount, digest, identifier
from .accounting_books import _csv

FINANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS finance_titles (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), direction TEXT NOT NULL,
 reference TEXT NOT NULL, counterparty TEXT NOT NULL, due_date TEXT NOT NULL, amount TEXT NOT NULL,
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, reason TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 canceled_at TEXT, cancellation_actor TEXT, cancellation_reason TEXT,
 UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS finance_settlements (
 id INTEGER PRIMARY KEY, title_id INTEGER NOT NULL REFERENCES finance_titles(id),
 amount TEXT NOT NULL, paid_date TEXT NOT NULL, reference TEXT NOT NULL, reason TEXT NOT NULL,
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 reversed_at TEXT, reversal_actor TEXT, reversal_reason TEXT,
 UNIQUE(title_id,request_key));
"""
FINANCE_GET = {"finance-titles", "finance-file"}
FINANCE_WRITE = {"finance-titles", "finance-settlements"}
FINANCE_REVIEW = {"finance-reversal", "finance-cancel"}
FINANCE_ROUTES = FINANCE_GET | FINANCE_WRITE | FINANCE_REVIEW


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError("Data deve ser texto ISO")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Data inválida") from None
    if parsed.isoformat() != value:
        raise ValueError("Data deve usar AAAA-MM-DD")
    return value


class FinanceMixin:
    def _finance_title(self, company_id, title_id):
        self._company(company_id)
        row = self.db.execute(
            "SELECT * FROM finance_titles WHERE company_id=? AND id=?",
            (company_id, identifier(title_id)),
        ).fetchone()
        if not row:
            raise ValueError("Título não pertence à empresa ou não existe")
        result = dict(row)
        settlements = [
            dict(row)
            for row in self.db.execute(
                "SELECT * FROM finance_settlements WHERE title_id=? ORDER BY id",
                (row["id"],),
            )
        ]
        with localcontext() as context:
            context.prec = 40
            paid = sum(
                (
                    Decimal(row["amount"])
                    for row in settlements
                    if not row["reversed_at"]
                ),
                Decimal(0),
            )
            balance = Decimal(result["amount"]) - paid
            if result["canceled_at"]:
                balance = Decimal(0)
        result.update(
            paid=format(paid, ".2f"),
            balance=format(balance, ".2f"),
            settlements=settlements,
            status=(
                "cancelado"
                if result["canceled_at"]
                else "quitado" if not balance else "parcial" if paid else "aberto"
            ),
        )
        result["snapshot_hash"] = digest(result)
        return result

    def list_finance_titles(self, company_id, period_id=None):
        self._company(company_id)
        if period_id is not None:
            period_id = self._owned("periods", company_id, identifier(period_id))["id"]
        with self.db:
            self.db.execute("BEGIN")
            rows = self.db.execute(
                "SELECT id,period_id FROM finance_titles WHERE company_id=? ORDER BY due_date,id",
                (company_id,),
            ).fetchall()
            return [
                self._finance_title(company_id, row["id"])
                for row in rows
                if period_id is None or row["period_id"] == period_id
            ]

    def create_finance_title(
        self,
        company_id,
        period_id,
        direction,
        reference,
        counterparty,
        due_date,
        value,
        reason,
        request_key,
    ):
        from .persistence import _text

        period_id = identifier(period_id)
        if direction not in ("pagar", "receber"):
            raise ValueError("Direção deve ser pagar ou receber")
        payload = dict(
            period_id=period_id,
            direction=direction,
            reference=_text(reference, "referência", 300),
            counterparty=_text(counterparty, "contraparte", 300),
            due_date=iso_date(due_date),
            amount=amount(value),
            reason=_text(reason, "motivo", 2000),
        )
        request_key = _text(request_key, "tentativa", 100)
        fingerprint = digest(payload)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            self._owned("periods", company_id, period_id)
            row = self.db.execute(
                "SELECT * FROM finance_titles WHERE company_id=? AND request_key=?",
                (company_id, request_key),
            ).fetchone()
            if row:
                if row["request_hash"] != fingerprint:
                    raise ValueError("Tentativa já utilizada com outro conteúdo")
                return self._finance_title(company_id, row["id"])
            cur = self.db.execute(
                "INSERT INTO finance_titles(company_id,period_id,direction,reference,counterparty,due_date,amount,request_key,request_hash,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    company_id,
                    period_id,
                    direction,
                    payload["reference"],
                    payload["counterparty"],
                    payload["due_date"],
                    payload["amount"],
                    request_key,
                    fingerprint,
                    payload["reason"],
                    self.actor,
                    self._now(),
                ),
            )
            self._audit(
                company_id,
                "titulo_financeiro_criado",
                {"title_id": cur.lastrowid, **payload},
            )
            return self._finance_title(company_id, cur.lastrowid)

    def settle_finance_title(
        self,
        company_id,
        title_id,
        value,
        paid_date,
        reference,
        reason,
        request_key,
        expected_hash,
    ):
        from .persistence import _text

        title_id = identifier(title_id)
        payload = dict(
            amount=amount(value),
            paid_date=iso_date(paid_date),
            reference=_text(reference, "referência da baixa", 300),
            reason=_text(reason, "motivo", 2000),
        )
        request_key = _text(request_key, "tentativa", 100)
        fingerprint = digest(payload)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            title = self._finance_title(company_id, title_id)
            previous = self.db.execute(
                "SELECT * FROM finance_settlements WHERE title_id=? AND request_key=?",
                (title_id, request_key),
            ).fetchone()
            if previous:
                if previous["request_hash"] != fingerprint:
                    raise ValueError("Tentativa já utilizada com outro conteúdo")
                return title
            if title["snapshot_hash"] != expected_hash:
                raise ValueError("Título alterado; atualize antes de baixar")
            if title["canceled_at"]:
                raise ValueError("Título cancelado não permite baixa")
            if Decimal(payload["amount"]) > Decimal(title["balance"]):
                raise ValueError("Baixa supera o saldo em aberto")
            cur = self.db.execute(
                "INSERT INTO finance_settlements(title_id,amount,paid_date,reference,reason,request_key,request_hash,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    title_id,
                    payload["amount"],
                    payload["paid_date"],
                    payload["reference"],
                    payload["reason"],
                    request_key,
                    fingerprint,
                    self.actor,
                    self._now(),
                ),
            )
            self._audit(
                company_id,
                "baixa_financeira_registrada",
                {"title_id": title_id, "settlement_id": cur.lastrowid, **payload},
            )
            return self._finance_title(company_id, title_id)

    def reverse_finance_settlement(
        self, company_id, title_id, settlement_id, expected_hash, reason
    ):
        from .persistence import _text

        reason = _text(reason, "motivo do estorno", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            title = self._finance_title(company_id, title_id)
            row = next(
                (
                    row
                    for row in title["settlements"]
                    if row["id"] == identifier(settlement_id)
                ),
                None,
            )
            if not row:
                raise ValueError("Baixa não pertence ao título")
            if row["reversed_at"]:
                if row["reversal_reason"] == reason:
                    return title
                raise ValueError("Baixa já estornada")
            if title["snapshot_hash"] != expected_hash:
                raise ValueError("Título alterado; atualize antes de estornar")
            self.db.execute(
                "UPDATE finance_settlements SET reversed_at=?,reversal_actor=?,reversal_reason=? WHERE id=?",
                (self._now(), self.actor, reason, row["id"]),
            )
            self._audit(
                company_id,
                "baixa_financeira_estornada",
                {"title_id": title["id"], "settlement_id": row["id"], "reason": reason},
            )
            return self._finance_title(company_id, title_id)

    def cancel_finance_title(self, company_id, title_id, expected_hash, reason):
        from .persistence import _text

        reason = _text(reason, "motivo do cancelamento", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            title = self._finance_title(company_id, title_id)
            if title["canceled_at"]:
                if title["cancellation_reason"] == reason:
                    return title
                raise ValueError("Título já cancelado")
            if title["snapshot_hash"] != expected_hash:
                raise ValueError("Título alterado; atualize antes de cancelar")
            if Decimal(title["paid"]) != 0:
                raise ValueError(
                    "Estorne as baixas vigentes antes de cancelar o título"
                )
            self.db.execute(
                "UPDATE finance_titles SET canceled_at=?,cancellation_actor=?,cancellation_reason=? WHERE id=?",
                (self._now(), self.actor, reason, title["id"]),
            )
            self._audit(
                company_id,
                "titulo_financeiro_cancelado",
                {"title_id": title["id"], "reason": reason},
            )
            return self._finance_title(company_id, title_id)

    def finance_file(self, company_id, period_id=None):
        rows = self.list_finance_titles(company_id, period_id)
        content = _csv(
            rows,
            (
                "id",
                "period_id",
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
            ("direction", "reference", "counterparty", "status", "snapshot_hash"),
        )
        return {
            "name": "financeiro.csv",
            "media_type": "text/csv; charset=utf-8",
            "content": content,
        }


def dispatch_finance(store, method, route, data):
    from .local_app import _required, APIError

    company = identifier(_required(data, "company_id"))
    if method == "GET":
        if route == "finance-titles":
            return store.list_finance_titles(company, data.get("period_id") or None)
        if route == "finance-file":
            return store.finance_file(company, data.get("period_id") or None)
    if method == "POST":
        if route == "finance-titles":
            return store.create_finance_title(
                company,
                *[
                    _required(data, key)
                    for key in (
                        "period_id",
                        "direction",
                        "reference",
                        "counterparty",
                        "due_date",
                        "amount",
                        "reason",
                        "request_key",
                    )
                ],
            )
        if route == "finance-settlements":
            return store.settle_finance_title(
                company,
                *[
                    _required(data, key)
                    for key in (
                        "title_id",
                        "amount",
                        "paid_date",
                        "reference",
                        "reason",
                        "request_key",
                        "snapshot_hash",
                    )
                ],
            )
        if route == "finance-reversal":
            return store.reverse_finance_settlement(
                company,
                *[
                    _required(data, key)
                    for key in ("title_id", "settlement_id", "snapshot_hash", "reason")
                ],
            )
        if route == "finance-cancel":
            return store.cancel_finance_title(
                company,
                *[
                    _required(data, key)
                    for key in ("title_id", "snapshot_hash", "reason")
                ],
            )
    raise APIError("Rota ou método não disponível.", 404)
