"""Comprehensive integration tests for PMS domain services and workflows."""

import datetime
import decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from modules.pms.domain.constants import (
    STATUS_APPROVED,
    STATUS_ASSIGNMENT_OFFERED,
    STATUS_ATTORNEY_ASSIGNED,
    STATUS_AWAITING_APPLICANT_APPROVAL,
    STATUS_BUDGET_APPROVED,
    STATUS_BUDGET_ESCALATED,
    STATUS_FILED,
    STATUS_GRANTED,
    STATUS_NEEDS_REVISION,
    STATUS_OFFICE_ACTION_RECORDED,
    STATUS_REJECTED,
    STATUS_REMANDED_FOR_AMENDMENT,
    STATUS_RESUBMITTED,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_WITHDRAWN,
)
from modules.pms.domain.exceptions import (
    ConflictOfInterestError,
    ValidationError,
)
from modules.pms.models import (
    AttorneyPanel,
    DeadlineTracking,
    PatentAuditLog,
)
from modules.pms.services.applications import (
    revise_and_resubmit_application,
    submit_patent_application,
    withdraw_patent_application,
)
from modules.pms.services.attorneys import (
    assign_attorney_to_application,
    record_patentability_assessment,
    respond_to_attorney_assignment,
)
from modules.pms.services.budget import (
    create_or_update_budget,
    decide_patent_budget,
)
from modules.pms.services.deadlines import evaluate_deadlines_and_alerts
from modules.pms.services.documents import upload_application_document
from modules.pms.services.filings import record_external_patent_filing
from modules.pms.services.licensing_appeals import (
    file_patent_appeal,
    review_patent_appeal,
)
from modules.pms.services.maintenance import (
    initialize_post_grant_patent,
    record_maintenance_payment,
    record_maintenance_renewal_decision,
    request_maintenance_renewal_decision,
)
from modules.pms.services.office_actions import (
    approve_office_action_response,
    prepare_office_action_response,
    record_office_action,
    submit_office_action_response,
)
from modules.pms.services.reviews import (
    assign_director_to_application,
    record_director_review,
)


@pytest.mark.django_db
class TestApplicationSubmissionAndLifecycle:
    def test_full_bw_01_submission_assignment_approval(self):
        # 1. Applicant submits
        app = submit_patent_application(
            user_id=1001,
            title="Graphene Supercapacitor",
            abstract="High density energy storage.",
            description="Detailed embodiment of electrode synthesis...",
            claims="Claim 1: A supercapacitor with graphene nanosheets...",
            domain="Nanotechnology",
            inventors_data=[
                {
                    "name": "Dr. Raman",
                    "email": "raman@institute.ac.in",
                    "department": "Nanotechnology",
                    "is_lead": True,
                    "share_percentage": decimal.Decimal("70.00"),
                    "user_id": 1001,
                },
                {
                    "name": "Student Arjun",
                    "email": "arjun@institute.ac.in",
                    "department": "Nanotechnology",
                    "is_lead": False,
                    "share_percentage": decimal.Decimal("30.00"),
                    "user_id": 1002,
                },
            ],
        )
        assert app.status == STATUS_SUBMITTED
        assert app.application_no.startswith("PMS-")
        assert app.inventors.count() == 2

        # 2. PCC_ADMIN assigns eligible Director
        assignment = assign_director_to_application(
            application=app,
            director_user_id=9001,
            assigned_by_user_id=8888,
        )
        assert app.status == STATUS_UNDER_REVIEW
        assert assignment.status == "assigned"

        # 3. Director approves with valid justification >= 50 chars
        justification = (
            "The technical claims demonstrate novelty, inventive step, "
            "and strong commercial applicability in power systems."
        )
        assert len(justification) >= 50
        review = record_director_review(
            application=app,
            director_user_id=9001,
            decision="approve",
            justification=justification,
        )
        assert app.status == STATUS_APPROVED
        assert review.decision == "approve"

        # Verify audit logs generated
        logs = PatentAuditLog.objects.filter(application=app)
        assert logs.count() >= 3

    def test_director_conflict_of_interest_blocked(self):
        app = submit_patent_application(
            user_id=1001,
            title="AI Co-pilot",
            abstract="Abstract...",
            description="Description...",
            claims="Claims...",
            domain="CSE",
            inventors_data=[
                {
                    "name": "Director Dave",
                    "email": "dave@institute.ac.in",
                    "department": "CSE",
                    "is_lead": True,
                    "share_percentage": decimal.Decimal("100.00"),
                    "user_id": 9005,
                }
            ],
        )
        with pytest.raises(ConflictOfInterestError, match="Conflict of interest"):
            assign_director_to_application(
                application=app,
                director_user_id=9005,  # Dave is inventor!
                assigned_by_user_id=8888,
            )

    def test_bw_02_revision_resubmission_loop(self):
        app = submit_patent_application(
            user_id=1001,
            title="Biofuel Reactor",
            abstract="Abstract...",
            description="Description...",
            claims="Claims...",
            domain="Biotech",
        )
        assign_director_to_application(app, director_user_id=9001, assigned_by_user_id=8888)

        # Director requests revision
        record_director_review(
            application=app,
            director_user_id=9001,
            decision="needs_revision",
            justification="Please expand claim 2 and provide additional experimental yield data.",
        )
        assert app.status == STATUS_NEEDS_REVISION
        assert app.revision_deadline is not None

        # Applicant revises and resubmits
        revise_and_resubmit_application(
            application=app,
            user_id=1001,
            description="Expanded description with experimental yield tables...",
            claims="Claim 1: ... Claim 2: Detailed biofuel formulation...",
            revision_notes="Addressed experimental yields in Section 4.",
        )
        assert app.status == STATUS_RESUBMITTED

    def test_bw_16_withdrawal_before_filing(self):
        app = submit_patent_application(
            user_id=1001,
            title="Drone Sensor",
            abstract="Abstract...",
            description="Description...",
            claims="Claims...",
            domain="Aerospace",
        )
        withdraw_patent_application(app, user_id=1001, reason="Commercial interest discontinued.")
        assert app.status == STATUS_WITHDRAWN


@pytest.mark.django_db
class TestAttorneyAndBudgetWorkflow:
    def test_bw_06_and_07_attorney_assignment_and_response(self):
        # Create approved app
        app = submit_patent_application(
            user_id=1001,
            title="Smart Grid Switch",
            abstract="Abstract...",
            description="Description...",
            claims="Claims...",
            domain="Electrical",
        )
        assign_director_to_application(app, director_user_id=9001, assigned_by_user_id=8888)
        record_director_review(
            app,
            director_user_id=9001,
            decision="approve",
            justification="Meets all requirements for patent filing and institutional sponsorship.",
        )
        assert app.status == STATUS_APPROVED

        # Setup attorney panel
        AttorneyPanel.objects.create(
            user_id=7001,
            name="Adv. Mehra",
            firm_name="Mehra IP Law",
            email="mehra@iplaw.in",
            specialization="Electrical & Electronics",
            is_active=True,
            max_workload=5,
            current_workload=0,
        )

        # 1. PCC_ADMIN offers assignment (BW-PMS-06)
        assign = assign_attorney_to_application(
            application=app,
            attorney_user_id=7001,
            assigned_by_user_id=8888,
        )
        assert app.status == STATUS_ASSIGNMENT_OFFERED
        assert assign.status == "offered"

        # 2. Attorney accepts
        respond_to_attorney_assignment(
            assign, attorney_user_id=7001, accept=True, remarks="Accepted."
        )
        assert app.status == STATUS_ATTORNEY_ASSIGNED

        # Record patentability assessment
        assessment = record_patentability_assessment(
            application=app,
            attorney_user_id=7001,
            recommendation="file_patent",
            novelty_analysis="Novel switching mechanism.",
            inventive_step_analysis="Non-obvious over US456789.",
            utility_analysis="High utility in transmission grids.",
            prior_art_summary="2 related patents reviewed.",
            opinion_text="Recommend complete patent filing in IN and PCT.",
        )
        assert assessment.recommendation == "file_patent"

    def test_bw_08_and_10_budget_approval_and_escalation(self):
        app = submit_patent_application(
            user_id=1001,
            title="AI Chip",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="CSE",
        )
        assign_director_to_application(app, 9001, 8888)
        record_director_review(
            app, 9001, "approve", "Approved after technical committee review and clearance."
        )

        # Create budget under threshold
        budget = create_or_update_budget(
            application=app,
            filing_fees=10000,
            attorney_fees=20000,
            administrative_costs=5000,
            user_id=8888,
        )
        assert budget.total_cost == decimal.Decimal("35000.00")

        # Approve budget (BW-PMS-08)
        decide_patent_budget(
            app,
            director_user_id=9001,
            decision="approve",
            justification="Standard budget approved.",
        )
        assert app.status == STATUS_BUDGET_APPROVED

        # App 2: Exceeding threshold -> Auto-escalate (BW-PMS-10)
        app2 = submit_patent_application(
            user_id=1001,
            title="International Rocket Engine",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="Mechanical",
        )
        assign_director_to_application(app2, 9001, 8888)
        record_director_review(
            app2, 9001, "approve", "Approved by space engineering review panel for patenting."
        )

        create_or_update_budget(
            app2, filing_fees=60000, attorney_fees=80000, administrative_costs=20000, user_id=8888
        )
        decide_patent_budget(app2, director_user_id=9001, decision="approve")
        assert app2.status == STATUS_BUDGET_ESCALATED
        assert app2.budget.status == "escalated"


@pytest.mark.django_db
class TestFilingAndOfficeActions:
    def test_bw_11_and_cw_03_filing_to_office_action(self):
        app = submit_patent_application(
            user_id=1001,
            title="Water Purifier",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="Civil",
        )
        assign_director_to_application(app, 9001, 8888)
        record_director_review(
            app, 9001, "approve", "High social relevance and clear technical novelty demonstrated."
        )

        AttorneyPanel.objects.create(
            user_id=7002,
            name="Adv. Sen",
            firm_name="Sen IP",
            email="sen@ip.com",
            specialization="Civil & Environmental",
            is_active=True,
        )
        assign = assign_attorney_to_application(app, 7002, 8888)
        respond_to_attorney_assignment(assign, 7002, True)

        record_patentability_assessment(
            app,
            7002,
            "file_patent",
            "Novel filter.",
            "Inventive filter membrane.",
            "Applicable.",
            "No prior art.",
            "File now.",
        )
        create_or_update_budget(app, 10000, 20000, 5000, 8888)
        decide_patent_budget(app, 9001, "approve", "Budget cleared.")

        # Complete agreements
        app.agreements.all().update(status="completed")

        # 1. External Filing (BW-PMS-11)
        record = record_external_patent_filing(
            application=app,
            attorney_user_id=7002,
            jurisdiction="IN",
            filing_number="202611099999",
            filing_date=timezone.now().date(),
            patent_office="IPO Delhi",
            confirmation_details="CBR No. 7788",
        )
        assert app.status == STATUS_FILED
        assert record.filing_number == "202611099999"

        # 2. Office Action Received (CW-PMS-03, BW-PMS-12)
        oa = record_office_action(
            application=app,
            attorney_user_id=7002,
            action_number="FER-01",
            issue_date=timezone.now().date(),
            response_deadline=timezone.now().date() + datetime.timedelta(days=60),
            action_type="FER",
            description="Prior art cited against claim 1.",
        )
        assert app.status == STATUS_OFFICE_ACTION_RECORDED

        # 3. Attorney prepares response requiring applicant review (BR-PMS-146)
        resp = prepare_office_action_response(
            office_action=oa,
            attorney_user_id=7002,
            draft_text="Draft arguments distinguishing cited art.",
            requires_applicant_approval=True,
        )
        assert app.status == STATUS_AWAITING_APPLICANT_APPROVAL

        # Cannot submit before applicant approval (BR-PMS-146)
        with pytest.raises(ValidationError, match="Applicant review and approval is required"):
            submit_office_action_response(resp, attorney_user_id=7002)

        # Applicant approves
        approve_office_action_response(resp, applicant_user_id=1001)

        # Attorney submits
        submit_office_action_response(
            resp, attorney_user_id=7002, submission_details="Submitted to IPO portal."
        )
        assert resp.submitted_at is not None


@pytest.mark.django_db
class TestPostGrantAndAppeals:
    def test_bw_14_and_15_post_grant_maintenance(self):
        app = submit_patent_application(
            user_id=1001,
            title="Electric Motor",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="Electrical",
        )
        app.status = STATUS_FILED
        app.save()

        # Grant patent
        pg = initialize_post_grant_patent(
            application=app,
            patent_number="IN999001",
            grant_date=timezone.now().date(),
            attorney_user_id=7001,
        )
        assert app.status == STATUS_GRANTED
        assert pg.schedules.count() == 18  # Years 3 to 20

        # Cycle renewal request
        first_sched = pg.schedules.first()
        request_maintenance_renewal_decision(first_sched, attorney_user_id=7001)

        # Director decides Renew (BW-PMS-14)
        record_maintenance_renewal_decision(
            first_sched,
            director_user_id=9001,
            decision="renew",
            justification="High commercial value.",
        )

        # Attorney records payment
        record_maintenance_payment(
            first_sched, attorney_user_id=7001, payment_reference="CHQ-888999"
        )
        assert first_sched.status == "renewed"
        assert app.status == STATUS_GRANTED

    def test_bw_03_rejection_and_appeal_remand(self):
        app = submit_patent_application(
            user_id=1001,
            title="Algorithm",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="CSE",
        )
        assign_director_to_application(app, 9001, 8888)
        record_director_review(
            app, 9001, "reject", "The claimed subject matter is purely abstract mathematical steps."
        )
        assert app.status == STATUS_REJECTED

        # File appeal
        appeal = file_patent_appeal(
            application=app,
            applicant_user_id=1001,
            grounds="Technical effect in image compression.",
            justification="The claims embody hardware transformation, not abstract math.",
        )
        assert app.status == "appeal_submitted"

        # Director remands for amendment (BW-PMS-03)
        review_patent_appeal(
            appeal=appeal,
            director_user_id=9001,
            outcome="remand_for_amendment",
            justification="Remanded to allow applicant to specify hardware codec constraints.",
        )
        assert app.status == STATUS_REMANDED_FOR_AMENDMENT


@pytest.mark.django_db
class TestDocumentAndDeadlines:
    def test_document_upload_and_versioning(self):
        app = submit_patent_application(
            user_id=1001,
            title="Biopolymer",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="Chemical",
        )
        # Put into needs_revision to permit applicant upload (BR-PMS-087)
        app.status = STATUS_NEEDS_REVISION
        app.save()

        pdf_bytes = b"%PDF-1.4 sample content with valid header."
        pdf_file = SimpleUploadedFile("claims_v1.pdf", pdf_bytes, content_type="application/pdf")

        doc1 = upload_application_document(
            application=app,
            uploaded_file=pdf_file,
            document_type="claims",
            title="Claims v1",
            uploaded_by_user_id=1001,
        )
        assert doc1.version == 1

        # Upload v2
        pdf_file2 = SimpleUploadedFile("claims_v2.pdf", pdf_bytes, content_type="application/pdf")
        doc2 = upload_application_document(
            application=app,
            uploaded_file=pdf_file2,
            document_type="claims",
            title="Claims v2",
            uploaded_by_user_id=1001,
        )
        assert doc2.version == 2

    def test_deadline_monitoring_sweep(self):
        app = submit_patent_application(
            user_id=1001,
            title="Battery",
            abstract="Abs...",
            description="Desc...",
            claims="Claims...",
            domain="Energy",
        )
        now = timezone.now()

        # 1. Deadline in 20 days -> triggers 30-day alert
        DeadlineTracking.objects.create(
            application=app,
            deadline_type="director_review",
            due_date=now + datetime.timedelta(days=20),
        )

        # 2. Deadline in 10 days -> triggers 15-day alert
        DeadlineTracking.objects.create(
            application=app,
            deadline_type="revision",
            due_date=now + datetime.timedelta(days=10),
        )

        # 3. Deadline in 2 days -> triggers 5-day alert
        DeadlineTracking.objects.create(
            application=app,
            deadline_type="office_action",
            due_date=now + datetime.timedelta(days=2),
        )

        # 4. Overdue deadline -> triggers escalation
        DeadlineTracking.objects.create(
            application=app,
            deadline_type="maintenance",
            due_date=now - datetime.timedelta(days=3),
        )

        stats = evaluate_deadlines_and_alerts()
        assert stats["alerts_30"] == 1
        assert stats["alerts_15"] == 1
        assert stats["alerts_5"] == 1
        assert stats["escalations"] == 1
