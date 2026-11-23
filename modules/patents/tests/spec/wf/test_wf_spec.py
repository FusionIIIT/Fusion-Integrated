"""Spec tests for patents, WF (workflow) strategy.

Generated from the frozen docs/11-patents/spec-tests/WF_DESIGN.json (27 cases).
Every test carries its test_id and source_id in its name and docstring.

Behaviour is driven through the module's public interfaces: the HTTP API where an
endpoint exists, otherwise the service layer (e.g. `submit`/`resubmit` transitions and
`submit_response`, which have no endpoint). Preconditions that place an application in a
given state are seeded directly, as the module's own journey tests do.

Refusal status codes, where the design names none, come from
docs/01-architecture/api-conventions.md "Status codes": 409 for "the world is in the
wrong state" (illegal transition, unmet record prerequisite), 422 for invalid input or a
policy-based business-rule refusal.
"""
from __future__ import annotations

import datetime
import itertools
import json
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import DomainError
from fusion_auth.client import UserRef
from modules.patents import registry
from modules.patents import selectors as sel
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    AppealRecord,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
)
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import office_actions as oa_service

pytestmark = pytest.mark.django_db

API = "/api/v1/patents"

APPLICANT_ID = 101
COINVENTOR_ID = 102
DIRECTOR_ID = 201
ATTORNEY_A_ID = 401
ATTORNEY_B_ID = 402
ADMIN_ID = 901

ROLE_OF = {
    "applicant": ("student", registry.ROLE_GRANTS["student"]),
    "director": ("director", registry.ROLE_GRANTS["Director"]),
    "attorney": ("attorney", registry.ROLE_GRANTS["attorney"]),
    "pcc_admin": ("pcc_admin", registry.ROLE_GRANTS["pcc_admin"]),
}

GOOD_JUSTIFICATION = (
    "Novelty, inventive step and industrial applicability are established for all claims."
)

_seq = itertools.count(1)


# -- Infrastructure -------------------------------------------------------------


def principal(user_id: int, role: str):
    """A real Principal with the registry grants for `role`, for service-level calls."""
    code, perms = ROLE_OF[role]
    return make_principal(
        user_id=user_id, roles=(code,), active_role=code,
        permissions=tuple(perms), modules=("patents",),
    )


#: The identity service's directory: everyone who appears in these workflows has an email
#: address, which is where PMS-triggered notifications are sent (BR-PMS-116).
DIRECTORY = {
    uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
                 kind="faculty", email=f"u{uid}@example.edu")
    for uid in (101, 102, 201, 401, 402, 901)
}


@pytest.fixture
def api(stub_iam):
    """An APIClient plus a switch that makes IAM resolve the next requests as an actor."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    def as_(user_id: int, role: str) -> APIClient:
        code, perms = ROLE_OF[role]
        stub_iam(make_session(
            user_id=user_id, roles=(code,), active_role=code,
            permissions=tuple(perms), modules=("patents",),
        ), users=DIRECTORY)
        return client

    return as_


@pytest.fixture
def policy():
    def _make(withdrawal_states=(), threshold=Decimal("150000.00")):
        return PatentPolicy.objects.create(
            is_active=True,
            director_review_days=15,
            revision_resubmission_days=60,
            cost_escalation_threshold=threshold,
            max_attorney_workload=5,
            withdrawal_eligible_states=list(withdrawal_states),
        )
    return _make


def panel_attorney(user_id: int, workload: int = 0) -> AttorneyPanelMember:
    return AttorneyPanelMember.objects.create(
        user_id=user_id, firm_name=f"Firm {user_id}",
        expertise_domains=["Quantum"], is_approved_panel=True, active_workload=workload,
    )


def seed_application(status: str, **fields) -> PatentApplication:
    """Seed an application already in `status` (precondition set-up only)."""
    defaults = {
        "user_id": APPLICANT_ID,
        "application_number": f"PMS-WF-{next(_seq):04d}",
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
        "status": status,
    }
    defaults.update(fields)
    return PatentApplication.objects.create(**defaults)


def add_coinventor(app, consent: bool) -> CoInventor:
    return CoInventor.objects.create(
        application=app, user_id=COINVENTOR_ID, name="Dr. Sarah Rao",
        email="sarah.rao@example.edu", share_percentage=Decimal("100.00"),
        consent_granted=consent, consent_timestamp=timezone.now() if consent else None,
    )


def approve_budget(app, amount=Decimal("45000.00")) -> PatentBudgetLedger:
    """Precondition: a budget request decided Approved by the Director."""
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE", amount, "GOVERNMENT_FEE",
    )
    return budget_service.decide_budget(principal(DIRECTOR_ID, "director"), req.id, "APPROVE")


def mails_about(mailoutbox, app, start: int = 0) -> list:
    """Messages issued since `start` that concern this application."""
    marker = app.application_number
    return [
        m for m in mailoutbox[start:]
        if marker in (m.subject or "") or marker in (m.body or "")
    ]


def audit_entries(api, app) -> list[str]:
    """Audit log lines (PCC_ADMIN view) that concern this application."""
    resp = api(ADMIN_ID, "pcc_admin").get(f"{API}/audit-logs")
    assert resp.status_code == 200
    lines = [json.dumps(e, default=str) if not isinstance(e, str) else e
             for e in resp.data.get("audit_logs", [])]
    return [ln for ln in lines if app.application_number in ln or f"{app.id}" in ln]


def history_payload(api, app) -> str:
    """Everything the module exposes about the application's history: its detail
    (minus the current status) and its audit log lines."""
    detail = dict(api(ADMIN_ID, "pcc_admin").get(f"{API}/applications/{app.id}").data)
    detail.pop("status", None)
    return json.dumps(detail, default=str) + json.dumps(audit_entries(api, app))


def in_active_queue(app) -> bool:
    admin = principal(ADMIN_ID, "pcc_admin")
    queues = (
        sel.applications_pending_director_review(admin),
        sel.applications_pending_attorney_response(admin),
        sel.applications_in_assessment(admin),
    )
    return any(q.filter(pk=app.id).exists() for q in queues)


def refusal_status(fn) -> int | None:
    """Run a service call; return the refusal's HTTP status, or None if it was accepted."""
    try:
        fn()
    except DomainError as err:
        return err.status_code
    return None


# -- BW-PMS-01 / 02: review --------------------------------------------------------


def test_wf_t001_bw_pms_01_initial_review_approval_path(api, policy, mailoutbox):
    """WF-T001 | BW-PMS-01 initial review approval path.

    Draft/Not Submitted -> Submitted -> Under Review -> Approved, with notification of the
    Director and an audit log entry (previous and new state) for every status change.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    created = client.post(f"{API}/applications", {
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
        "co_inventors": [{"user_id": APPLICANT_ID, "name": "Asha Verma",
                          "email": "asha@example.edu", "share_percentage": "100.00"}],
    }, format="json")
    assert created.status_code == 201, created.data
    app_id = created.data["id"]
    pdf = SimpleUploadedFile("spec.pdf", b"%PDF-1.4\n" + b"0" * 2048, "application/pdf")
    up = client.post(f"{API}/applications/{app_id}/documents",
                     {"document_type": "specification", "file": pdf}, format="multipart")
    assert up.status_code == 201, up.data

    # 1) Applicant submits.
    app_service.transition_application(app_id, "submit", principal(APPLICANT_ID, "applicant"))
    app = PatentApplication.objects.get(pk=app_id)
    assert app.application_number
    assert PatentApplication.objects.filter(application_number=app.application_number).count() == 1
    assert app.status == sm.SUBMITTED

    # 2) PCC_ADMIN assigns the eligible Director.
    before = len(mailoutbox)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app_id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == sm.UNDER_REVIEW
    director_mails = mails_about(mailoutbox, app, before)

    # 3) Director approves with a >= 50 character justification.
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app_id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.APPROVED

    assert director_mails, "Director was not notified of the assignment"
    logs = audit_entries(api, app)
    for prev, new in ((sm.DRAFT, sm.SUBMITTED), (sm.SUBMITTED, sm.UNDER_REVIEW),
                      (sm.UNDER_REVIEW, sm.APPROVED)):
        assert any(prev in ln and new in ln for ln in logs), (
            f"no audit entry for {prev} -> {new}; audit log: {logs}")


def test_wf_t002_bw_pms_01_justification_guard_false(api, policy):
    """WF-T002 | BW-PMS-01 row 3 guard-false (justification < 50 characters).

    Approve with a 20-character justification is rejected with a validation error; the
    application stays Under Review and no Approved status is recorded.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": "Looks novel enough."}, format="json")
    assert len("Looks novel enough.") < 50
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert not app.reviews.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_wf_t003_bw_pms_02_revision_and_reapproval_path(api, policy):
    """WF-T003 | BW-PMS-02 revision and re-approval path.

    Under Review -> Needs Revision -> Resubmitted -> Under Review -> Approved; Applicant
    receives feedback, a new version is retained, a new review cycle starts.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    feedback = "Claim 1 overlaps prior art D1; narrow it to the resonator-coupled variant."

    # 1) Director records Needs Revision.
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "NEEDS_REVISION", "justification": feedback}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    seen = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert seen.status_code == 200
    assert any(r["justification"] == feedback for r in seen.data["reviews"]), (
        "Applicant does not receive the Director feedback")

    # 2) Applicant revises (within 60 days) and resubmits.
    version_before = app.version
    revised_claims = "1. A resonator-coupled circuit comprising at least five transmons."
    put = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}", {"claims": revised_claims}, format="json")
    assert put.status_code == 200, put.data
    app_service.transition_application(app.id, "resubmit", principal(APPLICANT_ID, "applicant"))
    app.refresh_from_db()
    assert app.status == sm.RESUBMITTED
    assert app.version > version_before
    assert app.claims == revised_claims

    # 3) PCC_ADMIN re-assigns an eligible Director: a new review cycle.
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert app.assigned_director_id == DIRECTOR_ID

    # 4) Director approves.
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.APPROVED


def test_wf_t004_bw_pms_02_resubmission_after_60_days(api, policy):
    """WF-T004 | BW-PMS-02 row 2 guard-false (resubmission after 60 days).

    Resubmission is refused; the application does not reach Resubmitted.
    """
    policy()
    app = seed_application(
        sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=61),
    )
    put = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}",
        {"claims": "1. A narrowed circuit of five coupled transmons."}, format="json")
    if put.status_code >= 400:
        refused = put.status_code
    else:
        refused = refusal_status(lambda: app_service.transition_application(
            app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
    app.refresh_from_db()
    assert app.status != sm.RESUBMITTED
    assert app.status == sm.NEEDS_REVISION
    assert refused is not None, "resubmission after 60 days was accepted"
    assert refused == 422


# -- BW-PMS-03..05: appeals ---------------------------------------------------------


def test_wf_t005_bw_pms_03_appeal_remand_path(api, policy):
    """WF-T005 | BW-PMS-03 appeal remand path.

    Under Review -> Rejected -> Appeal Submitted -> Remanded for Amendment; Applicant gets
    rejection feedback; the appeal outcome is recorded.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    reason = "The claimed layout is anticipated by D1 and lacks an inventive step overall."

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "REJECT", "justification": reason}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.REJECTED
    seen = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert any(r["justification"] == reason for r in seen.data["reviews"]), (
        "Applicant does not receive the rejection feedback")

    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/appeal",
        {"grounds": "D1 does not disclose resonator coupling.",
         "justification": "Claim 1 requires coupling absent from D1, so novelty holds."},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "REMAND"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.REMANDED
    appeal = app.appeals.order_by("-id").first()
    assert appeal.status == "REMAND"
    assert appeal.decided_at is not None
    assert appeal.director_user_id == DIRECTOR_ID


def _appeal_submitted_application():
    app = seed_application(
        sm.APPEAL_SUBMITTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=2),
    )
    AppealRecord.objects.create(
        application=app, applicant_user_id=APPLICANT_ID,
        grounds="D1 does not disclose resonator coupling.",
    )
    return app


def test_wf_t006_bw_pms_04_appeal_rejection_upheld_path(api, policy):
    """WF-T006 | BW-PMS-04 appeal rejection-upheld path.

    Uphold Rejection -> status Rejection Upheld; appeal outcome recorded.
    """
    policy()
    app = _appeal_submitted_application()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "UPHOLD"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.REJECTION_UPHELD
    appeal = app.appeals.order_by("-id").first()
    assert appeal.status == "UPHOLD"
    assert appeal.decided_at is not None


def test_wf_t007_bw_pms_05_appeal_modified_decision_path(api, policy):
    """WF-T007 | BW-PMS-05 appeal modified-decision path.

    Modify Decision -> status Decision Modified; appeal outcome recorded.
    """
    policy()
    app = _appeal_submitted_application()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "MODIFY"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.DECISION_MODIFIED
    appeal = app.appeals.order_by("-id").first()
    assert appeal.status == "MODIFY"
    assert appeal.decided_at is not None


# -- BW-PMS-06..07: attorney assignment ---------------------------------------------


def test_wf_t008_bw_pms_06_attorney_assignment_acceptance_path(api, policy, mailoutbox):
    """WF-T008 | BW-PMS-06 attorney assignment acceptance path.

    Approved -> Assignment Offered (Attorney notified) -> Attorney Assigned.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)

    before = len(mailoutbox)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == sm.ASSIGNMENT_OFFERED
    assert resp.data["assigned_attorney_id"] == ATTORNEY_A_ID
    attorney_mails = mails_about(mailoutbox, app, before)

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.ATTORNEY_ASSIGNED

    assert attorney_mails, "Attorney was not notified of the offered assignment"


def test_wf_t009_bw_pms_07_decline_reassign_accept_path(api, policy):
    """WF-T009 | BW-PMS-07 decline-reassign-accept path.

    Assignment Offered -> Pending Review -> Assignment Offered (B) -> Attorney Assigned (B).
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    panel_attorney(ATTORNEY_B_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)

    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert resp.status_code == 200, resp.data

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "decline"},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.PENDING_REVIEW

    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_B_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.ASSIGNMENT_OFFERED
    assert app.assigned_attorney_id == ATTORNEY_B_ID

    resp = api(ATTORNEY_B_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.ATTORNEY_ASSIGNED
    assert app.assigned_attorney_id == ATTORNEY_B_ID


# -- BW-PMS-08..10: budget ------------------------------------------------------------


def test_wf_t010_bw_pms_08_budget_approval_path(api, policy, mailoutbox):
    """WF-T010 | BW-PMS-08 budget approval path.

    Filing, attorney and administrative fees totalling below the threshold; Director
    approves: Budget Approved recorded, transaction record and authorization level logged,
    approval notification issued.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    admin = principal(ADMIN_ID, "pcc_admin")
    requests = [
        budget_service.record_budget_entry(admin, app.id, "FILING_FEE",
                                           Decimal("20000.00"), "GOVERNMENT_FEE"),
        budget_service.record_budget_entry(admin, app.id, "ATTORNEY_FEE",
                                           Decimal("60000.00"), "PROFESSIONAL_FEE"),
        budget_service.record_budget_entry(admin, app.id, "ADMIN_FEE",
                                           Decimal("5000.00"), "ADMINISTRATIVE"),
    ]
    assert sum(r.amount for r in requests) < Decimal("150000.00")

    before = len(mailoutbox)
    client = api(DIRECTOR_ID, "director")
    for req in requests:
        resp = client.post(f"{API}/applications/{app.id}/budget-decision",
                           {"decision": "APPROVE", "budget_entry_id": req.id}, format="json")
        assert resp.status_code == 200, resp.data
        assert resp.data["status"] == "APPROVED"

    decisions = PatentBudgetLedger.objects.filter(application=app, replaces_entry__in=requests)
    assert decisions.count() == 3
    for row in decisions:
        assert row.status == "APPROVED"
        assert row.authorized_by_user_id == DIRECTOR_ID
        assert row.entry_kind == "APPROVAL"   # authorization level: within Director authority
    assert not decisions.filter(entry_kind="ESCALATION").exists()

    assert mails_about(mailoutbox, app, before), "no budget approval notification was issued"


def test_wf_t011_bw_pms_09_budget_rejection_path(api, policy, mailoutbox):
    """WF-T011 | BW-PMS-09 budget rejection path.

    Director rejects: Budget Rejected recorded with no further escalation; rejection
    notification issued.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE",
        Decimal("45000.00"), "GOVERNMENT_FEE")

    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "REJECT", "budget_entry_id": req.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "REJECTED"
    rows = PatentBudgetLedger.objects.filter(application=app, replaces_entry=req)
    assert list(rows.values_list("status", flat=True)) == ["REJECTED"]
    assert not PatentBudgetLedger.objects.filter(
        application=app, entry_kind="ESCALATION").exists()

    assert mails_about(mailoutbox, app, before), "no budget rejection notification was issued"


def test_wf_t012_bw_pms_10_budget_escalation_path(api, policy):
    """WF-T012 | BW-PMS-10 budget escalation path.

    Approved -> Escalated -> Escalation Tracked / External Decision Pending. No
    PMS-internal higher-authority decision is recorded.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE",
        Decimal("200000.00"), "GOVERNMENT_FEE")
    assert req.amount > Decimal("150000.00")

    # 1) Director reviews the budget: above the threshold it is Escalated, not Approved.
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "APPROVE", "budget_entry_id": req.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "ESCALATED"
    assert PatentBudgetLedger.objects.get(pk=resp.data["id"]).entry_kind == "ESCALATION"
    assert not PatentBudgetLedger.objects.filter(application=app, status="APPROVED").exists()

    # 2) PCC_ADMIN handles/routes the escalated case within PMS scope.
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/budget-escalation",
        {"budget_entry_id": req.id, "notes": "Routed to the Board; decision is external."},
        format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "ESCALATION_TRACKED"
    assert not PatentBudgetLedger.objects.filter(application=app, status="APPROVED").exists()
    assert budget_service.approved_total(app.id) == Decimal("0")
    statuses = list(PatentBudgetLedger.objects.filter(
        application=app, replaces_entry=req).order_by("id").values_list("status", flat=True))
    assert statuses == ["ESCALATED", "ESCALATION_TRACKED"]


# -- BW-PMS-11: external filing ---------------------------------------------------------


def _filing_ready_application(consent: bool):
    """Approved, attorney assigned and working the case (status ASSESSMENT_IN_PROGRESS,
    the state the module files from), budget approved, inventor agreements per `consent`."""
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID, jurisdiction="PCT",
    )
    add_coinventor(app, consent=consent)
    approve_budget(app)
    return app


def test_wf_t013_bw_pms_11_international_filing_with_justification(api, policy, mailoutbox):
    """WF-T013 | BW-PMS-11 external filing path (international filing with justification).

    Attorney records an international filing: status Filed; external filing ID, filing
    date, confirmation and justification stored; filing confirmation notification issued.
    """
    policy()
    app = _filing_ready_application(consent=True)
    filing_date = timezone.now().date() - datetime.timedelta(days=1)
    payload = {
        "external_filing_id": "PCT/IN2026/050123",
        "filing_date": filing_date.isoformat(),
        "jurisdiction": "PCT",
        "filing_type": "international",
        "confirmation": "WIPO-RO-CONF-778812",
        "justification": "Commercial partners in EU and US justify PCT national-phase cost.",
    }

    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", payload, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == payload["external_filing_id"]
    assert app.filing_date == filing_date
    stored = history_payload(api, app)
    assert payload["confirmation"] in stored, "filing confirmation details not stored"
    assert payload["justification"] in stored, "international filing justification not stored"
    assert mails_about(mailoutbox, app, before), "no filing confirmation notification issued"


def test_wf_t014_bw_pms_11_filing_blocked_inventor_agreements_incomplete(api, policy):
    """WF-T014 | BW-PMS-11 guard-false (inventor agreements incomplete).

    Filing is refused; status does not become Filed.
    """
    policy()
    app = _filing_ready_application(consent=False)
    status_before = app.status
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing",
        {"external_filing_id": "IN202611000123"}, format="json")
    app.refresh_from_db()
    assert app.status != sm.FILED
    assert app.status == status_before
    assert app.external_filing_id == ""
    assert resp.status_code == 409, (resp.status_code, resp.data)


# -- BW-PMS-12..13: office actions ------------------------------------------------------


def _filed_application():
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        external_filing_id="IN202611000123", filing_date=timezone.now().date(),
    )


def _record_office_action(api, app, requires_review: bool):
    today = timezone.now().date()
    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/office-actions", {
        "action_code": "FER-1",
        "issuing_authority": "Indian Patent Office",
        "issued_date": today.isoformat(),
        "response_deadline": (today + datetime.timedelta(days=180)).isoformat(),
        "requires_applicant_review": requires_review,
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data["id"]


def test_wf_t015_bw_pms_12_office_action_with_applicant_review(api, policy, mailoutbox):
    """WF-T015 | BW-PMS-12 office-action response with Applicant review path.

    Office Action Recorded -> Awaiting Applicant Approval -> Applicant Approved -> Response
    Submitted; office-action notification issued; submission tracked.
    """
    policy()
    app = _filed_application()
    states = []

    before = len(mailoutbox)
    oa_id = _record_office_action(api, app, requires_review=True)
    states.append(OfficeActionRecord.objects.get(pk=oa_id).status)
    oa_mails = mails_about(mailoutbox, app, before)

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert resp.status_code == 200, resp.data
    states.append(OfficeActionRecord.objects.get(pk=oa_id).status)

    resp = api(APPLICANT_ID, "applicant").post(f"{API}/office-actions/{oa_id}/approve")
    assert resp.status_code == 200, resp.data
    states.append(OfficeActionRecord.objects.get(pk=oa_id).status)

    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    states.append(oa.status)

    # Design states: Office Action Recorded -> Awaiting Applicant Approval ->
    # Applicant Approved -> Response Submitted.
    assert states == ["RECORDED", "AWAITING_APPLICANT", "APPLICANT_APPROVED", "SUBMITTED"], (
        f"observed office-action states {states}")
    assert oa.submitted_at is not None
    assert oa_mails, "no office-action notification was issued"


def test_wf_t016_bw_pms_13_office_action_without_applicant_review(api, policy):
    """WF-T016 | BW-PMS-13 office-action response without Applicant review path.

    Office Action Recorded -> Response Ready -> Response Submitted, with no Awaiting
    Applicant Approval state.
    """
    policy()
    app = _filed_application()
    states = []

    oa_id = _record_office_action(api, app, requires_review=False)
    states.append(OfficeActionRecord.objects.get(pk=oa_id).status)

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert resp.status_code == 200, resp.data
    states.append(OfficeActionRecord.objects.get(pk=oa_id).status)

    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    states.append(oa.status)

    assert states == ["RECORDED", "RESPONSE_READY", "SUBMITTED"], states
    assert "AWAITING_APPLICANT" not in states
    assert oa.submitted_at is not None


# -- BW-PMS-14..15: maintenance ---------------------------------------------------------


def _granted_application():
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.GRANTED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        grant_date=timezone.now().date() - datetime.timedelta(days=700),
        renewal_due_date=timezone.now().date() + datetime.timedelta(days=20),
    )


def test_wf_t017_bw_pms_14_maintenance_renewal_path(api, policy):
    """WF-T017 | BW-PMS-14 maintenance renewal path.

    Granted -> Renewal Decision Requested -> Renewal Approved -> Renewed / Next Cycle
    Scheduled; a renewal history entry exists and the next cycle is scheduled.
    """
    policy()
    app = _granted_application()
    due_before = app.renewal_due_date
    next_due = due_before + datetime.timedelta(days=365)
    states = []

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, resp.data
    states.append(resp.data["maintenance_state"])

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": True}, format="json")
    assert resp.status_code == 200, resp.data
    states.append(resp.data["maintenance_state"])

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": "IPO-ANNUITY-2026-0042", "next_due_date": next_due.isoformat()},
        format="json")
    assert resp.status_code == 200, resp.data
    states.append(resp.data["maintenance_state"])

    assert states == ["DECISION_REQUESTED", "RENEWAL_APPROVED", "RENEWED"]
    app.refresh_from_db()
    assert app.status == sm.GRANTED
    history = list(app.renewal_history.all())
    assert len(history) == 1
    entry = history[0]
    assert entry.decision == "RENEW"
    assert entry.cycle_due_date == due_before
    assert entry.action_reference == "IPO-ANNUITY-2026-0042"
    assert entry.next_due_date == next_due
    assert app.renewal_due_date == next_due, "next maintenance cycle was not scheduled"


def test_wf_t018_bw_pms_15_maintenance_non_renewal_path(api, policy):
    """WF-T018 | BW-PMS-15 maintenance non-renewal path.

    Granted -> Renewal Decision Requested -> Do Not Renew; the outcome is recorded in
    renewal history, no maintenance action is recorded and no next cycle is scheduled.
    """
    policy()
    app = _granted_application()
    due_before = app.renewal_due_date

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["maintenance_state"] == "DECISION_REQUESTED"

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": False}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["maintenance_state"] == "DO_NOT_RENEW"

    app.refresh_from_db()
    entry = app.renewal_history.get()
    assert entry.decision == "DO_NOT_RENEW"
    assert entry.action_reference == "" and entry.action_recorded_at is None
    assert entry.next_due_date is None
    assert app.renewal_due_date == due_before, "a next cycle was scheduled after Do Not Renew"

    refused = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": "IPO-ANNUITY-2026-0043",
         "next_due_date": (due_before + datetime.timedelta(days=365)).isoformat()},
        format="json")
    assert refused.status_code == 409, refused.data
    assert app.renewal_history.count() == 1


# -- BW-PMS-16 / CW-PMS-05: withdrawal ---------------------------------------------------


def _withdraw(api, app, reason):
    return api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/withdraw", {"reason": reason}, format="json")


def test_wf_t019_bw_pms_16_withdrawal_from_submitted(api, policy):
    """WF-T019 | BW-PMS-16 withdrawal path (Submitted origin; CW-PMS-05 row 1).

    Withdrawn; removed from active queue; reason and co-inventor consent stored in
    withdrawal history; action audit-logged.
    """
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, consent=False)
    resp = api(COINVENTOR_ID, "applicant").post(f"{API}/applications/{app.id}/consent")
    assert resp.status_code == 200, resp.data
    assert resp.data["consent_recorded"] is True

    reason = "Withdrawing to fold this into a broader continuation filing."
    resp = _withdraw(api, app, reason)
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert not in_active_queue(app)

    stored = history_payload(api, app)
    assert reason in stored, "withdrawal reason not stored in withdrawal history"
    detail = api(ADMIN_ID, "pcc_admin").get(f"{API}/applications/{app.id}").data
    assert all(ci["consent_granted"] for ci in detail["co_inventors"]), (
        "co-inventor consent not stored")
    assert audit_entries(api, app), "withdrawal was not audit-logged"


def test_wf_t020_bw_pms_16_withdrawal_blocked_after_filing(api, policy):
    """WF-T020 | BW-PMS-16 guard-false (application already Filed).

    Withdrawal is refused; status remains Filed.
    """
    policy(withdrawal_states=sorted(sm.PRE_FILING_STATES))
    app = seed_application(sm.FILED, external_filing_id="IN202611000123",
                           filing_date=timezone.now().date())
    resp = _withdraw(api, app, "No longer commercially relevant.")
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert resp.status_code == 409, (resp.status_code, resp.data)


def _withdraw_from(api, policy, origin, **fields):
    policy(withdrawal_states=[origin])
    app = seed_application(origin, **fields)
    reason = f"Withdrawing from {origin}: inventors are pursuing a trade-secret strategy."
    resp = _withdraw(api, app, reason)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert not in_active_queue(app)
    stored = history_payload(api, app)
    assert reason in stored, "withdrawal history not recorded"
    assert origin in stored, f"withdrawal history does not record previous state {origin}"


def test_wf_t021_cw_pms_05_withdraw_from_under_review(api, policy):
    """WF-T021 | CW-PMS-05 row 2 (Under Review -> Withdrawn).

    Withdrawn, removed from active queue; withdrawal history records previous state.
    """
    _withdraw_from(api, policy, sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)


def test_wf_t022_cw_pms_05_withdraw_from_needs_revision(api, policy):
    """WF-T022 | CW-PMS-05 row 3 (Needs Revision -> Withdrawn).

    Withdrawn, removed from active queue; withdrawal history records previous state.
    """
    _withdraw_from(api, policy, sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
                   decision_date=timezone.now() - datetime.timedelta(days=3))


def test_wf_t023_cw_pms_05_withdraw_from_rejected(api, policy):
    """WF-T023 | CW-PMS-05 row 4 (Rejected -> Withdrawn).

    Withdrawn, removed from active queue; withdrawal history records previous state.
    """
    _withdraw_from(api, policy, sm.REJECTED, assigned_director_id=DIRECTOR_ID,
                   decision_date=timezone.now() - datetime.timedelta(days=3))


def test_wf_t024_cw_pms_05_withdraw_from_approved(api, policy):
    """WF-T024 | CW-PMS-05 row 5 (Approved -> Withdrawn).

    Withdrawn, removed from active queue; withdrawal history records previous state.
    """
    _withdraw_from(api, policy, sm.APPROVED, assigned_director_id=DIRECTOR_ID)


def test_wf_t025_cw_pms_05_withdraw_from_attorney_assigned(api, policy):
    """WF-T025 | CW-PMS-05 row 6 (Attorney Assigned -> Withdrawn).

    Withdrawn, removed from active queue; withdrawal history records previous state.
    """
    panel_attorney(ATTORNEY_A_ID, workload=1)
    _withdraw_from(api, policy, sm.ATTORNEY_ASSIGNED, assigned_director_id=DIRECTOR_ID,
                   assigned_attorney_id=ATTORNEY_A_ID)


def test_wf_t026_cw_pms_05_withdraw_from_pending_review(api, policy):
    """WF-T026 | CW-PMS-05 row 7 (Pending Review -> Withdrawn).

    Withdrawn, removed from active queue; withdrawal history records previous state.
    """
    _withdraw_from(api, policy, sm.PENDING_REVIEW, assigned_director_id=DIRECTOR_ID)


# -- CW-PMS-02: integrated pre-filing governance --------------------------------------------


def test_wf_t027_cw_pms_02_integrated_prefiling_governance_to_filing(api, policy):
    """WF-T027 | CW-PMS-02 row 9 integrated pre-filing governance to filing.

    Attorney acceptance and budget approval jointly enable a domestic (IPO) filing:
    Attorney Assigned and Budget Approved recorded; filing accepted; status Filed.
    """
    policy(threshold=Decimal("150000.00"))
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID, jurisdiction="IN")
    add_coinventor(app, consent=True)

    # 1) PCC_ADMIN assigns, Attorney accepts.
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.ATTORNEY_ASSIGNED

    # 2) Director approves the (within-threshold) budget.
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE",
        Decimal("45000.00"), "GOVERNMENT_FEE")
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "APPROVE", "budget_entry_id": req.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "APPROVED"

    # 3) Attorney records the domestic IPO filing.
    filing_date = timezone.now().date()
    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/filing", {
        "external_filing_id": "IN202611000777",
        "filing_date": filing_date.isoformat(),
        "jurisdiction": "IN",
        "filing_office": "Indian Patent Office",
        "confirmation": "IPO-ACK-2026-000777",
    }, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == "IN202611000777"
