"""Additive source observations and canonical billing entities for the local store."""
from collections import Counter
import json

from .reconciliation import XML_PROFILE, SPED_PROFILE, document_fields, differences, parse_sped

RECONCILIATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
 id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id),
 reference TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
 UNIQUE(document_id,reference));
CREATE TABLE IF NOT EXISTS installments (
 id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices(id),
 reference TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
 UNIQUE(invoice_id,reference));
CREATE TABLE IF NOT EXISTS source_observations (
 id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES files(id), profile TEXT NOT NULL,
 locator TEXT NOT NULL, entity_kind TEXT NOT NULL, document_id INTEGER REFERENCES documents(id),
 invoice_id INTEGER REFERENCES invoices(id), installment_id INTEGER REFERENCES installments(id),
 raw TEXT NOT NULL, normalized TEXT NOT NULL, issues TEXT NOT NULL,
 UNIQUE(file_id,profile,locator));
CREATE TABLE IF NOT EXISTS file_indexings (
 id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES files(id), profile TEXT NOT NULL,
 status TEXT NOT NULL, metadata TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(file_id,profile));
CREATE INDEX IF NOT EXISTS observations_document ON source_observations(document_id);
"""


def _dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class ReconciliationMixin:
    def _pending_source(self, company_id, file_id, document_id):
        metadata = self._file(company_id, file_id)["metadata"]
        metadata["error"] = "Mesmo documento com conteúdo ou contexto divergente; original mantido"
        self.db.execute("UPDATE files SET status='pendente',metadata=? WHERE id=?", (_dump(metadata), file_id))
        self.db.execute("UPDATE documents SET status='pendente' WHERE id=?", (document_id,))

    def _ensure_document(self, company_id, period, file_id, payload, status):
        old = self.db.execute("SELECT * FROM documents WHERE company_id=? AND business_key=?", (company_id, payload["key"])).fetchone()
        conflict = False
        if old:
            left, right = document_fields(json.loads(old["payload"])), document_fields(payload)
            conflict = old["period_id"] != period["id"] or any(left[key] != right[key] for key in left.keys() & right.keys())
            document_id = old["id"]
        else:
            document_id = self.db.execute("INSERT INTO documents(company_id,period_id,business_key,payload,status,created_at) VALUES(?,?,?,?,?,?)",
                                          (company_id, period["id"], payload["key"], _dump(payload), status, self._now())).lastrowid
        self.db.execute("INSERT INTO document_sources(document_id,file_id,conflict) VALUES(?,?,?) ON CONFLICT(document_id,file_id) DO UPDATE SET conflict=MAX(conflict,excluded.conflict)",
                        (document_id, file_id, int(conflict)))
        if conflict:
            self._pending_source(company_id, file_id, document_id)
        return document_id

    def _observe(self, file_id, profile, locator, kind, raw, normalized, issues,
                 document_id=None, invoice_id=None, installment_id=None):
        self.db.execute("INSERT INTO source_observations(file_id,profile,locator,entity_kind,document_id,invoice_id,installment_id,raw,normalized,issues) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (file_id, profile, locator, kind, document_id, invoice_id, installment_id, _dump(raw), _dump(normalized), _dump(issues)))

    def _billing_entity(self, table, parent_id, reference, payload, pending):
        if table not in {"invoices", "installments"}:
            raise ValueError("Entidade de cobrança inválida")
        parent = "document_id" if table == "invoices" else "invoice_id"
        old = self.db.execute(f"SELECT * FROM {table} WHERE {parent}=? AND reference=?", (parent_id, reference)).fetchone()
        conflict = bool(old and old["payload"] != _dump(payload))
        if old:
            if conflict or pending:
                self.db.execute(f"UPDATE {table} SET status='pendente' WHERE id=?", (old["id"],))
            return old["id"], conflict
        entity_id = self.db.execute(f"INSERT INTO {table}({parent},reference,payload,status) VALUES(?,?,?,?)",
                                    (parent_id, reference, _dump(payload), "pendente" if pending else "extraido")).lastrowid
        return entity_id, False

    def _index_xml(self, company, period, file_id, payload):
        warnings = list(payload["billing_warnings"])
        if not company["cnpj"]:
            warnings.append("CNPJ da empresa ausente; identidade não conferida")
        document_id = self._ensure_document(company["id"], period, file_id, payload, "pendente" if warnings else "validado")
        self._observe(file_id, XML_PROFILE, "infNFe", "documento", payload, document_fields(payload), warnings, document_id)
        billing = payload.get("billing")
        if not billing:
            return
        invoice = billing["invoice"]
        invoice_id = None
        if invoice is not None:
            issues = list(warnings)
            existing_references={row[0] for row in self.db.execute("SELECT reference FROM invoices WHERE document_id=?",(document_id,))}
            if invoice["nFat"] and existing_references and invoice["nFat"] not in existing_references:
                issues.append("nFat diverge da fatura já identificada; possível duplicidade exige associação manual")
            elif invoice["nFat"]:
                invoice_id, conflict = self._billing_entity("invoices", document_id, invoice["nFat"], invoice, bool(issues))
                if conflict:
                    issues.append("Fatura com valores divergentes; primeira representação preservada")
                    self._pending_source(company["id"], file_id, document_id)
            else:
                issues.append("nFat ausente; identidade de fatura pendente")
            self._observe(file_id, XML_PROFILE, "infNFe/cobr/fat", "fatura", invoice, invoice, issues, document_id, invoice_id)
        counts = Counter(row["nDup"] for row in billing["installments"])
        existing_parts={row[0] for row in self.db.execute("SELECT reference FROM installments WHERE invoice_id=?",(invoice_id,))} if invoice_id is not None else set()
        for index, row in enumerate(billing["installments"], 1):
            issues = list(warnings)
            installment_id = None
            if invoice_id is None or not row["nDup"] or counts[row["nDup"]] != 1:
                issues.append("Parcela sem título ou identificador inequívoco; nenhuma identidade fabricada")
            elif existing_parts and row["nDup"] not in existing_parts:
                issues.append("nDup diverge das parcelas já identificadas; possível duplicidade exige associação manual")
            else:
                installment_id, conflict = self._billing_entity("installments", invoice_id, row["nDup"], row, bool(issues))
                if conflict:
                    issues.append("Parcela com valores divergentes; primeira representação preservada")
                    self._pending_source(company["id"], file_id, document_id)
            self._observe(file_id, XML_PROFILE, f"infNFe/cobr/dup[{index}]", "parcela", row, row, issues, document_id, invoice_id, installment_id)

    def _index_source(self, company, period, file_row, profile, payload=None):
        existing = self.db.execute("SELECT * FROM file_indexings WHERE file_id=? AND profile=?", (file_row["id"], profile)).fetchone()
        if existing:
            return {"id": existing["id"], "duplicate": True, "status": existing["status"], "metadata": json.loads(existing["metadata"])}
        metadata = {"partial": True, "profile": profile, "prosoft_validated": False}
        try:
            if profile == XML_PROFILE and file_row["kind"] == "XML":
                from .persistence import parse_nfe
                payload = payload if payload is not None else parse_nfe(bytes(file_row["original"]))
                if payload["competence"] != period["processing_competence"]:
                    raise ValueError("Competência de emissão diverge dos movimentos; nenhum documento criado")
                if company["cnpj"] and company["cnpj"] not in {payload["issuer"], payload["buyer"]}:
                    raise ValueError("Documento não identifica a empresa cadastrada")
                self._index_xml(company, period, file_row["id"], payload)
            elif profile == SPED_PROFILE and file_row["kind"] == "SPED":
                rows, parsed_metadata = parse_sped(bytes(file_row["original"]), company["cnpj"], period["processing_competence"])
                metadata.update(parsed_metadata)
                documents = {}
                for row in rows:
                    document_id = None
                    if row["normalized"]:
                        document_id = self._ensure_document(company["id"], period, file_row["id"], row["normalized"], "pendente")
                        documents[row["line"]] = document_id
                    elif row["parent_line"] is not None:
                        document_id = documents.get(row["parent_line"])
                    self._observe(file_row["id"], profile, f"linha:{row['line']}", "documento" if row["normalized"] else "registro",
                                  {"record": row["record"], "fields": row["fields"], "text": row["text"]},
                                  document_fields(row["normalized"]) if row["normalized"] else {}, row["issues"], document_id)
            else:
                raise ValueError("Perfil não corresponde ao tipo de arquivo")
        except ValueError as exc:
            metadata["error"] = str(exc)
            self._observe(file_row["id"], profile, "arquivo", "registro", {}, {}, [str(exc)])
        # Always partial; never ready for an accounting or Prosoft operation.
        metadata["observations"] = self.db.execute("SELECT COUNT(*) FROM source_observations WHERE file_id=? AND profile=?", (file_row["id"], profile)).fetchone()[0]
        indexing_id = self.db.execute("INSERT INTO file_indexings(file_id,profile,status,metadata,actor,created_at) VALUES(?,?,?,?,?,?)",
                                      (file_row["id"], profile, "parcial", _dump(metadata), self.actor, self._now())).lastrowid
        return {"id": indexing_id, "duplicate": False, "status": "parcial", "metadata": metadata}

    def index_file(self, company_id, file_id, profile):
        if profile not in {XML_PROFILE, SPED_PROFILE}:
            raise ValueError("Perfil de análise não suportado")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            company = self._company(company_id)
            file_row = self._owned("files", company_id, file_id)
            if file_row["status"] in {"excluido", "rejeitado"}:
                raise ValueError("Arquivo excluído ou rejeitado não pode ser analisado")
            if (file_row["kind"]=="XML" and profile!=XML_PROFILE) or (file_row["kind"]=="SPED" and profile!=SPED_PROFILE):
                raise ValueError("Perfil não corresponde ao tipo de arquivo")
            period = self._owned("periods", company_id, file_row["period_id"])
            result = self._index_source(company, period, file_row, profile)
            self._audit(company_id, "arquivo_analisado", {"file_id": file_row["id"], "profile": profile, "duplicate": result["duplicate"]})
        return result

    def list_observations(self, company_id, period_id=None):
        self._company(company_id)
        params = [company_id]
        query = "SELECT o.*,f.kind AS source_kind,f.status AS file_status,f.period_id,f.filename FROM source_observations o JOIN files f ON f.id=o.file_id WHERE f.company_id=?"
        if period_id is not None:
            period = self._owned("periods", company_id, period_id)
            query += " AND f.period_id=?"
            params.append(period["id"])
        rows = [dict(row) for row in self.db.execute(query + " ORDER BY o.id", params)]
        for row in rows:
            for key in ("raw", "normalized", "issues"):
                row[key] = json.loads(row[key])
        return rows

    def list_reconciliation(self, company_id, period_id=None):
        documents = self.list_documents(company_id)
        if period_id is not None:
            period = self._owned("periods",company_id,period_id)
            source_ids={row[0] for row in self.db.execute("SELECT s.document_id FROM document_sources s JOIN files f ON f.id=s.file_id WHERE f.company_id=? AND f.period_id=?",(company_id,period["id"]))}
            documents=[row for row in documents if row["period_id"]==period["id"] or row["id"] in source_ids]
        # Include all observations for a canonical document even when another
        # source was filed under a different reference period; show the conflict.
        observations = self.list_observations(company_id)
        result = []
        for document in documents:
            linked = [row for row in observations if row["document_id"] == document["id"]]
            active = [row for row in linked if row["file_status"] != "excluido"]
            document_rows = [row for row in active if row["entity_kind"] == "documento"]
            diff = differences(document_rows)
            kinds = {row["source_kind"] for row in document_rows}
            issues = [{"file_id": row["file_id"], "locator": row["locator"], "messages": row["issues"]} for row in active if row["issues"]]
            periods = {row["period_id"] for row in document_rows}
            if len(periods) > 1:
                issues.append({"messages": ["Fontes em contextos de período diferentes; exige revisão"]})
            invoices = []
            for invoice in self.db.execute("SELECT * FROM invoices WHERE document_id=? ORDER BY id", (document["id"],)):
                item = dict(invoice)
                item["payload"] = json.loads(item["payload"])
                item["sources"] = [row for row in linked if row["entity_kind"] == "fatura" and row["invoice_id"] == item["id"]]
                invoice_diff = differences([row for row in item["sources"] if row["file_status"] != "excluido"])
                diff.extend({"entity": "fatura", "entity_id": item["id"], **entry} for entry in invoice_diff)
                item["installments"] = []
                for installment in self.db.execute("SELECT * FROM installments WHERE invoice_id=? ORDER BY id", (item["id"],)):
                    part = dict(installment)
                    part["payload"] = json.loads(part["payload"])
                    part["sources"] = [row for row in linked if row["entity_kind"] == "parcela" and row["installment_id"] == part["id"]]
                    part_diff = differences([row for row in part["sources"] if row["file_status"] != "excluido"])
                    diff.extend({"entity": "parcela", "entity_id": part["id"], **entry} for entry in part_diff)
                    item["installments"].append(part)
                invoices.append(item)
            state = "divergente" if diff else "pendencia_de_origem" if issues else "coincidente_no_recorte" if kinds == {"XML", "SPED"} else "somente_xml" if kinds == {"XML"} else "somente_sped" if kinds == {"SPED"} else "aguardando_analise"
            result.append({"document_id": document["id"], "business_key": document["business_key"], "period_id": document["period_id"],
                           "source_period_ids": sorted({row["period_id"] for row in linked}),
                           "state": state, "differences": diff, "issues": issues, "sources": linked, "invoices": invoices,
                           "unindexed_file_ids": [source["file_id"] for source in document["sources"] if source["file_id"] not in {row["file_id"] for row in linked}],
                           "ready_for_export": False})
        return result
