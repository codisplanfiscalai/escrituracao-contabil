"""Financeiro também funciona no servidor HTTP local sem serviços externos."""

import unittest
import test_local_app as helpers


class FinanceLocalTests(unittest.TestCase):
    setUp = helpers.LocalApplicationTests.setUp
    tearDown = helpers.LocalApplicationTests.tearDown
    start_server = helpers.LocalApplicationTests.start_server
    stop_server = helpers.LocalApplicationTests.stop_server
    request = helpers.LocalApplicationTests.request
    api = helpers.LocalApplicationTests.api
    company = helpers.LocalApplicationTests.company

    def test_title_settlement_csv_and_restart(self):
        company = self.company()["id"]
        period = self.api(
            "periods",
            {
                "company_id": company,
                "reference_competence": "2026-08",
                "processing_competence": "2026-09",
            },
        )["id"]
        body = {
            "company_id": company,
            "period_id": period,
            "direction": "pagar",
            "reference": "Ref",
            "counterparty": "Sintético",
            "due_date": "2026-09-20",
            "amount": "100.30",
            "reason": "Teste",
            "request_key": "local-title",
        }
        title = self.api("finance-titles", body)
        self.assertEqual(
            self.request(
                "/api/finance-titles", "POST", body, headers={"X-Local-Token": None}
            )[0],
            403,
        )
        title = self.api(
            "finance-settlements",
            {
                "company_id": company,
                "title_id": title["id"],
                "amount": "40.10",
                "paid_date": "2026-09-20",
                "reference": "B1",
                "reason": "Teste",
                "request_key": "local-paid",
                "snapshot_hash": title["snapshot_hash"],
            },
        )
        self.assertEqual(title["balance"], "60.20")
        status, headers, content = self.request(
            f"/api/finance-file?company_id={company}&period_id={period}"
        )
        self.assertEqual(status, 200, content)
        self.assertIn("attachment;", headers["Content-Disposition"])
        self.assertIn(b"60.20", content)
        self.stop_server()
        self.start_server()
        self.assertEqual(self.api(f"finance-titles?company_id={company}"), [title])
