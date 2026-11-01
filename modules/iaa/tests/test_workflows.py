from types import SimpleNamespace
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError
from modules.iaa.models import IAAExpenseRequest, IAAApproval, IAAAuditEvent
from modules.iaa.services.workflows import submit_expense, decide_expense

class IAAWorkflowTests(TestCase):
    def setUp(self):
        self.claimant = SimpleNamespace(user_id=101)
        self.reviewer = SimpleNamespace(user_id=202)
        self.request = IAAExpenseRequest.objects.create(claimant_user_id=101,
            request_type="expense", title="Travel reimbursement", amount="1250.00",
            financial_year="2026-27")
    def test_submit_locks_record_and_writes_audit(self):
        submit_expense(self.request, self.claimant)
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, "submitted")
        self.assertIsNotNone(self.request.locked_at)
        self.assertTrue(IAAAuditEvent.objects.filter(action="submitted").exists())
    def test_claimant_cannot_approve_own_request(self):
        submit_expense(self.request, self.claimant)
        with self.assertRaises(PermissionDenied):
            decide_expense(self.request, self.claimant, decision="approved", remarks="OK")
    def test_decision_requires_remarks_and_records_actor(self):
        submit_expense(self.request, self.claimant)
        with self.assertRaises(ValidationError):
            decide_expense(self.request, self.reviewer, decision="approved", remarks="")
        decide_expense(self.request, self.reviewer, decision="approved", remarks="Verified")
        self.assertEqual(IAAApproval.objects.get().approver_user_id, 202)
        self.assertEqual(IAAExpenseRequest.objects.get().status, "approved")
