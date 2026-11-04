import unittest

from src.contract_safety import (
    AccountingLineIdentity,
    ImportState,
    RunScope,
    assert_unique_idempotency_keys,
    idempotency_key,
    may_retry_unknown_outcome,
    may_start_first_import,
    validate_competence,
)


class CompetenceTests(unittest.TestCase):
    def test_reference_and_processing_months_remain_distinct(self):
        scope = RunScope("2026-08", "2026-09")
        self.assertTrue(scope.accepts_document_month("2026-09"))
        self.assertFalse(scope.accepts_document_month("2026-08"))
        self.assertFalse(scope.accepts_document_month("2026-10"))

    def test_rejects_invalid_month(self):
        with self.assertRaises(ValueError):
            validate_competence("2026-13")


class AccountingIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.identity = AccountingLineIdentity(
            company_scope_alias="empresa-teste",
            processing_competence="2026-09",
            source_document_key="documento-sintetico-001",
            mapping_version="mapa-sintetico-v1",
            posting_group="grupo-sintetico-a",
            line_id="linha-sintetica-01",
        )

    def test_same_line_has_same_stable_key(self):
        self.assertEqual(idempotency_key(self.identity), idempotency_key(self.identity))

    def test_distinct_accounting_lines_have_distinct_keys(self):
        other_line = AccountingLineIdentity(
            **{**self.identity.__dict__, "line_id": "linha-sintetica-02"}
        )
        self.assertNotEqual(idempotency_key(self.identity), idempotency_key(other_line))

    def test_duplicate_key_in_batch_is_rejected(self):
        key = idempotency_key(self.identity)
        with self.assertRaises(ValueError):
            assert_unique_idempotency_keys([key, key])

    def test_missing_identity_component_is_rejected(self):
        incomplete = AccountingLineIdentity(
            company_scope_alias="empresa-teste",
            processing_competence="2026-09",
            source_document_key="documento-sintetico-001",
            mapping_version="",
            posting_group="grupo-sintetico-a",
            line_id="linha-sintetica-01",
        )
        with self.assertRaises(ValueError):
            idempotency_key(incomplete)


class ImportStateTests(unittest.TestCase):
    def test_only_first_reviewed_import_is_startable(self):
        self.assertTrue(may_start_first_import(ImportState.REVIEWED, 0))
        self.assertFalse(may_start_first_import(ImportState.REVIEWED, 1))
        self.assertFalse(may_start_first_import(ImportState.CONFIRMED, 0))

    def test_unknown_or_completed_result_cannot_be_blindly_retried(self):
        for state in (
            ImportState.STARTED,
            ImportState.UNKNOWN,
            ImportState.CONFIRMED,
            ImportState.RECONCILIATION_PENDING,
            ImportState.RECONCILED,
            ImportState.REJECTED,
        ):
            with self.subTest(state=state):
                self.assertFalse(may_retry_unknown_outcome(state))


if __name__ == "__main__":
    unittest.main()

