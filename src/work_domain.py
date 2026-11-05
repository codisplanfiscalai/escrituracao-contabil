"""New operational model: one versioned operation spans fiscal, journal and billing."""

from datetime import date
from decimal import Decimal, localcontext
import re
from .accounting_store import amount, digest

WORK_SCHEMA = """
CREATE TABLE IF NOT EXISTS work_cycles (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 competence TEXT NOT NULL, period_id INTEGER NOT NULL REFERENCES periods(id),
 plan_id INTEGER REFERENCES plans(id), state TEXT NOT NULL DEFAULT 'aberta',
 version INTEGER NOT NULL DEFAULT 1, actor TEXT NOT NULL, reason TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(company_id,competence));
CREATE TABLE IF NOT EXISTS work_policies (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 plan_id INTEGER NOT NULL REFERENCES plans(id), operation TEXT NOT NULL,
 reference_competence TEXT NOT NULL, version INTEGER NOT NULL, state TEXT NOT NULL,
 debit_account_id INTEGER NOT NULL REFERENCES accounts(id), credit_account_id INTEGER NOT NULL REFERENCES accounts(id),
 label TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,plan_id,operation,reference_competence,version));
CREATE TABLE IF NOT EXISTS work_operations (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), document_id INTEGER REFERENCES documents(id),
 reversal_of INTEGER UNIQUE REFERENCES work_operations(id), created_at TEXT NOT NULL,
 UNIQUE(company_id,document_id));
CREATE TABLE IF NOT EXISTS work_revisions (
 id INTEGER PRIMARY KEY, operation_id INTEGER NOT NULL REFERENCES work_operations(id),
 version INTEGER NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 review_actor TEXT, review_reason TEXT, reviewed_at TEXT, posted_at TEXT,
 UNIQUE(operation_id,version));
CREATE TABLE IF NOT EXISTS work_requests (
 company_id INTEGER NOT NULL REFERENCES companies(id), request_key TEXT NOT NULL,
 request_hash TEXT NOT NULL, revision_id INTEGER NOT NULL REFERENCES work_revisions(id),
 PRIMARY KEY(company_id,request_key));
CREATE TABLE IF NOT EXISTS work_movements (
 revision_id INTEGER NOT NULL REFERENCES work_revisions(id), line INTEGER NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY(revision_id,line));
CREATE TABLE IF NOT EXISTS work_title_links (
 operation_id INTEGER NOT NULL REFERENCES work_operations(id),
 title_id INTEGER NOT NULL UNIQUE REFERENCES finance_titles(id),
 installment_id INTEGER UNIQUE REFERENCES installments(id), reference TEXT NOT NULL,
 PRIMARY KEY(operation_id,reference));
CREATE TABLE IF NOT EXISTS work_tabs (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), actor TEXT NOT NULL,
 operation_id INTEGER REFERENCES work_operations(id), title TEXT NOT NULL,
 data TEXT NOT NULL, version INTEGER NOT NULL, closed INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_legacy_links (
 kind TEXT NOT NULL, source_id INTEGER NOT NULL, company_id INTEGER NOT NULL REFERENCES companies(id),
 operation_id INTEGER REFERENCES work_operations(id), snapshot_hash TEXT NOT NULL,
 PRIMARY KEY(kind,source_id));
CREATE TABLE IF NOT EXISTS work_exports (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 cycle_id INTEGER NOT NULL REFERENCES work_cycles(id), snapshot_hash TEXT NOT NULL,
 manifest_sha256 TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(cycle_id,snapshot_hash));
CREATE TABLE IF NOT EXISTS work_export_files (
 export_id INTEGER NOT NULL REFERENCES work_exports(id), name TEXT NOT NULL,
 content BLOB NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(export_id,name));
"""
OPERATIONS = {"entrada", "saida", "servico_tomado", "servico_prestado", "ajuste"}


def check_operation(payload, cycle, accounts, source=None):
    """Drafts may be incomplete; only a complete reviewed version can create effects."""
    issues = []

    def issue(field, message):
        issues.append({"field": field, "message": message, "severity": "bloqueio"})

    def text(value, field, limit=1000):
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > limit
            or any(ord(c) < 32 for c in value)
        ):
            issue(field, "Preencha um texto válido.")
            return ""
        return value.strip()

    def money(value, field):
        try:
            return amount(value)
        except ValueError as error:
            issue(field, str(error))
            return None

    def day(value, field):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError()
            return value
        except (ValueError, TypeError):
            issue(field, "Informe uma data válida.")
            return ""

    fiscal = payload.get("fiscal", {})
    if not isinstance(fiscal, dict):
        issue("fiscal", "Ficha fiscal inválida.")
        fiscal = {}
    operation = fiscal.get("operation")
    if not isinstance(operation, str) or operation not in OPERATIONS:
        issue("fiscal.operation", "Selecione a natureza da operação.")
        operation = ""
    reference = text(payload.get("reference"), "reference", 300)
    posted = day(fiscal.get("posting_date"), "fiscal.posting_date")
    if posted and posted[:7] != cycle["competence"]:
        issue(
            "fiscal.posting_date", "A data deve pertencer à competência de movimentos."
        )
    opening_zero = operation == "abertura" and payload.get("opening_zero") is True
    if opening_zero and fiscal.get("total") not in ("0", "0.0", "0.00"):
        issue(
            "fiscal.total",
            "Abertura confirmada como zero exige valor total zero explícito.",
        )
    total = "0.00" if opening_zero else money(fiscal.get("total"), "fiscal.total")
    if operation in {"entrada", "saida", "servico_tomado", "servico_prestado"}:
        text(fiscal.get("number"), "fiscal.number", 100)
        if fiscal.get("model") not in ("55", "65", "SERVICO"):
            issue(
                "fiscal.model", "Modelo suportado: 55, 65 ou ficha de serviço manual."
            )
        day(fiscal.get("issued_date"), "fiscal.issued_date")
    for field in [
        "icms_base",
        "icms_amount",
        "iss_base",
        "iss_amount",
        "pis_base",
        "pis_amount",
        "cofins_base",
        "cofins_amount",
    ]:
        value = fiscal.get(field)
        if value not in (None, "") and (
            not isinstance(value, str)
            or not re.fullmatch(r"\d{1,15}(?:\.\d{1,2})?", value)
        ):
            issue(
                "fiscal." + field,
                "Valor informado deve ser texto decimal não negativo, com até duas casas.",
            )
    if fiscal.get("cfop") and not re.fullmatch(r"[1-7]\d{3}", str(fiscal["cfop"])):
        issue(
            "fiscal.cfop",
            "CFOP informado deve conter quatro dígitos entre 1xxx e 7xxx; enquadramento não validado.",
        )
    if not cycle.get("plan_id"):
        issue("plan_id", "Vincule o plano da competência antes de escriturar.")
    if source:
        if payload.get("source_hash") != source["source_hash"]:
            issue(
                "source",
                "As fontes mudaram; prepare nova versão e confira as diferenças.",
            )
        chosen = next(
            (
                row
                for row in source["observations"]
                if str(row["id"]) == str(payload.get("observation_id"))
            ),
            None,
        )
        if not chosen or chosen["file_status"] == "excluido":
            issue("observation_id", "Selecione uma fonte documental ativa.")
        elif chosen["issues"]:
            issue(
                "observation_id",
                "A fonte possui pendências: " + "; ".join(chosen["issues"]),
            )
        elif total and chosen["normalized"].get("total") != total:
            issue(
                "fiscal.total",
                "Total diferente da fonte escolhida; registre a correção na origem ou uma operação de ajuste.",
            )
        if source["differences"] and payload.get("acknowledge_differences") is not True:
            issue(
                "acknowledge_differences",
                "Confira e reconheça as divergências entre fontes.",
            )
    lines = payload.get("entries", [])
    if (
        not isinstance(lines, list)
        or (not opening_zero and not 2 <= len(lines) <= 2000)
        or (opening_zero and lines)
    ):
        issue("entries", "Informe de 2 a 2000 partidas.")
        lines = []
    resolved = []
    groups = {}
    with localcontext() as context:
        context.prec = 40
        for index, line in enumerate(lines):
            path = f"entries.{index}"
            if not isinstance(line, dict):
                issue(path, "Partida inválida.")
                continue
            value = money(line.get("amount"), path + ".amount")
            account = accounts.get(str(line.get("account_id")))
            if not account or account["kind"] != "analitica":
                issue(
                    path + ".account_id",
                    "Selecione uma conta analítica do plano vinculado.",
                )
            side = line.get("side")
            if side not in ("D", "C"):
                issue(path + ".side", "Informe débito ou crédito.")
            group = text(line.get("group"), path + ".group", 100)
            memo = text(line.get("memo"), path + ".memo", 1000)
            line_date = day(line.get("date"), path + ".date")
            if line_date and line_date[:7] != cycle["competence"]:
                issue(path + ".date", "Data fora da competência dos movimentos.")
            if (
                line_date
                and posted
                and operation in ("abertura", "pagamento", "recebimento")
                and line_date != posted
            ):
                issue(
                    path + ".date",
                    "Partidas de abertura ou liquidação devem usar a data econômica da operação.",
                )
            if value and side in ("D", "C"):
                groups.setdefault(
                    (line_date, group), {"D": Decimal(0), "C": Decimal(0)}
                )[side] += Decimal(value)
            resolved.append(
                {
                    **line,
                    "amount": value,
                    "account": account,
                    "line": index + 1,
                    "memo": memo,
                }
            )
        if any(value["D"] != value["C"] for value in groups.values()):
            issue("entries", "Débitos e créditos devem equilibrar por data e grupo.")
        debit = sum((value["D"] for value in groups.values()), Decimal(0))
        credit = sum((value["C"] for value in groups.values()), Decimal(0))
        if total and debit != Decimal(total):
            issue(
                "entries",
                "O total de débitos da operação deve corresponder ao valor documental; segregue ajustes em outra operação.",
            )
    finance = payload.get("finance", {})
    if not isinstance(finance, dict):
        issue("finance", "Cobrança inválida.")
        finance = {}
    mode = finance.get("mode")
    if mode not in ("origem", "manual", "sem_cobranca"):
        issue("finance.mode", "Escolha como tratar a cobrança.")
    installments = finance.get("installments", []) if mode != "sem_cobranca" else []
    if not isinstance(installments, list) or len(installments) > 500:
        issue("finance.installments", "Parcelas inválidas.")
        installments = []
    if mode in ("origem", "manual"):
        if finance.get("direction") not in ("pagar", "receber"):
            issue("finance.direction", "Confirme pagar ou receber.")
        text(finance.get("counterparty"), "finance.counterparty", 300)
        if not installments:
            issue(
                "finance.installments", "Informe as parcelas ou selecione sem cobrança."
            )
    seen = set()
    settled = Decimal(0)
    for index, part in enumerate(installments):
        path = f"finance.installments.{index}"
        if not isinstance(part, dict):
            issue(path, "Parcela inválida.")
            continue
        key = text(part.get("reference"), path + ".reference", 100)
        if key in seen:
            issue(path + ".reference", "Referência de parcela repetida.")
        seen.add(key)
        day(part.get("due_date"), path + ".due_date")
        value = money(part.get("amount"), path + ".amount")
        if value:
            settled += Decimal(value)
        if mode == "origem" and source:
            original = next(
                (
                    row
                    for row in source["installments"]
                    if str(row["id"]) == str(part.get("installment_id"))
                    and (not chosen or row["file_id"] == chosen["file_id"])
                ),
                None,
            )
            if not original or (
                original["reference"],
                original["due_date"],
                original["amount"],
            ) != (key, part.get("due_date"), value):
                issue(
                    path,
                    "A parcela não corresponde à origem; confirme uma cobrança manual com motivo.",
                )
    if installments and total and settled != Decimal(total):
        issue(
            "finance.installments",
            "A soma das parcelas deve corresponder ao valor da operação.",
        )
    if (
        mode == "origem"
        and source
        and any(
            row["file_id"] == chosen["file_id"]
            for row in source.get("billing_issues", [])
            if chosen
        )
    ):
        issue(
            "finance.mode",
            "A cobrança da fonte contém pendências; confira e informe uma cobrança manual motivada ou não gere nova cobrança.",
        )
    if mode == "manual":
        text(finance.get("reason"), "finance.reason", 2000)
    return {
        "issues": issues,
        "ready": not issues,
        "totals": {
            "debit": format(debit, ".2f"),
            "credit": format(credit, ".2f"),
            "billing": format(settled, ".2f"),
        },
        "entries": resolved,
        "reference": reference,
    }


WORK_SCHEMA += """
CREATE TABLE IF NOT EXISTS work_settlement_links (
 operation_id INTEGER PRIMARY KEY REFERENCES work_operations(id),
 settlement_id INTEGER NOT NULL UNIQUE REFERENCES finance_settlements(id));
CREATE TABLE IF NOT EXISTS work_balance_starts (
 company_id INTEGER PRIMARY KEY REFERENCES companies(id),
 revision_id INTEGER NOT NULL UNIQUE REFERENCES work_revisions(id), competence TEXT NOT NULL,
 zero_confirmed INTEGER NOT NULL, reason TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_config_sources (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 kind TEXT NOT NULL, filename TEXT NOT NULL, content BLOB NOT NULL, sha256 TEXT NOT NULL,
 plan_id INTEGER REFERENCES plans(id), actor TEXT NOT NULL, created_at TEXT NOT NULL);
"""
OPERATIONS |= {"folha", "abertura", "pagamento", "recebimento"}
