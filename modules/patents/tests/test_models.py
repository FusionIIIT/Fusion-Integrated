from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    AppealRecord,
    ApplicationDocument,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
    ReviewDecision,
    TechnologyTransferRecord,
)


@pytest.mark.django_db
def test_create_patent_application():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0001",
        title="Novel Solar Cell",
        abstract="A highly efficient perovskite solar cell design.",
        description="Detailed description of fabrication and chemical layers.",
        claims="1. A solar cell comprising perovskite layers...",
        status=sm.DRAFT,
        domain_category="Renewable Energy",
    )
    assert app.id is not None
    assert app.applicant_user_id == 101
    assert app.version == 1
    assert app.jurisdiction == "IN"


@pytest.mark.django_db
def test_unique_application_number():
    PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0002",
        title="Title 1",
        abstract="Abstract 1",
        description="Desc 1",
        claims="Claim 1",
    )
    with pytest.raises(IntegrityError):
        PatentApplication.objects.create(
            user_id=102,
            application_number="PMS-2026-0002",
            title="Title 2",
            abstract="Abstract 2",
            description="Desc 2",
            claims="Claim 2",
        )


@pytest.mark.django_db
def test_co_inventor_and_share_constraint():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0003",
        title="Battery Tech",
        abstract="Solid-state battery",
        description="Description",
        claims="Claims",
    )
    ci = CoInventor.objects.create(
        application=app,
        user_id=102,
        name="Dr. Jane Smith",
        email="jane@example.com",
        share_percentage=Decimal("40.00"),
    )
    assert ci.id is not None
    assert ci.consent_granted is False

    with pytest.raises(IntegrityError):
        CoInventor.objects.create(
            application=app,
            name="Invalid Share",
            email="invalid@example.com",
            share_percentage=Decimal("150.00"),
        )


@pytest.mark.django_db
def test_application_document_size_constraint():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0004",
        title="App Doc Test",
        abstract="Abstract",
        description="Description",
        claims="Claims",
    )
    doc = ApplicationDocument.objects.create(
        application=app,
        document_type="specification",
        file_name="spec.pdf",
        file_format="pdf",
        file_size_bytes=1048576,
        storage_path="/uploads/patents/spec.pdf",
        uploaded_by_user_id=101,
    )
    assert doc.id is not None
    assert doc.version == 1

    with pytest.raises(IntegrityError):
        ApplicationDocument.objects.create(
            application=app,
            document_type="huge",
            file_name="huge.pdf",
            file_format="pdf",
            file_size_bytes=60000000,
            storage_path="/uploads/patents/huge.pdf",
            uploaded_by_user_id=101,
        )


@pytest.mark.django_db
def test_review_decision_and_appeal_records():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0005",
        title="App Review Test",
        abstract="Abstract",
        description="Description",
        claims="Claims",
        status=sm.UNDER_REVIEW,
    )
    review = ReviewDecision.objects.create(
        application=app,
        director_user_id=201,
        decision="Reject",
        justification="The technical novelty threshold is not met based on prior art analysis.",
    )
    assert review.id is not None

    appeal = AppealRecord.objects.create(
        application=app,
        applicant_user_id=101,
        grounds="The prior art citation relates to silicon, not perovskite crystal structures.",
    )
    assert appeal.id is not None
    assert appeal.status == "SUBMITTED"


@pytest.mark.django_db
def test_attorney_panel_member():
    panel_member = AttorneyPanelMember.objects.create(
        user_id=301,
        firm_name="IP Juris Partners",
        expertise_domains=["Renewable Energy", "Materials Science"],
        active_workload=2,
    )
    assert panel_member.is_approved_panel is True

    with pytest.raises(IntegrityError):
        AttorneyPanelMember.objects.create(
            user_id=301,
            firm_name="Duplicate Firm",
        )


@pytest.mark.django_db
def test_budget_ledger_and_office_actions():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0006",
        title="Budget Test",
        abstract="Abstract",
        description="Description",
        claims="Claims",
        status=sm.APPROVED,
    )
    entry = PatentBudgetLedger.objects.create(
        application=app,
        entry_type="APPROVAL",
        amount=Decimal("25000.00"),
        category="filing_fee",
        status="APPROVED",
        authorized_by_user_id=201,
        notes="Official filing fee allocated.",
    )
    assert entry.id is not None
    assert entry.currency == "INR"

    oa = OfficeActionRecord.objects.create(
        application=app,
        action_code="FER-2026-01",
        issuing_authority="Indian Patent Office",
        issued_date=date(2026, 6, 1),
        response_deadline=date(2026, 12, 1),
        requires_applicant_review=True,
    )
    assert oa.status == "RECORDED"


@pytest.mark.django_db
def test_tech_transfer_and_policy():
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0007",
        title="Tech Transfer Test",
        abstract="Abstract",
        description="Description",
        claims="Claims",
        status=sm.GRANTED,
    )
    tt = TechnologyTransferRecord.objects.create(
        application=app,
        applicant_user_id=101,
        request_type="Licensing",
        partner_name="Solar Solutions Corp",
        status="SUBMITTED",
        terms_summary="Exclusive regional manufacturing license.",
    )
    assert tt.id is not None

    pol = PatentPolicy.objects.create(
        director_review_days=15,
        revision_resubmission_days=60,
        cost_escalation_threshold=Decimal("150000.00"),
        withdrawal_eligible_states=["draft", "submitted"],
    )
    assert pol.is_active is True
    assert pol.cost_escalation_threshold == Decimal("150000.00")
