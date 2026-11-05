"""Synthetic partial-EFD fixtures; these are not valid official filings."""
import json
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

from src.persistence import AccountingStore, SCHEMA, parse_nfe
from src.reconciliation import XML_PROFILE, SPED_PROFILE, parse_sped
from test_persistence import ISSUER, BUYER, fictitious_key, fake_xml, edit_xml


def fake_sped(*, total="100,30", key=None, number="1", company=ISSUER, version="020", emitted="15092026", extras=(), repeated=False):
    header=["0000",version,"0","01092026","30092026","Empresa inteiramente fictícia",company,"","SP","IE-FICTICIA","3550308","","","A","1"]
    c100=["C100","1","0","PART-FICTICIO","55","00","001",number,fictitious_key() if key is None else key,emitted,"",total,"1"]+[""]*16
    rows=[header,["C001","0"],c100,*extras]
    if repeated:
        rows.append(c100)
    rows.extend([["C990",str(len(rows))],["9999",str(len(rows)+2)]])
    return ("\n".join("|"+"|".join(row)+"|" for row in rows)+"\n").encode()


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/"ficticio.sqlite3"
        self.store=AccountingStore(self.path,actor="analista-ficticio")
        self.addCleanup(lambda:self.store.close())
        self.company=self.store.create_company("Empresa fictícia","TEST","TEST",ISSUER)
        self.cid=self.company["id"]
        self.period=self.store.create_period(self.cid,"2026-08","2026-09")

    def upload(self,kind,content=None,profile=None,period=None):
        return self.store.import_file(self.cid,(period or self.period)["id"],"origem-ficticia."+("xml" if kind=="XML" else "txt"),
                                      content or (fake_xml() if kind=="XML" else fake_sped()),kind,sped_profile=profile)

    def count(self,table):
        assert table in {"invoices","installments","source_observations","file_indexings","documents","files"}
        return self.store.db.execute("SELECT COUNT(*) FROM "+table).fetchone()[0]

    def reconcile(self):
        return self.store.list_reconciliation(self.cid,self.period["id"])

    def test_both_import_orders_share_document_title_and_installments(self):
        for order in (("XML","SPED"),("SPED","XML")):
            with self.subTest(order=order):
                # A separate company scope keeps each ordering independent.
                self.cid=self.store.create_company("Empresa fictícia de ordem","TEST","TEST",ISSUER)["id"]
                self.period=self.store.create_period(self.cid,"2026-08","2026-09")
                imported=[self.upload(kind,profile=SPED_PROFILE if kind=="SPED" else None) for kind in order]
                docs=self.reconcile()
                self.assertEqual(len(docs),1)
                self.assertEqual(docs[0]["state"],"coincidente_no_recorte")
                self.assertFalse(docs[0]["ready_for_export"])
                self.assertEqual(docs[0]["differences"],[])
                self.assertEqual(len(docs[0]["invoices"]),1)
                self.assertEqual(len(docs[0]["invoices"][0]["installments"]),2)
                self.assertEqual(len([s for s in docs[0]["sources"] if s["entity_kind"]=="documento"]),2)
                self.assertEqual(docs[0]["unindexed_file_ids"],[])
                self.assertTrue(all(i["analyses"] for i in imported))

    def test_repeats_of_file_and_equivalent_xml_do_not_duplicate_billing(self):
        original=fake_xml()
        self.upload("XML",original)
        self.assertTrue(self.upload("XML",original)["duplicate"])
        self.upload("XML",ET.tostring(ET.fromstring(original)))
        self.assertEqual((self.count("documents"),self.count("invoices"),self.count("installments")),(1,1,2))
        invoice=self.reconcile()[0]["invoices"][0]
        self.assertEqual(len(invoice["sources"]),2)
        self.assertEqual([len(part["sources"]) for part in invoice["installments"]],[2,2])

    def test_differences_show_field_value_file_and_line_without_overwrite(self):
        self.upload("XML")
        doc_before=self.store.list_documents(self.cid)[0]["payload"]
        sped=self.upload("SPED",fake_sped(total="101,30"),SPED_PROFILE)
        result=self.reconcile()[0]
        self.assertEqual(result["state"],"divergente")
        total=next(diff for diff in result["differences"] if diff["field"]=="total")
        self.assertEqual({row["value"] for row in total["values"]},{"100.30","101.30"})
        self.assertIn({"file_id":sped["id"],"locator":"linha:3","value":"101.30"},total["values"])
        self.assertEqual(self.store.list_documents(self.cid)[0]["payload"],doc_before)

    def test_date_differences_within_month_remain_visible(self):
        self.upload("XML")
        self.upload("SPED",fake_sped(emitted="16092026"),SPED_PROFILE)
        self.assertIn("issued_date",[diff["field"] for diff in self.reconcile()[0]["differences"]])

    def test_missing_invalid_key_and_unsupported_version_do_not_create_document(self):
        for content in (fake_sped(key=""),fake_sped(key="1"*44),fake_sped(version="999"),fake_sped(number="2")):
            with self.subTest(content=content[:25]):
                self.upload("SPED",content,SPED_PROFILE)
                self.assertEqual(self.count("documents"),0)
        observations=self.store.list_observations(self.cid)
        self.assertTrue(any("CHV_NFE" in str(row["issues"]) for row in observations))
        self.assertTrue(any("COD_VER" in str(row["issues"]) for row in observations))
        self.assertTrue(all(row["document_id"] is None for row in observations))

    def test_header_company_and_period_mismatch_never_use_reference_movements(self):
        for content in (fake_sped(company=BUYER),fake_sped().replace(b"01092026",b"01082026").replace(b"30092026",b"31082026")):
            self.upload("SPED",content,SPED_PROFILE)
        self.assertEqual(self.count("documents"),0)
        self.assertTrue(all(row["issues"] for row in self.store.list_observations(self.cid)))

    def test_receipt_mode_remains_default_and_saved_file_can_be_analyzed(self):
        imported=self.upload("SPED")
        self.assertEqual(imported["analyses"],[])
        self.assertEqual(self.count("documents"),0)
        result=self.store.index_file(self.cid,imported["id"],SPED_PROFILE)
        self.assertFalse(result["duplicate"])
        self.assertEqual(self.reconcile()[0]["state"],"somente_sped")
        count=self.count("source_observations")
        self.assertTrue(self.store.index_file(self.cid,imported["id"],SPED_PROFILE)["duplicate"])
        self.assertEqual(self.count("source_observations"),count)
        self.assertEqual(self.store.list_audit(self.cid)[0]["action"],"arquivo_analisado")

    def test_reupload_with_explicit_profile_analyzes_saved_original_once(self):
        self.upload("SPED")
        result=self.upload("SPED",profile=SPED_PROFILE)
        self.assertTrue(result["duplicate"])
        self.assertEqual(len(result["analyses"]),1)
        self.assertEqual(self.count("files"),1)
        self.assertEqual(self.count("documents"),1)

    def test_c140_c141_model55_are_raw_pending_records_without_inferred_billing(self):
        content=fake_sped(extras=(["C140","0","00","","FATURA-FICTICIA-1","2","100,30"],["C141","01","15102026","100,30"]))
        self.upload("SPED",content,SPED_PROFILE)
        self.assertEqual((self.count("invoices"),self.count("installments")),(0,0))
        rows=[row for row in self.store.list_observations(self.cid) if row["raw"].get("record") in {"C140","C141"}]
        self.assertEqual(len(rows),2)
        self.assertTrue(all(row["issues"] and row["invoice_id"] is None for row in rows))
        self.assertEqual(self.reconcile()[0]["state"],"pendencia_de_origem")

    def test_repeated_c100_and_multiple_files_keep_one_document_and_all_records(self):
        self.upload("SPED",fake_sped(repeated=True),SPED_PROFILE)
        self.upload("SPED",fake_sped()+b"\n",SPED_PROFILE)
        self.assertEqual(self.count("documents"),1)
        observations=[row for row in self.store.list_observations(self.cid) if row["entity_kind"]=="documento"]
        self.assertEqual(len(observations),3)
        self.assertTrue(any("repetido" in str(row["issues"]) for row in observations))

    def test_missing_invoice_and_duplicate_installment_ids_remain_observations(self):
        self.upload("XML",edit_xml(fake_xml(),"cobr/fat/nFat",remove=True))
        self.assertEqual((self.count("invoices"),self.count("installments")),(0,0))
        self.assertEqual(len(self.store.list_observations(self.cid)),4)
        self.upload("XML",edit_xml(fake_xml(number=2),"cobr/dup/nDup","002"))
        self.assertEqual(self.count("invoices"),1)
        self.assertEqual(self.count("installments"),0)

    def test_changed_invoice_and_installment_preserve_first_values_and_sources(self):
        self.upload("XML")
        content=edit_xml(fake_xml(),"cobr/fat/vLiq","99.30")
        content=edit_xml(content,"cobr/dup/vDup","39.10")
        self.upload("XML",content)
        result=self.reconcile()[0]
        invoice=result["invoices"][0]
        self.assertEqual(invoice["payload"]["vLiq"],"100.30")
        self.assertEqual(invoice["installments"][0]["payload"]["vDup"],"40.10")
        self.assertTrue(any(diff.get("entity")=="fatura" for diff in result["differences"]))
        self.assertTrue(any(diff.get("entity")=="parcela" for diff in result["differences"]))

    def test_changed_billing_identifiers_are_pending_instead_of_creating_new_titles_or_parts(self):
        self.upload("XML")
        self.upload("XML",edit_xml(fake_xml(),"cobr/fat/nFat","OUTRO-TITULO-FICTICIO"))
        self.upload("XML",edit_xml(fake_xml(),"cobr/dup/nDup","003"))
        self.assertEqual((self.count("invoices"),self.count("installments")),(1,2))
        observations=self.store.list_observations(self.cid)
        pending=[row for row in observations if "possível duplicidade" in str(row["issues"])]
        self.assertEqual(len(pending),2)
        self.assertTrue(all(row["invoice_id"] is None or row["installment_id"] is None for row in pending))

    def test_multiple_billing_groups_or_invoices_are_rejected_without_silent_selection(self):
        from copy import deepcopy
        from test_persistence import NS
        for target,parent_path in (("cobr","infNFe"),("fat","cobr")):
            root=ET.fromstring(fake_xml())
            parent=root.find(f".//{{{NS}}}{parent_path}")
            parent.append(deepcopy(parent.find(f"{{{NS}}}{target}")))
            content=ET.tostring(root)
            imported=self.upload("XML",content)
            self.assertEqual(imported["status"],"rejeitado")
        self.assertEqual(self.count("documents"),0)

    def test_isolation_period_conflict_and_persistence(self):
        imported=self.upload("XML")
        other=self.store.create_company("Outra empresa fictícia","T2","P2",ISSUER)["id"]
        self.assertEqual(self.store.list_observations(other),[])
        self.assertEqual(self.store.list_reconciliation(other),[])
        with self.assertRaises(ValueError):
            self.store.index_file(other,imported["id"],XML_PROFILE)
        another_period=self.store.create_period(self.cid,"2026-07","2026-09")
        self.upload("SPED",profile=SPED_PROFILE,period=another_period)
        self.assertIn("período",str(self.reconcile()[0]["issues"]))
        alternate_view=self.store.list_reconciliation(self.cid,another_period["id"])
        self.assertEqual(len(alternate_view),1)
        self.assertIn("período",str(alternate_view[0]["issues"]))
        self.store.close();self.store=AccountingStore(self.path)
        self.assertEqual(len(self.reconcile()[0]["invoices"][0]["installments"]),2)

    def test_deletion_lists_billing_dependencies_preserves_observations_and_invalidates_preview(self):
        imported=self.upload("SPED",profile=SPED_PROFILE)
        preview=self.store.deletion_preview(self.cid,imported["id"])
        self.upload("XML")
        with self.assertRaisesRegex(ValueError,"desatualizada"):
            self.store.delete_file(self.cid,imported["id"],"Teste fictício",True,preview["preview_token"])
        preview=self.store.deletion_preview(self.cid,imported["id"])
        self.assertEqual(len(preview["invoice_ids"]),1)
        self.assertEqual(len(preview["installment_ids"]),2)
        before=self.count("source_observations")
        self.store.delete_file(self.cid,imported["id"],"Teste fictício",True,preview["preview_token"])
        self.assertEqual(self.count("source_observations"),before)
        result=self.reconcile()[0]
        self.assertEqual(result["state"],"somente_xml")
        self.assertEqual(result["invoices"][0]["status"],"pendente")
        self.assertTrue(any(row["file_status"]=="excluido" for row in result["sources"]))
        with self.assertRaises(ValueError):self.store.index_file(self.cid,imported["id"],SPED_PROFILE)

    def test_analysis_rolls_back_all_entities_when_audit_fails(self):
        imported=self.upload("SPED")
        with patch.object(self.store,"_audit",side_effect=RuntimeError("falha fictícia")):
            with self.assertRaises(RuntimeError):self.store.index_file(self.cid,imported["id"],SPED_PROFILE)
        self.assertEqual((self.count("documents"),self.count("source_observations"),self.count("file_indexings")),(0,0,0))
        self.assertFalse(self.store.index_file(self.cid,imported["id"],SPED_PROFILE)["duplicate"])

    def test_schema1_migration_is_additive_and_legacy_sources_require_explicit_analysis(self):
        legacy=Path(self.directory.name)/"legacy-ficticio.sqlite3"
        payload=json.dumps(parse_nfe(fake_xml()))
        original=fake_xml()
        with closing(sqlite3.connect(legacy)) as db, db:
            db.executescript(SCHEMA)
            db.execute("INSERT INTO schema_version VALUES(1)")
            db.execute("INSERT INTO companies VALUES(1,'Fictícia','TEST','TEST',?,'instante-ficticio')",(ISSUER,))
            db.execute("INSERT INTO periods VALUES(1,1,'2026-08','2026-09')")
            db.execute("INSERT INTO files VALUES(1,1,1,'ficticio.xml','XML','hash-ficticio',? ,?,'validado','{}','instante-ficticio')",(len(original),original))
            db.execute("INSERT INTO documents VALUES(1,1,1,?,?,'validado','instante-ficticio')",(fictitious_key(),payload))
            db.execute("INSERT INTO document_sources VALUES(1,1,0)")
        with AccountingStore(legacy) as store:
            self.assertEqual(store.db.execute("SELECT version FROM schema_version").fetchone()[0],9)
            self.assertEqual(store.db.execute("SELECT payload FROM documents").fetchone()[0],payload)
            self.assertEqual(bytes(store.db.execute("SELECT original FROM files").fetchone()[0]),original)
            self.assertEqual(store.list_observations(1),[])
            self.assertEqual(store.list_reconciliation(1)[0]["unindexed_file_ids"],[1])
            store.index_file(1,1,XML_PROFILE)
            self.assertEqual(len(store.list_reconciliation(1)[0]["invoices"]),1)
            self.assertEqual(store.db.execute("SELECT payload FROM documents").fetchone()[0],payload)


class PartialParserTests(unittest.TestCase):
    def test_unrecognized_situation_bad_dates_money_and_missing_block_remain_pending(self):
        for content in (fake_sped().replace(b'|55|00|',b'|55|02|'),fake_sped(emitted="31092026"),fake_sped(total="NaN"),fake_sped().replace(b'|C001|0|\n',b'')):
            rows,_=parse_sped(content,ISSUER,"2026-09")
            row=next(row for row in rows if row["record"]=="C100")
            self.assertEqual(row["normalized"],{})
            self.assertTrue(row["issues"])

    def test_encoding_and_unknown_fields_preserved_without_tax_calculation(self):
        content=fake_sped().decode().replace("Empresa inteiramente fictícia","Empresa fictícia ç").encode("cp1252")
        rows,metadata=parse_sped(content,ISSUER,"2026-09")
        self.assertEqual(metadata["encoding"],"cp1252")
        c100=next(row for row in rows if row["record"]=="C100")
        self.assertEqual(len(c100["fields"]),29)
        self.assertEqual(c100["normalized"]["total"],"100.30")

    def test_delimiters_and_nulls_rejected(self):
        for content in (b"not-sped",b"|0000|\x00|",b"|x|",b"\n"):
            with self.assertRaises(ValueError):parse_sped(content,ISSUER,"2026-09")
