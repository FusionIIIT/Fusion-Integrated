"""Spec tests for patents, BR (business rule) strategy, part B: BR-T073 .. BR-T144.

Generated from the frozen docs/11-patents/spec-tests/BR_DESIGN.json (cases 73..144 in
file order). Every test carries its test_id and source_id in its name and docstring.

Behaviour is driven through the module's public interfaces: the HTTP API where an
endpoint exists, otherwise the service layer or the deadline task. Preconditions that
place an application in a given state are seeded directly, as the module's journey tests
do. A case whose interface does not exist is a skipped NOT_AUTOMATED test.

Refusal status codes, where the design names none, come from
docs/01-architecture/api-conventions.md "Status codes": 409 for "the world is in the
wrong state" (illegal transition, unmet record prerequisite), 422 for invalid input or a
policy-based business-rule refusal, 403 for authenticated-but-not-permitted, 404 for a
record outside the caller's visibility.
"""
from __future__ import annotations

import datetime
import itertools
import json
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail.backends.base import BaseEmailBackend
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
    ApplicationDocument,
    AttorneyPanelMember,
    AuditImmutable,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentAuditLog,
    PatentBudgetLedger,
    PatentPolicy,
    TechnologyTransferRecord,
)
from modules.patents.selectors import scoping
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import office_actions as oa_service
from modules.patents.tasks import pms_sweep_deadlines

pytestmark = pytest.mark.django_db

API = "/api/v1/patents"

APPLICANT_ID = 101
COINVENTOR_ID = 102
COINVENTOR2_ID = 103
OTHER_APPLICANT_ID = 150
DIRECTOR_ID = 201
OTHER_DIRECTOR_ID = 250
ATTORNEY_A_ID = 401
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
APPEAL_GROUNDS = "D1 does not disclose resonator coupling."
APPEAL_JUSTIFICATION = "Claim 1 requires coupling absent from D1, so novelty holds."

_seq = itertools.count(1)


# -- Infrastructure -------------------------------------------------------------


def principal(user_id: int, role: str):
    """A real Principal with the registry grants for `role`, for service-level calls."""
    code, perms = ROLE_OF[role]
    return make_principal(
        user_id=user_id, roles=(code,), active_role=code,
        permissions=tuple(perms), modules=("patents",),
    )


#: The identity service's directory: everyone in these cases has an email address, which
#: is where PMS-triggered notifications are sent (BR-PMS-116).
DIRECTORY = {
    uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
                 kind="faculty", email=f"u{uid}@example.edu")
    for uid in (101, 102, 103, 150, 201, 250, 401, 901)
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
def directory(stub_iam):
    """Make the identity directory (with email addresses) available to PMS."""
    stub_iam(None, users=DIRECTORY)


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
        "application_number": f"PMS-BRB-{next(_seq):04d}",
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
        "status": status,
    }
    defaults.update(fields)
    return PatentApplication.objects.create(**defaults)


def add_coinventor(app, consent: bool, user_id: int = COINVENTOR_ID,
                   share: str = "100.00") -> CoInventor:
    return CoInventor.objects.create(
        application=app, user_id=user_id, name=f"Inventor {user_id}",
        email=f"inventor{user_id}@example.edu", share_percentage=Decimal(share),
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


def today() -> datetime.date:
    return timezone.now().date()


def detail_of(api, user_id: int, role: str, app):
    return api(user_id, role).get(f"{API}/applications/{app.id}")


# -- Office actions (shared set-up) ------------------------------------------------


def seed_filed_application() -> PatentApplication:
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        external_filing_id="IN202611000123", filing_date=today(),
    )


def seed_office_action(app, deadline, status="RESPONSE_READY", review=False):
    return OfficeActionRecord.objects.create(
        application=app, action_code="FER-1", issuing_authority="Indian Patent Office",
        issued_date=today() - datetime.timedelta(days=200), response_deadline=deadline,
        status=status, requires_applicant_review=review,
    )


def record_office_action(api, app, deadline=None, review=False):
    """Attorney records an office action through the API; the deadline is optional."""
    body = {
        "action_code": "FER-1",
        "issuing_authority": "Indian Patent Office",
        "issued_date": today().isoformat(),
        "requires_applicant_review": review,
    }
    if deadline is not None:
        body["response_deadline"] = deadline.isoformat()
    return api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/office-actions", body, format="json")


def submit_response(oa):
    """Attorney records the response submission; returns the refusal status or None."""
    return refusal_status(
        lambda: oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa.id))


# -- Withdrawal (shared set-up) ----------------------------------------------------


def withdraw(api, app, reason):
    return api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/withdraw", {"reason": reason}, format="json")


# -- Filing (shared set-up) --------------------------------------------------------


def filing_ready(consents=(True,), budget=True, status=sm.ATTORNEY_ASSIGNED):
    """Attorney assigned, one co-inventor record per entry of `consents`, budget approved
    unless `budget` is False."""
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        status, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        jurisdiction="IN",
    )
    share = f"{Decimal(100) / len(consents):.2f}"
    for i, consent in enumerate(consents):
        add_coinventor(app, consent, user_id=COINVENTOR_ID + i, share=share)
    if budget:
        approve_budget(app)
    return app


def record_filing(api, app):
    return api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/filing", {
        "external_filing_id": "IN202611000555",
        "filing_date": today().isoformat(),
        "jurisdiction": "IN",
        "filing_office": "Indian Patent Office",
        "confirmation": "IPO-ACK-2026-000555",
    }, format="json")


def assert_filing_refused(app, resp):
    app.refresh_from_db()
    assert app.status != sm.FILED
    assert app.external_filing_id == ""
    assert resp.status_code == 409, (resp.status_code, resp.data)


def assert_filing_recorded(app, resp):
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == "IN202611000555"


# -- Documents (shared set-up) -----------------------------------------------------


def upload(client, app_id, name="spec.pdf"):
    pdf = SimpleUploadedFile(name, b"%PDF-1.4\n" + b"0" * 2048, "application/pdf")
    return client.post(f"{API}/applications/{app_id}/documents",
                       {"document_type": "specification", "file": pdf}, format="multipart")


def seed_document(app, version=1) -> ApplicationDocument:
    return ApplicationDocument.objects.create(
        application=app, document_type="specification", file_name="spec.pdf",
        file_size_bytes=2048, storage_path=f"/var/patents/app_{app.id}/spec.pdf",
        version=version, uploaded_by_user_id=APPLICANT_ID,
    )


def document_versions(detail) -> list[int]:
    return sorted(d["version"] for d in detail.data["documents"])


# -- Appeals (shared set-up) -------------------------------------------------------


def seed_rejected(days_ago: int) -> PatentApplication:
    return seed_application(
        sm.REJECTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=days_ago),
    )


def file_appeal(api, app, grounds=APPEAL_GROUNDS, justification=APPEAL_JUSTIFICATION):
    return api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/appeal",
        {"grounds": grounds, "justification": justification}, format="json")


def seed_pending_appeal() -> PatentApplication:
    app = seed_application(
        sm.APPEAL_SUBMITTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=2),
    )
    AppealRecord.objects.create(
        application=app, applicant_user_id=APPLICANT_ID, grounds=APPEAL_GROUNDS,
    )
    return app


# =====================================================================================
# BR-PMS-065 .. 066: office-action response timing and deadline tracking
# =====================================================================================


def test_br_t073_br_pms_065_after_deadline_no_extension(policy):
    """BR-T073 | BR-PMS-065 after deadline no extension | Response after deadline
    without extension rejected.
    """
    policy()
    app = seed_filed_application()
    oa = seed_office_action(app, today() - datetime.timedelta(days=10))

    refused = submit_response(oa)

    oa.refresh_from_db()
    assert refused is not None, "a response after the deadline, with no extension, was accepted"
    assert refused == 422
    assert oa.status != "SUBMITTED" and oa.submitted_at is None


def test_br_t074_br_pms_065_permitted_extension():
    """BR-T074 | BR-PMS-065 permitted extension | Response after original deadline
    accepted with permitted extension.
    """
    pytest.skip(
        "NOT_AUTOMATED: PMS has no way to record a permitted extension (no extension "
        "field on OfficeActionRecord, no endpoint or service), so the precondition "
        "'original deadline passed, extension recorded, extended deadline in future' "
        "cannot be set up through any interface."
    )


def test_br_t075_br_pms_066_data_available(api, policy, directory):
    """BR-T075 | BR-PMS-066 data available | Automated deadline tracking when deadline
    data available.
    """
    policy()
    app = seed_filed_application()
    deadline = today() + datetime.timedelta(days=30)

    resp = record_office_action(api, app, deadline=deadline)

    assert resp.status_code == 201, resp.data
    oa = OfficeActionRecord.objects.get(pk=resp.data["id"])
    assert oa.response_deadline == deadline
    # The deadline is tracked automatically: the deadline processing picks it up.
    assert pms_sweep_deadlines()["alerts"] == 1


def test_br_t076_br_pms_066_data_unavailable(api, policy, directory):
    """BR-T076 | BR-PMS-066 data unavailable | No automated tracking without deadline
    data.
    """
    policy()
    app = seed_filed_application()

    resp = record_office_action(api, app, deadline=None)

    assert resp.status_code in (201, 400, 422), (resp.status_code, resp.data)
    created = OfficeActionRecord.objects.filter(application=app)
    assert not created.exclude(response_deadline__isnull=True).exists(), (
        "a response deadline was created without any deadline data")
    assert pms_sweep_deadlines()["alerts"] == 0


# =====================================================================================
# BR-PMS-067 .. 070: withdrawal
# =====================================================================================


def test_br_t077_br_pms_067_before_filing(api, policy):
    """BR-T077 | BR-PMS-067 before filing | Withdrawal permitted before filing stage."""
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    reason = "Withdrawing to fold this into a broader continuation filing."

    resp = withdraw(api, app, reason)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert not in_active_queue(app)
    stored = history_payload(api, app)
    assert reason in stored, "withdrawal history not recorded"
    assert sm.UNDER_REVIEW in stored


def test_br_t078_br_pms_067_after_filing(api, policy):
    """BR-T078 | BR-PMS-067 after filing | Withdrawal prohibited at/after filing stage."""
    policy(withdrawal_states=sorted(sm.PRE_FILING_STATES))
    app = seed_application(sm.FILED, external_filing_id="IN202611000123",
                           filing_date=today())

    resp = withdraw(api, app, "No longer commercially relevant.")

    app.refresh_from_db()
    assert app.status == sm.FILED
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_br_t079_br_pms_068_eligible_status(api, policy):
    """BR-T079 | BR-PMS-068 eligible status | Withdrawal permitted for
    withdrawal-eligible status.
    """
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)

    resp = withdraw(api, app, "Inventors chose a trade-secret strategy instead.")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN


def test_br_t080_br_pms_068_ineligible_status(api, policy):
    """BR-T080 | BR-PMS-068 ineligible status | Withdrawal prohibited for non-eligible
    status.
    """
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.WITHDRAWN)
    entries_before = PatentAuditLog.objects.filter(application=app).count()

    resp = withdraw(api, app, "Trying to withdraw a second time.")

    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert PatentAuditLog.objects.filter(application=app).count() == entries_before
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_br_t081_br_pms_069_reason_provided(api, policy):
    """BR-T081 | BR-PMS-069 reason provided | Withdrawal with reason accepted."""
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)
    reason = "Withdrawing because the invention was publicly disclosed at a conference."

    resp = withdraw(api, app, reason)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert reason in history_payload(api, app), "withdrawal reason was not recorded"


def test_br_t082_br_pms_069_reason_missing(api, policy):
    """BR-T082 | BR-PMS-069 reason missing | Withdrawal without reason rejected."""
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)

    resp = withdraw(api, app, "")

    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_br_t083_br_pms_070_consent_required_and_recorded(api, policy):
    """BR-T083 | BR-PMS-070 consent required and recorded | Withdrawal proceeds when
    required co-inventor consent recorded.
    """
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, consent=False)
    resp = api(COINVENTOR_ID, "applicant").post(f"{API}/applications/{app.id}/consent")
    assert resp.status_code == 200, resp.data
    reason = "Withdrawing to fold this into a broader continuation filing."

    resp = withdraw(api, app, reason)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    detail = detail_of(api, ADMIN_ID, "pcc_admin", app).data
    assert all(ci["consent_granted"] for ci in detail["co_inventors"])
    stored = history_payload(api, app)
    assert reason in stored
    assert "1/1 granted" in stored, "the withdrawal does not record the co-inventor consent"


def test_br_t084_br_pms_070_consent_required_and_missing():
    """BR-T084 | BR-PMS-070 consent required and missing | Withdrawal blocked when
    required consent missing.
    """
    pytest.skip(
        "NOT_AUTOMATED: PMS has no setting for 'the applicable process requires "
        "co-inventor consent for withdrawal' (no policy field, model flag or service "
        "parameter), so the precondition cannot be set up; the module only records the "
        "consent state with the withdrawal and never blocks on it."
    )


def test_br_t085_br_pms_070_consent_not_required(api, policy):
    """BR-T085 | BR-PMS-070 consent not required | Withdrawal proceeds without consent
    when not required.
    """
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, consent=False)
    reason = "Withdrawing because the market opportunity has disappeared."

    resp = withdraw(api, app, reason)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert reason in history_payload(api, app)


# =====================================================================================
# BR-PMS-073 .. 078: inventor information, ownership, consent, e-signature, agreements
# =====================================================================================

NO_INVENTOR_UPDATE = (
    "NOT_AUTOMATED: PMS exposes no interface to change inventor information or ownership "
    "percentages on an existing application (PUT /applications/<id> accepts only title, "
    "abstract, description, claims and domain_category; there is no co-inventor update "
    "endpoint or service)."
)

NO_ESIGNATURE = (
    "NOT_AUTOMATED: PMS has no electronic-signature capability (no model, service, "
    "endpoint, setting or 'legally permitted and configured' switch for e-signatures)."
)


def test_br_t086_br_pms_073_valid():
    """BR-T086 | BR-PMS-073 valid | Valid inventor information change accepted."""
    pytest.skip(NO_INVENTOR_UPDATE)


def test_br_t087_br_pms_073_invalid():
    """BR-T087 | BR-PMS-073 invalid | Invalid inventor information change rejected."""
    pytest.skip(NO_INVENTOR_UPDATE)


def test_br_t088_br_pms_074_valid():
    """BR-T088 | BR-PMS-074 valid | Valid ownership percentages accepted."""
    pytest.skip(NO_INVENTOR_UPDATE)


def test_br_t089_br_pms_074_invalid():
    """BR-T089 | BR-PMS-074 invalid | Invalid ownership percentages rejected."""
    pytest.skip(NO_INVENTOR_UPDATE)


def test_br_t090_br_pms_075_consent_obtained(api, policy):
    """BR-T090 | BR-PMS-075 consent obtained | Filing allowed when required inventor
    consent obtained.
    """
    policy()
    app = filing_ready(consents=(True, True))

    resp = record_filing(api, app)

    assert_filing_recorded(app, resp)


def test_br_t091_br_pms_075_consent_missing(api, policy):
    """BR-T091 | BR-PMS-075 consent missing | Filing blocked when required inventor
    consent missing.
    """
    policy()
    app = filing_ready(consents=(True, False))

    resp = record_filing(api, app)

    assert_filing_refused(app, resp)


def test_br_t092_br_pms_076_permitted_and_configured():
    """BR-T092 | BR-PMS-076 permitted and configured | E-signature collection allowed
    when legally permitted and configured.
    """
    pytest.skip(NO_ESIGNATURE)


def test_br_t093_br_pms_076_not_configured():
    """BR-T093 | BR-PMS-076 not configured | E-signature collection not allowed when
    not configured.
    """
    pytest.skip(NO_ESIGNATURE)


def test_br_t094_br_pms_077_configured():
    """BR-T094 | BR-PMS-077 configured | E-signature validation applied when permitted
    and configured.
    """
    pytest.skip(NO_ESIGNATURE)


def test_br_t095_br_pms_077_not_configured():
    """BR-T095 | BR-PMS-077 not configured | E-signature validation not applied when
    not configured.
    """
    pytest.skip(NO_ESIGNATURE)


def test_br_t096_br_pms_078_agreements_complete(api, policy):
    """BR-T096 | BR-PMS-078 agreements complete | Filing allowed when inventor
    agreements complete.
    """
    policy()
    app = filing_ready(consents=(True,))

    resp = record_filing(api, app)

    assert_filing_recorded(app, resp)


def test_br_t097_br_pms_078_agreements_incomplete(api, policy):
    """BR-T097 | BR-PMS-078 agreements incomplete | Filing blocked when inventor
    agreements incomplete.
    """
    policy()
    app = filing_ready(consents=(False,))

    resp = record_filing(api, app)

    assert_filing_refused(app, resp)


# =====================================================================================
# BR-PMS-082 .. 087: documents
# =====================================================================================


def test_br_t098_br_pms_082_auto_numbering(api, policy):
    """BR-T098 | BR-PMS-082 auto numbering | New document versions are automatically
    numbered.
    """
    policy()
    app = seed_application(sm.DRAFT)
    client = api(APPLICANT_ID, "applicant")
    first = upload(client, app.id)
    assert first.status_code == 201, first.data
    assert first.data["version"] == 1

    second = upload(client, app.id)
    third = upload(client, app.id)

    assert second.status_code == 201, second.data
    assert third.status_code == 201, third.data
    assert (second.data["version"], third.data["version"]) == (2, 3)
    # Prior versions are archived: every earlier version is still held.
    held = sorted(ApplicationDocument.objects.filter(application=app)
                  .values_list("version", flat=True))
    assert held == [1, 2, 3]


def test_br_t099_br_pms_084_permitted(api, policy):
    """BR-T099 | BR-PMS-084 permitted | Authorized role/status can access previous
    versions.
    """
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
                           decision_date=timezone.now())
    seed_document(app, version=1)
    seed_document(app, version=2)

    owner = detail_of(api, APPLICANT_ID, "applicant", app)
    director = detail_of(api, DIRECTOR_ID, "director", app)

    assert owner.status_code == 200
    assert 1 in document_versions(owner), "previous version not returned to the owner"
    assert director.status_code == 200
    assert 1 in document_versions(director), "previous version not returned to the Director"


def test_br_t100_br_pms_084_prohibited(api, policy):
    """BR-T100 | BR-PMS-084 prohibited | Unauthorized role/status cannot access
    previous versions.
    """
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
                           decision_date=timezone.now())
    seed_document(app, version=1)
    seed_document(app, version=2)

    resp = detail_of(api, OTHER_APPLICANT_ID, "applicant", app)

    assert resp.status_code == 404, (resp.status_code, resp.data)
    assert "documents" not in resp.data
    outsider = principal(OTHER_APPLICANT_ID, "applicant")
    assert not scoping.documents_for(outsider).exists()


def test_br_t101_br_pms_086_permitted(api, policy):
    """BR-T101 | BR-PMS-086 permitted | Document access allowed per role and status."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    doc = seed_document(app)

    resp = detail_of(api, APPLICANT_ID, "applicant", app)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert [d["id"] for d in resp.data["documents"]] == [doc.id]


def test_br_t102_br_pms_086_prohibited(api, policy):
    """BR-T102 | BR-PMS-086 prohibited | Document access denied per role and status."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_document(app)

    resp = detail_of(api, OTHER_APPLICANT_ID, "applicant", app)

    assert resp.status_code == 404, (resp.status_code, resp.data)
    assert "documents" not in resp.data


def test_br_t103_br_pms_087_condition_true(api, policy):
    """BR-T103 | BR-PMS-087 condition-true | Applicant may edit documents in Needs
    Revision.
    """
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
                           decision_date=timezone.now())
    seed_document(app, version=1)

    resp = upload(api(APPLICANT_ID, "applicant"), app.id)

    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert resp.data["version"] == 2
    assert ApplicationDocument.objects.filter(application=app).count() == 2


def test_br_t104_br_pms_087_condition_false(api, policy):
    """BR-T104 | BR-PMS-087 condition-false | Applicant cannot edit documents outside
    Needs Revision.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_document(app, version=1)

    resp = upload(api(APPLICANT_ID, "applicant"), app.id)

    assert ApplicationDocument.objects.filter(application=app).count() == 1, (
        "a document edit was accepted while the application was Under Review")
    assert resp.status_code == 409, (resp.status_code, resp.data)


# =====================================================================================
# BR-PMS-088 .. 091: licensing / technology transfer
# =====================================================================================


def test_br_t105_br_pms_088_routing():
    """BR-T105 | BR-PMS-088 routing | Licensing request routed per institutional
    process.
    """
    pytest.skip(
        "NOT_AUTOMATED: PMS has no configurable routing of licensing requests to a "
        "committee or Director (TechnologyTransferRecord stores no routing target, "
        "there is no routing setting, and submitting a request performs no routing or "
        "notification), so neither the configured-routing precondition nor the routed "
        "outcome can be exercised."
    )


def _tech_transfer(api, app):
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "LICENSE",
        "partner_name": "Quantum Devices Pvt Ltd", "terms_summary": "Exclusive, 5 years.",
    }, format="json")
    assert resp.status_code == 201, (resp.status_code, resp.data)
    return resp.data["id"]


def test_br_t106_br_pms_091_permitted(api, policy):
    """BR-T106 | BR-PMS-091 permitted | Authorized user can access license records."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    record_id = _tech_transfer(api, app)

    owner = detail_of(api, APPLICANT_ID, "applicant", app)
    director = detail_of(api, DIRECTOR_ID, "director", app)

    for resp in (owner, director):
        assert resp.status_code == 200, (resp.status_code, resp.data)
        assert [r["id"] for r in resp.data["licensing_records"]] == [record_id]


def test_br_t107_br_pms_091_prohibited(api, policy):
    """BR-T107 | BR-PMS-091 prohibited | Unauthorized user cannot access confidential
    license records.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    _tech_transfer(api, app)

    resp = detail_of(api, OTHER_APPLICANT_ID, "applicant", app)

    assert resp.status_code == 404, (resp.status_code, resp.data)
    assert "licensing_records" not in resp.data
    outsider = principal(OTHER_APPLICANT_ID, "applicant")
    assert not scoping.tech_transfers_for(outsider).exists()
    assert TechnologyTransferRecord.objects.filter(application=app).count() == 1


# =====================================================================================
# BR-PMS-092 .. 095: appeals
# =====================================================================================


def test_br_t108_br_pms_092_condition_true(api, policy):
    """BR-T108 | BR-PMS-092 condition-true | Appeal permitted for Rejected application."""
    policy()
    app = seed_rejected(days_ago=5)

    resp = file_appeal(api, app)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED
    assert app.appeals.get().grounds == APPEAL_GROUNDS


def test_br_t109_br_pms_092_condition_false(api, policy):
    """BR-T109 | BR-PMS-092 condition-false | Appeal prohibited for non-Rejected
    application.
    """
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
                           decision_date=timezone.now() - datetime.timedelta(days=5))

    resp = file_appeal(api, app)

    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    assert not app.appeals.exists()
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_br_t110_br_pms_093_within_period(api, policy):
    """BR-T110 | BR-PMS-093 within period | Appeal within allowed period accepted."""
    policy()
    app = seed_rejected(days_ago=3)

    resp = file_appeal(api, app)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED
    assert app.appeals.count() == 1


def test_br_t111_br_pms_093_after_period(api, policy):
    """BR-T111 | BR-PMS-093 after period | Appeal after allowed period rejected."""
    policy()
    # Far beyond any plausible appeal period.
    app = seed_rejected(days_ago=400)

    resp = file_appeal(api, app)

    app.refresh_from_db()
    assert app.status == sm.REJECTED, "an appeal filed after the allowed period was accepted"
    assert not app.appeals.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_br_t112_br_pms_094_grounds_provided(api, policy):
    """BR-T112 | BR-PMS-094 grounds provided | Appeal with grounds and justification
    accepted.
    """
    policy()
    app = seed_rejected(days_ago=5)

    resp = file_appeal(api, app, APPEAL_GROUNDS, APPEAL_JUSTIFICATION)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED
    assert app.appeals.get().grounds == APPEAL_GROUNDS


def test_br_t113_br_pms_094_grounds_missing(api, policy):
    """BR-T113 | BR-PMS-094 grounds missing | Appeal without grounds/justification
    rejected.
    """
    policy()
    app = seed_rejected(days_ago=5)

    resp = file_appeal(api, app, grounds="", justification="")

    app.refresh_from_db()
    assert app.status == sm.REJECTED
    assert not app.appeals.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


@pytest.mark.parametrize("outcome,expected_status", [
    pytest.param("UPHOLD", sm.REJECTION_UPHELD, id="Uphold Rejection"),
    pytest.param("REMAND", sm.REMANDED, id="Remand for Amendment"),
    pytest.param("MODIFY", sm.DECISION_MODIFIED, id="Modify Decision"),
])
def test_br_t114_br_pms_095_valid_outcome(api, policy, outcome, expected_status):
    """BR-T114 | BR-PMS-095 valid outcome | Director appeal outcome in allowed set
    accepted.
    """
    policy()
    app = seed_pending_appeal()

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": outcome}, format="json")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    appeal = app.appeals.get()
    assert appeal.status == outcome
    assert appeal.decided_at is not None
    assert appeal.director_user_id == DIRECTOR_ID
    assert app.status == expected_status, "the next process step was not initiated"


def test_br_t115_br_pms_095_invalid_outcome(api, policy):
    """BR-T115 | BR-PMS-095 invalid outcome | Appeal outcome outside allowed set
    rejected.
    """
    policy()
    app = seed_pending_appeal()

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "Defer"}, format="json")

    app.refresh_from_db()
    appeal = app.appeals.get()
    assert app.status == sm.APPEAL_SUBMITTED
    assert appeal.status == "SUBMITTED" and appeal.decided_at is None
    assert resp.status_code == 422, (resp.status_code, resp.data)


# =====================================================================================
# BR-PMS-097 .. 104: deadline calculation, alerts and escalation
# =====================================================================================


def test_br_t116_br_pms_097_review_deadline(api, policy, directory):
    """BR-T116 | BR-PMS-097 review deadline | PMS calculates/monitors Director review
    deadline.

    The review deadline is 15 business days from assignment. Fifteen calendar days
    contain at most 11 business days, so the review must not yet be overdue; thirty
    calendar days contain at least 20, so it must be.
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert pms_sweep_deadlines()["overdue_reviews"] == 0

    def assigned(days_ago: int) -> None:
        PatentApplication.objects.filter(pk=app.id).update(
            updated_at=timezone.now() - datetime.timedelta(days=days_ago))

    assigned(15)
    assert pms_sweep_deadlines()["overdue_reviews"] == 0, (
        "review flagged overdue before 15 business days had elapsed")
    assigned(30)
    assert pms_sweep_deadlines()["overdue_reviews"] == 1


@pytest.mark.parametrize("decision", ["NEEDS_REVISION", "REJECT"])
def test_br_t117_br_pms_098_revision_deadline(api, policy, directory, decision):
    """BR-T117 | BR-PMS-098 revision deadline | PMS calculates/monitors revision
    deadline.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    feedback = "Claim 1 overlaps prior art D1; narrow it to the resonator-coupled variant."

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": decision, "justification": feedback}, format="json")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    decided = app.decision_date
    assert decided is not None
    assert abs((timezone.now() - decided).total_seconds()) < 300

    # Tracked at decision date + 60 days: still open at day 59, expired at day 61.
    PatentApplication.objects.filter(pk=app.id).update(
        decision_date=timezone.now() - datetime.timedelta(days=59))
    assert pms_sweep_deadlines()["expired"] == 0
    app.refresh_from_db()
    assert app.status != sm.EXPIRED
    PatentApplication.objects.filter(pk=app.id).update(
        decision_date=timezone.now() - datetime.timedelta(days=61))
    assert pms_sweep_deadlines()["expired"] == 1
    app.refresh_from_db()
    assert app.status == sm.EXPIRED


def test_br_t118_br_pms_099_rules_available(api, policy, directory):
    """BR-T118 | BR-PMS-099 rules available | Office-action deadline calculated when
    rules/data available.
    """
    policy()
    app = seed_filed_application()
    deadline = today() + datetime.timedelta(days=15)

    resp = record_office_action(api, app, deadline=deadline)

    assert resp.status_code == 201, (resp.status_code, resp.data)
    oa = OfficeActionRecord.objects.get(pk=resp.data["id"])
    assert oa.response_deadline == deadline
    assert pms_sweep_deadlines()["alerts"] == 1, "the deadline is not monitored"


def test_br_t119_br_pms_099_rules_unavailable(api, policy, directory):
    """BR-T119 | BR-PMS-099 rules unavailable | No office-action deadline calculated
    without rules/data.
    """
    policy()
    app = seed_filed_application()

    resp = record_office_action(api, app, deadline=None, review=True)

    assert resp.status_code in (201, 400, 422), (resp.status_code, resp.data)
    created = OfficeActionRecord.objects.filter(application=app)
    assert not created.exclude(response_deadline__isnull=True).exists(), (
        "a response deadline was calculated without any deadline rules or data")
    assert pms_sweep_deadlines()["alerts"] == 0


def test_br_t120_br_pms_100_rules_available():
    """BR-T120 | BR-PMS-100 rules available | Maintenance deadlines calculated when
    jurisdiction rules available.
    """
    pytest.skip(
        "NOT_AUTOMATED: PMS holds no jurisdiction maintenance-schedule rules and has no "
        "interface to configure them (no model, setting or service); the next due date "
        "is supplied by the Attorney and never calculated, so the 'schedule rules "
        "configured' precondition and the calculated-deadline outcome cannot be exercised."
    )


def test_br_t121_br_pms_100_rules_unavailable(api, policy, directory):
    """BR-T121 | BR-PMS-100 rules unavailable | No maintenance deadlines without
    jurisdiction rules.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.GRANTED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        grant_date=today() - datetime.timedelta(days=700),
    )
    assert app.renewal_due_date is None

    summary = pms_sweep_deadlines()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.renewal_due_date is None, "a maintenance-fee deadline was calculated"
    assert summary["overdue_renewals"] == 0


def _alert_case(policy, mailoutbox, days: int) -> None:
    """A tracked deadline `days` from today; alert processing must alert stakeholders."""
    policy()
    app = seed_filed_application()
    seed_office_action(app, today() + datetime.timedelta(days=days), status="RECORDED")
    before = len(mailoutbox)

    summary = pms_sweep_deadlines()

    assert summary["alerts"] == 1, f"no {days}-day alert was generated"
    alerts = mails_about(mailoutbox, app, before)
    assert alerts, f"the {days}-day alert was not sent to any stakeholder"
    stakeholders = {DIRECTORY[APPLICANT_ID].email, DIRECTORY[ATTORNEY_A_ID].email}
    recipients = {r for m in alerts for r in m.to}
    assert recipients and recipients <= stakeholders


def test_br_t122_br_pms_101_30_day_alert(policy, directory, mailoutbox):
    """BR-T122 | BR-PMS-101 30-day alert | Alert at 30 days before tracked deadline."""
    _alert_case(policy, mailoutbox, 30)


def test_br_t123_br_pms_102_15_day_alert(policy, directory, mailoutbox):
    """BR-T123 | BR-PMS-102 15-day alert | Alert at 15 days before tracked deadline."""
    _alert_case(policy, mailoutbox, 15)


def test_br_t124_br_pms_103_5_day_alert(policy, directory, mailoutbox):
    """BR-T124 | BR-PMS-103 5-day alert | Alert at 5 days before tracked deadline."""
    _alert_case(policy, mailoutbox, 5)


def test_br_t125_br_pms_104_missed_deadline(api, policy, directory):
    """BR-T125 | BR-PMS-104 missed deadline | Missed deadline triggers escalation via
    configured chain.

    The tracked deadline is the Director review deadline: an Under Review application
    whose review is long past due.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    PatentApplication.objects.filter(pk=app.id).update(
        updated_at=timezone.now() - datetime.timedelta(days=40))

    summary = pms_sweep_deadlines()

    assert summary["overdue_reviews"] == 1
    logged = [ln for ln in audit_entries(api, app) if "escalat" in ln.lower()]
    assert logged, "no escalation was raised and logged for the missed deadline"


# =====================================================================================
# BR-PMS-116, 121, 122: notifications and audit
# =====================================================================================


class FailingEmailBackend(BaseEmailBackend):
    """Stand-in for the unavailable external mail delivery infrastructure."""

    def send_messages(self, email_messages):
        raise ConnectionRefusedError("mail infrastructure unavailable")


def test_br_t126_br_pms_116_trigger_only(directory, settings, caplog):
    """BR-T126 | BR-PMS-116 trigger only | PMS triggers email notifications without
    owning delivery.
    """
    settings.EMAIL_BACKEND = f"{__name__}.FailingEmailBackend"
    app = seed_application(sm.DRAFT)

    with caplog.at_level("INFO", logger="fusion.patents.notify"):
        result = app_service.transition_application(
            app.id, "submit", principal(APPLICANT_ID, "applicant"))

    assert result.status == sm.SUBMITTED
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert PatentAuditLog.objects.filter(application=app, new_state=sm.SUBMITTED).exists()
    triggered = [r for r in caplog.records if r.name == "fusion.patents.notify"]
    assert triggered, "PMS recorded no notification trigger for the status change"


def test_br_t127_br_pms_121_audit_fields(api, policy):
    """BR-T127 | BR-PMS-121 audit fields | Audit record contains required fields."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data

    lines = [ln for ln in audit_entries(api, app) if sm.UNDER_REVIEW in ln and sm.APPROVED in ln]
    assert len(lines) == 1, lines
    line = lines[0]
    parts = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in line.split(" | ")[1:] if "=" in p}
    datetime.datetime.fromisoformat(line.split(" | ")[0])      # timestamp
    assert parts["user"] == str(DIRECTOR_ID)
    assert parts["action"] == "submit_review"
    assert parts["application"] == app.application_number
    assert parts["previous"] == sm.UNDER_REVIEW
    assert parts["new"] == sm.APPROVED


def test_br_t128_br_pms_122_immutability(api, policy):
    """BR-T128 | BR-PMS-122 immutability | Critical-operation audit records are
    immutable.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    entry = PatentAuditLog.objects.filter(application=app).order_by("id").last()
    snapshot = (entry.actor_user_id, entry.action_type, entry.previous_state,
                entry.new_state, entry.details)
    total = PatentAuditLog.objects.count()

    entry.new_state = "tampered"
    with pytest.raises(AuditImmutable):
        entry.save()
    with pytest.raises(AuditImmutable):
        entry.delete()
    admin = api(ADMIN_ID, "pcc_admin")
    for method in (admin.put, admin.patch, admin.delete):
        assert method(f"{API}/audit-logs").status_code == 405

    stored = PatentAuditLog.objects.get(pk=entry.pk)
    assert PatentAuditLog.objects.count() == total
    assert (stored.actor_user_id, stored.action_type, stored.previous_state,
            stored.new_state, stored.details) == snapshot


# =====================================================================================
# BR-PMS-126 .. 131: access control and sequencing
# =====================================================================================


@pytest.mark.parametrize("user_id,role,path", [
    pytest.param(APPLICANT_ID, "applicant", "/applications", id="applicant"),
    pytest.param(DIRECTOR_ID, "director", "/applications", id="director"),
    pytest.param(ATTORNEY_A_ID, "attorney", "/applications", id="attorney"),
    pytest.param(ADMIN_ID, "pcc_admin", "/audit-logs", id="pcc_admin"),
])
def test_br_t129_br_pms_126_role_present(api, policy, user_id, role, path):
    """BR-T129 | BR-PMS-126 role present | User with valid PMS role can access
    functions.
    """
    policy()

    resp = api(user_id, role).get(f"{API}{path}")

    assert resp.status_code == 200, (resp.status_code, resp.data)


@pytest.mark.parametrize("modules", [(), ("patents",)], ids=["no-module", "module-only"])
def test_br_t130_br_pms_126_role_absent(stub_iam, policy, modules):
    """BR-T130 | BR-PMS-126 role absent | User without PMS role is denied."""
    policy()
    stub_iam(make_session(
        user_id=777, roles=("student",), active_role="student",
        permissions=(), modules=modules,
    ), users=DIRECTORY)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    assert client.get(f"{API}/applications").status_code == 403
    assert client.get(f"{API}/audit-logs").status_code == 403
    assert client.get(f"{API}/reports").status_code == 403
    created = client.post(f"{API}/applications", {
        "title": "T", "abstract": "A", "description": "D", "claims": "C",
    }, format="json")
    assert created.status_code == 403
    assert not PatentApplication.objects.exists()


def test_br_t131_br_pms_127_before_approval(api, policy):
    """BR-T131 | BR-PMS-127 before approval | Attorney assignment before Director
    approval is prohibited.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)

    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")

    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert app.assigned_attorney_id is None
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_br_t132_br_pms_127_after_approval(api, policy):
    """BR-T132 | BR-PMS-127 after approval | Attorney assignment after Director approval
    is permitted.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)

    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.ASSIGNMENT_OFFERED
    assert app.assigned_attorney_id == ATTORNEY_A_ID


def test_br_t133_br_pms_128_incomplete(api, policy):
    """BR-T133 | BR-PMS-128 incomplete | External filing blocked without required
    approvals and budget allocation.
    """
    policy()
    app = filing_ready(consents=(True,), budget=False)

    resp = record_filing(api, app)

    assert_filing_refused(app, resp)


def test_br_t134_br_pms_128_complete(api, policy):
    """BR-T134 | BR-PMS-128 complete | External filing allowed when approvals and
    budget complete.
    """
    policy()
    app = filing_ready(consents=(True,), budget=True)

    resp = record_filing(api, app)

    assert_filing_recorded(app, resp)


def test_br_t135_br_pms_130_permitted(api, policy):
    """BR-T135 | BR-PMS-130 permitted | Authorized role can view confidential patent
    information.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)

    resp = detail_of(api, DIRECTOR_ID, "director", app)

    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["id"] == app.id
    assert resp.data["claims"] == app.claims


def test_br_t136_br_pms_130_prohibited(api, policy):
    """BR-T136 | BR-PMS-130 prohibited | Unauthorized role cannot view confidential
    patent information.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)

    other_applicant = detail_of(api, OTHER_APPLICANT_ID, "applicant", app)
    other_director = detail_of(api, OTHER_DIRECTOR_ID, "director", app)

    for resp in (other_applicant, other_director):
        assert resp.status_code == 404, (resp.status_code, resp.data)
        assert "claims" not in resp.data and "title" not in resp.data


def test_br_t137_br_pms_131_single_pcc_admin():
    """BR-T137 | BR-PMS-131 single PCC_ADMIN | Only one active PCC_ADMIN allowed."""
    pytest.skip(
        "NOT_AUTOMATED: PMS has no role-assignment interface; roles, including PCC_ADMIN, "
        "are granted by the external identity service (IAM) and the patents module "
        "exposes no endpoint, service or model to assign the PCC_ADMIN role to a user."
    )


# =====================================================================================
# BR-PMS-138 .. 142: scope boundaries
# =====================================================================================


def test_br_t138_br_pms_138_external_office_boundary(api, policy):
    """BR-T138 | BR-PMS-138 external office boundary | PMS records patent-office data
    without controlling patent-office decisions.
    """
    policy()
    app = seed_filed_application()

    resp = record_office_action(api, app, deadline=today() + datetime.timedelta(days=90))

    assert resp.status_code == 201, (resp.status_code, resp.data)
    oa = OfficeActionRecord.objects.get(pk=resp.data["id"])
    assert (oa.action_code, oa.issuing_authority) == ("FER-1", "Indian Patent Office")
    assert any("office_action_recorded" in ln for ln in audit_entries(api, app)), (
        "the communication was not logged")
    app.refresh_from_db()
    assert app.status == sm.FILED, "PMS changed the status without recorded outcome data"
    assert app.grant_date is None


def test_br_t139_br_pms_139_financial_boundary(api, policy):
    """BR-T139 | BR-PMS-139 financial boundary | PMS records financial metadata without
    executing payments.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE",
        Decimal("45000.00"), "GOVERNMENT_FEE")

    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "APPROVE", "budget_entry_id": req.id}, format="json")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    row = PatentBudgetLedger.objects.get(pk=resp.data["id"])
    assert (row.status, row.entry_kind) == ("APPROVED", "APPROVAL")
    assert row.authorized_by_user_id == DIRECTOR_ID
    logged = [ln for ln in audit_entries(api, app) if "budget_decision" in ln]
    assert logged and "APPROVAL" in logged[0], "approval and authorization level not logged"
    ledger = PatentBudgetLedger.objects.filter(application=app)
    assert not ledger.filter(entry_kind="DISBURSEMENT").exists()
    assert not ledger.filter(status__icontains="PAID").exists()


def test_br_t140_br_pms_140_document_boundary(api, policy):
    """BR-T140 | BR-PMS-140 document boundary | PMS owns document/version/access/audit
    behavior internally.
    """
    policy()
    app = seed_application(sm.DRAFT)
    seed_document(app, version=1)

    resp = upload(api(APPLICANT_ID, "applicant"), app.id)

    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert resp.data["version"] == 2
    owner = detail_of(api, APPLICANT_ID, "applicant", app)
    assert document_versions(owner) == [1, 2]
    outsider = detail_of(api, OTHER_APPLICANT_ID, "applicant", app)
    assert outsider.status_code == 404
    logged = [ln for ln in audit_entries(api, app) if "document" in ln.lower()]
    assert logged, "no audit entry was recorded for the document version upload"


def test_br_t141_br_pms_141_prior_art_boundary():
    """BR-T141 | BR-PMS-141 prior-art boundary | External prior-art databases are
    query sources only.
    """
    pytest.skip(
        "NOT_AUTOMATED: PMS has no prior-art reference attachment (no model, service or "
        "endpoint to attach a search result to an application or to log a search "
        "session), and POST /prior-art/search is a placeholder that returns no results "
        "with no source to stub, so the results-with-relevance, attachment and "
        "session-log outcomes cannot be exercised."
    )


def test_br_t142_br_pms_142_filing_boundary(api, policy):
    """BR-T142 | BR-PMS-142 filing boundary | PMS only records filing details and
    confirmations.
    """
    policy()
    app = filing_ready(consents=(True,))
    filing_date = today() - datetime.timedelta(days=1)

    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/filing", {
        "external_filing_id": "IN202611000999",
        "filing_date": filing_date.isoformat(),
        "jurisdiction": "IN",
        "filing_office": "Indian Patent Office",
        "confirmation": "IPO-ACK-2026-000999",
    }, format="json")

    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.status != sm.GRANTED and app.grant_date is None
    detail = detail_of(api, ADMIN_ID, "pcc_admin", app).data
    assert detail["external_filing_id"] == "IN202611000999"
    assert detail["filing_date"] == filing_date.isoformat()
    assert detail["filing_confirmation"] == "IPO-ACK-2026-000999"


# =====================================================================================
# BR-PMS-146: Applicant approval of an office-action response
# =====================================================================================


def test_br_t143_br_pms_146_condition_true_review_required(api, policy):
    """BR-T143 | BR-PMS-146 condition-true (review required) | Applicant approval
    required before response submission when process requires it.
    """
    policy()
    app = seed_filed_application()
    oa_id = record_office_action(
        api, app, deadline=today() + datetime.timedelta(days=90), review=True).data["id"]
    drafted = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert drafted.status_code == 200, drafted.data
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert oa.status == "AWAITING_APPLICANT"

    blocked = submit_response(oa)

    oa.refresh_from_db()
    assert blocked == 409, f"submission before Applicant approval returned {blocked}"
    assert oa.status == "AWAITING_APPLICANT" and oa.submitted_at is None

    approved = api(APPLICANT_ID, "applicant").post(f"{API}/office-actions/{oa_id}/approve")
    assert approved.status_code == 200, approved.data
    assert submit_response(oa) is None
    oa.refresh_from_db()
    assert oa.status == "SUBMITTED" and oa.submitted_at is not None


def test_br_t144_br_pms_146_condition_false_review_not_required(api, policy):
    """BR-T144 | BR-PMS-146 condition-false (review not required) | Applicant approval
    not required when process does not require it.
    """
    policy()
    app = seed_filed_application()
    oa_id = record_office_action(
        api, app, deadline=today() + datetime.timedelta(days=90), review=False).data["id"]
    drafted = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert drafted.status_code == 200, drafted.data
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert oa.status == "RESPONSE_READY"

    refused = submit_response(oa)

    oa.refresh_from_db()
    assert refused is None, f"submission was refused ({refused}) without Applicant approval"
    assert oa.status == "SUBMITTED" and oa.submitted_at is not None
