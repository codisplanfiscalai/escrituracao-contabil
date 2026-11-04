"""Deterministic historical evidence. Never a Prosoft/EFD import format."""
import csv
import hashlib
import io
import json
from datetime import date
from decimal import Decimal, localcontext

from .accounting_store import amount, digest, dump, identifier
from .contract_safety import validate_competence

PROFILE = "accounting-evidence-v1"
ARTIFACT_TYPES = {
    "evidence.json": "application/json; charset=utf-8",
    "postings.csv": "text/csv; charset=utf-8",
    "manifest.json": "application/json; charset=utf-8",
}
EVIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounting_evidence_exports (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 batch_id INTEGER NOT NULL REFERENCES accounting_batches(id), profile TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL, manifest_sha256 TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(batch_id,profile));
CREATE TABLE IF NOT EXISTS accounting_evidence_artifacts (
 export_id INTEGER NOT NULL REFERENCES accounting_evidence_exports(id),
 name TEXT NOT NULL, media_type TEXT NOT NULL, sha256 TEXT NOT NULL,
 size INTEGER NOT NULL, content BLOB NOT NULL, PRIMARY KEY(export_id,name));
"""
CSV_COLUMNS = (
    "profile", "batch_id", "batch_version", "snapshot_sha256", "company_id", "company_name",
    "reference_competence", "processing_competence", "plan_id", "plan_label", "plan_version",
    "line", "document_id", "document_business_key", "observation_id", "source_file_id",
    "source_sha256", "source_filename", "source_profile", "source_locator", "document_review_id",
    "document_review_version", "document_review_actor", "document_review_reason", "source_fingerprint",
    "group", "date", "side", "amount", "account_id", "account_code", "account_description",
    "account_nature", "mapping_id", "mapping_version", "mapping_source_account", "mapping_target_code",
    "mapping_valid_from", "mapping_valid_to", "mapping_actor", "mapping_reason", "memo",
)
CSV_TEXT_COLUMNS = (
    "company_name", "plan_label", "document_business_key", "source_filename", "source_locator",
    "document_review_actor", "document_review_reason", "group", "account_code", "account_description",
    "mapping_source_account", "mapping_target_code", "mapping_actor", "mapping_reason", "memo",
)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(value):
    return (dump(value) + "\n").encode("utf-8")


def _require(condition, message):
    if not condition:
        raise ValueError("Evidência inconsistente: " + message)


def validate_historical_batch(batch):
    """Verify the sealed snapshot itself without consulting live source versions."""
    _require(batch["status"] == "fechado", "somente lote fechado pode gerar evidências")
    _require(all(batch.get(key) for key in ("review_actor", "review_reason", "reviewed_at", "closed_at")), "revisão e fechamento explícitos obrigatórios")
    snapshot = batch["snapshot"]
    _require(digest(snapshot) == batch["snapshot_hash"], "hash do snapshot divergente")
    try:
        _validate_snapshot(snapshot, batch)
    except (KeyError, TypeError, IndexError, AttributeError, ArithmeticError) as exc:
        raise ValueError("Evidência inconsistente: estrutura do snapshot inválida") from exc
    return snapshot


def _validate_snapshot(snapshot, batch):
    _require(snapshot["engine"] == "explicit-document-v1" and snapshot["ready_for_export"] is False, "motor/perfil não suportado")
    _require(snapshot["company"]["id"] == batch["company_id"], "empresa do snapshot")
    for key, field in (("period", "period_id"), ("plan", "plan_id")):
        _require(snapshot[key]["id"] == batch[field] and snapshot[key]["company_id"] == batch["company_id"], key + " do snapshot")
    competence = validate_competence(snapshot["period"]["processing_competence"])
    validate_competence(snapshot["period"]["reference_competence"])
    _require(isinstance(snapshot["documents"], list) and bool(snapshot["documents"]), "decisões documentais ausentes")
    reviews = {}
    for review in snapshot["documents"]:
        document_id = identifier(review["document_id"])
        _require(document_id not in reviews, "decisão duplicada para documento")
        _require(review["company_id"] == batch["company_id"] and review["period_id"] == batch["period_id"] and review["valid"] is True, "contexto da revisão documental")
        _require(all(review[key] for key in ("actor", "reason", "created_at")), "metadados da revisão documental")
        source = review["snapshot"]
        _require(digest(source) == review["source_fingerprint"], "fingerprint da revisão documental")
        _require(source["document_id"] == document_id and source["period_id"] == batch["period_id"], "documento da revisão")
        chosen = [row for row in source["observations"] if row["id"] == review["chosen_observation_id"]]
        _require(len(chosen) == 1, "observação escolhida ausente/ambígua")
        chosen = chosen[0]
        _require(chosen["entity_kind"] == "documento" and chosen["document_id"] == document_id and chosen["period_id"] == batch["period_id"] and chosen["file_status"] != "excluido", "origem documental escolhida")
        files = [row for row in source["files"] if row["id"] == chosen["file_id"]]
        _require(len(files) == 1 and files[0]["status"] != "excluido" and files[0]["period_id"] == batch["period_id"], "arquivo da origem")
        _require(chosen["normalized"]["key"] == source["business_key"], "chave documental da origem")
        reviews[document_id] = review
    entries = snapshot["entries"]
    _require(isinstance(entries, list) and 2 <= len(entries) <= 10000, "quantidade de partidas")
    groups, seen_documents = {}, set()
    with localcontext() as context:
        context.prec = 40
        for number, line in enumerate(entries, 1):
            _require(line["line"] == number, "sequência de partidas")
            document_id = identifier(line["document_id"])
            _require(document_id in reviews, "revisão da partida ausente")
            review = reviews[document_id]
            seen_documents.add(document_id)
            _require(line["review_id"] == review["id"] and line["observation_id"] == review["chosen_observation_id"], "rastreabilidade da partida")
            posting_date = date.fromisoformat(line["date"])
            _require(posting_date.isoformat() == line["date"] and line["date"][:7] == competence, "data fora dos movimentos")
            _require(line["side"] in ("D", "C") and bool(line["group"]), "lado/grupo da partida")
            value = amount(line["amount"])
            _require(value == line["amount"], "representação decimal da partida")
            mapping, account = line["mapping"], line["account"]
            _require(mapping["company_id"] == batch["company_id"] and mapping["plan_id"] == batch["plan_id"] and account["plan_id"] == batch["plan_id"], "plano/empresa da conta e mapeamento")
            _require(mapping["state"] == "aprovado" and mapping["target_code"] == account["code"] and account["kind"] == "analitica", "mapeamento aprovado com destino analítico")
            _require(mapping["valid_from"] <= competence and (mapping["valid_to"] is None or mapping["valid_to"] >= competence), "vigência do mapeamento histórico")
            key = (document_id, line["group"])
            groups.setdefault(key, {"D": Decimal(0), "C": Decimal(0)})[line["side"]] += Decimal(value)
        _require(seen_documents == set(reviews), "documento sem partidas")
        for totals in groups.values():
            _require(totals["D"] == totals["C"], "grupo desequilibrado")
        for document_id, review in reviews.items():
            chosen = next(row for row in review["snapshot"]["observations"] if row["id"] == review["chosen_observation_id"])
            debit = sum((totals["D"] for key, totals in groups.items() if key[0] == document_id), Decimal(0))
            _require(debit == Decimal(amount(chosen["normalized"]["total"])), "total documental diferente da origem")
        totals = {"debit": format(sum((row["D"] for row in groups.values()), Decimal(0)), ".2f"),
                  "credit": format(sum((row["C"] for row in groups.values()), Decimal(0)), ".2f")}
        _require(totals == snapshot["totals"], "totalizadores do lote")
        expected_groups = [{"document_id": key[0], "group": key[1], "debit": format(value["D"], ".2f"), "credit": format(value["C"], ".2f")} for key, value in sorted(groups.items())]
        _require(snapshot["groups"] == expected_groups, "totalizadores por grupo")


def build_artifacts(batch, closure):
    snapshot = validate_historical_batch(batch)
    envelope = {"profile": PROFILE, "purpose": "historical_local_accounting_evidence",
                "prosoft_compatible": False, "efd_compatible": False, "externally_posted": False,
                "batch": {key: value for key, value in batch.items() if key != "snapshot"},
                "closure_audit": closure, "snapshot": snapshot}
    evidence = json_bytes(envelope)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    reviews = {review["document_id"]: review for review in snapshot["documents"]}
    for line in snapshot["entries"]:
        review = reviews[line["document_id"]]
        source = next(row for row in review["snapshot"]["observations"] if row["id"] == line["observation_id"])
        file_info = next(row for row in review["snapshot"]["files"] if row["id"] == source["file_id"])
        mapping, account = line["mapping"], line["account"]
        row = {"profile": PROFILE, "batch_id": batch["id"], "batch_version": batch["version"], "snapshot_sha256": batch["snapshot_hash"],
               "company_id": batch["company_id"], "company_name": snapshot["company"]["name"],
               "reference_competence": snapshot["period"]["reference_competence"], "processing_competence": snapshot["period"]["processing_competence"],
               "plan_id": batch["plan_id"], "plan_label": snapshot["plan"]["label"], "plan_version": snapshot["plan"]["version"],
               "line": line["line"], "document_id": line["document_id"], "document_business_key": review["snapshot"]["business_key"],
               "observation_id": line["observation_id"], "source_file_id": source["file_id"], "source_sha256": file_info["sha256"],
               "source_filename": source["filename"], "source_profile": source["profile"], "source_locator": source["locator"],
               "document_review_id": review["id"], "document_review_version": review["version"], "document_review_actor": review["actor"],
               "document_review_reason": review["reason"], "source_fingerprint": review["source_fingerprint"],
               "group": line["group"], "date": line["date"], "side": line["side"], "amount": line["amount"],
               "account_id": account["id"], "account_code": account["code"], "account_description": account["description"],
               "account_nature": account["nature"], "mapping_id": mapping["id"], "mapping_version": mapping["version"],
               "mapping_source_account": mapping["source_account"], "mapping_target_code": mapping["target_code"],
               "mapping_valid_from": mapping["valid_from"], "mapping_valid_to": mapping["valid_to"],
               "mapping_actor": mapping["actor"], "mapping_reason": mapping["reason"], "memo": line["memo"]}
        for column in CSV_TEXT_COLUMNS:
            row[column] = "'" + row[column]
        writer.writerow(row)
    postings = stream.getvalue().encode("utf-8-sig")
    manifest = {"profile": PROFILE, "company_id": batch["company_id"], "batch_id": batch["id"], "batch_version": batch["version"],
                "snapshot_sha256": batch["snapshot_hash"], "historical_snapshot_only": True,
                "prosoft_compatible": False, "efd_compatible": False, "externally_posted": False,
                "line_count": len(snapshot["entries"]), "document_count": len(snapshot["documents"]), "totals": snapshot["totals"],
                "artifacts": [{"name": name, "media_type": ARTIFACT_TYPES[name], "sha256": sha256(content), "size": len(content)} for name, content in (("evidence.json", evidence), ("postings.csv", postings))],
                "csv": {"encoding": "utf-8-sig", "delimiter": ",", "line_ending": "CRLF", "columns": CSV_COLUMNS,
                        "apostrophe_prefixed_text_columns": CSV_TEXT_COLUMNS, "text_recovery": "Remove exactly the first apostrophe from the listed columns; JSON preserves originals."}}
    return {"evidence.json": evidence, "postings.csv": postings, "manifest.json": json_bytes(manifest)}


class EvidenceExportMixin:
    def _evidence_record(self, company_id, export_id):
        self._company(company_id)
        row = self.db.execute("SELECT * FROM accounting_evidence_exports WHERE company_id=? AND id=?", (company_id, identifier(export_id))).fetchone()
        if row is None:
            raise ValueError("Evidência não pertence à empresa selecionada ou não existe")
        return dict(row)

    def _evidence_metadata(self, record):
        result = dict(record)
        result["artifacts"] = [dict(row) for row in self.db.execute("SELECT name,media_type,sha256,size FROM accounting_evidence_artifacts WHERE export_id=? ORDER BY name", (record["id"],))]
        return result

    def _verified_artifacts(self, record):
        rows = {row["name"]: dict(row) for row in self.db.execute("SELECT * FROM accounting_evidence_artifacts WHERE export_id=?", (record["id"],))}
        _require(set(rows) == set(ARTIFACT_TYPES), "conjunto de arquivos preservados incompleto")
        for name, row in rows.items():
            content = bytes(row["content"])
            _require(row["media_type"] == ARTIFACT_TYPES[name] and len(content) == row["size"] and sha256(content) == row["sha256"], "hash/tamanho/tipo de arquivo preservado divergente")
        _require(rows["manifest.json"]["sha256"] == record["manifest_sha256"], "hash do manifesto divergente")
        manifest = json.loads(rows["manifest.json"]["content"])
        _require(manifest.get("profile") == record["profile"] and manifest.get("batch_id") == record["batch_id"] and manifest.get("company_id") == record["company_id"] and manifest.get("snapshot_sha256") == record["snapshot_hash"], "contexto do manifesto divergente")
        expected = [{key: rows[name][key] for key in ("name", "media_type", "sha256", "size")} for name in ("evidence.json", "postings.csv")]
        _require(manifest.get("artifacts") == expected, "manifesto não corresponde aos arquivos preservados")
        return rows

    def list_evidence_exports(self, company_id, batch_id=None):
        self._company(company_id)
        if batch_id is not None:
            batch_id = self._batch(company_id, batch_id)["id"]
        records = self.db.execute("SELECT * FROM accounting_evidence_exports WHERE company_id=? ORDER BY id DESC", (company_id,)).fetchall()
        return [self._evidence_metadata(dict(row)) for row in records if batch_id is None or row["batch_id"] == batch_id]

    def create_evidence_export(self, company_id, batch_id, snapshot_hash, reason):
        from .persistence import _text
        reason = _text(reason, "motivo da exportação de evidências", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            batch = self._batch(company_id, batch_id)
            _require(snapshot_hash == batch["snapshot_hash"], "hash informado diverge do lote; confira o snapshot")
            validate_historical_batch(batch)
            existing = self.db.execute("SELECT * FROM accounting_evidence_exports WHERE company_id=? AND batch_id=? AND profile=?", (company_id, batch["id"], PROFILE)).fetchone()
            if existing:
                record = dict(existing)
                _require(record["snapshot_hash"] == snapshot_hash, "hash do lote diverge da exportação preservada")
                self._verified_artifacts(record)
                self._audit(company_id, "evidencia_contabil_repetida", {"export_id": record["id"], "batch_id": batch["id"], "manifest_sha256": record["manifest_sha256"], "reason": reason})
                return {**self._evidence_metadata(record), "duplicate": True}
            closures = []
            for row in self.db.execute("SELECT * FROM audit WHERE company_id=? AND action='lote_contabil_fechado' ORDER BY id", (company_id,)):
                details = json.loads(row["details"])
                if details.get("batch_id") == batch["id"]:
                    closures.append({**dict(row), "details": details})
            _require(len(closures) == 1 and closures[0]["details"].get("snapshot_hash") == snapshot_hash and bool(closures[0]["details"].get("reason")), "evento auditado de fechamento ausente/ambíguo")
            artifacts = build_artifacts(batch, closures[0])
            manifest_hash = sha256(artifacts["manifest.json"])
            cur = self.db.execute("INSERT INTO accounting_evidence_exports(company_id,batch_id,profile,snapshot_hash,manifest_sha256,actor,reason,created_at) VALUES(?,?,?,?,?,?,?,?)", (company_id, batch["id"], PROFILE, snapshot_hash, manifest_hash, self.actor, reason, self._now()))
            export_id = cur.lastrowid
            for name, content in artifacts.items():
                self.db.execute("INSERT INTO accounting_evidence_artifacts(export_id,name,media_type,sha256,size,content) VALUES(?,?,?,?,?,?)", (export_id, name, ARTIFACT_TYPES[name], sha256(content), len(content), content))
            self._audit(company_id, "evidencia_contabil_criada", {"export_id": export_id, "batch_id": batch["id"], "profile": PROFILE, "snapshot_hash": snapshot_hash, "manifest_sha256": manifest_hash, "reason": reason})
            return {**self._evidence_metadata(self._evidence_record(company_id, export_id)), "duplicate": False}

    def read_evidence_artifact(self, company_id, export_id, name):
        if not isinstance(name, str) or name not in ARTIFACT_TYPES:
            raise ValueError("Nome de artefato não suportado; use um arquivo do manifesto")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            record = self._evidence_record(company_id, export_id)
            row = self._verified_artifacts(record)[name]
            self._audit(company_id, "evidencia_contabil_disponibilizada", {"export_id": record["id"], "batch_id": record["batch_id"], "name": name, "sha256": row["sha256"], "size": row["size"]})
            return {key: row[key] for key in ("name", "media_type", "sha256", "size", "content")}
