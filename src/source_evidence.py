"""source-evidence/2: immutable intake evidence before competence or chart selection."""

import hashlib
import json
import time
from pathlib import PurePosixPath
from .accounting_store import digest, dump, identifier
from .archive_reader import archive_members, MAX_EXPANDED_BYTES, MAX_MEMBERS
from .batch_import import inferred_kind

SOURCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS source_receipts (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 request_key TEXT NOT NULL, request_hash TEXT NOT NULL, actor TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(company_id,request_key));
CREATE TABLE IF NOT EXISTS source_inputs (
 id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
 receipt_id INTEGER REFERENCES source_receipts(id), parent_id INTEGER REFERENCES source_inputs(id),
 filename TEXT NOT NULL, kind TEXT NOT NULL, content BLOB, sha256 TEXT NOT NULL,
 size INTEGER NOT NULL, file_id INTEGER REFERENCES files(id), legacy_file_id INTEGER UNIQUE REFERENCES files(id),
 legacy_import_item_id INTEGER UNIQUE REFERENCES import_items(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_revisions (
 id INTEGER PRIMARY KEY, input_id INTEGER NOT NULL REFERENCES source_inputs(id),
 version INTEGER NOT NULL, evidence TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(input_id,version));
"""


def identify_source(content, kind):
    from .persistence import parse_nfe
    from .reconciliation import read_sped

    result = {
        "profile": "source-evidence/2",
        "state": "identificado",
        "kind": kind,
        "issues": [],
    }
    try:
        if kind == "XML":
            doc = parse_nfe(content)
            result.update(
                key=doc["key"],
                model=doc["model"],
                number=doc["number"],
                issued_date=doc["issued_at"][:10],
                issuer=doc["issuer"],
                buyer=doc["buyer"],
                total=doc["total"],
                suggested_competence=doc["competence"],
                products=doc.get("products", []),
                billing=doc.get("billing"),
            )
        elif kind == "SPED":
            records, metadata = read_sped(content)
            header = next((row for row in records if row["record"] == "0000"), None)
            if not header:
                raise ValueError("Cabeçalho 0000 ausente; original preservado.")
            result.update(
                encoding=metadata["encoding"],
                records=len(records),
                header=header["fields"],
                note="Identificação estrutural; o perfil de leitura é escolhido ao organizar.",
            )
        else:
            raise ValueError("Formato não suportado; original preservado para decisão.")
    except (ValueError, KeyError, TypeError) as error:
        result.update(state="pendente", issues=[str(error)])
    return result


class SourceEvidenceMixin:
    def _source_revision(self, company_id, input_id):
        self._company(company_id)
        row = self.db.execute(
            "SELECT r.*,i.company_id,i.receipt_id,i.parent_id,i.filename,i.kind,i.sha256,i.size,i.file_id,i.legacy_import_item_id FROM source_revisions r JOIN source_inputs i ON i.id=r.input_id WHERE i.company_id=? AND i.id=? ORDER BY r.version DESC LIMIT 1",
            (company_id, identifier(input_id)),
        ).fetchone()
        if not row:
            raise ValueError("Fonte não pertence à empresa.")
        result = dict(row)
        result["evidence"] = json.loads(result["evidence"])
        if digest(result["evidence"]) != result["snapshot_hash"]:
            raise ValueError("Evidência de origem alterada.")
        return result

    def source_history(self, company_id, input_id):
        self._source_revision(company_id, input_id)
        results = []
        for row in self.db.execute(
            "SELECT version,evidence,snapshot_hash,actor,reason,created_at FROM source_revisions WHERE input_id=? ORDER BY version DESC",
            (identifier(input_id),),
        ):
            data = dict(row)
            data["evidence"] = json.loads(data["evidence"])
            if digest(data["evidence"]) != data["snapshot_hash"]:
                raise ValueError("Histórico de evidência alterado.")
            results.append(data)
        return results

    def source_inbox(self, company_id):
        self._company(company_id)
        return [
            self._source_revision(company_id, row["id"])
            for row in self.db.execute(
                "SELECT id FROM source_inputs WHERE company_id=? ORDER BY id DESC",
                (company_id,),
            )
        ]

    def _append_source_revision(self, company_id, input_id, evidence, reason):
        version = self.db.execute(
            "SELECT COALESCE(MAX(version),0)+1 FROM source_revisions WHERE input_id=?",
            (input_id,),
        ).fetchone()[0]
        self.db.execute(
            "INSERT INTO source_revisions(input_id,version,evidence,snapshot_hash,actor,reason,created_at) VALUES(?,?,?,?,?,?,?)",
            (
                input_id,
                version,
                dump(evidence),
                digest(evidence),
                self.actor,
                reason,
                self._now(),
            ),
        )
        self._audit(
            company_id,
            "evidencia_fonte_versionada",
            {
                "input_id": input_id,
                "version": version,
                "snapshot_hash": digest(evidence),
                "reason": reason,
            },
        )

    def receive_sources(self, company_id, inputs, request_key):
        from .persistence import _text, MAX_FILE_BYTES

        self._company(company_id)
        request_key = _text(request_key, "tentativa", 100)
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_MEMBERS:
            raise ValueError("Envie de 1 a 500 fontes por recebimento.")
        manifest = []
        for item in inputs:
            if not isinstance(item, dict):
                raise ValueError("Entrada inválida.")
            name = _text(item.get("filename"), "nome", 255)
            content = item.get("content")
            if "/" in name or "\\" in name or name in {".", ".."}:
                raise ValueError("Nome externo deve ser um arquivo, sem caminho.")
            if not isinstance(content, bytes) or len(content) > MAX_FILE_BYTES:
                raise ValueError("Arquivo acima de 10 MiB ou conteúdo inválido.")
            manifest.append(
                {
                    "filename": name,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size": len(content),
                }
            )
        if sum(row["size"] for row in manifest) > MAX_EXPANDED_BYTES:
            raise ValueError("Recebimento acima de 100 MiB.")
        fingerprint = digest(manifest)
        deadline = time.monotonic() + 60
        expanded = 0
        count = 0
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.db.execute(
                "SELECT id,request_hash FROM source_receipts WHERE company_id=? AND request_key=?",
                (company_id, request_key),
            ).fetchone()
            if old:
                if old["request_hash"] != fingerprint:
                    raise ValueError("Tentativa já utilizada com outros arquivos.")
                return {
                    "receipt_id": old["id"],
                    "duplicate": True,
                    "items": [
                        row
                        for row in self.source_inbox(company_id)
                        if row["receipt_id"] == old["id"]
                    ],
                }
            receipt = self.db.execute(
                "INSERT INTO source_receipts(company_id,request_key,request_hash,actor,created_at) VALUES(?,?,?,?,?)",
                (company_id, request_key, fingerprint, self.actor, self._now()),
            ).lastrowid

            def record(name, content, kind, parent=None, error=None):
                nonlocal count, expanded
                count += 1
                if count > MAX_MEMBERS:
                    raise ValueError("Recebimento excede 500 entradas totais.")
                if content is not None:
                    expanded += len(content) if parent else 0
                if expanded > MAX_EXPANDED_BYTES:
                    raise ValueError("Expansão do recebimento excede 100 MiB.")
                sha = hashlib.sha256(content or b"").hexdigest()
                ident = self.db.execute(
                    "INSERT INTO source_inputs(company_id,receipt_id,parent_id,filename,kind,content,sha256,size,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        company_id,
                        receipt,
                        parent,
                        name,
                        kind,
                        content,
                        sha,
                        len(content or b""),
                        self._now(),
                    ),
                ).lastrowid
                evidence = (
                    {
                        "profile": "source-evidence/2",
                        "state": "pendente",
                        "kind": kind,
                        "issues": [error],
                    }
                    if error
                    else identify_source(content, kind)
                )
                self._append_source_revision(
                    company_id,
                    ident,
                    evidence,
                    "Recebimento e identificação da origem.",
                )
                return ident

            for item in inputs:
                kind = inferred_kind(item["filename"]) or "DESCONHECIDO"
                if kind not in {"ZIP", "7Z", "RAR"}:
                    record(
                        item["filename"],
                        item["content"],
                        kind,
                        error=(
                            "Orçamento de tempo excedido; original preservado."
                            if time.monotonic() >= deadline
                            else None
                        ),
                    )
                    continue
                parent = record(
                    item["filename"],
                    item["content"],
                    kind,
                    error="Pacote aguardando leitura.",
                )
                try:
                    if time.monotonic() >= deadline:
                        raise ValueError("Orçamento de tempo excedido.")
                    members = list(
                        archive_members(
                            item["content"],
                            kind,
                            timeout=max(0.01, min(20, deadline - time.monotonic())),
                        )
                    )
                    if (
                        count + len(members) > MAX_MEMBERS
                        or expanded + sum(len(m.get("content") or b"") for m in members)
                        > MAX_EXPANDED_BYTES
                    ):
                        raise ValueError(
                            "Pacote excede limites restantes do recebimento."
                        )
                    seen = set()
                    for member in members:
                        name = member["name"]
                        error = member.get("error")
                        if name in seen:
                            error = "Nome interno repetido; confira o pacote."
                        seen.add(name)
                        child_kind = inferred_kind(name) or "DESCONHECIDO"
                        if child_kind in {"ZIP", "7Z", "RAR"}:
                            error = "Pacotes aninhados não são processados."
                        record(name, member.get("content"), child_kind, parent, error)
                    self._append_source_revision(
                        company_id,
                        parent,
                        {
                            "profile": "source-evidence/2",
                            "state": "pacote",
                            "members": len(members),
                            "issues": [],
                        },
                        "Pacote expandido em memória; original preservado.",
                    )
                except ValueError as error:
                    self._append_source_revision(
                        company_id,
                        parent,
                        {
                            "profile": "source-evidence/2",
                            "state": "pendente",
                            "issues": [str(error)],
                        },
                        "Pacote recusado; original preservado.",
                    )
        return {
            "receipt_id": receipt,
            "duplicate": False,
            "items": [
                row
                for row in self.source_inbox(company_id)
                if row["receipt_id"] == receipt
            ],
        }

    def source_original(self, company_id, input_id):
        row = self._source_revision(company_id, input_id)
        source = self.db.execute(
            "SELECT content FROM source_inputs WHERE id=?", (identifier(input_id),)
        ).fetchone()
        if source["content"] is not None:
            content = bytes(source["content"])
        elif row["file_id"]:
            content = bytes(
                self._owned("files", company_id, row["file_id"])["original"]
            )
        elif row["legacy_import_item_id"]:
            content = self.read_import_original(
                company_id, row["legacy_import_item_id"]
            )["content"]
        else:
            raise ValueError("Conteúdo não extraído; consulte o pacote de origem.")
        if hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise ValueError("Hash do original divergente.")
        return {
            "name": "fonte-" + str(input_id) + ".bin",
            "content": content,
            "media_type": "application/octet-stream",
        }

    def organize_source(
        self, company_id, input_id, cycle_id, expected_hash, reason, sped_profile=None
    ):
        from .persistence import _text

        reason = _text(reason, "motivo da organização", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            source = self._source_revision(company_id, input_id)
            cycle = self._work_cycle(company_id, cycle_id)
            if source["snapshot_hash"] != expected_hash:
                raise ValueError("Evidência alterada; confira a versão vigente.")
            if cycle["state"] != "aberta":
                raise ValueError("Competência encerrada.")
            if source["evidence"]["state"] == "organizado":
                if source["evidence"].get("cycle_id") != cycle["id"]:
                    raise ValueError(
                        "Fonte já organizada em outra competência; não deslocar movimentos silenciosamente."
                    )
                if not sped_profile:
                    return source
            if source["evidence"]["state"] == "descartado":
                raise ValueError(
                    "Fonte retirada: não restaurar silenciosamente uma decisão anterior."
                )
            if source["kind"] not in {"XML", "SPED"}:
                raise ValueError(
                    "Organize os arquivos documentais, não o pacote ou formato desconhecido."
                )
            content = self.source_original(company_id, input_id)["content"]
            result = self.import_file(
                company_id,
                cycle["period_id"],
                PurePosixPath(source["filename"].replace("\\", "/")).name,
                content,
                source["kind"],
                sped_profile=sped_profile,
                _in_batch=True,
            )
            ids = [
                row["document_id"]
                for row in self.db.execute(
                    "SELECT document_id FROM document_sources WHERE file_id=?",
                    (result["id"],),
                )
            ]
            for doc in ids:
                document = self._owned("documents", company_id, doc)
                if (
                    self._owned("periods", company_id, document["period_id"])[
                        "processing_competence"
                    ]
                    != cycle["competence"]
                ):
                    raise ValueError(
                        "Documento já organizado em outra competência; consulte o vínculo existente."
                    )
            evidence = {
                **source["evidence"],
                "state": (
                    "organizado"
                    if result["status"] != "rejeitado" and ids
                    else "pendente"
                ),
                "cycle_id": cycle["id"],
                "period_id": cycle["period_id"],
                "file_id": result["id"],
                "document_ids": ids,
                "normalization": result["metadata"],
                "issues": (
                    []
                    if ids
                    else [
                        "Nenhum documento normalizado; selecione um perfil implementado ou registre a pendência."
                    ]
                ),
            }
            self.db.execute(
                "UPDATE source_inputs SET file_id=? WHERE id=?",
                (result["id"], identifier(input_id)),
            )
            self._append_source_revision(
                company_id, identifier(input_id), evidence, reason
            )
        return self._source_revision(company_id, input_id)

    def discard_source(self, company_id, input_id, expected_hash, reason):
        from .persistence import _text

        reason = _text(reason, "motivo da retirada", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            source = self._source_revision(company_id, input_id)
            if source["snapshot_hash"] != expected_hash:
                raise ValueError("Evidência alterada.")
            if source["file_id"]:
                raise ValueError(
                    "Fonte normalizada tem dependências; não pode ser retirada da caixa de entrada."
                )
            self._append_source_revision(
                company_id,
                identifier(input_id),
                {**source["evidence"], "state": "descartado"},
                reason,
            )
        return self._source_revision(company_id, input_id)

    def _migrate_work_sources(self):
        for row in self.db.execute(
            "SELECT id,company_id,period_id,filename,kind,sha256,size,status,metadata,created_at FROM files ORDER BY id"
        ).fetchall():
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO source_inputs(company_id,filename,kind,sha256,size,file_id,legacy_file_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    row["company_id"],
                    row["filename"],
                    row["kind"],
                    row["sha256"],
                    row["size"],
                    row["id"],
                    row["id"],
                    row["created_at"],
                ),
            )
            ident = cursor.lastrowid
            if not cursor.rowcount:
                continue
            period = self._owned("periods", row["company_id"], row["period_id"])
            cycle = self.db.execute(
                "SELECT id FROM work_cycles WHERE company_id=? AND competence=?",
                (row["company_id"], period["processing_competence"]),
            ).fetchone()
            evidence = {
                "profile": "source-evidence/2",
                "legacy": True,
                "state": (
                    "organizado"
                    if row["status"] not in {"rejeitado", "excluido"}
                    else "pendente" if row["status"] == "rejeitado" else "descartado"
                ),
                "file_id": row["id"],
                "period_id": row["period_id"],
                "cycle_id": cycle["id"],
                "metadata": json.loads(row["metadata"]),
                "issues": (
                    ["Fonte anterior: conferir o perfil de leitura."]
                    if row["status"] == "rejeitado"
                    else []
                ),
            }
            self._append_source_revision(
                row["company_id"],
                ident,
                evidence,
                "Migração: referência preservada, sem reinterpretar o original.",
            )
        for row in self.db.execute(
            "SELECT id,filename,kind,sha256,size,created_at,company_id FROM (SELECT i.*,b.company_id,b.created_at FROM import_items i JOIN import_batches b ON b.id=i.batch_id) WHERE original IS NOT NULL AND file_id IS NULL"
        ).fetchall():
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO source_inputs(company_id,filename,kind,sha256,size,legacy_import_item_id,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    row["company_id"],
                    row["filename"],
                    row["kind"],
                    row["sha256"] or hashlib.sha256(b"").hexdigest(),
                    row["size"],
                    row["id"],
                    row["created_at"],
                ),
            )
            ident = cursor.lastrowid
            if cursor.rowcount:
                self._append_source_revision(
                    row["company_id"],
                    ident,
                    {
                        "profile": "source-evidence/2",
                        "legacy": True,
                        "state": (
                            "pacote"
                            if row["kind"] in {"ZIP", "7Z", "RAR"}
                            else "pendente"
                        ),
                        "issues": [],
                    },
                    "Migração: pacote anterior preservado por referência.",
                )

    def source_impact(self, company_id, input_id):
        source = self._source_revision(company_id, input_id)
        document_ids = (
            [
                row["document_id"]
                for row in self.db.execute(
                    "SELECT document_id FROM document_sources WHERE file_id=?",
                    (source["file_id"],),
                )
            ]
            if source["file_id"]
            else []
        )
        protected = []
        for doc in document_ids:
            protected.extend(
                "operacao:" + str(row["operation_id"])
                for row in self.db.execute(
                    "SELECT o.id AS operation_id FROM work_operations o JOIN work_revisions r ON r.operation_id=o.id WHERE o.document_id=? AND r.state='escriturado'",
                    (doc,),
                )
            )
            protected.extend(
                "lote_anterior:" + str(row["batch_id"])
                for row in self.db.execute(
                    "SELECT batch_id FROM accounting_events WHERE company_id=? AND document_id=?",
                    (company_id, doc),
                )
            )
        if source["file_id"]:
            file = self._owned("files", company_id, source["file_id"])
            preview = self.deletion_preview(company_id, file["id"])
            if preview.get("removal_blocked"):
                protected.append("histórico fiscal/contábil protegido")
        result = {
            "input_id": identifier(input_id),
            "source_hash": source["snapshot_hash"],
            "document_ids": document_ids,
            "protected": protected,
            "effect": "Retirada lógica: originais e histórico permanecem; revisões abertas terão de ser conferidas novamente.",
        }
        return {**result, "impact_hash": digest(result)}

    def remove_source(self, company_id, input_id, impact_hash, reason, confirmed=False):
        from .persistence import _text

        reason = _text(reason, "motivo da retirada", 2000)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            impact = self.source_impact(company_id, input_id)
            if confirmed is not True or impact["impact_hash"] != impact_hash:
                raise ValueError("Confira e confirme as dependências atuais da fonte.")
            if impact["protected"]:
                raise ValueError(
                    "Fonte vinculada a escrituração fechada; registre ajuste, sem excluir a evidência."
                )
            source = self._source_revision(company_id, input_id)
            if source["file_id"]:
                self.db.execute(
                    "UPDATE files SET status='excluido' WHERE company_id=? AND id=?",
                    (company_id, source["file_id"]),
                )
                for doc in impact["document_ids"]:
                    self.db.execute(
                        "UPDATE documents SET status='pendente' WHERE id=?", (doc,)
                    )
            self._append_source_revision(
                company_id,
                identifier(input_id),
                {
                    **source["evidence"],
                    "state": "descartado",
                    "withdrawal_reason": reason,
                },
                reason,
            )
        return self._source_revision(company_id, input_id)
