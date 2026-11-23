"""Regression tests for defects found by the specification-based tests.

Each test cites the PMS specification obligation it protects.
"""
from __future__ import annotations

import datetime
import itertools
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import DomainError
from fusion_auth.client import UserRef
from modules.patents import registry
from modules.patents.domain import state_machine as sm
from modules.patents.domain import validation as val
from modules.patents.models import (
    AttorneyPanelMember,
    AuditImmutable,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentAuditLog,
    PatentPolicy,
)
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import maintenance as maint_service
from modules.patents.services import office_actions as oa_service

pytestmark = pytest.mark.django_db

API = "/api/v1/patents"
APPLICANT, DIRECTOR, ATTORNEY, ADMIN = 101, 201, 401, 901
LONG_TEXT = "Novelty, inventive step and industrial applicability are established for all claims."
_seq = itertools.count(1)

ROLES = {
    "applicant": ("student", registry.ROLE_GRANTS["student"]),
    "director": ("director", registry.ROLE_GRANTS["Director"]),
    "attorney": ("attorney", registry.ROLE_GRANTS["attorney"]),
    "pcc_admin": ("pcc_admin", registry.ROLE_GRANTS["pcc_admin"]),
}


def principal(user_id, role):
    code, perms = ROLES[role]
    return make_principal(
        user_id=user_id, roles=(code,), active_role=code,
        permissions=tuple(perms), modules=("patents",),
    )


#: People the identity service knows, with an email address, for notification tests.
DIRECTORY: dict[int, UserRef] = {}


@pytest.fixture(autouse=True)
def _clear_directory():
    DIRECTORY.clear()


@pytest.fixture
def api(stub_iam):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    def as_(user_id, role):
        code, perms = ROLES[role]
        stub_iam(make_session(
            user_id=user_id, roles=(code,), active_role=code,
            permissions=tuple(perms), modules=("patents",),
        ), users=DIRECTORY)
        return client

    return as_


@pytest.fixture
def policy():
    def _make(withdrawal_states=(), days=60):
        return PatentPolicy.objects.create(
            is_active=True, revision_resubmission_days=days,
            cost_escalation_threshold=Decimal("150000.00"), max_attorney_workload=5,
            withdrawal_eligible_states=list(withdrawal_states),
        )
    return _make


def seed(status, **fields):
    data = {
        "user_id": APPLICANT, "application_number": f"PMS-FIX-{next(_seq):04d}",
        "title": "Qubit layout", "abstract": "A surface-code layout.",
        "description": "Resonator coupling detail.", "claims": "1. A circuit.",
        "domain_category": "Quantum", "status": status,
    }
    data.update(fields)
    return PatentApplication.objects.create(**data)


def user_ref(user_id, email):
    DIRECTORY[user_id] = UserRef(
        user_id=user_id, username=f"u{user_id}", display_name=f"User {user_id}",
        kind="faculty", email=email,
    )


# -- Rule violations are refusals, not server errors (BR-PMS-026, BR-PMS-030) ------------


def test_short_justification_is_a_422_refusal(api, policy):
    """BR-PMS-030: fewer than 50 characters is refused as a validation error."""
    policy()
    app = seed(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR)
    resp = api(DIRECTOR, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": "Looks novel enough."}, format="json")
    assert resp.status_code == 422, resp.data
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW and not app.reviews.exists()


def test_conflicted_director_assignment_is_a_422_refusal(api, policy):
    """BR-PMS-026: assigning the applicant as reviewer is refused, not a 500."""
    policy()
    app = seed(sm.SUBMITTED)
    resp = api(ADMIN, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": APPLICANT},
        format="json")
    assert resp.status_code == 422, resp.data
    with pytest.raises(val.ConflictOfInterestError):
        app_service.transition_application(
            app.id, "assign_director", principal(ADMIN, "pcc_admin"),
            payload={"director_id": APPLICANT})


# -- 60-day resubmission window (BR-PMS-035) ------------------------------------------------


@pytest.mark.parametrize("status", [sm.NEEDS_REVISION, sm.REJECTED])
def test_resubmission_after_the_window_is_refused(api, policy, status):
    """BR-PMS-035: a revision after 60 days is refused, for edits and for resubmission."""
    policy()
    app = seed(status, decision_date=timezone.now() - datetime.timedelta(days=61))
    put = api(APPLICANT, "applicant").put(
        f"{API}/applications/{app.id}", {"claims": "1. A narrowed circuit."}, format="json")
    assert put.status_code == 422, put.data
    with pytest.raises(DomainError) as refused:
        app_service.transition_application(app.id, "resubmit", principal(APPLICANT, "applicant"))
    assert refused.value.code == "revision_deadline_expired"
    app.refresh_from_db()
    assert app.status == status


def test_resubmission_inside_the_window_is_accepted(policy):
    """BR-PMS-035: day 59 is still inside the 60-day window."""
    policy()
    app = seed(sm.NEEDS_REVISION, decision_date=timezone.now() - datetime.timedelta(days=59))
    done = app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT, "applicant"))
    assert done.status == sm.RESUBMITTED


def test_window_follows_the_policy_value(policy):
    """BR-PMS-035: the period is the configured one, not a hard-coded 60."""
    policy(days=30)
    app = seed(sm.NEEDS_REVISION, decision_date=timezone.now() - datetime.timedelta(days=31))
    with pytest.raises(DomainError):
        app_service.transition_application(app.id, "resubmit", principal(APPLICANT, "applicant"))


# -- Withdrawal (BR-PMS-067..070, CW-PMS-05) ------------------------------------------------


def test_rejected_application_can_be_withdrawn_and_history_is_kept(api, policy):
    """CW-PMS-05 row 4 and PMS-AFR-130: Rejected -> Withdrawn, reason and origin recorded."""
    policy(withdrawal_states=[sm.REJECTED])
    app = seed(sm.REJECTED, decision_date=timezone.now())
    reason = "The inventors will pursue a trade-secret strategy instead."
    resp = api(APPLICANT, "applicant").post(
        f"{API}/applications/{app.id}/withdraw", {"reason": reason}, format="json")
    assert resp.status_code == 200, resp.data
    entry = PatentAuditLog.objects.get(application=app, action_type="withdraw")
    assert (entry.previous_state, entry.new_state) == (sm.REJECTED, sm.WITHDRAWN)
    assert entry.details["reason"] == reason


def test_withdrawal_still_needs_a_policy_eligible_state(api, policy):
    """BR-PMS-068: a state the policy does not list is refused even though the machine allows it."""
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed(sm.REJECTED, decision_date=timezone.now())
    resp = api(APPLICANT, "applicant").post(
        f"{API}/applications/{app.id}/withdraw", {"reason": "No longer needed."}, format="json")
    assert resp.status_code == 409
    app.refresh_from_db()
    assert app.status == sm.REJECTED


# -- External filing (BR-PMS-020, 056, 128; CW-PMS-02 row 9) --------------------------------


def _filing_ready(status, jurisdiction="IN", consent=True):
    AttorneyPanelMember.objects.create(
        user_id=ATTORNEY, firm_name="Firm", expertise_domains=["Quantum"],
        is_approved_panel=True, active_workload=1)
    app = seed(status, assigned_attorney_id=ATTORNEY, jurisdiction=jurisdiction)
    CoInventor.objects.create(
        application=app, user_id=102, name="Dr. Rao", email="rao@example.edu",
        share_percentage=Decimal("100.00"), consent_granted=consent)
    req = budget_service.record_budget_entry(
        principal(ADMIN, "pcc_admin"), app.id, "FILING_FEE", Decimal("45000"), "GOVERNMENT_FEE")
    budget_service.decide_budget(principal(DIRECTOR, "director"), req.id, "APPROVE")
    return app


def test_domestic_filing_follows_attorney_acceptance_and_stores_details(api, policy):
    """CW-PMS-02 row 9: acceptance + budget enable filing; patentability is not forced first."""
    policy()
    app = _filing_ready(sm.ATTORNEY_ASSIGNED)
    when = timezone.now().date() - datetime.timedelta(days=1)
    resp = api(ATTORNEY, "attorney").post(f"{API}/applications/{app.id}/filing", {
        "external_filing_id": "IN202611000777", "filing_date": when.isoformat(),
        "filing_office": "Indian Patent Office", "confirmation": "IPO-ACK-777",
    }, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert (app.filing_date, app.filing_confirmation) == (when, "IPO-ACK-777")
    assert app.filing_office == "Indian Patent Office"


def test_international_filing_needs_a_justification(api, policy):
    """BR-PMS-056: an international filing without a recorded justification is refused."""
    policy()
    app = _filing_ready(sm.ASSESSMENT_IN_PROGRESS, jurisdiction="WO")
    client = api(ATTORNEY, "attorney")
    refused = client.post(f"{API}/applications/{app.id}/filing",
                          {"external_filing_id": "PCT/IN2026/1"}, format="json")
    assert refused.status_code == 422, refused.data
    app.refresh_from_db()
    assert app.status == sm.ASSESSMENT_IN_PROGRESS
    ok = client.post(f"{API}/applications/{app.id}/filing", {
        "external_filing_id": "PCT/IN2026/1",
        "justification": "EU and US partners justify the national-phase cost."}, format="json")
    assert ok.status_code == 200, ok.data
    app.refresh_from_db()
    assert app.filing_justification.startswith("EU and US")


def test_incomplete_agreements_block_filing_before_anything_else(api, policy):
    """BR-PMS-020: missing inventor agreements refuse the filing with a state conflict."""
    policy()
    app = _filing_ready(sm.ASSESSMENT_IN_PROGRESS, jurisdiction="WO", consent=False)
    resp = api(ATTORNEY, "attorney").post(
        f"{API}/applications/{app.id}/filing", {"external_filing_id": "X"}, format="json")
    assert resp.status_code == 409, resp.data
    app.refresh_from_db()
    assert app.status == sm.ASSESSMENT_IN_PROGRESS and app.external_filing_id == ""


# -- Office-action response states (BW-PMS-12 / BW-PMS-13) ----------------------------------


def _office_action(requires_review):
    app = seed(sm.FILED, assigned_attorney_id=ATTORNEY)
    return OfficeActionRecord.objects.create(
        application=app, action_code="FER-1", issuing_authority="IPO",
        issued_date=timezone.now().date(),
        response_deadline=timezone.now().date() + datetime.timedelta(days=30),
        requires_applicant_review=requires_review, status="RECORDED")


def test_applicant_approval_is_its_own_state_before_submission():
    """BW-PMS-12: Awaiting Applicant Approval -> Applicant Approved -> Response Submitted."""
    oa = _office_action(requires_review=True)
    atty, applicant = principal(ATTORNEY, "attorney"), principal(APPLICANT, "applicant")
    states = [oa_service.draft_response(atty, oa.id, "Distinguish D1.").status]
    states.append(oa_service.applicant_approve_response(applicant, oa.id).status)
    states.append(oa_service.submit_response(atty, oa.id).status)
    assert states == ["AWAITING_APPLICANT", "APPLICANT_APPROVED", "SUBMITTED"]


def test_unapproved_response_cannot_be_submitted():
    """BR-PMS-146: a response that needs Applicant review is not submittable before approval."""
    oa = _office_action(requires_review=True)
    atty = principal(ATTORNEY, "attorney")
    oa_service.draft_response(atty, oa.id, "Distinguish D1.")
    with pytest.raises(DomainError):
        oa_service.submit_response(atty, oa.id)


# -- Audit trail (PMS-AFR-207..212, BR-PMS-121/122) -----------------------------------------


def test_status_changes_are_audited_with_previous_and_new_state(api, policy):
    """BR-PMS-121: user, action, application, previous and new state, visible to PCC_ADMIN."""
    policy()
    app = seed(sm.SUBMITTED)
    resp = api(ADMIN, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR}, format="json")
    assert resp.status_code == 200
    lines = api(ADMIN, "pcc_admin").get(f"{API}/audit-logs").data["audit_logs"]
    line = next(ln for ln in lines if app.application_number in ln)
    for part in (f"user={ADMIN}", "action=assign_director", "previous=submitted",
                 "new=under_review"):
        assert part in line


def test_audit_records_are_immutable():
    """BR-PMS-122: an audit record can be neither changed nor deleted."""
    app = seed(sm.SUBMITTED)
    entry = PatentAuditLog.objects.create(application=app, action_type="x")
    entry.action_type = "y"
    with pytest.raises(AuditImmutable):
        entry.save()
    with pytest.raises(AuditImmutable):
        entry.delete()


def test_audit_view_refuses_roles_without_the_audit_grant(api, policy):
    """UC-PMS-028: unauthorized audit access is blocked."""
    policy()
    app = seed(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR)
    PatentAuditLog.objects.create(application=app, action_type="seen")
    assert api(DIRECTOR, "director").get(f"{API}/audit-logs").status_code == 403
    assert api(APPLICANT, "applicant").get(f"{API}/audit-logs").status_code == 403


# -- Notifications (PMS-AFR-192..205, BR-PMS-116) -------------------------------------------


def test_director_assignment_and_budget_decision_send_email(api, policy, mailoutbox):
    """PMS triggers the emails through the configured backend."""
    policy()
    user_ref(DIRECTOR, "director@example.edu")
    user_ref(APPLICANT, "applicant@example.edu")
    app = seed(sm.SUBMITTED)
    api(ADMIN, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR}, format="json")
    assert any(app.application_number in m.subject and "director@example.edu" in m.to
               for m in mailoutbox)

    app.status = sm.APPROVED
    app.save()
    req = budget_service.record_budget_entry(
        principal(ADMIN, "pcc_admin"), app.id, "FILING_FEE", Decimal("1000"), "GOVERNMENT_FEE")
    budget_service.decide_budget(principal(DIRECTOR, "director"), req.id, "REJECT")
    assert any("Budget rejected" in m.subject for m in mailoutbox)


def test_unreachable_recipient_never_fails_the_action(api, policy, mailoutbox):
    """BR-PMS-116: with no address on file the action still succeeds and nothing is sent."""
    policy()
    app = seed(sm.SUBMITTED)
    resp = api(ADMIN, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR}, format="json")
    assert resp.status_code == 200
    assert mailoutbox == []


# -- Maintenance renewal outcome (BR-PMS-061) -----------------------------------------------


@pytest.mark.parametrize(("renew", "outcome"), [(True, "RENEW"), (False, "DO_NOT_RENEW")])
def test_renewal_outcome_is_recorded(renew, outcome):
    """BR-PMS-061: the explicit Renew / Do Not Renew decision is stored, not discarded."""
    app = seed(sm.GRANTED, grant_date=timezone.now().date(), assigned_director_id=DIRECTOR)
    done = maint_service.record_renewal_decision(
        principal(DIRECTOR, "director"), app.id, renew=renew)
    assert done.renewal_decision == outcome
    assert PatentAuditLog.objects.filter(application=app, action_type="renewal_decision").exists()


# -- Maintenance cycle and escalation handling (BW-PMS-10, BW-PMS-14, BW-PMS-15) ------------


def _granted(**fields):
    return seed(sm.GRANTED, assigned_director_id=DIRECTOR, assigned_attorney_id=ATTORNEY,
                renewal_due_date=timezone.now().date() + datetime.timedelta(days=20), **fields)


def test_maintenance_action_needs_an_approved_renewal():
    """UC-PMS-017: no maintenance action is recorded without a Renew decision."""
    app = _granted()
    atty = principal(ATTORNEY, "attorney")
    with pytest.raises(DomainError):
        maint_service.record_maintenance_action(atty, app.id, "REF-1")
    maint_service.request_renewal_decision(atty, app.id)
    maint_service.record_renewal_decision(principal(DIRECTOR, "director"), app.id, renew=False)
    with pytest.raises(DomainError):
        maint_service.record_maintenance_action(atty, app.id, "REF-1")


def test_a_cycle_takes_one_decision():
    """BR-PMS-061: the cycle's decision cannot be made twice."""
    app = _granted()
    director = principal(DIRECTOR, "director")
    maint_service.record_renewal_decision(director, app.id, renew=True)
    with pytest.raises(DomainError):
        maint_service.record_renewal_decision(director, app.id, renew=False)
    assert maint_service.PatentApplication.objects.get(pk=app.id).renewal_decision == "RENEW"


def test_next_cycle_is_never_invented():
    """BR-PMS-060: without schedule data from the Attorney no next due date is scheduled."""
    app = _granted()
    atty = principal(ATTORNEY, "attorney")
    maint_service.record_renewal_decision(principal(DIRECTOR, "director"), app.id, renew=True)
    done = maint_service.record_maintenance_action(atty, app.id, "REF-2")
    assert done.renewal_due_date is None and done.maintenance_state == "RENEWED"
    entry = PatentAuditLog.objects.get(application=app, action_type="maintenance_action_recorded")
    assert "schedule data required" in entry.details["next_cycle"]


def test_renewal_request_is_for_granted_patents_only():
    """BR-PMS-059: only Granted patents enter post-grant tracking."""
    app = seed(sm.FILED, assigned_attorney_id=ATTORNEY)
    with pytest.raises(DomainError):
        maint_service.request_renewal_decision(principal(ATTORNEY, "attorney"), app.id)


def test_escalation_tracking_needs_an_escalated_case_and_pcc_admin(policy):
    """BW-PMS-10: only an escalated case can be tracked, and only by PCC_ADMIN."""
    policy()
    app = seed(sm.APPROVED, assigned_director_id=DIRECTOR)
    req = budget_service.record_budget_entry(
        principal(ADMIN, "pcc_admin"), app.id, "FILING_FEE", Decimal("1000"), "GOVERNMENT_FEE")
    with pytest.raises(DomainError):
        budget_service.track_escalation(principal(ADMIN, "pcc_admin"), app.id, req.id)
    big = budget_service.record_budget_entry(
        principal(ADMIN, "pcc_admin"), app.id, "FILING_FEE", Decimal("900000"), "GOVERNMENT_FEE")
    budget_service.decide_budget(principal(DIRECTOR, "director"), big.id, "APPROVE")
    with pytest.raises(DomainError):
        budget_service.track_escalation(principal(DIRECTOR, "director"), app.id, big.id)
    row = budget_service.track_escalation(principal(ADMIN, "pcc_admin"), app.id, big.id)
    assert row.status == "ESCALATION_TRACKED"
    with pytest.raises(DomainError):
        budget_service.track_escalation(principal(ADMIN, "pcc_admin"), app.id, big.id)
