"""Configurable accounting queries over the existing unified operational books.

No second ledger, migrations, source posting or tax/account inference. The
canonical work_books service owns historical validation and opening continuity.
"""
from calendar import monthrange
from datetime import date
import re

from .accounting_store import digest, identifier

PROFILE = "escritura-relatorios-contabeis-v1"
REPORTS = {"diario", "razao", "balancete"}


def _cents(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]{2}", value):
        raise ValueError("Valor inconsistente no livro contábil")
    return int(value.replace(".", ""))


def _money(value):
    units, fraction = divmod(abs(value), 100)
    return f"{'-' if value < 0 else ''}{units}.{fraction:02d}"


def _side(value):
    return "D" if value > 0 else "C" if value < 0 else "0"


def _date(value):
    try:
        parsed = date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None or parsed.isoformat() != value:
        raise ValueError("Data inválida; use AAAA-MM-DD")
    return value


def accounting_report(store, company_id, cycle_id, plan_id, report="balancete",
                      start_date=None, end_date=None, account_code=None,
                      level="analitico", include_zero=False):
    """Read one company/cycle/plan in a consistent caller-safe SQLite snapshot."""
    company_id, cycle_id, plan_id = map(identifier, (company_id, cycle_id, plan_id))
    if report not in REPORTS or level not in {"analitico", "sintetico"}:
        raise ValueError("Relatório ou nível não suportado")
    if type(include_zero) is not bool:
        raise ValueError("include_zero deve ser booleano")
    if account_code is not None and (not isinstance(account_code, str) or not account_code):
        raise ValueError("Código de conta inválido")
    store.db.execute("SAVEPOINT accounting_report")
    try:
        result = _report(store, company_id, cycle_id, plan_id, report,
                         start_date, end_date, account_code, level, include_zero)
    except BaseException:
        store.db.execute("ROLLBACK TO accounting_report")
        store.db.execute("RELEASE accounting_report")
        raise
    store.db.execute("RELEASE accounting_report")
    return result


def _report(store, company, cycle_id, plan_id, report, start, end, account_code, level, include_zero):
    cycle = store._work_cycle(company, cycle_id)
    plan = store._owned("plans", company, plan_id)
    month = cycle["competence"]
    start = _date(start) if start is not None else month + "-01"
    year, number = map(int, month.split("-"))
    end = _date(end) if end is not None else f"{month}-{monthrange(year, number)[1]:02d}"
    if start > end or start[:7] != month or end[:7] != month:
        raise ValueError("Datas devem estar em ordem e dentro da competência selecionada")
    accounts = {a["code"]: a for a in store.list_accounts(company, plan_id)}
    ancestors = {}
    for code in accounts:
        cursor, chain = code, []
        while cursor is not None:
            if cursor in chain or cursor not in accounts:
                raise ValueError("Hierarquia do plano inconsistente")
            chain.append(cursor)
            cursor = accounts[cursor]["parent_code"]
        ancestors[code] = chain
    if account_code is not None and account_code not in accounts:
        raise ValueError("Conta não pertence ao plano selecionado")
    selected = {code for code, a in accounts.items() if a["kind"] == "analitica"
                and (account_code is None or account_code in ancestors[code])}
    book = store.work_books(company, cycle_id)
    book_payload = {key: value for key, value in book.items() if key != "snapshot_hash"}
    if digest(book_payload) != book["snapshot_hash"] or book["company"]["id"] != company or book["cycle"]["id"] != cycle_id:
        raise ValueError("Livro canônico inconsistente")
    values = {code: [0, 0, 0] for code in accounts}
    for row in book["trial_balance"]:
        if row["plan_id"] != plan_id:
            continue
        code = row["code"]
        if code not in accounts or accounts[code]["id"] != row["account_id"]:
            raise ValueError("Conta do livro incompatível com a versão do plano")
        if code in selected:
            for ancestor in ancestors[code]:
                values[ancestor][0] += _cents(row["opening"])
    rows = []
    for entry in book["diary"]:
        if entry["plan_id"] != plan_id:
            continue
        code = entry["account_code"]
        if code not in accounts or accounts[code]["id"] != entry["account_id"]:
            raise ValueError("Partida incompatível com a versão do plano")
        if code not in selected or entry["date"] > end:
            continue
        amount = _cents(entry["amount"])
        if amount <= 0 or entry["side"] not in {"D", "C"}:
            raise ValueError("Partida contábil inconsistente")
        before = entry["date"] < start
        for ancestor in ancestors[code]:
            values[ancestor][0 if before else 1 if entry["side"] == "D" else 2] += (
                amount if not before or entry["side"] == "D" else -amount)
        if not before:
            rows.append(dict(entry))
    # Canonical order preserves distinct lines and original sequence, including
    # multiple lines of the same account in one operation.
    running = {code: values[code][0] for code in selected}
    ledger = []
    for row in rows:
        code = row["account_code"]
        running[code] += _cents(row["amount"]) * (1 if row["side"] == "D" else -1)
        ledger.append({**row, "balance": _money(running[code]), "balance_side": _side(running[code])})

    def summary(code):
        a = accounts[code]
        opening, debit, credit = values[code]
        closing = opening + debit - credit
        return {"account_id": a["id"], "code": code, "description": a["description"],
                "parent_code": a["parent_code"], "kind": a["kind"], "nature": a["nature"],
                "depth": len(ancestors[code]), "opening": _money(opening), "opening_side": _side(opening),
                "debit": _money(debit), "credit": _money(credit),
                "closing": _money(closing), "closing_side": _side(closing)}

    trial = [summary(code) for code in sorted(selected) if include_zero or any(values[code])]
    if report == "balancete":
        visible = {code for code in accounts if account_code is None or account_code in ancestors[code]}
        kind = "analitica" if level == "analitico" else "sintetica"
        output = [summary(code) for code in sorted(visible)
                  if accounts[code]["kind"] == kind and (include_zero or any(values[code]))]
    elif report == "razao":
        output = sorted(ledger, key=lambda row: (row["account_code"], row["sequence"]))
    else:
        output = rows
    opening, debit, credit = (sum(values[code][i] for code in selected) for i in range(3))
    result = {"profile": PROFILE, "report": report,
              "company": {"id": company, "name": book["company"]["name"]},
              "cycle": {"id": cycle_id, "competence": month},
              "plan": {key: plan[key] for key in ("id", "label", "version")},
              "filters": {"start_date": start, "end_date": end, "account_code": account_code,
                          "level": level, "include_zero": include_zero},
              "opening_declared": book["opening_declared"], "opening_competence": book["opening_competence"],
              "balance_convention": "debit_minus_credit", "book_snapshot_hash": book["snapshot_hash"],
              "totals_basis": "Contas analíticas do recorte; não somar linhas sintéticas sobrepostas",
              "totals": {"opening": _money(opening), "debit": _money(debit), "credit": _money(credit),
                         "closing": _money(opening + debit - credit), "balanced_in_selection": debit == credit},
              "rows": output, "accounts": trial, "entry_count": len(rows),
              "prosoft_validated": False, "pva_validated": False, "statutory_book": False}
    return {**result, "snapshot_hash": digest(result)}


def report_from_request(store, data):
    allowed = {"company_id", "cycle_id", "plan_id", "report", "start_date", "end_date", "account_code", "level", "include_zero"}
    if set(data) - allowed:
        raise ValueError("Filtro não suportado neste perfil contábil")
    for key in ("company_id", "cycle_id", "plan_id"):
        if key not in data:
            raise ValueError(f"Informe o campo {key}")
    include = data.get("include_zero", "false")
    if include not in ("true", "false"):
        raise ValueError("include_zero deve ser true ou false")
    return accounting_report(store, data["company_id"], data["cycle_id"], data["plan_id"],
                             data.get("report", "balancete"), data.get("start_date") or None,
                             data.get("end_date") or None, data.get("account_code") or None,
                             data.get("level", "analitico"), include == "true")
