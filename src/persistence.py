"""Transactional storage with explicit fiscal rules; no Prosoft transmission."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import re
import sqlite3
from decimal import Decimal
from datetime import date, datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from .contract_safety import validate_competence
from .reconciliation import XML_PROFILE, SPED_PROFILE
from .reconciliation_store import ReconciliationMixin, RECONCILIATION_SCHEMA
from .accounting_store import AccountingMixin, ACCOUNTING_SCHEMA
from .finance import FinanceMixin, FINANCE_SCHEMA
from .evidence_export import EvidenceExportMixin, EVIDENCE_SCHEMA
from .billing_association import BillingAssociationMixin, BILLING_ASSOCIATION_SCHEMA
from .fiscal_ledger import FiscalLedgerMixin, FISCAL_SCHEMA
from .fiscal_workspace import FiscalWorkspaceMixin, WORKSPACE_SCHEMA
from .manual_accounting import ManualAccountingMixin, MANUAL_SCHEMA
from .accounting_books import AccountingBooksMixin, BOOKS_SCHEMA
from .source_evidence import SourceEvidenceMixin, SOURCE_SCHEMA
from .work_domain import WORK_SCHEMA
from .work_store import WorkStoreMixin
from .work_books import WorkBooksMixin
from .batch_import import BatchImportMixin, BATCH_SCHEMA
from .product_catalog import ProductCatalogMixin, PRODUCT_SCHEMA
from .company_profiles import CompanyProfilesMixin, PROFILE_SCHEMA
from .module_closure import ModuleClosureMixin, MODULE_SCHEMA
from .tax_engine import TaxEngineMixin, TAX_SCHEMA
from .tax_catalog import TaxCatalogMixin, CATALOG_SCHEMA
from .tax_assessment import TaxAssessmentMixin
from .tax_catalog_import import TaxCatalogImportMixin, CATALOG_IMPORT_SCHEMA
from .tax_balances import TaxBalancesMixin, BALANCE_SCHEMA

MAX_FILE_BYTES = 10 * 1024 * 1024
NS = {"n": "http://www.portalfiscal.inf.br/nfe"}


def _json(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Dados não serializáveis em JSON seguro") from exc


def _text(value, field, limit=300, required=True):
    if not isinstance(value, str):
        raise ValueError(f"{field}: informe texto")
    value = value.strip()
    if (
        (required and not value)
        or len(value) > limit
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError(f"{field}: vazio, longo demais ou com caractere de controle")
    return value


def _month(value):
    return validate_competence(_text(value, "competência", 7))


def _money(value, field):
    from decimal import Decimal, InvalidOperation

    try:
        amount = Decimal(value)
        if (
            not amount.is_finite()
            or amount < 0
            or amount != amount.quantize(Decimal(".01"))
        ):
            raise ValueError()
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field}: valor monetário inválido") from None
    return format(amount, ".2f")


def parse_nfe(content):
    """Subset: document header and original billing from NF-e 4.00 only."""
    # Reject entity/DTD declarations even when encoded as UTF-16/32.
    if b"\x00" in content or re.search(rb"<!\s*(DOCTYPE|ENTITY)\b", content, re.I):
        raise ValueError("XML com DTD, entidades ou encoding não suportado")
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError) as exc:
        raise ValueError("XML malformado") from exc
    if root.tag not in {f"{{{NS['n']}}}NFe", f"{{{NS['n']}}}nfeProc"}:
        raise ValueError("Somente XML NF-e 4.00 é normalizado neste incremento")
    infos = root.findall(".//n:infNFe", NS)
    if len(infos) != 1:
        raise ValueError("XML deve conter exatamente uma NF-e")
    info = infos[0]
    if info.get("versao") != "4.00":
        raise ValueError("Versão NF-e ainda não suportada")

    def get(path, required=True):
        result = info.findtext(path, default="", namespaces=NS).strip()
        if required and not result:
            raise ValueError(f"Campo obrigatório ausente: {path}")
        return result

    key = info.get("Id", "").removeprefix("NFe")
    if not re.fullmatch(r"\d{44}", key):
        raise ValueError("Chave NF-e ausente ou inválida")
    model = get("n:ide/n:mod")
    if model not in {"55", "65"}:
        raise ValueError("Perfil de cabeçalho suporta NF-e 55 e NFC-e 65")
    emitted = get("n:ide/n:dhEmi")
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)", emitted
    ):
        raise ValueError("Data/hora de emissão exige T, segundos e fuso explícito")
    try:
        datetime.fromisoformat(emitted.replace("Z", "+00:00"))
        date.fromisoformat(emitted[:10])
    except ValueError as exc:
        raise ValueError("Data de emissão inválida") from exc
    issuer = get("n:emit/n:CNPJ")
    buyer = get("n:dest/n:CNPJ", False) or get("n:dest/n:CPF", False)
    if (
        not re.fullmatch(r"\d{14}", issuer)
        or (buyer and not re.fullmatch(r"\d{11}|\d{14}", buyer))
        or (not buyer and model == "55")
    ):
        raise ValueError("Identificação do emitente/destinatário ausente ou inválida")
    series = get("n:ide/n:serie")
    number = get("n:ide/n:nNF")
    if not re.fullmatch(r"\d{1,3}", series) or not re.fullmatch(r"\d{1,9}", number):
        raise ValueError("Série ou número NF-e inválido")
    total_dv = sum(
        int(digit) * (2 + index % 8) for index, digit in enumerate(reversed(key[:43]))
    )
    dv = 11 - total_dv % 11
    dv = 0 if dv >= 10 else dv
    if (
        int(key[-1]) != dv
        or key[6:20] != issuer
        or key[2:6] != emitted[2:4] + emitted[5:7]
        or key[20:22] != model
        or key[22:25] != series.zfill(3)
        or key[25:34] != number.zfill(9)
    ):
        raise ValueError("Chave NF-e inconsistente com os campos ou dígito verificador")
    billing_warnings = []
    billing = None
    if len(info.findall("n:cobr", NS)) > 1:
        raise ValueError("Mais de um grupo de cobrança; exige conferência de estrutura")
    cobr = info.find("n:cobr", NS)
    if cobr is not None:
        if len(cobr.findall("n:fat", NS)) > 1:
            raise ValueError(
                "Mais de uma fatura no XML; exige conferência de estrutura"
            )
        invoice = cobr.find("n:fat", NS)

        def optional(element, name):
            return element.findtext(f"n:{name}", default="", namespaces=NS).strip()

        billing = {
            "invoice": (
                {k: optional(invoice, k) for k in ("nFat", "vOrig", "vDesc", "vLiq")}
                if invoice is not None
                else None
            ),
            "installments": [],
        }
        if invoice is not None:
            for field in ("vOrig", "vDesc", "vLiq"):
                if billing["invoice"][field]:
                    billing["invoice"][field] = _money(billing["invoice"][field], field)
            if (
                not billing["invoice"]["nFat"]
                or not billing["invoice"]["vOrig"]
                or not billing["invoice"]["vLiq"]
            ):
                billing_warnings.append("Fatura incompleta; saída Prosoft bloqueada")
        seen_installments = set()
        for installment in cobr.findall("n:dup", NS):
            row = {k: optional(installment, k) for k in ("nDup", "dVenc", "vDup")}
            if row["dVenc"]:
                try:
                    date.fromisoformat(row["dVenc"])
                except ValueError as exc:
                    raise ValueError("Vencimento de parcela inválido") from exc
            if row["vDup"]:
                row["vDup"] = _money(row["vDup"], "Parcela")
            if not all(row.values()):
                billing_warnings.append("Parcela incompleta; nenhum dado presumido")
            if row["nDup"] and row["nDup"] in seen_installments:
                billing_warnings.append("Número de parcela repetido")
            seen_installments.add(row["nDup"])
            billing["installments"].append(row)
        if billing["installments"] and invoice is None:
            billing_warnings.append(
                "Parcelas sem fatura identificada; exige conferência"
            )
        if invoice is not None:
            values = billing["invoice"]
            if all(values[field] for field in ("vOrig", "vDesc", "vLiq")):
                if Decimal(values["vOrig"]) - Decimal(values["vDesc"]) != Decimal(
                    values["vLiq"]
                ):
                    billing_warnings.append(
                        "Valor original menos desconto diverge do líquido da fatura"
                    )
            installments = billing["installments"]
            if (
                installments
                and values["vLiq"]
                and all(row["vDup"] for row in installments)
            ):
                if sum(
                    (Decimal(row["vDup"]) for row in installments), Decimal("0")
                ) != Decimal(values["vLiq"]):
                    billing_warnings.append(
                        "Soma das parcelas diverge do líquido da fatura"
                    )
    products = []
    for index, detail in enumerate(info.findall("n:det", NS), 1):
        product = detail.find("n:prod", NS)
        if product is not None:
            data = {
                key: product.findtext("n:" + tag, default="", namespaces=NS).strip()
                for key, tag in {
                    "code": "cProd",
                    "description": "xProd",
                    "ncm": "NCM",
                    "unit": "uCom",
                    "gtin": "cEAN",
                    "cest": "CEST",
                }.items()
            }
            products.append({"locator": f"infNFe/det[{index}]/prod", "data": data})
    normalized = ET.canonicalize(
        ET.tostring(info, encoding="unicode"), strip_text=True, rewrite_prefixes=True
    )
    return {
        "key": key,
        "model": model,
        "number": number,
        "series": series,
        "issued_at": emitted,
        "competence": emitted[:7],
        "issuer": issuer,
        "buyer": buyer,
        "issuer_name": get("n:emit/n:xNome", False),
        "buyer_name": get("n:dest/n:xNome", False),
        "total": _money(get("n:total/n:ICMSTot/n:vNF"), "Total NF-e"),
        "billing": billing,
        "billing_warnings": billing_warnings,
        "products": products,
        "content_fingerprint": hashlib.sha256(normalized.encode()).hexdigest(),
    }


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, prosoft_company_code TEXT NOT NULL,
 prosoft_plan_code TEXT NOT NULL, cnpj TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS periods (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 reference_competence TEXT NOT NULL, processing_competence TEXT NOT NULL,
 UNIQUE(company_id,reference_competence,processing_competence));
CREATE TABLE IF NOT EXISTS plans (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 label TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,label,version));
CREATE TABLE IF NOT EXISTS accounts (
 id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id), code TEXT NOT NULL,
 description TEXT NOT NULL, parent_code TEXT, kind TEXT NOT NULL, nature TEXT NOT NULL,
 attributes TEXT NOT NULL, UNIQUE(plan_id,code));
CREATE TABLE IF NOT EXISTS mappings (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 plan_id INTEGER NOT NULL REFERENCES plans(id), source_account TEXT NOT NULL, target_code TEXT NOT NULL,
 valid_from TEXT NOT NULL, valid_to TEXT, state TEXT NOT NULL, version INTEGER NOT NULL,
 reason TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,plan_id,source_account,version));
CREATE TABLE IF NOT EXISTS files (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), filename TEXT NOT NULL,
 kind TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL, original BLOB NOT NULL,
 status TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,period_id,kind,sha256));
CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 period_id INTEGER NOT NULL REFERENCES periods(id), business_key TEXT NOT NULL,
 payload TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(company_id,business_key));
CREATE TABLE IF NOT EXISTS document_sources (
 document_id INTEGER NOT NULL REFERENCES documents(id), file_id INTEGER NOT NULL REFERENCES files(id),
 conflict INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(document_id,file_id));
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 actor TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
"""


class AccountingStore(
    TaxBalancesMixin,
    TaxCatalogImportMixin,
    TaxAssessmentMixin,
    TaxEngineMixin,
    TaxCatalogMixin,
    ModuleClosureMixin,
    CompanyProfilesMixin,
    SourceEvidenceMixin,
    WorkBooksMixin,
    WorkStoreMixin,
    ProductCatalogMixin,
    BatchImportMixin,
    FinanceMixin,
    AccountingBooksMixin,
    ManualAccountingMixin,
    FiscalWorkspaceMixin,
    FiscalLedgerMixin,
    BillingAssociationMixin,
    EvidenceExportMixin,
    AccountingMixin,
    ReconciliationMixin,
):
    def __init__(self, db_path, actor="operador-local"):
        self.actor = _text(actor, "usuário", 100)
        path = Path(db_path).expanduser()
        if str(db_path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=15000")
        version_table = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        ).fetchone()
        version = (
            self.db.execute("SELECT version FROM schema_version").fetchone()
            if version_table
            else None
        )
        if version and version[0] not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}:
            self.close()
            raise ValueError(
                "Versão do banco não suportada; nenhuma migração automática realizada"
            )
        try:
            self.db.executescript(
                "BEGIN IMMEDIATE;\n"
                + SCHEMA
                + RECONCILIATION_SCHEMA
                + ACCOUNTING_SCHEMA
                + EVIDENCE_SCHEMA
                + BILLING_ASSOCIATION_SCHEMA
                + FISCAL_SCHEMA
                + WORKSPACE_SCHEMA
                + MANUAL_SCHEMA
                + BOOKS_SCHEMA
                + FINANCE_SCHEMA
                + BATCH_SCHEMA
                + PRODUCT_SCHEMA
                + WORK_SCHEMA
                + SOURCE_SCHEMA
                + PROFILE_SCHEMA
                + MODULE_SCHEMA
                + TAX_SCHEMA
                + CATALOG_SCHEMA
                + CATALOG_IMPORT_SCHEMA
                + BALANCE_SCHEMA
            )
            if not version:
                self.db.execute("INSERT INTO schema_version VALUES (15)")
            elif version[0] in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}:
                self.db.execute("UPDATE schema_version SET version=15")
            if not version or version[0] < 10:
                self.db.execute(
                    "INSERT OR IGNORE INTO work_cycles(company_id,competence,period_id,plan_id,actor,reason,created_at) SELECT company_id,processing_competence,MIN(id),NULL,'migracao-10','Migração: confirmar parâmetros e plano.',? FROM periods GROUP BY company_id,processing_competence",
                    (self._now(),),
                )
                self.db.execute(
                    "UPDATE work_cycles SET state='encerrada',reason='Migração: fechamento fiscal anterior preservado.' WHERE EXISTS(SELECT 1 FROM fiscal_period_states f WHERE f.company_id=work_cycles.company_id AND f.competence=work_cycles.competence AND f.state IN ('fechado','exportado'))"
                )
                self._migrate_work_sources()
            self.db.commit()
        except Exception:
            self.db.rollback()
            self.close()
            raise
        if str(db_path) != ":memory:":
            path.chmod(0o600)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.db.close()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _audit(self, company_id, action, details):
        self.db.execute(
            "INSERT INTO audit(company_id,actor,action,details,created_at) VALUES(?,?,?,?,?)",
            (company_id, self.actor, action, _json(details), self._now()),
        )

    def _company(self, company_id):
        row = self.db.execute(
            "SELECT * FROM companies WHERE id=?", (company_id,)
        ).fetchone()
        if not row:
            raise ValueError("Empresa não encontrada")
        return dict(row)

    def _owned(self, table, company_id, item_id):
        if table not in {"periods", "plans", "files", "documents"}:
            raise ValueError("Tipo de registro inválido")
        self._company(company_id)
        row = self.db.execute(
            f"SELECT * FROM {table} WHERE id=? AND company_id=?", (item_id, company_id)
        ).fetchone()
        if not row:
            raise ValueError(
                "Registro não pertence à empresa selecionada ou não existe"
            )
        return dict(row)

    def create_company(
        self, name, prosoft_company_code="", prosoft_plan_code="", cnpj=""
    ):
        name = _text(name, "nome", 200)
        prosoft_company_code = _text(prosoft_company_code, "código Prosoft", 50, False)
        prosoft_plan_code = _text(prosoft_plan_code, "plano Prosoft", 50, False)
        cnpj = _text(cnpj, "CNPJ", 18, False)
        if cnpj and not re.fullmatch(r"\d{14}", cnpj):
            raise ValueError(
                "CNPJ deve conter 14 dígitos sem pontuação; autenticidade não verificada"
            )
        with self.db:
            cur = self.db.execute(
                "INSERT INTO companies(name,prosoft_company_code,prosoft_plan_code,cnpj,created_at) VALUES(?,?,?,?,?)",
                (name, prosoft_company_code, prosoft_plan_code, cnpj, self._now()),
            )
            self._audit(cur.lastrowid, "empresa_criada", {"id": cur.lastrowid})
        return self._company(cur.lastrowid)

    def list_companies(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM companies ORDER BY id")]

    def create_period(self, company_id, reference_competence, processing_competence):
        self._company(company_id)
        reference_competence, processing_competence = _month(
            reference_competence
        ), _month(processing_competence)
        with self.db:
            old = self.db.execute(
                "SELECT * FROM periods WHERE company_id=? AND reference_competence=? AND processing_competence=?",
                (company_id, reference_competence, processing_competence),
            ).fetchone()
            if old:
                return dict(old)
            cur = self.db.execute(
                "INSERT INTO periods(company_id,reference_competence,processing_competence) VALUES(?,?,?)",
                (company_id, reference_competence, processing_competence),
            )
            self._audit(
                company_id,
                "periodo_criado",
                {
                    "id": cur.lastrowid,
                    "reference_competence": reference_competence,
                    "processing_competence": processing_competence,
                },
            )
        return self._owned("periods", company_id, cur.lastrowid)

    def list_periods(self, company_id):
        self._company(company_id)
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM periods WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            )
        ]

    def import_plan(self, company_id, label, accounts, *, _in_transaction=False):
        self._company(company_id)
        label = _text(label, "nome do plano", 100)
        if not isinstance(accounts, list) or not accounts or len(accounts) > 50000:
            raise ValueError("Plano deve conter de 1 a 50000 contas")
        normalized = {}
        for entry in accounts:
            if not isinstance(entry, dict):
                raise ValueError("Cada conta deve ser um objeto")
            row = {
                "code": _text(entry.get("code"), "código", 80),
                "description": _text(entry.get("description"), "descrição", 500),
                "parent_code": _text(
                    entry.get("parent_code") or "", "conta superior", 80, False
                )
                or None,
                "kind": entry.get("kind"),
                "nature": entry.get("nature"),
                "attributes": entry.get("attributes", {}),
            }
            if row["kind"] not in {"sintetica", "analitica"} or row["nature"] not in {
                "devedora",
                "credora",
            }:
                raise ValueError(
                    "Informe tipo sintetica/analitica e natureza devedora/credora"
                )
            if not isinstance(row["attributes"], dict):
                raise ValueError("Atributos devem ser um objeto")
            _json(row["attributes"])
            if row["code"] in normalized:
                raise ValueError("Código de conta duplicado")
            normalized[row["code"]] = row
        for row in normalized.values():
            parent = row["parent_code"]
            if parent and (
                parent not in normalized or normalized[parent]["kind"] != "sintetica"
            ):
                raise ValueError("Conta superior ausente ou não sintética")
        visited = set()
        for code in normalized:
            path = set()
            cursor = code
            while cursor and cursor not in visited:
                if cursor in path:
                    raise ValueError("Ciclo na hierarquia do plano")
                path.add(cursor)
                cursor = normalized[cursor]["parent_code"]
            visited.update(path)
        with self._import_transaction(_in_transaction):
            version = self.db.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM plans WHERE company_id=? AND label=?",
                (company_id, label),
            ).fetchone()[0]
            cur = self.db.execute(
                "INSERT INTO plans(company_id,label,version,created_at) VALUES(?,?,?,?)",
                (company_id, label, version, self._now()),
            )
            plan_id = cur.lastrowid
            for row in normalized.values():
                self.db.execute(
                    "INSERT INTO accounts(plan_id,code,description,parent_code,kind,nature,attributes) VALUES(?,?,?,?,?,?,?)",
                    (
                        plan_id,
                        row["code"],
                        row["description"],
                        row["parent_code"],
                        row["kind"],
                        row["nature"],
                        _json(row["attributes"]),
                    ),
                )
            self._audit(
                company_id,
                "plano_importado",
                {"id": plan_id, "version": version, "accounts": len(accounts)},
            )
        return self._owned("plans", company_id, plan_id)

    def list_plans(self, company_id):
        self._company(company_id)
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT p.*, (SELECT COUNT(*) FROM accounts a WHERE a.plan_id=p.id) AS account_count FROM plans p WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            )
        ]

    def list_accounts(self, company_id, plan_id):
        self._owned("plans", company_id, plan_id)
        rows = [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM accounts WHERE plan_id=? ORDER BY code", (plan_id,)
            )
        ]
        for r in rows:
            r["attributes"] = json.loads(r["attributes"])
        return rows

    def save_mapping(
        self,
        company_id,
        plan_id,
        source_account,
        target_code,
        valid_from,
        valid_to=None,
        state="rascunho",
        reason="",
    ):
        self._owned("plans", company_id, plan_id)
        source_account, target_code = _text(
            source_account, "conta de origem", 100
        ), _text(target_code, "destino", 80)
        valid_from = _month(valid_from)
        valid_to = _month(valid_to) if valid_to else None
        if valid_to and valid_to < valid_from:
            raise ValueError("Fim de vigência anterior ao início")
        if state not in {"rascunho", "revisado", "aprovado", "inativo"}:
            raise ValueError("Estado de mapeamento inválido")
        reason = _text(reason, "justificativa", 1000, False)
        if state in {"revisado", "aprovado"} and not reason:
            raise ValueError("Revisão/aprovação exige justificativa")
        target = self.db.execute(
            "SELECT kind FROM accounts WHERE plan_id=? AND code=?",
            (plan_id, target_code),
        ).fetchone()
        if not target or target[0] != "analitica":
            raise ValueError("Destino deve ser conta analítica do plano selecionado")
        with self.db:
            version = self.db.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM mappings WHERE company_id=? AND plan_id=? AND source_account=?",
                (company_id, plan_id, source_account),
            ).fetchone()[0]
            cur = self.db.execute(
                "INSERT INTO mappings(company_id,plan_id,source_account,target_code,valid_from,valid_to,state,version,reason,actor,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    company_id,
                    plan_id,
                    source_account,
                    target_code,
                    valid_from,
                    valid_to,
                    state,
                    version,
                    reason,
                    self.actor,
                    self._now(),
                ),
            )
            self._audit(
                company_id,
                "mapeamento_versionado",
                {"id": cur.lastrowid, "version": version, "state": state},
            )
        return dict(
            self.db.execute(
                "SELECT * FROM mappings WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        )

    def list_mappings(self, company_id):
        self._company(company_id)
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM mappings WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            )
        ]

    @contextmanager
    def _import_transaction(self, in_batch):
        if not in_batch:
            with self.db:
                yield
            return
        self.db.execute("SAVEPOINT import_one_file")
        try:
            yield
        except Exception:
            self.db.execute("ROLLBACK TO import_one_file")
            self.db.execute("RELEASE import_one_file")
            raise
        else:
            self.db.execute("RELEASE import_one_file")

    def import_file(
        self,
        company_id,
        period_id,
        filename,
        content,
        kind,
        sped_profile=None,
        *,
        _in_batch=False,
    ):
        company = self._company(company_id)
        period = self._owned("periods", company_id, period_id)
        filename = _text(filename, "nome de arquivo", 255)
        if "/" in filename or "\\" in filename:
            raise ValueError("Use apenas o nome do arquivo")
        if (
            kind not in {"XML", "SPED"}
            or not isinstance(content, bytes)
            or not content
            or len(content) > MAX_FILE_BYTES
        ):
            raise ValueError("Tipo não suportado ou arquivo vazio/maior que 10 MiB")
        if sped_profile is not None and (
            kind != "SPED" or sped_profile != SPED_PROFILE
        ):
            raise ValueError("Perfil SPED não suportado para este arquivo")
        digest = hashlib.sha256(content).hexdigest()
        metadata = {}
        status = "validado"
        payload = None
        try:
            if kind == "XML":
                payload = parse_nfe(content)
                if company["cnpj"] and company["cnpj"] not in {
                    payload["issuer"],
                    payload["buyer"],
                }:
                    raise ValueError("Documento não identifica a empresa cadastrada")
                metadata = {
                    "normalizer": XML_PROFILE,
                    "company_identity_verified": bool(company["cnpj"]),
                    "warnings": [],
                }
                metadata["catalog_profile"] = "cadastros-origem-v1"
                metadata["catalog_issues"] = [
                    product["locator"]
                    + ": código ou descrição ausente; cadastro pendente"
                    for product in payload["products"]
                    if not product["data"]["code"] or not product["data"]["description"]
                ]
                if payload["competence"] != period["processing_competence"]:
                    metadata["warnings"].append(
                        "Emissão fora da competência de escrituração; conferir entrada/saída e enquadramento."
                    )
                if not payload["buyer"]:
                    metadata["warnings"].append(
                        "NFC-e sem destinatário identificado na fonte; conferir as condições aplicáveis."
                    )
                if payload["billing_warnings"]:
                    status = "pendente"
                    metadata["billing_warnings"] = payload["billing_warnings"]
                if not company["cnpj"]:
                    status = "pendente"
                    metadata["warning"] = (
                        "CNPJ da empresa ausente; identidade não conferida"
                    )
            else:
                try:
                    text = content.decode("utf-8-sig")
                    encoding = "utf-8"
                except UnicodeDecodeError:
                    text = content.decode("cp1252")
                    encoding = "cp1252"
                if "\x00" in text:
                    raise ValueError("SPED contém caractere nulo")
                counts = {}
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    if not line.startswith("|") or not line.endswith("|"):
                        raise ValueError("Linha SPED sem delimitadores")
                    record = line.split("|")[1]
                    if not re.fullmatch(r"[A-Z0-9]{4}", record):
                        raise ValueError("Identificador de registro inválido")
                    counts[record] = counts.get(record, 0) + 1
                if not counts:
                    raise ValueError("Nenhum registro SPED identificado")
                status = "pendente"
                metadata = {
                    "encoding": encoding,
                    "record_counts": counts,
                    "warning": "Recebimento apenas: leiaute, documentos e reconciliação XML × SPED ainda não normalizados",
                }
        except (ValueError, UnicodeError) as exc:
            status = "rejeitado"
            metadata = {"error": str(exc)}
            payload = None
        with self._import_transaction(_in_batch):
            existing = self.db.execute(
                "SELECT id,status FROM files WHERE company_id=? AND period_id=? AND kind=? AND sha256=?",
                (company_id, period_id, kind, digest),
            ).fetchone()
            if existing:
                if existing["status"] == "excluido":
                    raise ValueError(
                        "Arquivo foi removido logicamente; restauração exige fluxo próprio"
                    )
                if sped_profile is not None and existing["status"] != "rejeitado":
                    self._index_source(
                        company,
                        period,
                        self._owned("files", company_id, existing["id"]),
                        sped_profile,
                    )
                self._audit(company_id, "arquivo_repetido", {"id": existing["id"]})
                result = self._file(company_id, existing["id"])
                result["duplicate"] = True
                return result
            cur = self.db.execute(
                "INSERT INTO files(company_id,period_id,filename,kind,sha256,size,original,status,metadata,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    company_id,
                    period_id,
                    filename,
                    kind,
                    digest,
                    len(content),
                    content,
                    status,
                    _json(metadata),
                    self._now(),
                ),
            )
            file_id = cur.lastrowid
            if payload is not None:
                file_row = self._owned("files", company_id, file_id)
                self._index_source(company, period, file_row, XML_PROFILE, payload)
            elif kind == "SPED" and status != "rejeitado" and sped_profile is not None:
                indexed = self._index_source(
                    company,
                    period,
                    self._owned("files", company_id, file_id),
                    sped_profile,
                )
                current_metadata = self._file(company_id, file_id)["metadata"]
                current_metadata["analysis"] = indexed
                current_metadata["warning"] = (
                    "Leitura parcial para conciliação; sem validação integral ou liberação Prosoft"
                )
                self.db.execute(
                    "UPDATE files SET metadata=? WHERE id=?",
                    (_json(current_metadata), file_id),
                )
            self._audit(
                company_id,
                "arquivo_importado",
                {
                    "id": file_id,
                    "kind": kind,
                    "status": self.db.execute(
                        "SELECT status FROM files WHERE id=?", (file_id,)
                    ).fetchone()[0],
                    "sha256": digest,
                },
            )
        result = self._file(company_id, file_id)
        result["duplicate"] = False
        return result

    def _file(self, company_id, file_id):
        self._company(company_id)
        row = self.db.execute(
            "SELECT id,company_id,period_id,filename,kind,sha256,size,status,metadata,created_at FROM files WHERE id=? AND company_id=?",
            (file_id, company_id),
        ).fetchone()
        if not row:
            raise ValueError("Arquivo não encontrado para empresa")
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        result["analyses"] = [
            dict(r)
            for r in self.db.execute(
                "SELECT id,profile,status,created_at FROM file_indexings WHERE file_id=? ORDER BY id",
                (file_id,),
            )
        ]
        return result

    def list_files(self, company_id):
        self._company(company_id)
        return [
            self._file(company_id, r[0])
            for r in self.db.execute(
                "SELECT id FROM files WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            ).fetchall()
        ]

    def list_documents(self, company_id, period_id=None):
        self._company(company_id)
        params = [company_id]
        sql = "SELECT * FROM documents WHERE company_id=?"
        if period_id is not None:
            self._owned("periods", company_id, period_id)
            sql += " AND period_id=?"
            params.append(period_id)
        rows = [dict(r) for r in self.db.execute(sql + " ORDER BY id DESC", params)]
        for row in rows:
            row["payload"] = json.loads(row["payload"])
            row["sources"] = [
                dict(r)
                for r in self.db.execute(
                    "SELECT s.file_id,s.conflict,f.filename,f.status FROM document_sources s JOIN files f ON f.id=s.file_id WHERE s.document_id=? ORDER BY s.file_id",
                    (row["id"],),
                )
            ]
        return rows

    def list_audit(self, company_id):
        self._company(company_id)
        rows = [
            dict(r)
            for r in self.db.execute(
                "SELECT * FROM audit WHERE company_id=? ORDER BY id DESC", (company_id,)
            )
        ]
        for row in rows:
            row["details"] = json.loads(row["details"])
        return rows

    def deletion_preview(self, company_id, file_id):
        row = self._file(company_id, file_id)
        docs = [
            r[0]
            for r in self.db.execute(
                "SELECT document_id FROM document_sources WHERE file_id=? ORDER BY document_id",
                (file_id,),
            )
        ]
        preview = {
            "file_id": row["id"],
            "filename": row["filename"],
            "document_ids": docs,
            "status": row["status"],
            "operation": "remocao_logica",
            "consequence": "Preserva original e auditoria; documentos vinculados ficam pendentes. Purga definitiva indisponível.",
        }
        preview["invoice_ids"] = [
            r[0]
            for r in self.db.execute(
                "SELECT i.id FROM invoices i JOIN document_sources s ON s.document_id=i.document_id WHERE s.file_id=? ORDER BY i.id",
                (file_id,),
            )
        ]
        preview["installment_ids"] = [
            r[0]
            for r in self.db.execute(
                "SELECT p.id FROM installments p JOIN invoices i ON i.id=p.invoice_id JOIN document_sources s ON s.document_id=i.document_id WHERE s.file_id=? ORDER BY p.id",
                (file_id,),
            )
        ]
        preview["closed_batch_ids"] = [
            r[0]
            for r in self.db.execute(
                "SELECT DISTINCT b.id FROM accounting_batches b JOIN accounting_batch_documents d ON d.batch_id=b.id JOIN document_sources s ON s.document_id=d.document_id WHERE s.file_id=? AND b.status='fechado' ORDER BY b.id",
                (file_id,),
            )
        ]
        fiscal = [
            e for e in self.list_fiscal_entries(company_id) if e["document_id"] in docs
        ]
        preview["fiscal_entry_ids"] = [e["id"] for e in fiscal]
        preview["protected_fiscal_entry_ids"] = [
            e["id"]
            for e in fiscal
            if e["current"]
            and self._fiscal_guard(
                company_id, e["current"]["period_id"], e["document_id"]
            )
        ]
        preview["removal_blocked"] = bool(
            preview["closed_batch_ids"] or preview["protected_fiscal_entry_ids"]
        )
        preview["preview_token"] = hashlib.sha256(_json(preview).encode()).hexdigest()
        return preview

    def delete_file(
        self, company_id, file_id, reason, confirmed=False, preview_token=None
    ):
        reason = _text(reason, "motivo", 1000)
        if confirmed is not True:
            raise ValueError("Confirme a prévia de dependências para remoção lógica")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            preview = self.deletion_preview(company_id, file_id)
            if preview["status"] == "excluido":
                raise ValueError("Arquivo já removido logicamente")
            if preview_token is not None and preview_token != preview["preview_token"]:
                raise ValueError(
                    "Prévia desatualizada; confira novamente as dependências"
                )
            if preview["removal_blocked"]:
                raise ValueError(
                    "Fonte vinculada a lote fechado ou período fiscal protegido; remoção bloqueada até fluxo de estorno/ajuste"
                )
            self.db.execute(
                "UPDATE files SET status='excluido' WHERE id=? AND company_id=?",
                (file_id, company_id),
            )
            for document_id in preview["document_ids"]:
                self.db.execute(
                    "UPDATE documents SET status='pendente' WHERE id=? AND company_id=?",
                    (document_id, company_id),
                )
                self.db.execute(
                    "UPDATE invoices SET status='pendente' WHERE document_id=?",
                    (document_id,),
                )
                self.db.execute(
                    "UPDATE installments SET status='pendente' WHERE invoice_id IN (SELECT id FROM invoices WHERE document_id=?)",
                    (document_id,),
                )
            self._audit(
                company_id,
                "arquivo_removido_logicamente",
                {
                    "id": file_id,
                    "reason": reason,
                    "document_ids": preview["document_ids"],
                    "invoice_ids": preview["invoice_ids"],
                    "installment_ids": preview["installment_ids"],
                },
            )
        return preview
