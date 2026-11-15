from django.test import SimpleTestCase

from modules.patents.domain import workflow as wf


class DocumentRules(SimpleTestCase):
    def test_accepts_small_pdf(self):
        self.assertIsNone(wf.validate_document("application/pdf", 1024))

    def test_rejects_non_pdf(self):
        self.assertIsNotNone(wf.validate_document("image/png", 1024))

    def test_rejects_over_50_mb(self):
        self.assertIsNotNone(wf.validate_document("application/pdf", wf.DOCUMENT_MAX_BYTES + 1))

    def test_rejects_empty(self):
        self.assertIsNotNone(wf.validate_document("application/pdf", 0))


class OwnershipRules(SimpleTestCase):
    def test_shares_must_total_100(self):
        self.assertIsNone(wf.validate_ownership([60, 40]))
        self.assertIsNotNone(wf.validate_ownership([60, 30]))

    def test_no_inventors_is_an_error(self):
        self.assertIsNotNone(wf.validate_ownership([]))

    def test_zero_share_is_an_error(self):
        self.assertIsNotNone(wf.validate_ownership([100, 0]))


class StatusRules(SimpleTestCase):
    def test_revisable_states(self):
        self.assertIn(wf.NEEDS_REVISION, wf.REVISABLE)
        self.assertNotIn(wf.APPROVED, wf.REVISABLE)

    def test_withdrawal_excludes_filed(self):
        self.assertNotIn(wf.FILED, wf.WITHDRAWABLE)

    def test_every_status_has_a_label(self):
        for status in (wf.DRAFT, wf.FILED, wf.REMANDED):
            self.assertIn(status, wf.LABELS)

    def test_justification_minimum(self):
        self.assertEqual(wf.JUSTIFICATION_MIN, 50)
