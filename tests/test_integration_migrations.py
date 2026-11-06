"""Converge independent schema-7 branches and schema-8 finance without data loss."""

from pathlib import Path
import tempfile
import unittest
from src.persistence import AccountingStore
from test_persistence import fake_accounts, ISSUER
from test_product_catalog import product_xml
from test_batch_import import zip_bytes


class IntegrationMigrationTests(unittest.TestCase):
    def test_all_preintegration_variants_preserve_sealed_bytes_and_movements(self):
        for variant, version in [("manual", 7), ("import", 7), ("finance", 8)]:
            with (
                self.subTest(variant=variant),
                tempfile.TemporaryDirectory() as temporary,
            ):
                path = Path(temporary) / "synthetic.sqlite3"
                with AccountingStore(path) as store:
                    company = store.create_company(
                        "Empresa sintética", "TEST", "TEST", ISSUER
                    )["id"]
                    period = store.create_period(company, "2026-08", "2026-09")["id"]
                    plan = store.import_plan(
                        company, "Plano sintético", fake_accounts()
                    )["id"]
                    ids = {
                        row["code"]: row["id"]
                        for row in store.list_accounts(company, plan)
                    }
                    if variant == "import":
                        packed = zip_bytes([("produto.xml", product_xml())])
                        batch = store.import_batch(
                            company,
                            period,
                            [{"filename": "origem.zip", "content": packed}],
                            "synthetic-batch",
                        )
                        batch.pop("duplicate", None)
                        products = store.list_products(company)
                        absent = [
                            "finance_settlements",
                            "finance_titles",
                            "accounting_book_artifacts",
                            "accounting_book_exports",
                            "manual_journal_requests",
                            "manual_journal_revisions",
                            "manual_journals",
                        ]
                    else:
                        lines = [
                            dict(
                                date="2026-09-15",
                                group="synthetic",
                                side=side,
                                amount="0.30",
                                account_id=ids[code],
                                memo="Histórico sintético",
                            )
                            for side, code in [("D", "1.1.1"), ("C", "2.1")]
                        ]
                        journal = store.save_manual_journal(
                            company,
                            period,
                            plan,
                            lines,
                            "Referência",
                            "Teste",
                            "synthetic-journal",
                        )
                        for target in ["revisado", "fechado"]:
                            journal = store.transition_manual_journal(
                                company,
                                journal["journal_id"],
                                journal["snapshot_hash"],
                                "Teste",
                                target,
                            )
                        books = store.accounting_books(company, period, plan)
                        exported = store.create_book_export(
                            company, period, plan, books["book_hash"], "Teste"
                        )
                        preserved = {
                            file["name"]: store.read_book_artifact(
                                company, exported["id"], file["name"]
                            )["content"]
                            for file in exported["artifacts"]
                        }
                        absent = [
                            "product_observations",
                            "products",
                            "import_items",
                            "import_batches",
                        ]
                        if variant == "finance":
                            title = store.create_finance_title(
                                company,
                                period,
                                "pagar",
                                "Ref",
                                "Fictício",
                                "2026-09-20",
                                "0.30",
                                "Teste",
                                "synthetic-title",
                            )
                            title = store.settle_finance_title(
                                company,
                                title["id"],
                                "0.10",
                                "2026-09-20",
                                "Ref",
                                "Teste",
                                "synthetic-paid",
                                title["snapshot_hash"],
                            )
                        else:
                            absent += ["finance_settlements", "finance_titles"]
                    for table in absent:
                        store.db.execute("DROP TABLE " + table)
                    store.db.execute("UPDATE schema_version SET version=?", (version,))
                    store.db.commit()
                with AccountingStore(path) as migrated:
                    self.assertEqual(
                        migrated.db.execute(
                            "SELECT version FROM schema_version"
                        ).fetchone()[0],
                        17,
                    )
                    self.assertEqual(migrated.list_periods(company)[0]["id"], period)
                    self.assertEqual(
                        migrated.db.execute("PRAGMA foreign_key_check").fetchall(), []
                    )
                    if variant == "import":
                        self.assertEqual(migrated.list_import_batches(company), [batch])
                        self.assertEqual(
                            migrated.read_import_original(
                                company, batch["items"][0]["id"]
                            )["content"],
                            packed,
                        )
                        self.assertEqual(migrated.list_products(company), products)
                        self.assertEqual(migrated.list_manual_journals(company), [])
                        self.assertEqual(migrated.list_finance_titles(company), [])
                    else:
                        self.assertEqual(
                            migrated.list_manual_journals(company), [journal]
                        )
                        self.assertEqual(
                            migrated.accounting_books(company, period, plan), books
                        )
                        for name, content in preserved.items():
                            self.assertEqual(
                                migrated.read_book_artifact(
                                    company, exported["id"], name
                                )["content"],
                                content,
                            )
                        self.assertEqual(migrated.list_import_batches(company), [])
                        if variant == "finance":
                            self.assertEqual(
                                migrated.list_finance_titles(company), [title]
                            )
