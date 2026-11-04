"""Small synthetic safeguards for the documented integration contract.

This is not a fiscal parser, SPED generator, Prosoft adapter, or accounting
posting engine. Production behavior must be designed from the confirmed
importer contract and approved mappings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import hashlib
import json


def validate_competence(value: str) -> str:
    """Return YYYY-MM if it is a valid calendar month."""
    if len(value) != 7 or value[4] != "-":
        raise ValueError("competência deve usar AAAA-MM")
    try:
        date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise ValueError("competência inválida") from exc
    return value


@dataclass(frozen=True)
class RunScope:
    reference_competence: str
    processing_competence: str

    def __post_init__(self) -> None:
        validate_competence(self.reference_competence)
        validate_competence(self.processing_competence)

    def accepts_document_month(self, document_competence: str) -> bool:
        return validate_competence(document_competence) == self.processing_competence


@dataclass(frozen=True)
class AccountingLineIdentity:
    company_scope_alias: str
    processing_competence: str
    source_document_key: str
    mapping_version: str
    posting_group: str
    line_id: str


def idempotency_key(identity: AccountingLineIdentity) -> str:
    """Stable local manifest key. Never use identifying company data here."""
    if not all(asdict(identity).values()):
        raise ValueError("todos os campos de identidade precisam estar preenchidos")
    validate_competence(identity.processing_competence)
    canonical = json.dumps(
        asdict(identity), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_unique_idempotency_keys(keys: list[str]) -> None:
    if len(keys) != len(set(keys)):
        raise ValueError("chave contábil duplicada no lote")


class ImportState(str, Enum):
    PREPARED = "PREPARADO"
    REVIEWED = "REVISADO"
    STARTED = "IMPORTACAO_INICIADA"
    UNKNOWN = "RESULTADO_DESCONHECIDO"
    CONFIRMED = "CONFIRMADO"
    RECONCILIATION_PENDING = "RECONCILIACAO_PENDENTE"
    REJECTED = "REJEITADO"
    RECONCILED = "CONCILIADO"


def may_start_first_import(state: ImportState, attempt_count: int) -> bool:
    """Allow only the first reviewed attempt; retries need a new manifest."""
    return state is ImportState.REVIEWED and attempt_count == 0


def may_retry_unknown_outcome(state: ImportState) -> bool:
    """An uncertain result always requires reconciliation, never blind retry."""
    return state not in {
        ImportState.STARTED,
        ImportState.UNKNOWN,
        ImportState.CONFIRMED,
        ImportState.RECONCILIATION_PENDING,
        ImportState.RECONCILED,
        ImportState.REJECTED,
    }

