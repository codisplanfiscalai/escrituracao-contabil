"""Permissões do financeiro e downloads com escopo por empresa."""

import unittest
from server import test_identity_portal as helpers


class FinancePortalTests(unittest.TestCase):
    setUp = helpers.PortalTests.setUp
    tearDown = helpers.PortalTests.tearDown
    post = helpers.PortalTests.post
    create_company = helpers.PortalTests.create_company
    other_client = helpers.PortalTests.other_client

    def test_write_review_scope_and_csv_download(self):
        company = self.create_company()
        other = self.create_company("Outra sintética")

        def admin(route, body):
            response = self.client.post(
                "/api/" + route,
                json={"company_id": company, **body},
                headers=self.headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()["data"]

        period = admin(
            "periods",
            {"reference_competence": "2026-08", "processing_competence": "2026-09"},
        )["id"]
        self.post(
            "users",
            {
                "name": "Operador sintético",
                "email": "finance@example.test",
                "password": self.password,
                "role": "accountant",
                "companies": [company],
            },
        )
        operator, headers = self.other_client("finance@example.test")
        self.addCleanup(operator.close)
        payload = {
            "company_id": company,
            "period_id": period,
            "direction": "receber",
            "reference": "SINTETICO",
            "counterparty": "Fictício",
            "due_date": "2026-09-20",
            "amount": "10.30",
            "reason": "Teste",
            "request_key": "portal-title",
        }
        response = operator.post("/api/finance-titles", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        title = response.json()["data"]
        response = operator.post(
            "/api/finance-settlements",
            json={
                "company_id": company,
                "title_id": title["id"],
                "amount": "0.10",
                "paid_date": "2026-09-20",
                "reference": "Ref",
                "reason": "Teste",
                "request_key": "portal-paid",
                "snapshot_hash": title["snapshot_hash"],
            },
            headers=headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        title = response.json()["data"]
        reversal = {
            "company_id": company,
            "title_id": title["id"],
            "settlement_id": title["settlements"][0]["id"],
            "snapshot_hash": title["snapshot_hash"],
            "reason": "Correção sintética",
        }
        self.assertEqual(
            operator.post(
                "/api/finance-reversal", json=reversal, headers=headers
            ).status_code,
            403,
        )
        self.assertEqual(admin("finance-reversal", reversal)["balance"], "10.30")
        self.assertEqual(
            operator.get(
                "/api/finance-titles", params={"company_id": other}
            ).status_code,
            403,
        )
        cancellation = {
            "company_id": company,
            "title_id": title["id"],
            "snapshot_hash": admin("finance-reversal", reversal)["snapshot_hash"],
            "reason": "Cancelamento sintético",
        }
        self.assertEqual(
            operator.post(
                "/api/finance-cancel", json=cancellation, headers=headers
            ).status_code,
            403,
        )
        self.assertEqual(admin("finance-cancel", cancellation)["status"], "cancelado")
        report = operator.get(
            "/api/finance-file", params={"company_id": company, "period_id": period}
        )
        self.assertEqual(report.status_code, 200, report.text)
        self.assertIn("attachment;", report.headers["content-disposition"])
        self.assertIn("10.30", report.text)
        self.assertEqual(
            operator.get("/api/finance-file", params={"company_id": other}).status_code,
            403,
        )
        self.assertEqual(
            operator.post("/api/finance-titles", json=payload).status_code, 403
        )
