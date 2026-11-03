from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.pms.models import (
    Application,
    ApplicationDocument,
    ApplicationInventorAgreement,
    AttorneyAssignment,
    AttorneyProfile,
    BudgetProposal,
    DirectorProfile,
    Inventor,
    PmsAuditEvent,
)
from modules.pms.services import workflows


class PmsWorkflowTests(TestCase):
    def setUp(self):
        self.applicant_id = 101
        self.director_id = 202
        self.attorney_id = 303
        self.app = Application.objects.create(
            applicant_user_id=self.applicant_id,
            title="Novel thermal storage design",
            abstract="A thermal storage method.",
            detailed_description="Detailed technical description.",
            claims="1. A system comprising a storage chamber.",
            technical_domain="Energy",
        )
        self.inventor = Inventor.objects.create(
            user_id=self.applicant_id, full_name="Applicant One", email="applicant@example.test"
        )
        ApplicationInventorAgreement.objects.create(
            application=self.app,
            inventor=self.inventor,
            ownership_percent=Decimal("100.00"),
            agreement_status="accepted",
            consent_recorded_at=timezone.now(),
        )
        self.clean_document()

    def clean_document(self):
        return ApplicationDocument.objects.create(
            application=self.app,
            uploaded_by_user_id=self.applicant_id,
            document_type="initial_filing",
            sensitivity="internal",
            file="pms/test.pdf",
            original_filename="test.pdf",
            content_type="application/pdf",
            size_bytes=5,
            version=1,
            malware_scan_status="clean",
        )

    def test_submission_creates_history_and_review_assignment(self):
        submitted = workflows.submit_application(self.app.pk, self.applicant_id)
        self.assertEqual(submitted.status, Application.Status.SUBMITTED)
        self.assertIsNotNone(submitted.submitted_at)
        self.assertEqual(submitted.transitions.get().action, "application_submitted")
        self.assertTrue(PmsAuditEvent.objects.filter(action="application_submitted").exists())

    def test_submission_rejects_missing_or_unclean_documents(self):
        self.app.documents.all().delete()
        with self.assertRaises(ValidationError):
            workflows.submit_application(self.app.pk, self.applicant_id)
        self.app.documents.create(
            uploaded_by_user_id=self.applicant_id,
            document_type="initial_filing",
            sensitivity="internal",
            file="pms/test.pdf",
            original_filename="test.pdf",
            content_type="application/pdf",
            size_bytes=5,
            version=1,
            malware_scan_status="pending",
        )
        with self.assertRaises(ValidationError):
            workflows.submit_application(self.app.pk, self.applicant_id)

    def test_director_conflict_and_expertise_are_enforced(self):
        self.app.status = Application.Status.SUBMITTED
        self.app.save(update_fields=["status"])
        DirectorProfile.objects.create(user_id=self.director_id, expertise_domains=["Energy"])
        inventor_profile = DirectorProfile.objects.create(
            user_id=self.applicant_id, expertise_domains=["Energy"]
        )
        with self.assertRaises(ValidationError):
            workflows.assign_director(self.app.pk, inventor_profile.user_id, 999)
        other = DirectorProfile.objects.create(user_id=404, expertise_domains=["Chemistry"])
        with self.assertRaises(ValidationError):
            workflows.assign_director(self.app.pk, other.user_id, 999)
        app = workflows.assign_director(self.app.pk, self.director_id, 999)
        self.assertEqual(app.status, Application.Status.UNDER_REVIEW)
        self.assertEqual(app.assigned_director_user_id, self.director_id)

    def test_director_decision_requires_50_characters(self):
        self.app.status = Application.Status.UNDER_REVIEW
        self.app.assigned_director_user_id = self.director_id
        self.app.review_due_at = timezone.now() + timedelta(days=2)
        self.app.save()
        with self.assertRaises(ValidationError):
            workflows.review_application(self.app.pk, self.director_id, "approved", "Too short")
        app = workflows.review_application(
            self.app.pk,
            self.director_id,
            "approved",
            "The claims describe a clear technical contribution and meet review requirements.",
        )
        self.assertEqual(app.status, Application.Status.APPROVED)
        self.assertEqual(app.transitions.count(), 1)

    def test_expired_revision_is_marked_expired(self):
        self.app.status = Application.Status.NEEDS_REVISION
        self.app.revision_due_at = timezone.now() - timedelta(seconds=1)
        self.app.save()
        app = workflows.resubmit_revision(
            self.app.pk, self.applicant_id, "We revised the description."
        )
        app.refresh_from_db()
        self.assertEqual(app.status, Application.Status.EXPIRED)

    def test_attorney_assignment_preserves_approved_application_state(self):
        self.app.status = Application.Status.APPROVED
        self.app.save(update_fields=["status"])
        AttorneyProfile.objects.create(
            user_id=self.attorney_id, panel_approved=True, expertise_domains=["Energy"]
        )
        assignment = workflows.assign_attorney(self.app.pk, self.attorney_id, 505)
        self.assertEqual(assignment.status, AttorneyAssignment.Status.OFFERED)
        workflows.respond_to_attorney_assignment(assignment.pk, self.attorney_id, True)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, Application.Status.APPROVED)
        budget = workflows.propose_budget(
            self.app.pk,
            self.applicant_id,
            {
                "filing_fees": Decimal("1000"),
                "attorney_fees": Decimal("2000"),
                "administrative_costs": Decimal("100"),
            },
        )
        self.assertEqual(budget.status, BudgetProposal.Status.PROPOSED)

    def test_filing_requires_budget_and_agreements(self):
        self.app.status = Application.Status.ATTORNEY_ASSIGNED
        self.app.assigned_attorney_user_id = self.attorney_id
        self.app.save()
        AttorneyProfile.objects.create(
            user_id=self.attorney_id, panel_approved=True, expertise_domains=["Energy"]
        )
        AttorneyAssignment.objects.create(
            application=self.app,
            attorney_user_id=self.attorney_id,
            assigned_by_user_id=606,
            status=AttorneyAssignment.Status.ACCEPTED,
        )
        with self.assertRaises(ValidationError):
            workflows.record_filing(
                self.app.pk,
                self.attorney_id,
                jurisdiction="India",
                external_filing_id="IN-123",
                filing_date=timezone.localdate(),
            )

    def test_application_history_and_audit_events_are_immutable(self):
        event = PmsAuditEvent.objects.create(
            actor_user_id=self.applicant_id, application=self.app, action="test"
        )
        with self.assertRaises(DjangoValidationError):
            event.delete()
