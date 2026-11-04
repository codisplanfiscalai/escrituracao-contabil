"""Synthetic-only regression tests for local transactional persistence.

All names, identifiers, fiscal keys and XML/SPED snippets are invented fixtures.
No production documents, Prosoft implementation or generator code is used.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from src.persistence import AccountingStore, MAX_FILE_BYTES, parse_nfe


ISSUER = "00000000000191"  # Deliberately fictitious test identifier.
BUYER = "00000000000272"  # Deliberately fictitious test identifier.
NS = "http://www.portalfiscal.inf.br/nfe"


def fictitious_key(number=1, month="2609", issuer=ISSUER):
    """Create a fabricated, internally consistent key, never an issued NF-e."""
    base = "35" + month + issuer + "55" + "001" + f"{number:09d}" + "1" + "12345678"
    remainder = sum(int(digit) * (2 + index % 8) for index, digit in enumerate(reversed(base))) % 11
    check_digit = 0 if remainder in (0, 1) else 11 - remainder
    return base + str(check_digit)


def fake_xml(*, number=1, issued="2026-09-15T10:00:00-03:00", total="100.30", billing=True, wrapper=True):
    root = ET.Element(f"{{{NS}}}nfeProc", {"versao": "4.00"}) if wrapper else None
    nfe = ET.SubElement(root, f"{{{NS}}}NFe") if wrapper else ET.Element(f"{{{NS}}}NFe")
    info = ET.SubElement(nfe, f"{{{NS}}}infNFe", {"versao": "4.00", "Id": "NFe" + fictitious_key(number, issued[2:4] + issued[5:7])})
    def group(parent, name, values):
        element = ET.SubElement(parent, f"{{{NS}}}{name}")
        for field, value in values.items():
            ET.SubElement(element, f"{{{NS}}}{field}").text = value
        return element
    group(info, "ide", {"cUF": "35", "cNF": "12345678", "mod": "55", "serie": "1", "nNF": str(number), "dhEmi": issued, "tpEmis": "1", "cDV": fictitious_key(number, issued[2:4] + issued[5:7])[-1]})
    group(info, "emit", {"CNPJ": ISSUER, "xNome": "Emitente inteiramente fictício"})
    group(info, "dest", {"CNPJ": BUYER, "xNome": "Destinatário inteiramente fictício"})
    totals = ET.SubElement(info, f"{{{NS}}}total")
    group(totals, "ICMSTot", {"vNF": total})
    if billing:
        cobr = ET.SubElement(info, f"{{{NS}}}cobr")
        group(cobr, "fat", {"nFat": "FATURA-FICTICIA-1", "vOrig": "100.30", "vDesc": "0.00", "vLiq": "100.30"})
        group(cobr, "dup", {"nDup": "001", "dVenc": "2026-10-15", "vDup": "40.10"})
        group(cobr, "dup", {"nDup": "002", "dVenc": "2026-11-15", "vDup": "60.20"})
    return ET.tostring(root if root is not None else nfe, encoding="utf-8", xml_declaration=True)


def edit_xml(content, path, value=None, *, remove=False):
    root = ET.fromstring(content)
    element = root.find(".//" + "/".join(f"{{{NS}}}{name}" for name in path.split("/")))
    if element is None:
        raise AssertionError("Bad synthetic fixture path: " + path)
    if remove:
        parent = next(parent for parent in root.iter() if element in list(parent))
        parent.remove(element)
    else:
        element.text = value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def fake_accounts():
    return [
        {"code": "1", "description": "Ativo fictício", "kind": "sintetica", "nature": "devedora"},
        {"code": "1.1", "description": "Disponível fictício", "parent_code": "1", "kind": "sintetica", "nature": "devedora"},
        {"code": "1.1.1", "description": "Caixa fictício", "parent_code": "1.1", "kind": "analitica", "nature": "devedora", "attributes": {"synthetic_fixture": True}},
        {"code": "2", "description": "Passivo fictício", "kind": "sintetica", "nature": "credora"},
        {"code": "2.1", "description": "Fornecedor fictício", "parent_code": "2", "kind": "analitica", "nature": "credora"},
    ]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="contabilidade-testes-ficticios-")
        self.db_path = Path(self.temp.name) / "estado.sqlite3"
        self.store = AccountingStore(self.db_path, actor="operador-ficticio")
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: self.store.close())
        self.company = self.store.create_company("Empresa fictícia A", "EMPRESA-A", "PLANO-A", ISSUER)
        self.other = self.store.create_company("Empresa fictícia B", "EMPRESA-B", "PLANO-B", BUYER)
        self.company_id = self.company["id"]
        self.other_id = self.other["id"]
        self.period = self.store.create_period(self.company_id, "2026-08", "2026-09")

    def import_xml(self, content=None, *, filename="nfe-ficticia.xml", period=None, company_id=None):
        return self.store.import_file(company_id or self.company_id, (period or self.period)["id"], filename, content if content is not None else fake_xml(), "XML")

    def count(self, table):
        self.assertIn(table, {"companies", "periods", "plans", "accounts", "mappings", "files", "documents", "document_sources", "audit"})
        return self.store.db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]

    def test_state_and_original_survive_close_and_reopen(self):
        plan = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        mapping = self.store.save_mapping(self.company_id, plan["id"], "ORIGEM-FICTICIA", "1.1.1", "2026-09")
        content = fake_xml()
        imported = self.import_xml(content)
        self.store.close()
        self.store = AccountingStore(self.db_path, actor="segundo-operador-ficticio")
        self.assertEqual(len(self.store.list_companies()), 2)
        self.assertEqual(self.store.list_periods(self.company_id)[0], self.period)
        self.assertEqual(self.store.list_accounts(self.company_id, plan["id"])[2]["attributes"], {"synthetic_fixture": True})
        self.assertEqual(self.store.list_mappings(self.company_id)[0]["id"], mapping["id"])
        self.assertEqual(self.store.list_documents(self.company_id)[0]["payload"]["key"], fictitious_key())
        self.assertEqual(bytes(self.store.db.execute("SELECT original FROM files WHERE id=?", (imported["id"],)).fetchone()[0]), content)
        self.assertTrue(self.store.list_audit(self.company_id))

    def test_unknown_schema_version_is_rejected_without_mutating_database(self):
        unsupported = Path(self.temp.name) / "versao-ficticia-nao-suportada.sqlite3"
        with closing(sqlite3.connect(unsupported)) as db, db:
            db.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
            db.execute("INSERT INTO schema_version VALUES (999)")
            db.execute("CREATE TABLE sentinel (value TEXT)")
            db.execute("INSERT INTO sentinel VALUES ('registro fictício preservado')")
        before = unsupported.read_bytes()
        with self.assertRaisesRegex(ValueError, "Versão do banco não suportada"):
            AccountingStore(unsupported)
        self.assertEqual(unsupported.read_bytes(), before)
        with closing(sqlite3.connect(unsupported)) as db, db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {"schema_version", "sentinel"})
            self.assertEqual(db.execute("SELECT value FROM sentinel").fetchone()[0], "registro fictício preservado")

    def test_existing_connection_observes_committed_changes(self):
        with AccountingStore(self.db_path) as observer:
            self.import_xml()
            self.assertEqual(len(observer.list_documents(self.company_id)), 1)
            self.assertEqual(len(observer.list_documents(self.other_id)), 0)

    def test_company_isolation_for_period_plan_files_and_documents(self):
        plan = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        imported = self.import_xml()
        for operation in (
            lambda: self.store.list_accounts(self.other_id, plan["id"]),
            lambda: self.store.save_mapping(self.other_id, plan["id"], "ORIGEM", "1.1.1", "2026-09"),
            lambda: self.store.import_file(self.other_id, self.period["id"], "ficticio.xml", fake_xml(), "XML"),
            lambda: self.store.list_documents(self.other_id, self.period["id"]),
            lambda: self.store.deletion_preview(self.other_id, imported["id"]),
            lambda: self.store.delete_file(self.other_id, imported["id"], "Tentativa fictícia", True),
        ):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                operation()
        self.assertEqual(self.store.list_files(self.other_id), [])
        self.assertEqual(self.store.list_documents(self.other_id), [])
        self.assertEqual(self.store.list_plans(self.other_id), [])
        self.assertEqual(self.store.list_mappings(self.other_id), [])
        self.assertTrue(all(row["company_id"] == self.other_id for row in self.store.list_audit(self.other_id)))

    def test_same_key_and_bytes_are_independent_between_companies(self):
        other_period = self.store.create_period(self.other_id, "2026-08", "2026-09")
        first = self.import_xml()
        second = self.import_xml(period=other_period, company_id=self.other_id)
        self.assertFalse(second["duplicate"])
        self.assertNotEqual(first["id"], second["id"])
        first_doc, second_doc = self.store.list_documents(self.company_id)[0], self.store.list_documents(self.other_id)[0]
        self.assertNotEqual(first_doc["id"], second_doc["id"])
        self.assertEqual(first_doc["business_key"], second_doc["business_key"])

    def test_textual_period_identifier_does_not_create_false_document_conflict(self):
        content=fake_xml()
        self.import_xml(content)
        equivalent=ET.tostring(ET.fromstring(content))
        result=self.store.import_file(str(self.company_id),str(self.period["id"]),"outra-origem-ficticia.xml",equivalent,"XML")
        self.assertEqual(result["status"],"validado")
        self.assertFalse(result["duplicate"])
        docs=self.store.list_documents(self.company_id)
        self.assertEqual(len(docs),1)
        self.assertEqual(len(docs[0]["sources"]),2)
        self.assertTrue(all(source["conflict"]==0 for source in docs[0]["sources"]))

    def test_billing_arithmetic_divergences_are_pending_and_original_is_preserved(self):
        for number,path,value in ((21,"cobr/fat/vDesc","1.00"),(22,"cobr/dup/vDup","40.11")):
            with self.subTest(path=path):
                content=edit_xml(fake_xml(number=number),path,value)
                result=self.import_xml(content)
                self.assertEqual(result["status"],"pendente")
                self.assertTrue(result["metadata"]["billing_warnings"])
                original=self.store.db.execute("SELECT original FROM files WHERE id=?",(result["id"],)).fetchone()[0]
                self.assertEqual(bytes(original),content)
                self.assertEqual(parse_nfe(content)["billing"]["invoice"]["vLiq"],"100.30")

    def test_installments_without_invoice_are_pending_without_inventing_title(self):
        content=edit_xml(fake_xml(),"cobr/fat",remove=True)
        result=self.import_xml(content)
        self.assertEqual(result["status"],"pendente")
        payload=self.store.list_documents(self.company_id)[0]["payload"]
        self.assertIsNone(payload["billing"]["invoice"])
        self.assertEqual(len(payload["billing"]["installments"]),2)

    def test_stale_deletion_preview_and_repeated_removal_have_no_side_effect(self):
        imported=self.import_xml()
        preview=self.store.deletion_preview(self.company_id,imported["id"])
        with self.store.db:
            self.store.db.execute("UPDATE files SET status='pendente' WHERE id=?",(imported["id"],))
        before=self.count("audit")
        with self.assertRaisesRegex(ValueError,"desatualizada"):
            self.store.delete_file(self.company_id,imported["id"],"Motivo fictício",True,preview["preview_token"])
        self.assertEqual(self.count("audit"),before)
        self.assertEqual(self.store.list_files(self.company_id)[0]["status"],"pendente")
        current=self.store.deletion_preview(self.company_id,imported["id"])
        self.store.delete_file(self.company_id,imported["id"],"Motivo fictício",True,current["preview_token"])
        with self.assertRaisesRegex(ValueError,"já removido"):
            self.store.delete_file(self.company_id,imported["id"],"Motivo fictício",True,current["preview_token"])
        self.assertEqual(self.count("audit"),before+1)

    def test_period_reference_does_not_move_document_competence(self):
        result = self.import_xml()
        self.assertEqual(result["status"], "validado")
        self.assertEqual(self.period["reference_competence"], "2026-08")
        self.assertEqual(self.period["processing_competence"], "2026-09")
        self.assertEqual(self.store.list_documents(self.company_id)[0]["payload"]["competence"], "2026-09")
        self.assertEqual(self.store.create_period(self.company_id, "2026-08", "2026-09")["id"], self.period["id"])

    def test_processing_mismatch_is_rejected_without_document_but_keeps_original(self):
        content = fake_xml(issued="2026-08-15T10:00:00-03:00")
        result = self.import_xml(content)
        self.assertEqual(result["status"], "rejeitado")
        self.assertIn("Competência", result["metadata"]["error"])
        self.assertEqual(self.store.list_documents(self.company_id), [])
        self.assertEqual(bytes(self.store.db.execute("SELECT original FROM files WHERE id=?", (result["id"],)).fetchone()[0]), content)

    def test_invalid_or_missing_competence_never_creates_period(self):
        before = self.count("periods")
        for reference, processing in (("", "2026-09"), (None, "2026-09"), ("2026-08", ""), ("2026-08", "2026-13"), ("2026-8", "2026-09")):
            with self.subTest(reference=reference, processing=processing), self.assertRaises(ValueError):
                self.store.create_period(self.company_id, reference, processing)
        self.assertEqual(self.count("periods"), before)

    def test_plan_hierarchy_attributes_and_versioning(self):
        first = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        second = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        self.assertEqual((first["version"], second["version"]), (1, 2))
        accounts = self.store.list_accounts(self.company_id, first["id"])
        self.assertEqual(len(accounts), 5)
        self.assertEqual(next(a for a in accounts if a["code"] == "1.1.1")["parent_code"], "1.1")
        self.assertEqual(self.store.list_plans(self.company_id)[0]["account_count"], 5)

    def test_plan_missing_parent_analytic_parent_duplicates_and_cycles_are_atomic(self):
        missing = fake_accounts(); missing[2]["parent_code"] = "INEXISTENTE"
        analytic_parent = fake_accounts(); analytic_parent[1]["parent_code"] = "1.1.1"
        duplicate = fake_accounts(); duplicate.append(deepcopy(duplicate[0]))
        cycle = fake_accounts(); cycle[0]["parent_code"] = "1.1"
        self_cycle = fake_accounts(); self_cycle[0]["parent_code"] = "1"
        invalid_nature = fake_accounts(); invalid_nature[-1]["nature"] = "indefinida"
        before = {name: self.count(name) for name in ("plans", "accounts", "audit")}
        for accounts in (missing, analytic_parent, duplicate, cycle, self_cycle, invalid_nature):
            with self.subTest(accounts=accounts), self.assertRaises(ValueError):
                self.store.import_plan(self.company_id, "Plano inválido fictício", accounts)
            self.assertEqual({name: self.count(name) for name in before}, before)

    def test_plan_transaction_rolls_back_insertions_if_audit_fails(self):
        before = {name: self.count(name) for name in ("plans", "accounts", "audit")}
        with patch.object(self.store, "_audit", side_effect=sqlite3.OperationalError("falha fictícia")):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        self.assertEqual({name: self.count(name) for name in before}, before)
        self.assertEqual(self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())["version"], 1)

    def test_mapping_requires_analytic_destination_in_selected_plan(self):
        plan = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        for code in ("1", "INEXISTENTE"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.store.save_mapping(self.company_id, plan["id"], "ORIGEM-FICTICIA", code, "2026-09")
        self.assertEqual(self.store.list_mappings(self.company_id), [])

    def test_mapping_versions_retain_vigency_reason_state_and_actor(self):
        plan = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        first = self.store.save_mapping(self.company_id, plan["id"], "ORIGEM-FICTICIA", "1.1.1", "2026-09", "2026-12")
        second = self.store.save_mapping(self.company_id, plan["id"], "ORIGEM-FICTICIA", "2.1", "2027-01", state="aprovado", reason="Aprovação inteiramente fictícia")
        self.assertEqual((first["version"], second["version"]), (1, 2))
        rows = self.store.list_mappings(self.company_id)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["valid_to"], "2026-12")
        self.assertEqual(rows[1]["target_code"], "1.1.1")
        self.assertEqual(rows[0]["state"], "aprovado")
        self.assertEqual(rows[0]["actor"], "operador-ficticio")
        self.assertEqual(rows[0]["reason"], "Aprovação inteiramente fictícia")

    def test_mapping_rejects_invalid_vigency_states_and_unjustified_review(self):
        plan = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        cases = ({"valid_from": "2026-13"}, {"valid_from": ""}, {"valid_from": "2026-09", "valid_to": "2026-08"}, {"valid_from": "2026-09", "state": "qualquer"}, {"valid_from": "2026-09", "state": "revisado"}, {"valid_from": "2026-09", "state": "aprovado", "reason": " "})
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.store.save_mapping(self.company_id, plan["id"], "ORIGEM", "1.1.1", **kwargs)
        self.assertEqual(self.store.list_mappings(self.company_id), [])

    def test_mapping_transaction_rolls_back_if_audit_fails(self):
        plan = self.store.import_plan(self.company_id, "Plano fictício", fake_accounts())
        before = self.count("audit")
        with patch.object(self.store, "_audit", side_effect=sqlite3.OperationalError("falha fictícia")):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.save_mapping(self.company_id, plan["id"], "ORIGEM", "1.1.1", "2026-09")
        self.assertEqual(self.count("mappings"), 0)
        self.assertEqual(self.count("audit"), before)

    def test_exact_hash_repeat_is_idempotent_and_audited(self):
        first = self.import_xml()
        again = self.import_xml(filename="outro-nome-ficticio.xml")
        self.assertTrue(again["duplicate"])
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(self.count("files"), 1)
        self.assertEqual(self.count("documents"), 1)
        self.assertEqual(self.count("document_sources"), 1)
        self.assertEqual(self.store.list_audit(self.company_id)[0]["action"], "arquivo_repetido")

    def test_different_bytes_same_document_add_provenance_without_duplication(self):
        content = fake_xml()
        first = self.import_xml(content)
        second = self.import_xml(content + b"\n", filename="mesma-nfe-ficticia.xml")
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertFalse(second["duplicate"])
        doc = self.store.list_documents(self.company_id)[0]
        self.assertEqual(self.count("documents"), 1)
        self.assertEqual(doc["status"], "validado")
        self.assertEqual(len(doc["sources"]), 2)
        self.assertTrue(all(not source["conflict"] for source in doc["sources"]))

    def test_same_key_changed_content_is_pending_and_never_overwrites_payload(self):
        original = fake_xml()
        first = self.import_xml(original)
        before = self.store.list_documents(self.company_id)[0]
        divergent = edit_xml(original, "total/ICMSTot/vNF", "999.99")
        second = self.import_xml(divergent, filename="divergencia-ficticia.xml")
        after = self.store.list_documents(self.company_id)[0]
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["payload"], before["payload"])
        self.assertEqual(after["period_id"], before["period_id"])
        self.assertEqual(after["status"], "pendente")
        self.assertEqual(second["status"], "pendente")
        self.assertIn("original mantido", second["metadata"]["error"])
        self.assertEqual([source["conflict"] for source in after["sources"]], [0, 1])
        for imported, expected in ((first, original), (second, divergent)):
            row = self.store.db.execute("SELECT original,sha256 FROM files WHERE id=?", (imported["id"],)).fetchone()
            self.assertEqual(bytes(row["original"]), expected)
            self.assertEqual(row["sha256"], hashlib.sha256(expected).hexdigest())

    def test_same_document_different_reference_context_is_pending(self):
        self.import_xml()
        other_context = self.store.create_period(self.company_id, "2026-07", "2026-09")
        result = self.import_xml(period=other_context)
        doc = self.store.list_documents(self.company_id)[0]
        self.assertFalse(result["duplicate"])
        self.assertEqual(result["status"], "pendente")
        self.assertEqual(doc["period_id"], self.period["id"])
        self.assertEqual(self.store.list_documents(self.company_id, other_context["id"]), [])
        self.assertEqual(len(doc["sources"]), 2)

    def test_different_keys_produce_distinct_documents(self):
        self.import_xml()
        self.import_xml(fake_xml(number=2))
        self.assertEqual(self.count("documents"), 2)

    def test_failed_file_transaction_keeps_no_partial_file_document_or_source(self):
        before = {name: self.count(name) for name in ("files", "documents", "document_sources", "audit")}
        with patch.object(self.store, "_audit", side_effect=sqlite3.OperationalError("falha fictícia")):
            with self.assertRaises(sqlite3.OperationalError):
                self.import_xml()
        self.assertEqual({name: self.count(name) for name in before}, before)
        self.assertEqual(self.import_xml()["status"], "validado")

    def test_company_identity_mismatch_rejects_and_missing_cnpj_is_pending(self):
        mismatch = self.store.create_company("Outra fictícia", "EMPRESA-C", "PLANO-C", "00000000000353")
        no_cnpj = self.store.create_company("Sem identificação fictícia", "EMPRESA-D", "PLANO-D")
        for company, expected in ((mismatch, "rejeitado"), (no_cnpj, "pendente")):
            period = self.store.create_period(company["id"], "2026-08", "2026-09")
            result = self.import_xml(company_id=company["id"], period=period)
            self.assertEqual(result["status"], expected)
            docs = self.store.list_documents(company["id"])
            self.assertEqual(len(docs), 0 if expected == "rejeitado" else 1)
            if docs:
                self.assertFalse(result["metadata"]["company_identity_verified"])
                self.assertEqual(docs[0]["status"], "pendente")

    def test_sped_is_preserved_pending_and_never_claims_normalization(self):
        content = b"|0000|ARQUIVO-FICTICIO|\n|C100|DOCUMENTO-FICTICIO|\n|C100|OUTRO-FICTICIO|\n|9999|4|\n"
        result = self.store.import_file(self.company_id, self.period["id"], "ficticio.txt", content, "SPED")
        self.assertEqual(result["status"], "pendente")
        self.assertEqual(result["metadata"]["record_counts"], {"0000": 1, "C100": 2, "9999": 1})
        self.assertNotIn("normalizer", result["metadata"])
        self.assertIn("ainda não normalizados", result["metadata"]["warning"])
        self.assertEqual(self.store.list_documents(self.company_id), [])
        self.assertEqual(bytes(self.store.db.execute("SELECT original FROM files WHERE id=?", (result["id"],)).fetchone()[0]), content)
        again = self.store.import_file(self.company_id, self.period["id"], "repetido-ficticio.txt", content, "SPED")
        self.assertTrue(again["duplicate"])
        self.assertEqual(again["id"], result["id"])

    def test_sped_cp1252_and_structural_rejections(self):
        cp1252 = "|0000|FICTÍCIO|\n".encode("cp1252")
        accepted = self.store.import_file(self.company_id, self.period["id"], "ficticio-cp1252.txt", cp1252, "SPED")
        self.assertEqual(accepted["metadata"]["encoding"], "cp1252")
        for content in (b"\n", b"0000|FICTICIO|", b"|000|FICTICIO|", b"|C100|FICTICIO", b"|0000|FICTICIO\x00|"):
            with self.subTest(content=content):
                result = self.store.import_file(self.company_id, self.period["id"], "invalido-ficticio.txt", content, "SPED")
                self.assertEqual(result["status"], "rejeitado")
        self.assertEqual(self.store.list_documents(self.company_id), [])

    def test_invalid_upload_arguments_do_not_write_files(self):
        for filename, content, kind in (("../ficticio.xml", fake_xml(), "XML"), ("sub\\ficticio.xml", fake_xml(), "XML"), ("", fake_xml(), "XML"), ("ficticio.xml", "texto", "XML"), ("ficticio.xml", b"", "XML"), ("ficticio.pdf", b"ficticio", "PDF"), ("ficticio.xml", b"x" * (MAX_FILE_BYTES + 1), "XML")):
            with self.subTest(filename=filename, kind=kind, size=len(content)), self.assertRaises(ValueError):
                self.store.import_file(self.company_id, self.period["id"], filename, content, kind)
        self.assertEqual(self.count("files"), 0)

    def test_rejected_xml_keeps_original_and_audit_without_document(self):
        content = b"<XML-FICTICIO-MALFORMADO>"
        result = self.import_xml(content)
        self.assertEqual(result["status"], "rejeitado")
        self.assertIn("error", result["metadata"])
        self.assertEqual(self.count("documents"), 0)
        self.assertEqual(bytes(self.store.db.execute("SELECT original FROM files WHERE id=?", (result["id"],)).fetchone()[0]), content)
        self.assertEqual(self.store.list_audit(self.company_id)[0]["details"]["status"], "rejeitado")

    def test_incomplete_invoice_or_installment_is_pending_without_inventing_values(self):
        for path in ("cobr/fat/nFat", "cobr/fat/vOrig", "cobr/fat/vLiq", "cobr/dup/nDup", "cobr/dup/dVenc", "cobr/dup/vDup"):
            with self.subTest(path=path):
                content = edit_xml(fake_xml(), path, remove=True)
                result = self.import_xml(content, filename="cobranca-incompleta-ficticia.xml")
                self.assertEqual(result["status"], "pendente")
                normalized = parse_nfe(content)
                self.assertTrue(normalized["billing_warnings"])
                group = normalized["billing"]["invoice"] if "/fat/" in path else normalized["billing"]["installments"][0]
                self.assertEqual(group[path.rsplit("/", 1)[1]], "")
        self.assertEqual(self.count("documents"), 1)

    def test_duplicate_installment_numbers_are_pending_and_preserved_for_review(self):
        root = ET.fromstring(fake_xml())
        installments = root.findall(f".//{{{NS}}}dup")
        installments[1].find(f"{{{NS}}}nDup").text = "001"
        content = ET.tostring(root)
        result = self.import_xml(content)
        self.assertEqual(result["status"], "pendente")
        payload = self.store.list_documents(self.company_id)[0]["payload"]
        self.assertIn("Número de parcela repetido", payload["billing_warnings"])
        self.assertEqual([row["nDup"] for row in payload["billing"]["installments"]], ["001", "001"])

    def test_malicious_xml_and_multi_nfe_are_rejected_without_any_document(self):
        plain = fake_xml().split(b"?>", 1)[1]
        multi = ET.fromstring(fake_xml())
        multi.append(ET.fromstring(fake_xml(number=2)).find(f"{{{NS}}}NFe"))
        candidates = (b'<!DOCTYPE nfeProc [<!ENTITY ficticia "nunca expandir">]>' + plain, plain.decode("utf-8").encode("utf-16"), ET.tostring(multi))
        for content in candidates:
            with self.subTest(size=len(content)):
                result = self.import_xml(content, filename="rejeicao-seguranca-ficticia.xml")
                self.assertEqual(result["status"], "rejeitado")
                self.assertEqual(bytes(self.store.db.execute("SELECT original FROM files WHERE id=?", (result["id"],)).fetchone()[0]), content)
        self.assertEqual(self.count("documents"), 0)

    def test_logical_deletion_preview_confirmation_reason_and_audit(self):
        content = fake_xml()
        imported = self.import_xml(content)
        doc_id = self.store.list_documents(self.company_id)[0]["id"]
        preview = self.store.deletion_preview(self.company_id, imported["id"])
        self.assertEqual(preview["document_ids"], [doc_id])
        self.assertEqual(preview["operation"], "remocao_logica")
        self.assertIn("Purga definitiva indisponível", preview["consequence"])
        self.assertEqual(self.store.list_files(self.company_id)[0]["status"], "validado")
        audit_before = self.count("audit")
        for reason, confirmed in (("Motivo fictício", False), ("Motivo fictício", 1), ("Motivo fictício", "true"), (" ", True)):
            with self.subTest(reason=reason, confirmed=confirmed), self.assertRaises(ValueError):
                self.store.delete_file(self.company_id, imported["id"], reason, confirmed)
        self.assertEqual(self.count("audit"), audit_before)
        self.assertEqual(self.store.list_files(self.company_id)[0]["status"], "validado")
        self.assertEqual(self.store.delete_file(self.company_id, imported["id"], "Remoção fictícia autorizada", True), preview)
        self.assertEqual(self.store.list_files(self.company_id)[0]["status"], "excluido")
        self.assertEqual(self.store.list_documents(self.company_id)[0]["status"], "pendente")
        self.assertEqual(self.store.list_documents(self.company_id)[0]["sources"][0]["status"], "excluido")
        self.assertEqual(self.count("files"), 1)
        self.assertEqual(self.count("documents"), 1)
        self.assertEqual(bytes(self.store.db.execute("SELECT original FROM files WHERE id=?", (imported["id"],)).fetchone()[0]), content)
        audit = self.store.list_audit(self.company_id)[0]
        self.assertEqual(audit["action"], "arquivo_removido_logicamente")
        self.assertEqual(audit["actor"], "operador-ficticio")
        self.assertEqual(audit["details"]["reason"], "Remoção fictícia autorizada")
        with self.assertRaises(ValueError):
            self.import_xml(content)
        self.assertEqual(self.count("files"), 1)

    def test_logical_deletion_transaction_rolls_back_if_audit_fails(self):
        imported = self.import_xml()
        before = self.count("audit")
        with patch.object(self.store, "_audit", side_effect=sqlite3.OperationalError("falha fictícia")):
            with self.assertRaises(sqlite3.OperationalError):
                self.store.delete_file(self.company_id, imported["id"], "Remoção fictícia", True)
        self.assertEqual(self.store.list_files(self.company_id)[0]["status"], "validado")
        self.assertEqual(self.store.list_documents(self.company_id)[0]["status"], "validado")
        self.assertEqual(self.count("audit"), before)


class ParseNFeTests(unittest.TestCase):
    def test_header_invoice_installments_and_decimal_values_are_preserved(self):
        payload = parse_nfe(fake_xml())
        self.assertEqual(payload["key"], fictitious_key())
        self.assertEqual((payload["model"], payload["number"], payload["series"]), ("55", "1", "1"))
        self.assertEqual((payload["issuer"], payload["buyer"]), (ISSUER, BUYER))
        self.assertEqual(payload["issued_at"], "2026-09-15T10:00:00-03:00")
        self.assertEqual(payload["competence"], "2026-09")
        self.assertEqual(payload["total"], "100.30")
        self.assertEqual(payload["billing"]["invoice"], {"nFat": "FATURA-FICTICIA-1", "vOrig": "100.30", "vDesc": "0.00", "vLiq": "100.30"})
        self.assertEqual(payload["billing"]["installments"], [{"nDup": "001", "dVenc": "2026-10-15", "vDup": "40.10"}, {"nDup": "002", "dVenc": "2026-11-15", "vDup": "60.20"}])
        self.assertEqual(sum(Decimal(row["vDup"]) for row in payload["billing"]["installments"]), Decimal("100.30"))
        self.assertRegex(payload["content_fingerprint"], r"^[a-f0-9]{64}$")

    def test_bare_nfe_and_missing_optional_billing_are_supported(self):
        payload = parse_nfe(fake_xml(billing=False, wrapper=False))
        self.assertIsNone(payload["billing"])
        self.assertEqual(payload["total"], "100.30")

    def test_cent_values_do_not_pass_through_binary_float(self):
        payload = parse_nfe(fake_xml(total="999999999999.99"))
        self.assertEqual(payload["total"], "999999999999.99")
        small = parse_nfe(fake_xml(total="0.30"))
        self.assertEqual(Decimal(small["total"]), Decimal("0.10") + Decimal("0.20"))

    def test_invalid_total_and_installment_money_are_rejected(self):
        for path in ("total/ICMSTot/vNF", "cobr/dup/vDup"):
            for amount in ("NaN", "Infinity", "-0.01", "1.001", "abc"):
                with self.subTest(path=path, amount=amount), self.assertRaises(ValueError):
                    parse_nfe(edit_xml(fake_xml(), path, amount))

    def test_invoice_money_must_also_be_finite_nonnegative_and_cent_exact(self):
        for field in ("vOrig", "vDesc", "vLiq"):
            for amount in ("NaN", "Infinity", "-0.01", "1.001", "abc"):
                with self.subTest(field=field, amount=amount), self.assertRaises(ValueError):
                    parse_nfe(edit_xml(fake_xml(), "cobr/fat/" + field, amount))

    def test_missing_key_is_rejected(self):
        root = ET.fromstring(fake_xml())
        info = root.find(f".//{{{NS}}}infNFe")
        del info.attrib["Id"]
        with self.assertRaises(ValueError):
            parse_nfe(ET.tostring(root))

    def test_missing_required_header_fields_are_rejected(self):
        for path in ("ide/dhEmi", "ide/mod", "ide/nNF", "ide/serie", "emit/CNPJ", "dest/CNPJ", "total/ICMSTot/vNF"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                parse_nfe(edit_xml(fake_xml(), path, remove=True))

    def test_invalid_dates_are_rejected(self):
        for path, value in (("ide/dhEmi", "2026-02-30T10:00:00-03:00"), ("ide/dhEmi", "data inexistente"), ("cobr/dup/dVenc", "2026-02-30"), ("cobr/dup/dVenc", "não é uma data")):
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                parse_nfe(edit_xml(fake_xml(), path, value))

    def test_emission_requires_time_timezone_and_t_separator(self):
        for value in ("2026-09-15", "2026-09-15T10:00:00", "2026-09-15 10:00:00-03:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_nfe(edit_xml(fake_xml(), "ide/dhEmi", value))

    def test_emission_basic_key_coherence_and_check_digit_are_required(self):
        for path, value in (("ide/nNF", "2"), ("ide/serie", "2"), ("ide/dhEmi", "2026-08-15T10:00:00-03:00"), ("emit/CNPJ", BUYER)):
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                parse_nfe(edit_xml(fake_xml(), path, value))
        root = ET.fromstring(fake_xml())
        root.find(f".//{{{NS}}}infNFe").set("Id", "NFe" + fictitious_key()[:-1] + str((int(fictitious_key()[-1]) + 1) % 10))
        with self.assertRaises(ValueError):
            parse_nfe(ET.tostring(root))

    def test_invalid_key_version_model_or_root_are_rejected(self):
        root = ET.fromstring(fake_xml())
        for attribute, value in (("Id", "NFe123"), ("Id", "NFe" + "A" * 44), ("versao", "3.10")):
            candidate = deepcopy(root)
            candidate.find(f".//{{{NS}}}infNFe").set(attribute, value)
            with self.subTest(attribute=attribute, value=value), self.assertRaises(ValueError):
                parse_nfe(ET.tostring(candidate))
        with self.assertRaises(ValueError):
            parse_nfe(edit_xml(fake_xml(), "ide/mod", "65"))
        with self.assertRaises(ValueError):
            parse_nfe(b"<lote-ficticio/>")

    def test_multi_nfe_payload_is_rejected_instead_of_silently_taking_first(self):
        root = ET.fromstring(fake_xml())
        other = ET.fromstring(fake_xml(number=2)).find(f"{{{NS}}}NFe")
        root.append(other)
        with self.assertRaises(ValueError):
            parse_nfe(ET.tostring(root))

    def test_dtd_internal_and_external_entity_declarations_are_rejected(self):
        content = fake_xml().split(b"?>", 1)[1]
        for declaration in (b'<!DOCTYPE nfeProc [<!ENTITY ficticia "NUNCA EXPANDIR">]>', b'<!DOCTYPE nfeProc SYSTEM "file:///arquivo-ficticio-inexistente">', b'<!ENTITY ficticia SYSTEM "https://example.invalid/ficticio">', b'<!doctype nfeProc []>'):
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                parse_nfe(declaration + content)

    def test_utf16_utf32_and_nul_encoded_payloads_are_rejected(self):
        plain = fake_xml().decode("utf-8").split("?>", 1)[1]
        for encoding in ("utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be"):
            for prefix in ("", '<!DOCTYPE nfeProc [<!ENTITY ficticia "NUNCA EXPANDIR">]>'):
                with self.subTest(encoding=encoding, prefix=prefix), self.assertRaises(ValueError):
                    parse_nfe((prefix + plain).encode(encoding))
        with self.assertRaises(ValueError):
            parse_nfe(fake_xml() + b"\x00")

    def test_canonical_fingerprint_ignores_formatting_but_detects_changed_control_data(self):
        content = fake_xml()
        pretty = ET.fromstring(content)
        ET.indent(pretty, space="  ")
        self.assertEqual(parse_nfe(content)["content_fingerprint"], parse_nfe(ET.tostring(pretty))["content_fingerprint"])
        self.assertNotEqual(parse_nfe(content)["content_fingerprint"], parse_nfe(edit_xml(content, "total/ICMSTot/vNF", "100.31"))["content_fingerprint"])


if __name__ == "__main__":
    unittest.main()
