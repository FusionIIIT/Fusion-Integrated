"""Model creation and relationship tests for PMS.

Maps to:
- CFR-PMS-005, CFR-PMS-007, CFR-PMS-009, CFR-PMS-011, CFR-PMS-012, CFR-PMS-013, CFR-PMS-014, CFR-PMS-016, CFR-PMS-017, CFR-PMS-018, CFR-PMS-019, CFR-PMS-020, CFR-PMS-023, CFR-PMS-024, CFR-PMS-028
- BR-PMS-131 (Exactly one active PCC_ADMIN constraint)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    ApplicationDocument,
    AttorneyAssignment,
    AttorneyPanel,
    CoInventor,
    DirectorReview,
    LicensingRequest,
    OfficeAction,
    PatentabilityAssessment,
    PatentAppeal,
    PatentApplication,
    PatentBudget,
    PatentLegalAdvice,
    PmsAuditTrail,
    PmsNotificationOutbox,
    PmsRoleAssignment,
    PostGrantMaintenance,
    PriorArtReference,
)

pytestmark = pytest.mark.django_db


def test_patent_application_creation():
    """Verify PatentApplication model fields, defaults, and string representation."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0001",
        title="Novel Quantum Computing Architecture",
        abstract="A system and method for error-tolerant quantum circuits.",
        detailed_description="Full technical specification...",
        claims="1. An error-tolerant quantum circuit...",
        domain="Computer Science",
        status=PatentApplicationStatus.SUBMITTED.value,
        applicant_user_id=1001,
        jurisdiction="IN",
    )
    assert app.pk is not None
    assert app.status == PatentApplicationStatus.SUBMITTED.value
    assert str(app) == "PMS-2026-0001: Novel Quantum Computing Architecture (submitted)"
    assert app.is_withdrawn is False
    assert app.is_international is False


def test_patent_application_unique_application_no():
    """Application number must be strictly unique."""
    PatentApplication.objects.create(
        application_no="PMS-UNIQUE-01",
        title="App 1",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Tech",
        applicant_user_id=1001,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        PatentApplication.objects.create(
            application_no="PMS-UNIQUE-01",
            title="App 2",
            abstract="Abstract 2",
            detailed_description="Desc 2",
            claims="Claims 2",
            domain="Tech",
            applicant_user_id=1002,
        )


def test_coinventor_relationship_and_cascade():
    """Co-inventors belong to a patent application and cascade delete with it."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0002",
        title="Bio-Mechanical Sensor",
        abstract="Sensor abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Biotechnology",
        applicant_user_id=1001,
    )
    inv1 = CoInventor.objects.create(
        application=app,
        user_id=1002,
        name="Dr. Vikram Sarabhai",
        email="vikram@institute.edu",
        department="Bioengineering",
        ownership_percentage=Decimal("60.00"),
        consent_given=True,
        agreement_signed=True,
    )
    inv2 = CoInventor.objects.create(
        application=app,
        user_id=1003,
        name="Dr. Homi Bhabha",
        email="homi@institute.edu",
        department="Physics",
        ownership_percentage=Decimal("40.00"),
        consent_given=True,
    )

    assert app.coinventors.count() == 2
    assert "Dr. Vikram Sarabhai" in str(inv1)

    app_id = app.id
    app.delete()
    assert CoInventor.objects.filter(application_id=app_id).count() == 0


def test_application_document_versioning():
    """Documents support versioning and current version flag."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0003",
        title="AI Algorithm",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="AI",
        applicant_user_id=1001,
    )
    doc_v1 = ApplicationDocument.objects.create(
        application=app,
        doc_type="specification",
        title="Specification Document v1",
        file_format="pdf",
        file_size_bytes=2048,
        version=1,
        is_current=False,
        uploaded_by_user_id=1001,
    )
    doc_v2 = ApplicationDocument.objects.create(
        application=app,
        doc_type="specification",
        title="Specification Document v2",
        file_format="pdf",
        file_size_bytes=4096,
        version=2,
        is_current=True,
        uploaded_by_user_id=1001,
    )

    assert app.documents.count() == 2
    assert app.documents.filter(is_current=True).get().version == 2


def test_director_review_relationship():
    """Director review records decision, justification, and relationship to application."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0004",
        title="Solar Cell Efficiency",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Energy",
        applicant_user_id=1001,
    )
    review = DirectorReview.objects.create(
        application=app,
        director_user_id=2001,
        decision="Approve",
        justification="The technical novelty and institutional relevance are clearly demonstrated.",
        feedback="Proceed to patent drafting.",
    )
    assert app.director_reviews.count() == 1
    assert "Approve" in str(review)


def test_patent_budget_one_to_one():
    """Patent application has a 1-to-1 relationship with its budget."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0005",
        title="Robotic Gripper",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Robotics",
        applicant_user_id=1001,
    )
    budget = PatentBudget.objects.create(
        application=app,
        filing_fees=Decimal("15000.00"),
        attorney_fees=Decimal("25000.00"),
        administrative_costs=Decimal("5000.00"),
        total_cost=Decimal("45000.00"),
        status="pending_approval",
    )
    assert app.budget.total_cost == Decimal("45000.00")
    assert "pending_approval" in str(budget)


def test_attorney_assignment_and_panel():
    """AttorneyPanel and AttorneyAssignment models."""
    panel_entry = AttorneyPanel.objects.create(
        attorney_user_id=3001,
        name="Adv. Meera Sen",
        firm_name="Sen & Associates IP",
        email="meera@senip.com",
        is_approved=True,
        expertise_domains=["Computer Science", "Electronics"],
        current_workload=2,
        max_workload=8,
    )
    assert panel_entry.is_approved is True
    assert "Adv. Meera Sen" in str(panel_entry)

    app = PatentApplication.objects.create(
        application_no="PMS-2026-0006",
        title="Semiconductor Layer",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Electronics",
        applicant_user_id=1001,
    )
    assignment = AttorneyAssignment.objects.create(
        application=app,
        attorney_user_id=3001,
        assigned_by_user_id=9001,
        status="offered",
        is_active=True,
    )
    assert app.attorney_assignments.count() == 1
    assert assignment.status == "offered"


def test_patentability_assessment_and_legal_advice():
    """Patentability assessment and legal advice models."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0007",
        title="Optical Fiber Sensor",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Photonics",
        applicant_user_id=1001,
    )
    assessment = PatentabilityAssessment.objects.create(
        application=app,
        attorney_user_id=3001,
        novelty_score=9,
        non_obviousness_score=8,
        utility_score=10,
        recommendation="File Patent",
        opinion_text="Strong patentability profile.",
    )
    assert "File Patent" in str(assessment)

    advice = PatentLegalAdvice.objects.create(
        application=app,
        attorney_user_id=3001,
        stage="pre-filing",
        advice_text="Ensure all claims are supported by experimental data.",
    )
    assert "pre-filing" in str(advice)


def test_prior_art_and_office_action():
    """PriorArtReference and OfficeAction models."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0008",
        title="Graphene Membrane",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Materials",
        applicant_user_id=1001,
    )
    ref = PriorArtReference.objects.create(
        application=app,
        source="Google Patents",
        reference_id="US9876543B2",
        title="Graphene filtration membrane",
        authors="Smith et al.",
        relevance="high",
        attached_by_user_id=1001,
    )
    assert "US9876543B2" in str(ref)

    oa = OfficeAction.objects.create(
        application=app,
        action_type="First Examination Report (FER)",
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 12, 1),
        details="Objection under section 3(d).",
        status="recorded",
    )
    assert "FER" in str(oa)


def test_post_grant_maintenance():
    """PostGrantMaintenance model for renewal cycles."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0009",
        title="Water Purifier",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Environmental",
        applicant_user_id=1001,
        status="granted",
        patent_number="IN456789",
    )
    maint = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date(2029, 9, 1),
        fee_amount=Decimal("5000.00"),
        maintenance_status="scheduled",
    )
    assert "Cycle 1" in str(maint)


def test_licensing_and_appeal_models():
    """LicensingRequest and PatentAppeal models."""
    app = PatentApplication.objects.create(
        application_no="PMS-2026-0010",
        title="Drone Control System",
        abstract="Abstract",
        detailed_description="Desc",
        claims="Claims",
        domain="Aerospace",
        applicant_user_id=1001,
    )
    lic = LicensingRequest.objects.create(
        application=app,
        requested_by_user_id=1001,
        licensee_name="AeroDynamics Ltd",
        request_type="exclusive",
        commercial_terms="5% royalty on gross revenue",
    )
    assert "AeroDynamics Ltd" in str(lic)

    appeal = PatentAppeal.objects.create(
        application=app,
        applicant_user_id=1001,
        grounds="Director overlooked comparative experimental data.",
        justification="The comparative analysis in Appendix B clearly establishes non-obviousness.",
    )
    assert "appeal" in str(appeal).lower()


def test_audit_trail_and_notification_outbox():
    """PmsAuditTrail and PmsNotificationOutbox models."""
    audit = PmsAuditTrail.objects.create(
        actor_user_id=1001,
        action_type="application_submitted",
        from_state="draft",
        to_state="submitted",
        details={"app": "PMS-001"},
    )
    assert audit.is_immutable is True
    assert "application_submitted" in str(audit)

    notif = PmsNotificationOutbox.objects.create(
        topic="application.submitted",
        dedupe_key="notif-key-01",
        recipient_user_id=1001,
        subject="Application Received",
        body="Your application has been received.",
    )
    assert notif.status == "pending"
    assert "application.submitted" in str(notif)


def test_exactly_one_active_pcc_admin_constraint():
    """BR-PMS-131: PMS maintains exactly one active PCC_ADMIN oversight role."""
    PmsRoleAssignment.objects.create(
        user_id=9001,
        role="PCC_ADMIN",
        is_active=True,
    )

    # Attempting to create a second active PCC_ADMIN must violate the UniqueConstraint
    with pytest.raises(IntegrityError), transaction.atomic():
        PmsRoleAssignment.objects.create(
            user_id=9002,
            role="PCC_ADMIN",
            is_active=True,
        )

    # An inactive PCC_ADMIN can exist alongside the active one
    inactive = PmsRoleAssignment.objects.create(
        user_id=9003,
        role="PCC_ADMIN",
        is_active=False,
    )
    assert inactive.pk is not None
