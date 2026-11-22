"""Tests for patents services layer (Step 4.4)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    CoInventor,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
)
from modules.patents.services import (
    applicant_approve_response,
    create_application,
    decide_budget,
    draft_response,
    log_office_action,
    record_budget_entry,
    record_coinventor_consent,
    register_panel_member,
    review_tech_transfer_request,
    submit_response,
    submit_tech_transfer_request,
    transition_application,
    update_application,
    upload_document,
)

pytestmark = pytest.mark.django_db


def applicant_actor(user_id=101):
    return make_principal(
        user_id=user_id,
        kind="student",
        roles=("student",),
        active_role="student",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE, p.P_APPLICATION_UPDATE),
    )


def director_actor(user_id=201):
    return make_principal(
        user_id=user_id,
        kind="faculty",
        roles=("Director",),
        active_role="Director",
        modules=("patents",),
        permissions=(
            p.P_APPLICATION_VIEW,
            p.P_APPLICATION_REVIEW,
            p.P_APPLICATION_DECIDE_APPEAL,
            p.P_BUDGET_APPROVE,
            p.P_MAINTENANCE_DECIDE,
            p.P_TECH_TRANSFER_REVIEW,
        ),
    )


def attorney_actor(user_id=301):
    return make_principal(
        user_id=user_id,
        kind="external",
        roles=("attorney",),
        active_role="attorney",
        modules=("patents",),
        permissions=(
            p.P_APPLICATION_VIEW,
            p.P_ATTORNEY_RESPOND_ASSIGNMENT,
            p.P_ASSESSMENT_PERFORM,
            p.P_FILING_RECORD,
            p.P_OFFICE_ACTION_RECORD,
            p.P_OFFICE_ACTION_RESPOND,
        ),
    )


def pcc_admin_actor(user_id=401):
    return make_principal(
        user_id=user_id,
        kind="staff",
        roles=("pcc_admin",),
        active_role="pcc_admin",
        modules=("patents",),
        permissions=(
            p.P_APPLICATION_VIEW,
            p.P_APPLICATION_ASSIGN_DIRECTOR,
            p.P_ATTORNEY_ASSIGN,
            p.P_PANEL_MANAGE,
            p.P_AUDIT_VIEW,
        ),
    )


def test_create_and_update_application():
    app = applicant_actor(101)
    application = create_application(
        actor=app,
        title="Novel Quantum Computing Architecture",
        abstract="A fault-tolerant qubit configuration.",
        description="Detailed specification of quantum topology.",
        claims="1. A quantum circuit comprising...",
        domain_category="Quantum",
        co_inventors=[
            {"user_id": 102, "name": "Alice", "email": "a@ex.com", "share_percentage": 50.0},
            {"user_id": 103, "name": "Bob", "email": "b@ex.com", "share_percentage": 50.0},
        ],
    )
    assert application.status == sm.DRAFT
    assert application.version == 1
    assert application.co_inventors.count() == 2

    # Update application
    updated = update_application(
        actor=app,
        application_id=application.id,
        title="Updated Quantum Architecture",
    )
    assert updated.title == "Updated Quantum Architecture"
    assert updated.version == 2


def test_co_inventor_consent():
    app = applicant_actor(101)
    application = create_application(
        actor=app,
        title="Test App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        co_inventors=[
            {"user_id": 102, "name": "Alice", "email": "a@ex.com", "share_percentage": 100.0},
        ],
    )
    co_actor = applicant_actor(102)
    assert record_coinventor_consent(co_actor, application.id) is True
    ci = CoInventor.objects.get(application=application, user_id=102)
    assert ci.consent_granted is True


def test_state_transitions_happy_path():
    app_actor = applicant_actor(101)
    adm_actor = pcc_admin_actor(401)
    dir_actor = director_actor(201)
    att_actor = attorney_actor(301)

    # 1. Create and submit
    app = create_application(
        actor=app_actor,
        title="Patent Lifecycle App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
    )
    app = transition_application(app.id, "submit", app_actor)
    assert app.status == sm.SUBMITTED

    # 2. Assign Director (PCC_ADMIN)
    app = transition_application(
        app.id, "assign_director", adm_actor, payload={"director_id": 201}
    )
    assert app.status == sm.UNDER_REVIEW
    assert app.assigned_director_id == 201

    # 3. Director Review (Approve with >= 50 char justification)
    app = transition_application(
        app.id,
        "submit_review",
        dir_actor,
        payload={
            "decision": "APPROVE",
            "justification": "This invention meets all standard criteria for novelty and industrial applicability.",
        },
    )
    assert app.status == sm.APPROVED

    # 4. Register attorney and assign
    register_panel_member(adm_actor, user_id=301, firm_name="IP Partners")
    app = transition_application(
        app.id, "assign_attorney", adm_actor, payload={"attorney_id": 301}
    )
    assert app.status == sm.ASSIGNMENT_OFFERED
    assert app.assigned_attorney_id == 301

    # 5. Attorney accepts
    app = transition_application(app.id, "accept_assignment", att_actor)
    assert app.status == sm.ATTORNEY_ASSIGNED

    # 6. Start assessment
    app = transition_application(app.id, "start_assessment", att_actor)
    assert app.status == sm.ASSESSMENT_IN_PROGRESS

    # Record approved budget entry
    budget_request = record_budget_entry(adm_actor, app.id, "APPROVAL", "50000.00", "filing")
    decide_budget(adm_actor, budget_request.id, "APPROVE")
    assert PatentBudgetLedger.objects.filter(application=app, status="APPROVED").exists()

    # 7. File external
    app = transition_application(
        app.id, "file_external", att_actor, payload={"external_filing_id": "IPO-9999"}
    )
    assert app.status == sm.FILED
    assert app.external_filing_id == "IPO-9999"


def test_attorney_decline_goes_to_pending_review():
    adm_actor = pcc_admin_actor(401)
    att_actor = attorney_actor(301)

    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0099",
        title="Decline Test",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        assigned_attorney_id=301,
        status=sm.ASSIGNMENT_OFFERED,
    )
    app = transition_application(app.id, "decline_assignment", att_actor)
    assert app.status == sm.PENDING_REVIEW

    # Admin reassigns back to ASSIGNMENT_OFFERED per BW-PMS-07 rows 2 and 3
    register_panel_member(adm_actor, user_id=302, firm_name="Second IP")
    app = transition_application(
        app.id, "assign_attorney", adm_actor, payload={"attorney_id": 302}
    )
    assert app.status == sm.ASSIGNMENT_OFFERED


def test_withdrawal_fails_if_status_not_eligible():
    app_actor = applicant_actor(101)
    PatentPolicy.objects.create(withdrawal_eligible_states=["DRAFT"], is_active=True)

    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0100",
        title="Withdrawal Test",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.SUBMITTED,
    )
    with pytest.raises(ConflictError):
        transition_application(app.id, "withdraw", app_actor, payload={"reason": "Changing strategy"})


def test_document_upload_and_budget():
    app_actor = applicant_actor(101)
    dir_actor = director_actor(201)
    PatentPolicy.objects.create(cost_escalation_threshold=Decimal("20000.00"), is_active=True)

    app = create_application(app_actor, "Doc App", "Abs", "Desc", "Claims")

    # Document upload
    doc = upload_document(
        app_actor,
        app.id,
        document_type="specification",
        file_name="spec.pdf",
        file_bytes=b"%PDF-1.4 mock content",
        storage_path="/var/docs/spec.pdf",
    )
    assert doc.file_format == "pdf"
    assert doc.version == 1

    # Budget entry exceeding threshold escalates
    entry = record_budget_entry(app_actor, app.id, "ESTIMATE", "25000.00", "prior_art")
    assert entry.status == "PENDING"

    decided = decide_budget(dir_actor, entry.id, "APPROVE")
    assert decided.status == "ESCALATED"  # Exceeds 20000 threshold


def test_office_action_and_tech_transfer():
    app_actor = applicant_actor(101)
    att_actor = attorney_actor(301)
    dir_actor = director_actor(201)

    app = create_application(app_actor, "OA App", "Abs", "Desc", "Claims")

    # Log office action
    oa = log_office_action(
        app_actor,
        app.id,
        action_code="FER-1",
        issuing_authority="IPO",
        issued_date=timezone.now().date(),
        response_deadline=timezone.now().date(),
        requires_applicant_review=True,
    )
    assert oa.status == "RECORDED"

    # Draft response
    oa = draft_response(att_actor, oa.id, "Response to objection 1.")
    assert oa.status == "AWAITING_APPLICANT"

    # Applicant approve response
    oa = applicant_approve_response(app_actor, oa.id)
    assert oa.status == "RESPONSE_READY"

    # Submit response
    oa = submit_response(att_actor, oa.id)
    assert oa.status == "SUBMITTED"

    # Tech transfer
    tt = submit_tech_transfer_request(app_actor, app.id, "licensing", "Global Corp")
    assert tt.status == "SUBMITTED"

    tt = review_tech_transfer_request(dir_actor, tt.id, "APPROVED", "Approved on standard terms")
    assert tt.status == "APPROVED"
