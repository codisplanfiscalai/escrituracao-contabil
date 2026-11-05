"""New bookkeeping process; generated sources, no production data or external systems."""

from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import tempfile
import unittest
from src.persistence import AccountingStore
from test_persistence import fake_accounts, fake_xml, BUYER
from test_batch_import import zip_bytes


class WorkApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic.sqlite3"
        self.s = AccountingStore(self.path, actor="operador-sintetico")
        self.addCleanup(self.s.close)
        self.c = self.s.create_company(
            "Empresa inteiramente sintética", "TEST", "TEST", BUYER
        )["id"]
        self.other = self.s.create_company("Outra sintética", "OUT", "OUT")["id"]
        self.plan = self.s.import_plan(self.c, "Plano fictício", fake_accounts())["id"]
        self.ids = {a["code"]: a["id"] for a in self.s.list_accounts(self.c, self.plan)}
        self.cycle = self.s.save_work_cycle(
            self.c, "2026-08", "2026-09", self.plan, "Configuração explícita"
        )
        self.policy = self.s.save_work_policy(
            self.c,
            self.plan,
            "entrada",
            "2026-08",
            "Compra sintética",
            self.ids["1.1.1"],
            self.ids["2.1"],
            "Contas explicitamente informadas",
            True,
        )
        self.key = 0

    def save(self, payload, operation_id=None, version=0, cycle=None):
        self.key += 1
        return self.s.save_work_operation(
            self.c,
            (cycle or self.cycle)["id"],
            payload,
            "Registro sintético",
            "work-" + str(self.key),
            operation_id,
            version,
        )

    def post(self, operation):
        row = self.s.review_work_operation(
            self.c,
            operation["operation_id"],
            operation["snapshot_hash"],
            "Conferência integrada",
        )
        return self.s.post_work_operation(
            self.c, row["operation_id"], row["snapshot_hash"], "Escrituração explícita"
        )

    def document(self):
        receipt = self.s.receive_sources(
            self.c, [{"filename": "ficticio.xml", "content": fake_xml()}], "receipt-1"
        )
        source = receipt["items"][0]
        organized = self.s.organize_source(
            self.c,
            source["input_id"],
            self.cycle["id"],
            source["snapshot_hash"],
            "Competência de entrada confirmada",
        )
        doc = organized["evidence"]["document_ids"][0]
        return self.s.prepare_work_operation(
            self.c, self.cycle["id"], doc, policy_id=self.policy["id"]
        )

    def opening(self):
        p = self.s.prepare_work_operation(
            self.c, self.cycle["id"], operation="abertura"
        )
        p.update(reference="Abertura zero confirmada", opening_zero=True, entries=[])
        p["fiscal"].update(total="0.00", posting_date="2026-09-01")
        return self.post(self.save(p))

    def test_receive_without_period_or_plan_then_one_integrated_operation(self):
        fresh = self.s.create_company("Recepção sem configuração", "F", "F")["id"]
        receipt = self.s.receive_sources(
            fresh,
            [
                {
                    "filename": "ficticio.zip",
                    "content": zip_bytes(
                        [("valido.xml", fake_xml()), ("erro.xml", b"<broken")]
                    ),
                }
            ],
            "first",
        )
        self.assertEqual(self.s.list_periods(fresh), [])
        self.assertEqual(len(receipt["items"]), 3)
        self.assertTrue(
            any(row["evidence"]["state"] == "identificado" for row in receipt["items"])
        )
        payload = self.document()
        self.assertEqual(payload["finance"]["mode"], "origem")
        self.assertEqual(
            [p["amount"] for p in payload["finance"]["installments"]],
            ["40.10", "60.20"],
        )
        op = self.save(payload)
        self.assertTrue(op["validation"]["ready"], op["validation"])
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM work_movements").fetchone()[0], 0
        )
        posted = self.post(op)
        self.assertEqual(posted["state"], "escriturado")
        self.assertEqual(len(posted["titles"]), 2)
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM work_movements").fetchone()[0], 2
        )
        self.s.post_work_operation(
            self.c, op["operation_id"], op["snapshot_hash"], "Repetição segura"
        )
        self.assertEqual(len(self.s.list_finance_titles(self.c)), 2)
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM accounting_batches").fetchone()[0],
            0,
        )
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM fiscal_entries").fetchone()[0], 0
        )
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM manual_journals").fetchone()[0], 0
        )

    def test_drafts_revisions_and_atomic_validation_do_not_fake_ready(self):
        p = self.document()
        p["entries"][0]["amount"] = "0.10"
        draft = self.save(p)
        self.assertFalse(draft["validation"]["ready"])
        with self.assertRaises(ValueError):
            self.post(draft)
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM work_movements").fetchone()[0], 0
        )
        corrected = self.document()
        corrected = self.save(corrected, draft["operation_id"], 1)
        self.assertEqual(corrected["version"], 2)
        self.assertEqual(corrected["history"][1]["state"], "substituido")
        with self.assertRaises(ValueError):
            self.s.review_work_operation(
                self.c,
                corrected["operation_id"],
                draft["snapshot_hash"],
                "Desatualizado",
            )
        self.post(corrected)
        with self.assertRaises(ValueError):
            self.save(p, draft["operation_id"], 2)

    def test_opening_continuity_and_liquidation_share_one_ledger(self):
        self.opening()
        recognized = self.post(self.save(self.document()))
        title = recognized["titles"][0]
        october = self.s.save_work_cycle(
            self.c, "2026-08", "2026-10", self.plan, "Próxima competência"
        )
        rule = self.s.save_work_policy(
            self.c,
            self.plan,
            "pagamento",
            "2026-08",
            "Liquidação de obrigação",
            self.ids["2.1"],
            self.ids["1.1.1"],
            "Reclassificação explícita",
            True,
        )
        p = self.s.prepare_work_settlement(
            self.c,
            october["id"],
            title["id"],
            rule["id"],
            "10.10",
            "2026-10-15",
            "Pagamento parcial informado",
        )
        payment = self.post(self.save(p, cycle=october))
        self.assertEqual(payment["state"], "escriturado")
        current = self.s._finance_title(self.c, title["id"])
        self.assertEqual(current["balance"], "30.00")
        september = self.s.work_books(self.c, self.cycle["id"])
        october_book = self.s.work_books(self.c, october["id"])
        self.assertTrue(september["opening_declared"])
        self.assertEqual(september["totals"]["debit"], "100.30")
        self.assertEqual(october_book["totals"]["debit"], "10.10")
        old = {row["account_id"]: row["closing"] for row in september["trial_balance"]}
        new = {
            row["account_id"]: row["opening"] for row in october_book["trial_balance"]
        }
        self.assertEqual(old, new)
        self.assertEqual(len(october_book["fiscal_book"]), 0)
        self.assertEqual(september["finance"][0]["paid"], "0.00")
        self.assertEqual(october_book["finance"][0]["paid"], "10.10")
        self.assertEqual(len(self.s.list_finance_titles(self.c)), 2)

    def test_guards_scope_source_drift_tabs_and_preserved_exports(self):
        self.opening()
        p = self.document()
        op = self.post(self.save(p))
        book = self.s.work_books(self.c, self.cycle["id"])
        exp = self.s.create_work_export(
            self.c, self.cycle["id"], book["snapshot_hash"], "Relatório de conferência"
        )
        original = self.s.work_export_file(
            self.c, exp["id"], "pacote-escrituracao.zip"
        )["content"]
        with self.assertRaises(ValueError):
            self.s.work_export_file(self.other, exp["id"], "pacote-escrituracao.zip")
        tab = self.s.save_work_tab(
            self.c, self.cycle["id"], "Ficha em trabalho", {"incompleto": "sim"}
        )
        with AccountingStore(self.path, actor="outra-pessoa") as other:
            self.assertEqual(other.work_tabs(self.c, self.cycle["id"]), [])
        with AccountingStore(self.path, actor="operador-sintetico") as same:
            self.assertEqual(
                same.work_tabs(self.c, self.cycle["id"])[0]["data"],
                {"incompleto": "sim"},
            )
        with self.assertRaises(ValueError):
            self.s.save_work_tab(
                self.c, self.cycle["id"], "Concorrente", {}, tab["id"], 0
            )
        self.assertEqual(
            self.s.work_export_file(self.c, exp["id"], "pacote-escrituracao.zip")[
                "content"
            ],
            original,
        )
        self.assertEqual(self.s.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_reversal_reconciles_ledger_and_titles_and_cannot_be_forged(self):
        recognized = self.post(self.save(self.document()))
        reversed_op = self.s.reverse_work_operation(
            self.c,
            recognized["operation_id"],
            self.cycle["id"],
            "2026-09-20",
            recognized["snapshot_hash"],
            "Correção sintética",
            "reverse-1",
        )
        self.assertTrue(reversed_op["validation"]["ready"], reversed_op["validation"])
        p = copy.deepcopy(reversed_op["payload"])
        p["cancel_titles"] = []
        bad = self.s.save_work_operation(
            self.c,
            self.cycle["id"],
            p,
            "Tentativa inválida",
            "bad-reverse",
            reversed_op["operation_id"],
            1,
        )
        self.assertFalse(bad["validation"]["ready"])
        fixed = self.s.save_work_operation(
            self.c,
            self.cycle["id"],
            reversed_op["payload"],
            "Correção",
            "fixed-reverse",
            reversed_op["operation_id"],
            2,
        )
        self.post(fixed)
        self.assertTrue(
            all(t["canceled_at"] for t in self.s.list_finance_titles(self.c))
        )
        self.assertTrue(
            all(
                r["closing"] == "0.00"
                for r in self.s.work_books(self.c, self.cycle["id"])["trial_balance"]
            )
        )
        with self.assertRaises(ValueError):
            self.s.reverse_work_operation(
                self.c,
                recognized["operation_id"],
                self.cycle["id"],
                "2026-09-21",
                recognized["snapshot_hash"],
                "Duplicado",
                "reverse-2",
            )

    def test_settlement_reversal_reopens_balance_without_recognizing_again(self):
        recognized = self.post(self.save(self.document()))
        policy = self.s.save_work_policy(
            self.c,
            self.plan,
            "pagamento",
            "2026-08",
            "Pagamento sintético",
            self.ids["2.1"],
            self.ids["1.1.1"],
            "Teste",
            True,
        )
        title = recognized["titles"][0]
        p = self.s.prepare_work_settlement(
            self.c,
            self.cycle["id"],
            title["id"],
            policy["id"],
            "10.10",
            "2026-09-20",
            "Baixa sintética",
        )
        paid = self.post(self.save(p))
        self.assertTrue(paid["validation"]["ready"])
        with self.assertRaisesRegex(ValueError, "liquidações"):
            self.s.reverse_work_operation(
                self.c,
                recognized["operation_id"],
                self.cycle["id"],
                "2026-09-21",
                recognized["snapshot_hash"],
                "Teste",
                "blocked-recognition",
            )
        rev = self.s.reverse_work_operation(
            self.c,
            paid["operation_id"],
            self.cycle["id"],
            "2026-09-21",
            paid["snapshot_hash"],
            "Correção da baixa",
            "reverse-payment",
        )
        self.post(rev)
        self.assertEqual(self.s._finance_title(self.c, title["id"])["balance"], "40.10")
        self.assertEqual(
            len(self.s.work_books(self.c, self.cycle["id"])["fiscal_book"]), 1
        )

    def test_post_rolls_back_every_effect_on_audit_failure(self):
        from unittest.mock import patch

        o = self.save(self.document())
        o = self.s.review_work_operation(
            self.c, o["operation_id"], o["snapshot_hash"], "Conferido"
        )
        with patch.object(
            self.s, "_audit", side_effect=RuntimeError("Falha sintética")
        ):
            with self.assertRaises(RuntimeError):
                self.s.post_work_operation(
                    self.c, o["operation_id"], o["snapshot_hash"], "Teste"
                )
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM work_movements").fetchone()[0], 0
        )
        self.assertEqual(self.s.list_finance_titles(self.c), [])
        self.assertEqual(
            self.s.get_work_operation(self.c, o["operation_id"])["state"], "revisado"
        )

    def test_competing_posts_are_idempotent_and_source_drift_blocks_review(self):
        o = self.save(self.document())
        o = self.s.review_work_operation(
            self.c, o["operation_id"], o["snapshot_hash"], "Conferido"
        )

        def post():
            with AccountingStore(self.path) as other:
                return other.post_work_operation(
                    self.c, o["operation_id"], o["snapshot_hash"], "Concorrência"
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            rows = list(executor.map(lambda _: post(), range(2)))
        self.assertEqual([r["state"] for r in rows], ["escriturado"] * 2)
        self.assertEqual(len(self.s.list_finance_titles(self.c)), 2)
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM work_movements").fetchone()[0], 2
        )
        # A new source decision changes only the future context, never the posted snapshot.
        source = self.s.source_inbox(self.c)[0]
        with self.s.db:
            self.s._append_source_revision(
                self.c,
                source["input_id"],
                {**source["evidence"], "annotation": "Complemento sintético"},
                "Anotação",
            )
        self.assertEqual(
            self.s.get_work_operation(self.c, o["operation_id"])["snapshot_hash"],
            o["snapshot_hash"],
        )
        self.assertEqual(
            self.s.work_books(self.c, self.cycle["id"])["totals"]["debit"], "100.30"
        )

    def test_plan_csv_original_and_migration_are_atomic_and_idempotent(self):
        content = "codigo;descricao;tipo;natureza;superior;acesso\n1;Ativo;sintetica;devedora;;10\n1.1;Caixa;analitica;devedora;1;11\n"
        p = self.s.import_work_plan(
            self.c, "plano.csv", content, "Plano completo", "Teste"
        )
        self.assertEqual(
            self.s.list_accounts(self.c, p["id"])[1]["attributes"]["acesso"], "11"
        )
        self.assertEqual(
            bytes(
                self.s.db.execute(
                    "SELECT content FROM work_config_sources WHERE plan_id=?",
                    (p["id"],),
                ).fetchone()[0]
            ),
            content.encode(),
        )
        self.document()
        before = self.s.db.execute("SELECT COUNT(*) FROM source_revisions").fetchone()[
            0
        ]
        with self.s.db:
            self.s._migrate_work_sources()
            self.s._migrate_work_sources()
        # Existing technical file gets one preserved legacy reference, never a repeated revision.
        after = self.s.db.execute("SELECT COUNT(*) FROM source_revisions").fetchone()[0]
        with self.s.db:
            self.s._migrate_work_sources()
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM source_revisions").fetchone()[0],
            after,
        )
        self.assertGreaterEqual(after, before)

    def test_closing_requires_opening_and_resolved_open_forms(self):
        self.opening()
        t = self.s.save_work_tab(self.c, self.cycle["id"], "Rascunho incompleto", {})
        current = self.s.work_overview(self.c, self.cycle["id"])
        with self.assertRaises(ValueError):
            self.s.transition_work_cycle(
                self.c, self.cycle["id"], "encerrada", current["snapshot_hash"], "Teste"
            )
        self.s.save_work_tab(
            self.c, self.cycle["id"], t["title"], {}, t["id"], t["version"], True
        )
        current = self.s.work_overview(self.c, self.cycle["id"])
        self.assertEqual(
            self.s.transition_work_cycle(
                self.c,
                self.cycle["id"],
                "encerrada",
                current["snapshot_hash"],
                "Conferido",
            )["state"],
            "encerrada",
        )

    def test_schema_nine_migration_preserves_closed_ledger_and_fiscal(self):
        file = self.s.import_file(
            self.c, self.cycle["period_id"], "historico.xml", fake_xml(), "XML"
        )
        doc = self.s.list_documents(self.c)[0]["id"]
        seed = self.s.fiscal_seed(self.c, self.cycle["period_id"], doc)
        data = {**seed["data"], "posting_date": "2026-09-15"}
        fiscal = self.s.save_fiscal_entry(
            self.c,
            self.cycle["period_id"],
            data,
            "Histórico",
            "legacy-fiscal",
            document_id=doc,
            expected_source_hash=seed["source_hash"],
        )
        self.s.review_fiscal_entry(
            self.c, fiscal["entry_id"], fiscal["snapshot_hash"], "Conferido", True
        )
        lines = [
            {
                "date": "2026-09-15",
                "group": "histórico",
                "side": side,
                "amount": "10.00",
                "account_id": self.ids[code],
                "memo": "Movimento anterior",
            }
            for side, code in [("D", "1.1.1"), ("C", "2.1")]
        ]
        manual = self.s.save_manual_journal(
            self.c,
            self.cycle["period_id"],
            self.plan,
            lines,
            "Histórico",
            "Histórico",
            "legacy-manual",
        )
        self.s.transition_manual_journal(
            self.c,
            manual["journal_id"],
            manual["snapshot_hash"],
            "Conferido",
            "revisado",
        )
        self.s.transition_manual_journal(
            self.c, manual["journal_id"], manual["snapshot_hash"], "Fechado", "fechado"
        )
        original = bytes(
            self.s.db.execute(
                "SELECT original FROM files WHERE id=?", (file["id"],)
            ).fetchone()[0]
        )
        with self.s.db:
            self.s.db.execute(
                "INSERT INTO fiscal_period_states VALUES(?,?,'exportado',1,'Referência anterior')",
                (self.c, "2026-09"),
            )
        self.s.db.execute("PRAGMA foreign_keys=OFF")
        with self.s.db:
            tables = [
                r[0]
                for r in self.s.db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'work_%' OR name LIKE 'source_%')"
                )
            ]
            for table in tables:
                self.s.db.execute('DROP TABLE "' + table + '"')
            self.s.db.execute("UPDATE schema_version SET version=9")
        self.s.close()
        self.s = AccountingStore(self.path, actor="operador-sintetico")
        self.addCleanup(self.s.close)
        cycle = self.s.work_cycles(self.c)[0]
        self.assertEqual(cycle["state"], "encerrada")
        self.assertEqual(
            bytes(
                self.s.db.execute(
                    "SELECT original FROM files WHERE id=?", (file["id"],)
                ).fetchone()[0]
            ),
            original,
        )
        books = self.s.work_books(self.c, cycle["id"])
        self.assertEqual(books["totals"]["debit"], "10.00")
        self.assertEqual(len(books["fiscal_book"]), 1)
        self.assertEqual(
            books["fiscal_book"][0]["snapshot_hash"], fiscal["snapshot_hash"]
        )
        self.assertEqual(
            self.s.work_overview(self.c, cycle["id"])["documents"][0]["state"], "legado"
        )
        with self.assertRaisesRegex(ValueError, "exportada"):
            self.s.transition_work_cycle(
                self.c,
                cycle["id"],
                "aberta",
                self.s.work_overview(self.c, cycle["id"])["snapshot_hash"],
                "Teste",
            )
        self.assertEqual(self.s.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_legacy_draft_resumes_once_and_preserves_snapshot(self):
        lines = [
            {
                "date": "2026-09-15",
                "group": "anterior",
                "side": side,
                "amount": "10.00",
                "account_id": self.ids[code],
                "memo": "Rascunho anterior",
            }
            for side, code in [("D", "1.1.1"), ("C", "2.1")]
        ]
        old = self.s.save_manual_journal(
            self.c,
            self.cycle["period_id"],
            self.plan,
            lines,
            "Anterior",
            "Preservado",
            "legacy-draft",
        )
        item = next(
            r
            for r in self.s.work_legacy(self.c, self.cycle["id"])
            if r["kind"] == "manual"
        )
        self.assertTrue(item["can_resume"])
        resumed = self.s.resume_work_legacy(
            self.c,
            self.cycle["id"],
            "manual",
            old["journal_id"],
            old["snapshot_hash"],
            "Retomada explícita",
            "resume-1",
        )
        self.assertEqual(resumed["payload"]["reference"], "Anterior")
        self.assertEqual(
            self.s._manual_revision(self.c, old["journal_id"])["snapshot_hash"],
            old["snapshot_hash"],
        )
        with self.assertRaises(ValueError):
            self.s.resume_work_legacy(
                self.c,
                self.cycle["id"],
                "manual",
                old["journal_id"],
                old["snapshot_hash"],
                "Duplicado",
                "resume-2",
            )
        self.assertEqual(len(self.s.work_operations(self.c, self.cycle["id"])), 1)

    def test_source_revision_change_blocks_review_but_not_original_retrieval(self):
        from src.accounting_store import digest

        o = self.save(self.document())
        source = self.s.source_inbox(self.c)[0]
        original = self.s.source_original(self.c, source["input_id"])["content"]
        with self.s.db:
            self.s._append_source_revision(
                self.c,
                source["input_id"],
                {**source["evidence"], "annotation": "Nova decisão"},
                "Motivo registrado",
            )
        self.assertEqual(len(self.s.source_history(self.c, source["input_id"])), 3)
        with self.assertRaisesRegex(ValueError, "fontes mudaram"):
            self.s.review_work_operation(
                self.c,
                o["operation_id"],
                o["snapshot_hash"],
                "Conferência desatualizada",
            )
        self.assertEqual(
            self.s.source_original(self.c, source["input_id"])["content"], original
        )
        with self.assertRaises(ValueError):
            self.s.source_original(self.other, source["input_id"])

    def test_xml_and_partial_sped_share_document_without_creating_an_operation(self):
        from test_persistence import ISSUER
        from test_reconciliation import fake_sped
        from src.reconciliation import SPED_PROFILE

        company = self.s.create_company("Emitente sintético", cnpj=ISSUER)["id"]
        cycle = self.s.save_work_cycle(company, "2026-08", "2026-09", None, "Teste")
        receipt = self.s.receive_sources(
            company,
            [
                {"filename": "fonte.xml", "content": fake_xml()},
                {"filename": "fonte.txt", "content": fake_sped()},
            ],
            "mixed",
        )
        for source in receipt["items"]:
            self.s.organize_source(
                company,
                source["input_id"],
                cycle["id"],
                source["snapshot_hash"],
                "Organização explícita",
                SPED_PROFILE if source["kind"] == "SPED" else None,
            )
        docs = self.s.list_documents(company)
        self.assertEqual(len(docs), 1)
        self.assertEqual(len(docs[0]["sources"]), 2)
        self.assertEqual(self.s.work_operations(company, cycle["id"]), [])
        with self.assertRaisesRegex(ValueError, "fonte"):
            self.s.prepare_work_operation(company, cycle["id"], docs[0]["id"])

    def test_persistent_legacy_fiscal_guides_remain_owned_and_resumable(self):
        raw = {
            "data": {
                "operation": "servico_tomado",
                "model": "SERVICO",
                "number": "PENDENTE-ANTERIOR",
                "issued_date": "2026-08-30",
                "posting_date": "2026-09-01",
                "total": "12.30",
                "notes": "Texto ainda incompleto",
            },
            "reason": "Rascunho anterior",
            "ui_only": {"preservar": "original"},
        }
        old = self.s.save_fiscal_workspace(
            self.c, self.cycle["period_id"], "Guia anterior", raw, "legacy-fiscal-tab"
        )
        item = next(
            r
            for r in self.s.work_legacy(self.c, self.cycle["id"])
            if r["kind"] == "guia_fiscal"
        )
        self.assertEqual(item["snapshot"]["data"], raw)
        with AccountingStore(self.path, actor="outro-operador") as other:
            self.assertFalse(
                any(
                    r["kind"] == "guia_fiscal"
                    for r in other.work_legacy(self.c, self.cycle["id"])
                )
            )
        resumed = self.s.resume_work_legacy(
            self.c,
            self.cycle["id"],
            "guia_fiscal",
            old["id"],
            item["snapshot_hash"],
            "Retomar rascunho",
            "resume-legacy-tab",
        )
        self.assertEqual(resumed["payload"]["fiscal"]["number"], "PENDENTE-ANTERIOR")
        self.assertEqual(resumed["payload"]["legacy_workspace"]["original"], raw)
        self.assertFalse(resumed["validation"]["ready"])
        self.assertEqual(
            self.s.list_fiscal_workspaces(self.c, self.cycle["period_id"])[0]["data"],
            raw,
        )
        with self.assertRaises(ValueError):
            self.s.resume_work_legacy(
                self.c,
                self.cycle["id"],
                "guia_fiscal",
                old["id"],
                item["snapshot_hash"],
                "Não duplicar",
                "resume-legacy-tab-2",
            )

    def test_opening_requires_consistent_zero_and_date_of_all_lines(self):
        p = self.s.prepare_work_operation(
            self.c, self.cycle["id"], operation="abertura"
        )
        p.update(reference="Abertura", opening_zero=True, entries=[])
        p["fiscal"].update(total="100.00", posting_date="2026-09-01")
        o = self.save(p)
        self.assertFalse(
            o["validation"]["ready"],
            "Abertura declarada zero não pode conter total não zero",
        )
        p.update(
            opening_zero=False,
            entries=[
                {
                    "account_id": self.ids[code],
                    "side": side,
                    "date": "2026-09-02",
                    "amount": "100.00",
                    "group": "abertura",
                    "memo": "Abertura informada",
                }
                for side, code in [("D", "1.1.1"), ("C", "2.1")]
            ],
        )
        o = self.save(p)
        self.assertFalse(
            o["validation"]["ready"],
            "Partidas da abertura devem representar o início do mês",
        )
        for line in p["entries"]:
            line["date"] = "2026-09-01"
        valid = self.post(self.save(p))
        self.assertEqual(valid["state"], "escriturado")
        book = self.s.work_books(self.c, self.cycle["id"])
        self.assertEqual(
            {r["code"]: r["opening"] for r in book["trial_balance"]},
            {"1.1.1": "100.00", "2.1": "-100.00"},
        )
        self.assertEqual(book["totals"]["debit"], "0.00")

    def test_settlement_date_must_match_ledger_event(self):
        recognized = self.post(self.save(self.document()))
        policy = self.s.save_work_policy(
            self.c,
            self.plan,
            "pagamento",
            "2026-08",
            "Liquidação",
            self.ids["2.1"],
            self.ids["1.1.1"],
            "Teste",
            True,
        )
        p = self.s.prepare_work_settlement(
            self.c,
            self.cycle["id"],
            recognized["titles"][0]["id"],
            policy["id"],
            "10.10",
            "2026-09-20",
            "Parcial",
        )
        for line in p["entries"]:
            line["date"] = "2026-09-19"
        o = self.save(p)
        self.assertFalse(
            o["validation"]["ready"],
            "Baixa e suas partidas precisam ter a mesma data econômica",
        )
        with self.assertRaises(ValueError):
            self.s.review_work_operation(
                self.c,
                o["operation_id"],
                o["snapshot_hash"],
                "Não conferir datas divergentes",
            )
        self.assertEqual(
            self.s._finance_title(self.c, recognized["titles"][0]["id"])["balance"],
            "40.10",
        )

    def test_cycle_version_rejects_boolean_without_mutation(self):
        with self.assertRaises(ValueError):
            self.s.save_work_cycle(
                self.c, "2026-07", "2026-09", self.plan, "Versão inválida", True
            )
        self.assertEqual(self.s._work_cycle(self.c, self.cycle["id"]), self.cycle)

    def test_repeated_original_cannot_silently_restore_withdrawn_normalization(self):
        self.document()
        source = self.s.source_inbox(self.c)[0]
        impact = self.s.source_impact(self.c, source["input_id"])
        self.s.remove_source(
            self.c,
            source["input_id"],
            impact["impact_hash"],
            "Retirada explícita",
            True,
        )
        receipt = self.s.receive_sources(
            self.c,
            [{"filename": "repetido.xml", "content": fake_xml()}],
            "new-receipt-same-bytes",
        )
        repeated = receipt["items"][0]
        with self.assertRaisesRegex(ValueError, "retirad|excluíd|excluid|removid"):
            self.s.organize_source(
                self.c,
                repeated["input_id"],
                self.cycle["id"],
                repeated["snapshot_hash"],
                "Nova tentativa",
            )
        self.assertEqual(
            self.s._source_revision(self.c, repeated["input_id"])["snapshot_hash"],
            repeated["snapshot_hash"],
        )
        self.assertEqual(self.s.list_files(self.c)[0]["status"], "excluido")
        self.assertEqual(
            self.s.source_original(self.c, repeated["input_id"])["content"], fake_xml()
        )

    def test_corrupt_original_blocks_effect_after_review(self):
        o = self.save(self.document())
        o = self.s.review_work_operation(
            self.c, o["operation_id"], o["snapshot_hash"], "Conferido"
        )
        with self.s.db:
            self.s.db.execute(
                "UPDATE files SET original=? WHERE company_id=?",
                (b"corrompido para teste", self.c),
            )
        with self.assertRaisesRegex(ValueError, "original|integridade|Hash"):
            self.s.post_work_operation(
                self.c,
                o["operation_id"],
                o["snapshot_hash"],
                "Tentativa após corrupção",
            )
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM work_movements").fetchone()[0], 0
        )
        self.assertEqual(self.s.list_finance_titles(self.c), [])
        self.assertEqual(
            self.s._work_revision(self.c, o["operation_id"])["state"], "revisado"
        )

    def test_past_financial_book_rejects_corrupt_future_snapshot(self):
        recognized = self.post(self.save(self.document()))
        october = self.s.save_work_cycle(
            self.c, "2026-09", "2026-10", self.plan, "Outubro"
        )
        policy = self.s.save_work_policy(
            self.c,
            self.plan,
            "pagamento",
            "2026-09",
            "Liquidação",
            self.ids["2.1"],
            self.ids["1.1.1"],
            "Teste",
            True,
        )
        p = self.s.prepare_work_settlement(
            self.c,
            october["id"],
            recognized["titles"][0]["id"],
            policy["id"],
            "10.10",
            "2026-10-20",
            "Parcial",
        )
        paid = self.post(self.save(p, cycle=october))
        payload = copy.deepcopy(paid["payload"])
        payload["reference"] = "alterado sem atualizar o hash"
        with self.s.db:
            self.s.db.execute(
                "UPDATE work_revisions SET payload=? WHERE id=?",
                (json.dumps(payload), paid["id"]),
            )
        with self.assertRaisesRegex(ValueError, "Snapshot|snapshot"):
            self.s.work_books(self.c, self.cycle["id"])


if __name__ == "__main__":
    unittest.main()
