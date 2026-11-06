"""Financeiro sintético: centavos, concorrência, isolamento, estorno e preservação."""

import csv
import io
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import unittest
from src.persistence import AccountingStore


class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "synthetic.sqlite3"
        self.s = AccountingStore(self.path)
        self.addCleanup(self.s.close)
        self.c = self.s.create_company("Sintética", "TEST", "TEST")["id"]
        self.p = self.s.create_period(self.c, "2026-08", "2026-09")["id"]
        self.other = self.s.create_company("Outra sintética", "OUT", "OUT")["id"]
        self.op = self.s.create_period(self.other, "2026-08", "2026-09")["id"]

    def title(self, value="100.30", key="title-1"):
        return self.s.create_finance_title(
            self.c,
            self.p,
            "pagar",
            "=SINTETICO",
            "Contraparte sintética",
            "2026-09-20",
            value,
            "Teste",
            key,
        )

    def settle(self, title, value="0.10", key="baixa-1"):
        return self.s.settle_finance_title(
            self.c,
            title["id"],
            value,
            "2026-09-20",
            "Ref sintética",
            "Teste",
            key,
            title["snapshot_hash"],
        )

    def test_partial_exact_idempotent_reversal_and_reopen(self):
        title = self.title("0.30")
        partial = self.settle(title)
        self.assertEqual(
            (partial["paid"], partial["balance"], partial["status"]),
            ("0.10", "0.20", "parcial"),
        )
        self.assertEqual(self.settle(title), partial)
        self.assertEqual(self.title("0.30"), partial)
        paid = self.settle(partial, "0.20", "baixa-2")
        self.assertEqual(paid["status"], "quitado")
        reversed = self.s.reverse_finance_settlement(
            self.c,
            title["id"],
            paid["settlements"][0]["id"],
            paid["snapshot_hash"],
            "Ajuste sintético",
        )
        self.assertEqual(reversed["balance"], "0.10")
        self.assertEqual(len(reversed["settlements"]), 2)
        self.assertEqual(
            self.s.reverse_finance_settlement(
                self.c,
                title["id"],
                paid["settlements"][0]["id"],
                paid["snapshot_hash"],
                "Ajuste sintético",
            ),
            reversed,
        )
        with AccountingStore(self.path) as reopened:
            self.assertEqual(reopened.list_finance_titles(self.c), [reversed])
        self.assertEqual(
            self.s.db.execute("SELECT COUNT(*) FROM manual_journals").fetchone()[0], 0
        )

    def test_invalid_scope_values_and_stale_hash_do_not_mutate(self):
        title = self.title()
        for value in ["NaN", "-1", "0", "1e2", "0.001", 0.1, "100.31"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.settle(title, value)
        with self.assertRaises(ValueError):
            self.s.create_finance_title(
                self.c, self.op, "pagar", "R", "C", "2026-09-20", "1", "Teste", "other"
            )
        with self.assertRaises(ValueError):
            self.s.list_finance_titles(self.other, self.p)
        with self.assertRaises(ValueError):
            self.s.settle_finance_title(
                self.other,
                title["id"],
                "1",
                "2026-09-20",
                "R",
                "Teste",
                "k",
                title["snapshot_hash"],
            )
        for value in ["2026-09-31", "20260920", "2026-9-20"]:
            with self.assertRaises(ValueError):
                self.s.settle_finance_title(
                    self.c,
                    title["id"],
                    "1",
                    value,
                    "R",
                    "Teste",
                    "k",
                    title["snapshot_hash"],
                )
        partial = self.settle(title)
        with self.assertRaisesRegex(ValueError, "alterado"):
            self.settle(title, "1", "stale")
        with self.assertRaisesRegex(ValueError, "outro conteúdo"):
            self.settle(title, "1")
        with self.assertRaises(ValueError):
            self.s.reverse_finance_settlement(
                self.other,
                title["id"],
                partial["settlements"][0]["id"],
                partial["snapshot_hash"],
                "Teste",
            )
        self.assertEqual(self.s.list_finance_titles(self.c), [partial])

    def test_concurrent_settlements_cannot_overpay(self):
        title = self.title("0.30")

        def run(key):
            with AccountingStore(self.path) as store:
                try:
                    return store.settle_finance_title(
                        self.c,
                        title["id"],
                        "0.20",
                        "2026-09-20",
                        "R",
                        "Teste",
                        key,
                        title["snapshot_hash"],
                    )["balance"]
                except ValueError:
                    return "stale"

        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(run, ["first", "second"]))
        self.assertCountEqual(results, ["0.10", "stale"])
        self.assertEqual(len(self.s.list_finance_titles(self.c)[0]["settlements"]), 1)

    def test_cancellation_preserves_original_and_requires_reversed_settlements(self):
        title = self.title()
        paid = self.settle(title)
        with self.assertRaisesRegex(ValueError, "Estorne"):
            self.s.cancel_finance_title(
                self.c, title["id"], paid["snapshot_hash"], "Teste"
            )
        reversed = self.s.reverse_finance_settlement(
            self.c,
            title["id"],
            paid["settlements"][0]["id"],
            paid["snapshot_hash"],
            "Teste",
        )
        canceled = self.s.cancel_finance_title(
            self.c, title["id"], reversed["snapshot_hash"], "Título incorreto sintético"
        )
        self.assertEqual(
            (canceled["status"], canceled["amount"], canceled["balance"]),
            ("cancelado", "100.30", "0.00"),
        )
        self.assertEqual(len(canceled["settlements"]), 1)
        with self.assertRaisesRegex(ValueError, "cancelado"):
            self.settle(canceled, "1", "new")
        self.assertEqual(
            self.s.cancel_finance_title(
                self.c,
                title["id"],
                reversed["snapshot_hash"],
                "Título incorreto sintético",
            ),
            canceled,
        )

    def test_migration_from_seven_preserves_existing_workspace(self):
        self.s.db.execute("DROP TABLE finance_settlements")
        self.s.db.execute("DROP TABLE finance_titles")
        self.s.db.execute("UPDATE schema_version SET version=7")
        self.s.db.commit()
        with AccountingStore(self.path) as upgraded:
            self.assertEqual(
                upgraded.db.execute("SELECT version FROM schema_version").fetchone()[0],
                12,
            )
            self.assertEqual(upgraded.list_periods(self.c)[0]["id"], self.p)
            self.assertEqual(upgraded.list_finance_titles(self.c), [])
            self.assertEqual(upgraded.list_manual_journals(self.c), [])

    def test_csv_escapes_text_and_filters_period(self):
        title = self.title()
        self.settle(title)
        report = self.s.finance_file(self.c, self.p)
        rows = list(csv.DictReader(io.StringIO(report["content"].decode("utf-8-sig"))))
        self.assertEqual(rows[0]["reference"], "'=SINTETICO")
        self.assertEqual((rows[0]["paid"], rows[0]["balance"]), ("0.10", "100.20"))
        self.assertEqual(self.s.finance_file(self.other)["content"].count(b"\r\n"), 1)


if __name__ == "__main__":
    unittest.main()
