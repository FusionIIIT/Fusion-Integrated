"""Spec tests for patents, FR (functional requirement) strategy, part A.

Generated from the frozen docs/11-patents/spec-tests/FR_DESIGN.json: cases FR-T001 to
FR-T111 (the first half of the 222 cases). Every test carries its test_id and source_id in
its name and docstring.

Behaviour is driven through the module's public interfaces: the HTTP API where an endpoint
exists, otherwise the service layer (`submit`/`resubmit` transitions, `submit_response`,
`record_budget_entry`, `register_panel_member`, which have no endpoint) and the deadline
sweep task. Preconditions that place an application in a given state are seeded directly,
as the module's own journey tests do.

Refusal status codes, where the design names none, come from
docs/01-architecture/api-conventions.md "Status codes": 409 for "the world is in the wrong
state" (illegal transition, unmet record prerequisite), 422 for invalid input or a
policy-based business-rule refusal, 403 for authenticated but not permitted.

A case is skipped (NOT_AUTOMATED) only when the module offers no interface at all for the
behaviour: no endpoint, service, model field or task through which it can be driven.
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
    ApplicationDocument,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
    ReviewDecision,
)
from modules.patents.services import applications as app_service
from modules.patents.services import attorney as attorney_service
from modules.patents.services import budget as budget_service
from modules.patents.services import office_actions as oa_service
from modules.patents.tasks import pms_sweep_deadlines

pytestmark = pytest.mark.django_db

API = "/api/v1/patents"

APPLICANT_ID = 101
COINVENTOR_ID = 102
OTHER_APPLICANT_ID = 103
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
FEEDBACK = "Claim 1 overlaps prior art D1; narrow it to the resonator-coupled variant."

_seq = itertools.count(1)


# -- Infrastructure -------------------------------------------------------------


def principal(user_id: int, role: str):
    """A real Principal with the registry grants for `role`, for service-level calls."""
    code, perms = ROLE_OF[role]
    return make_principal(
        user_id=user_id, roles=(code,), active_role=code,
        permissions=tuple(perms), modules=("patents",),
    )


#: The identity service's directory: everyone who appears in these flows has an email
#: address, which is where PMS-triggered notifications are sent (BR-PMS-116).
DIRECTORY = {
    uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
                 kind="faculty", email=f"u{uid}@example.edu")
    for uid in (101, 102, 103, 201, 401, 402, 901)
}


def email_of(user_id: int) -> str:
    return f"u{user_id}@example.edu"


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


def panel_attorney(user_id: int, workload: int = 0, domains=("Quantum",),
                   approved: bool = True) -> AttorneyPanelMember:
    return AttorneyPanelMember.objects.create(
        user_id=user_id, firm_name=f"Firm {user_id}",
        expertise_domains=list(domains), is_approved_panel=approved,
        active_workload=workload,
    )


def seed_application(status: str, **fields) -> PatentApplication:
    """Seed an application already in `status` (precondition set-up only)."""
    defaults = {
        "user_id": APPLICANT_ID,
        "application_number": f"PMS-FRA-{next(_seq):04d}",
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
        application=app, user_id=user_id, name=f"Co-inventor {user_id}",
        email=email_of(user_id), share_percentage=Decimal(share),
        consent_granted=consent, consent_timestamp=timezone.now() if consent else None,
    )


def request_budget(app, amount="45000.00", entry_type="FILING_FEE",
                   category="GOVERNMENT_FEE") -> PatentBudgetLedger:
    return budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, entry_type, Decimal(amount), category,
    )


def approve_budget(app, amount="45000.00") -> PatentBudgetLedger:
    """Precondition: a budget request decided Approved by the Director."""
    req = request_budget(app, amount)
    return budget_service.decide_budget(principal(DIRECTOR_ID, "director"), req.id, "APPROVE")


def filing_ready(consent: bool = True, jurisdiction: str = "IN") -> PatentApplication:
    """An application the Attorney may file: working the case, budget approved, inventor
    agreements per `consent`."""
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID, jurisdiction=jurisdiction,
    )
    add_coinventor(app, consent=consent)
    approve_budget(app)
    return app


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


def detail_of(api, app, user_id: int, role: str) -> dict:
    resp = api(user_id, role).get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    return dict(resp.data)


def history_payload(api, app) -> str:
    """Everything the module exposes about the application's history: its detail
    (minus the current status) and its audit log lines."""
    detail = detail_of(api, app, ADMIN_ID, "pcc_admin")
    detail.pop("status", None)
    return json.dumps(detail, default=str) + json.dumps(audit_entries(api, app))


def rows(resp) -> list:
    data = resp.data
    return data["results"] if isinstance(data, dict) and "results" in data else list(data)


def refusal_status(fn) -> int | None:
    """Run a service call; return the refusal's HTTP status, or None if it was accepted."""
    try:
        fn()
    except DomainError as err:
        return err.status_code
    return None


def business_days_between(start: datetime.date, end: datetime.date) -> int:
    """Weekdays in (start, end]."""
    days, cur = 0, start
    while cur < end:
        cur += datetime.timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def business_days_ago(n: int) -> datetime.datetime:
    """The moment `n` business days (weekends excluded) before now."""
    cur, left = timezone.now(), n
    while left:
        cur -= datetime.timedelta(days=1)
        if cur.weekday() < 5:
            left -= 1
    return cur


def recorded_review_deadline(detail: dict) -> datetime.date | None:
    """The review deadline the module records on an application, wherever it keeps it:
    a deadline/due field of the application or of its review records."""
    holders = [detail, *detail.get("reviews", [])]
    for holder in holders:
        for key, value in holder.items():
            if not value or not isinstance(value, str):
                continue
            if "deadline" in key or "due" in key:
                return datetime.date.fromisoformat(value[:10])
    return None


NEW_APPLICATION = {
    "title": "Topological qubit layout",
    "abstract": "A surface-code layout for superconducting transmon qubits.",
    "description": "Detailed description of resonator coupling and error syndromes.",
    "claims": "1. A circuit comprising at least five coupled transmons.",
    "domain_category": "Quantum",
    "co_inventors": [{"user_id": APPLICANT_ID, "name": "Asha Verma",
                      "email": "asha@example.edu", "share_percentage": "100.00"}],
}


def create_application(client, **overrides) -> int:
    """Applicant creates a draft application through the API; returns its id."""
    body = {**NEW_APPLICATION, **overrides}
    resp = client.post(f"{API}/applications", body, format="json")
    assert resp.status_code == 201, (resp.status_code, resp.data)
    return resp.data["id"]


def upload(client, app_id: int, size: int = 2048, name: str = "spec.pdf",
           content_type: str = "application/pdf"):
    data = b"%PDF-1.4\n" + b"0" * (size - 9)
    return client.post(
        f"{API}/applications/{app_id}/documents",
        {"document_type": "specification",
         "file": SimpleUploadedFile(name, data, content_type)},
        format="multipart",
    )


def submit(app_id: int) -> PatentApplication:
    """Applicant submits (no endpoint exists for `submit`; the service is the interface)."""
    app_service.transition_application(app_id, "submit", principal(APPLICANT_ID, "applicant"))
    return PatentApplication.objects.get(pk=app_id)


def submitted_application(api) -> PatentApplication:
    """A complete application created, documented and submitted by the Applicant."""
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    assert upload(client, app_id).status_code == 201
    return submit(app_id)


def assign_director(api, app, director_id: int = DIRECTOR_ID):
    return api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": director_id},
        format="json")


def decide(api, app, decision: str, justification: str = GOOD_JUSTIFICATION):
    return api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": decision, "justification": justification}, format="json")


def under_review(**fields) -> PatentApplication:
    return seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID, **fields)


def needs_revision(days_ago: int = 5, status: str = sm.NEEDS_REVISION) -> PatentApplication:
    """A revision-requested (or rejected) application with Director feedback recorded."""
    app = seed_application(
        status, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=days_ago),
    )
    ReviewDecision.objects.create(
        application=app, director_user_id=DIRECTOR_ID,
        decision="NEEDS_REVISION" if status == sm.NEEDS_REVISION else "REJECT",
        justification=FEEDBACK,
    )
    return app


def revise(api, app, claims: str = "1. A resonator-coupled circuit of five transmons."):
    return api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}", {"claims": claims}, format="json")


def granted_application(**fields) -> PatentApplication:
    if not AttorneyPanelMember.objects.filter(user_id=ATTORNEY_A_ID).exists():
        panel_attorney(ATTORNEY_A_ID, workload=1)
    defaults = {
        "assigned_director_id": DIRECTOR_ID,
        "assigned_attorney_id": ATTORNEY_A_ID,
        "grant_date": timezone.now().date() - datetime.timedelta(days=700),
        "renewal_due_date": timezone.now().date() + datetime.timedelta(days=20),
    }
    defaults.update(fields)
    return seed_application(sm.GRANTED, **defaults)


def filed_application() -> PatentApplication:
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        external_filing_id="IN202611000123", filing_date=timezone.now().date(),
    )


def record_office_action(api, app, requires_review: bool = False, days: int = 180):
    today = timezone.now().date()
    return api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/office-actions", {
        "action_code": "FER-1",
        "issuing_authority": "Indian Patent Office",
        "issued_date": today.isoformat(),
        "response_deadline": (today + datetime.timedelta(days=days)).isoformat(),
        "requires_applicant_review": requires_review,
    }, format="json")


# -- Tracking, reports and oversight ------------------------------------------------


def test_fr_t001_pms_afr_010(api, policy):
    """FR-T001 | PMS-AFR-010 | Applicant can track status and progress of own application

    Applicant requests the status/progress view of an Under Review application: the
    current status Under Review and the progress/history are returned.
    """
    policy()
    app = submitted_application(api)
    assert assign_director(api, app).status_code == 200

    resp = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == sm.UNDER_REVIEW
    progress = dict(resp.data)
    progress.pop("status")
    assert "submitted" in json.dumps(progress, default=str).lower(), (
        "no progress/history of the application is returned to the Applicant")


def test_fr_t002_pms_afr_016(api, policy):
    """FR-T002 | PMS-AFR-016 | Applicant can view reports for own applications

    Applicant owns two applications, another Applicant owns a third; the personal report
    is returned and contains only the Applicant's own two applications.
    """
    policy()
    seed_application(sm.DRAFT)
    seed_application(sm.SUBMITTED)
    seed_application(sm.SUBMITTED, user_id=OTHER_APPLICANT_ID)

    resp = api(APPLICANT_ID, "applicant").get(f"{API}/reports")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["total_applications"] == 2


def test_fr_t003_pms_afr_023(api, policy):
    """FR-T003 | PMS-AFR-023 | Director receives oversight information for workflows in own domain

    Director assigned to expertise domain D requests the workflow oversight view:
    status/progress of domain-D application workflows is returned.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no Director expertise-domain assignment, so the "
        "precondition 'Director assigned to expertise domain D' cannot be set up and no "
        "domain-scoped oversight view exists (Directors only see applications assigned "
        "to them)."
    )


def test_fr_t004_pms_afr_026(api, policy):
    """FR-T004 | PMS-AFR-026 | PCC_ADMIN monitors workflows and resolves a conflict-of-interest case

    PCC_ADMIN opens the workflow monitor and records resolution of a flagged conflict case.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no conflict-of-interest case record (no model, "
        "service or endpoint to flag or resolve a conflict case), so the flagged case "
        "precondition and the recorded resolution have no interface."
    )


def test_fr_t005_pms_afr_027(api, policy):
    """FR-T005 | PMS-AFR-027 | PCC_ADMIN manages PMS configuration and user-role assignments

    PCC_ADMIN assigns the Director role to a user and updates a PMS configuration value.
    """
    pytest.skip(
        "NOT_AUTOMATED: PMS has no user-role assignment interface (roles live in the "
        "external identity service) and no administrator configuration endpoint; only an "
        "internal policy-supersede service exists."
    )


def test_fr_t006_pms_afr_029(api, policy):
    """FR-T006 | PMS-AFR-029 | PCC_ADMIN handles an escalation/exceptional case

    An escalated case exists; PCC_ADMIN records a handling action on it, and the
    escalation handling is recorded against the case.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, "200000.00")
    escalated = budget_service.decide_budget(principal(DIRECTOR_ID, "director"), req.id, "APPROVE")
    assert escalated.status == "ESCALATED"

    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/budget-escalation",
        {"budget_entry_id": req.id, "notes": "Routed to the Board; decision is external."},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    handled = PatentBudgetLedger.objects.filter(
        application=app, replaces_entry=req, status="ESCALATION_TRACKED")
    assert handled.count() == 1
    assert handled.get().authorized_by_user_id == ADMIN_ID
    assert any("budget_escalation_tracked" in ln for ln in audit_entries(api, app))


def test_fr_t007_pms_afr_030(api, policy):
    """FR-T007 | PMS-AFR-030 | PCC_ADMIN maintains attorney panels and expertise mappings

    PCC_ADMIN adds the Attorney to the approved panel with expertise domain D; the Attorney
    is listed on the approved panel with expertise mapping D.
    """
    policy()
    attorney_service.register_panel_member(
        principal(ADMIN_ID, "pcc_admin"), ATTORNEY_A_ID, "Firm A", ["Quantum"])

    resp = api(ADMIN_ID, "pcc_admin").get(f"{API}/attorney-panel")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    listed = [r for r in rows(resp) if r["user_id"] == ATTORNEY_A_ID]
    assert len(listed) == 1
    assert listed[0]["is_approved_panel"] is True
    assert "Quantum" in listed[0]["expertise_domains"]


def test_fr_t008_pms_afr_037(api, policy):
    """FR-T008 | PMS-AFR-037 | Attorney records legal advice for an application

    Attorney submits a legal advice record: it is stored and linked to the application
    and the Attorney.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no legal-advice record (no model, service or "
        "endpoint); the assessment endpoint only starts the assessment or acknowledges an "
        "opinion without storing any advice."
    )


# -- Application submission ----------------------------------------------------------


def test_fr_t009_pms_afr_038(api, policy):
    """FR-T009 | PMS-AFR-038 | Applicant submits a complete patent application

    Title, abstract, description, claims, inventor information and a valid PDF are
    accepted and stored with all supplied fields and the document.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    assert upload(client, app_id, size=4096).status_code == 201
    app = submit(app_id)

    assert app.status == sm.SUBMITTED
    for field in ("title", "abstract", "description", "claims"):
        assert getattr(app, field) == NEW_APPLICATION[field]
    inventor = app.co_inventors.get()
    assert (inventor.name, inventor.email) == ("Asha Verma", "asha@example.edu")
    doc = app.documents.get()
    assert doc.file_format == "pdf" and doc.file_size_bytes == 4096


def test_fr_t010_pms_afr_039(api, policy):
    """FR-T010 | PMS-AFR-039 | Non-PDF application document is rejected

    A .docx supporting document is rejected with a format validation error; no document
    (and no further application) is created.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    resp = upload(client, app_id, name="spec.docx",
                  content_type="application/vnd.openxmlformats-officedocument."
                               "wordprocessingml.document")
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert not ApplicationDocument.objects.exists()
    assert PatentApplication.objects.count() == 1


def test_fr_t011_pms_afr_040(api, policy):
    """FR-T011 | PMS-AFR-040 | Document larger than 50 MB is rejected

    A PDF of 50 MB + 1 byte is rejected with a size validation error; no document is
    accepted.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    resp = upload(client, app_id, size=50 * 1024 * 1024 + 1)
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert not ApplicationDocument.objects.exists()


def test_fr_t012_pms_afr_040(api, policy):
    """FR-T012 | PMS-AFR-040 | Document below 50 MB is accepted

    A 49 MB malware-free PDF is accepted.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    resp = upload(client, app_id, size=49 * 1024 * 1024)
    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert ApplicationDocument.objects.filter(application_id=app_id).count() == 1


def test_fr_t013_pms_afr_041(api, policy):
    """FR-T013 | PMS-AFR-041 | Document failing malware validation is rejected

    The malware scanner reports the file as infected: the document is not accepted and a
    malware validation error is returned.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no malware-scanning hook or scanner client "
        "(document upload validates only format and size), so an infected-file result "
        "cannot be produced or injected."
    )


def test_fr_t014_pms_afr_042(api, policy):
    """FR-T014 | PMS-AFR-042 | Incomplete application is not accepted

    An application missing the claims field is rejected with a completeness validation
    error and no application ID is assigned.
    """
    policy()
    body = {k: v for k, v in NEW_APPLICATION.items() if k != "claims"}
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/applications", body, format="json")
    assert not PatentApplication.objects.exists(), "an application ID was assigned"
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t015_pms_afr_043(api, policy):
    """FR-T015 | PMS-AFR-043 | Submitted document is classified by sensitivity

    A valid application document is stored carrying a sensitivity classification value.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    resp = upload(client, app_id)
    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert resp.data["sensitivity_level"]
    assert ApplicationDocument.objects.get(application_id=app_id).sensitivity_level


def test_fr_t016_pms_afr_044(api, policy):
    """FR-T016 | PMS-AFR-044 | Each accepted application gets a unique ID

    Two valid applications each get an application ID and the two IDs differ.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    first = create_application(client)
    second = create_application(client, title="Second invention")
    numbers = [PatentApplication.objects.get(pk=i).application_number for i in (first, second)]
    assert all(numbers)
    assert numbers[0] != numbers[1]


def test_fr_t017_pms_afr_045(api, policy):
    """FR-T017 | PMS-AFR-045 | Status set to Submitted after successful submission

    A valid application submitted by the Applicant has status Submitted.
    """
    policy()
    app = submitted_application(api)
    assert app.status == sm.SUBMITTED
    assert api(APPLICANT_ID, "applicant").get(
        f"{API}/applications/{app.id}").data["status"] == sm.SUBMITTED


def test_fr_t018_pms_afr_046(api, policy):
    """FR-T018 | PMS-AFR-046 | Filing blocked until inventor agreements completed

    Application otherwise eligible for filing but one inventor agreement is not completed:
    the Attorney's external filing is rejected and the status does not become Filed.
    """
    policy()
    app = filing_ready(consent=False)
    before = app.status
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing",
        {"external_filing_id": "IN202611000123"}, format="json")
    app.refresh_from_db()
    assert app.status != sm.FILED
    assert app.status == before
    assert app.external_filing_id == ""
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_fr_t019_pms_afr_047(api, policy):
    """FR-T019 | PMS-AFR-047 | Application history is recorded

    A submitted application is assigned to a Director: its history contains the submission
    and the status change entries.
    """
    policy()
    app = submitted_application(api)
    assert assign_director(api, app).status_code == 200

    logs = audit_entries(api, app)
    assert any("previous=draft" in ln and "new=submitted" in ln for ln in logs), logs
    assert any("previous=submitted" in ln and "new=under_review" in ln for ln in logs), logs


def test_fr_t020_pms_afr_048(api, policy, mailoutbox):
    """FR-T020 | PMS-AFR-048 | Stakeholders notified on submission/status update

    Submitting a valid application triggers a notification to the relevant stakeholder(s),
    at least the Applicant.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    app_id = create_application(client)
    assert upload(client, app_id).status_code == 201
    before = len(mailoutbox)
    app = submit(app_id)

    sent = mails_about(mailoutbox, app, before)
    assert sent, "no notification was triggered for the submission"
    assert any(email_of(APPLICANT_ID) in m.to for m in sent)


# -- Director assignment ------------------------------------------------------------


def test_fr_t021_pms_afr_049(api, policy):
    """FR-T021 | PMS-AFR-049 | PCC_ADMIN assigns submitted application to Director

    PCC_ADMIN assigns a submitted application to an eligible Director without conflict:
    the application is assigned to the Director.
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = assign_director(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.assigned_director_id == DIRECTOR_ID


def test_fr_t022_pms_afr_049(api, policy):
    """FR-T022 | PMS-AFR-049 | Non-PCC_ADMIN cannot perform manual Director assignment

    An Applicant's attempt to assign a submitted application to a Director is denied
    (permission error) and no assignment is recorded.
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 403, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert app.assigned_director_id is None


def test_fr_t023_pms_afr_050(api, policy):
    """FR-T023 | PMS-AFR-050 | Automatic Director assignment when rules configured

    With assignment rules configured and an eligible Director existing, a valid submitted
    application is automatically assigned to an eligible Director.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no automatic Director assignment or assignment-rule "
        "configuration; submission leaves the application Submitted until PCC_ADMIN "
        "assigns a Director manually."
    )


def test_fr_t024_pms_afr_051(api, policy):
    """FR-T024 | PMS-AFR-051 | Director expertise matching used in assignment

    For an application in domain D, Director X (expertise D) is selected over Director Y
    (expertise E) at equal workload.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module records no Director expertise and has no Director "
        "selection/recommendation function; Director assignment takes an explicit "
        "director_id only."
    )


def test_fr_t025_pms_afr_052(api, policy):
    """FR-T025 | PMS-AFR-052 | Director workload balance used in assignment

    Of two Directors with matching expertise, the one with fewer active reviews (X) is
    selected.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no Director workload tracking and no Director "
        "selection/recommendation function; Director assignment takes an explicit "
        "director_id only."
    )


def test_fr_t026_pms_afr_053(api, policy):
    """FR-T026 | PMS-AFR-053 | Conflict-of-interest check before Director assignment

    Assigning an application to a Director with a recorded conflict of interest for it is
    rejected (the Director is excluded).
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no conflict-of-interest record, so a Director "
        "'with a recorded conflict' cannot be set up; only the structural author/"
        "co-inventor conflict is checked and that is covered by FR-T027."
    )


def test_fr_t027_pms_afr_054(api, policy):
    """FR-T027 | PMS-AFR-054 | Director listed as inventor cannot review

    An application lists Director X as an inventor: assigning it to X is rejected, and a
    review decision submitted by X is rejected.
    """
    policy()
    submitted = seed_application(sm.SUBMITTED)
    add_coinventor(submitted, consent=True, user_id=DIRECTOR_ID)
    resp = assign_director(api, submitted)
    assert resp.status_code == 422, (resp.status_code, resp.data)
    submitted.refresh_from_db()
    assert submitted.status == sm.SUBMITTED
    assert submitted.assigned_director_id is None

    reviewing = under_review()
    add_coinventor(reviewing, consent=True, user_id=DIRECTOR_ID)
    resp = decide(api, reviewing, "APPROVE")
    reviewing.refresh_from_db()
    assert reviewing.status == sm.UNDER_REVIEW
    assert not reviewing.reviews.exists()
    assert resp.status_code in (403, 422), (resp.status_code, resp.data)


def test_fr_t028_pms_afr_055(api, policy):
    """FR-T028 | PMS-AFR-055 | PCC_ADMIN listed as inventor cannot review

    An application lists the PCC_ADMIN user as an inventor: the PCC_ADMIN's attempt to
    review/decide it is rejected.
    """
    policy()
    app = under_review()
    add_coinventor(app, consent=True, user_id=ADMIN_ID)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert not app.reviews.exists()
    assert resp.status_code in (403, 422), (resp.status_code, resp.data)


def test_fr_t029_pms_afr_056(api, policy):
    """FR-T029 | PMS-AFR-056 | Status becomes Under Review on Director assignment

    Assigning a submitted application to an eligible Director sets status Under Review.
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = assign_director(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW


def test_fr_t030_pms_afr_057(api, policy, mailoutbox):
    """FR-T030 | PMS-AFR-057 | Director notified and review timeline initiated on assignment

    Assigning a Director triggers a notification to that Director and records the review
    deadline/timeline from the assignment date.
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    before = len(mailoutbox)
    resp = assign_director(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)

    sent = mails_about(mailoutbox, app, before)
    assert any(email_of(DIRECTOR_ID) in m.to for m in sent), (
        "the assigned Director was not notified")
    deadline = recorded_review_deadline(detail_of(api, app, ADMIN_ID, "pcc_admin"))
    assert deadline is not None, "no review deadline/timeline was recorded at assignment"
    assert deadline >= timezone.now().date()


def test_fr_t031_pms_afr_058(api, policy):
    """FR-T031 | PMS-AFR-058 | Director views details, documents and materials of assigned application

    Director X requests the detail of an Under Review application assigned to X: details,
    documents and supporting materials are returned.
    """
    policy()
    app = under_review()
    ApplicationDocument.objects.create(
        application=app, document_type="specification", file_name="spec.pdf",
        file_size_bytes=2048, storage_path="/var/patents/spec.pdf",
        uploaded_by_user_id=APPLICANT_ID,
    )
    resp = api(DIRECTOR_ID, "director").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    for field in ("title", "abstract", "description", "claims"):
        assert resp.data[field] == getattr(app, field)
    assert [d["file_name"] for d in resp.data["documents"]] == ["spec.pdf"]


def test_fr_t032_pms_afr_059(api, policy):
    """FR-T032 | PMS-AFR-059 | Director records each allowed decision value

    Approve, Reject and Needs Revision with 50+ character justifications are each accepted
    and recorded; statuses become Approved, Rejected, Needs Revision.
    """
    policy()
    expected = {"APPROVE": sm.APPROVED, "REJECT": sm.REJECTED,
                "NEEDS_REVISION": sm.NEEDS_REVISION}
    for decision, status in expected.items():
        app = under_review()
        resp = decide(api, app, decision)
        assert resp.status_code == 200, (decision, resp.status_code, resp.data)
        app.refresh_from_db()
        assert app.status == status
        review = app.reviews.get()
        assert review.decision == decision
        assert review.director_user_id == DIRECTOR_ID


def test_fr_t033_pms_afr_059(api, policy):
    """FR-T033 | PMS-AFR-059 | Decision outside the allowed set is rejected

    Decision value 'Defer' with a valid justification is rejected with a validation
    error; the status is unchanged.
    """
    policy()
    app = under_review()
    resp = decide(api, app, "Defer")
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert not app.reviews.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t034_pms_afr_060(api, policy):
    """FR-T034 | PMS-AFR-060 | Justification shorter than 50 characters rejected

    Approve with a 49-character justification is rejected with a validation error; the
    status is unchanged.
    """
    policy()
    app = under_review()
    resp = decide(api, app, "APPROVE", "J" * 49)
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert not app.reviews.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t035_pms_afr_060(api, policy):
    """FR-T035 | PMS-AFR-060 | Justification of exactly 50 characters accepted

    Approve with a 50-character justification is accepted and recorded.
    """
    policy()
    app = under_review()
    resp = decide(api, app, "APPROVE", "J" * 50)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.APPROVED
    assert app.reviews.get().justification == "J" * 50


def test_fr_t036_pms_afr_061(api, policy):
    """FR-T036 | PMS-AFR-061 | Review deadline set to 15 business days from assignment

    The recorded review deadline equals the assignment date plus 15 business days
    (weekends excluded).
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    assigned_on = timezone.now().date()
    assert assign_director(api, app).status_code == 200

    deadline = recorded_review_deadline(detail_of(api, app, ADMIN_ID, "pcc_admin"))
    assert deadline is not None, "no review deadline was recorded"
    assert deadline.weekday() < 5
    assert business_days_between(assigned_on, deadline) == 15


def test_fr_t037_pms_afr_061(api, policy, mailoutbox):
    """FR-T037 | PMS-AFR-061 | Review not completed within 15 business days is flagged/escalated

    16 business days after assignment with no decision, deadline monitoring identifies the
    review as overdue and an escalation is triggered.
    """
    policy()
    app = under_review()
    PatentApplication.objects.filter(pk=app.id).update(updated_at=business_days_ago(16))
    before = len(mailoutbox)

    result = pms_sweep_deadlines()
    assert result["overdue_reviews"] == 1
    escalated = mails_about(mailoutbox, app, before) or [
        ln for ln in audit_entries(api, app) if "escalat" in ln.lower()]
    assert escalated, "no escalation was triggered for the overdue review"


def test_fr_t038_pms_afr_062(api, policy, mailoutbox):
    """FR-T038 | PMS-AFR-062 | Applicant notified with feedback on rejection

    The Director records Reject with a justification: the Applicant receives a
    notification containing the Director's feedback.
    """
    policy()
    app = under_review()
    before = len(mailoutbox)
    assert decide(api, app, "REJECT", FEEDBACK).status_code == 200

    sent = [m for m in mails_about(mailoutbox, app, before) if email_of(APPLICANT_ID) in m.to]
    assert sent, "the Applicant was not notified"
    assert any(FEEDBACK in m.body for m in sent)


def test_fr_t039_pms_afr_063(api, policy, mailoutbox):
    """FR-T039 | PMS-AFR-063 | Applicant notified with feedback on revision request

    The Director records Needs Revision with a justification: the Applicant receives a
    notification containing the Director's feedback.
    """
    policy()
    app = under_review()
    before = len(mailoutbox)
    assert decide(api, app, "NEEDS_REVISION", FEEDBACK).status_code == 200

    sent = [m for m in mails_about(mailoutbox, app, before) if email_of(APPLICANT_ID) in m.to]
    assert sent, "the Applicant was not notified"
    assert any(FEEDBACK in m.body for m in sent)


def test_fr_t040_pms_afr_064(api, policy):
    """FR-T040 | PMS-AFR-064 | Approved application routed to attorney assignment

    After the Director records Approve the application status is Approved and it appears
    in the attorney-assignment queue (the PCC_ADMIN's Approved applications).
    """
    policy()
    app = under_review()
    assert decide(api, app, "APPROVE").status_code == 200
    app.refresh_from_db()
    assert app.status == sm.APPROVED

    resp = api(ADMIN_ID, "pcc_admin").get(f"{API}/applications")
    assert resp.status_code == 200
    queue = [r for r in rows(resp) if r["status"] == sm.APPROVED]
    assert [r["id"] for r in queue] == [app.id]


def test_fr_t041_pms_afr_065(api, policy):
    """FR-T041 | PMS-AFR-065 | Director review process audited

    An audit entry exists for the review decision with the Director, the decision and a
    timestamp.
    """
    policy()
    app = under_review()
    assert decide(api, app, "APPROVE").status_code == 200

    entries = [ln for ln in audit_entries(api, app) if "action=submit_review" in ln]
    assert len(entries) == 1, entries
    line = entries[0]
    assert f"user={DIRECTOR_ID}" in line
    assert "APPROVE" in line
    datetime.datetime.fromisoformat(line.split(" | ")[0])


# -- Revision and resubmission ------------------------------------------------------


def test_fr_t042_pms_afr_066(api, policy):
    """FR-T042 | PMS-AFR-066 | Applicant can revise Needs Revision application

    A Needs Revision application within 60 days of the decision accepts the Applicant's
    revision.
    """
    policy()
    app = needs_revision(days_ago=5)
    resp = revise(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.claims == "1. A resonator-coupled circuit of five transmons."


def test_fr_t043_pms_afr_067(api, policy):
    """FR-T043 | PMS-AFR-067 | Applicant can revise Rejected application

    A Rejected application within 60 days of the decision accepts the Applicant's revision.
    """
    policy()
    app = needs_revision(days_ago=5, status=sm.REJECTED)
    resp = revise(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.claims == "1. A resonator-coupled circuit of five transmons."


def test_fr_t044_pms_afr_066(api, policy):
    """FR-T044 | PMS-AFR-066 | Revision not allowed for status other than Needs Revision/Rejected

    The Applicant's attempt to revise an Under Review application is rejected and the
    application is unchanged.
    """
    policy()
    app = under_review()
    before = app.claims
    resp = revise(api, app)
    assert resp.status_code == 409, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.claims == before
    assert app.status == sm.UNDER_REVIEW


def test_fr_t045_pms_afr_068(api, policy):
    """FR-T045 | PMS-AFR-068 | Resubmission on day 60 accepted

    A Needs Revision application whose decision was 60 days ago accepts the Applicant's
    revised resubmission.
    """
    policy()
    app = needs_revision(days_ago=60)
    resp = revise(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app_service.transition_application(app.id, "resubmit", principal(APPLICANT_ID, "applicant"))
    app.refresh_from_db()
    assert app.status == sm.RESUBMITTED


def test_fr_t046_pms_afr_068(api, policy):
    """FR-T046 | PMS-AFR-068 | Resubmission after 60 days rejected

    A Needs Revision application whose decision was 61 days ago: resubmission is rejected
    as out of period.
    """
    policy()
    app = needs_revision(days_ago=61)
    put = revise(api, app)
    if put.status_code >= 400:
        refused = put.status_code
    else:
        refused = refusal_status(lambda: app_service.transition_application(
            app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    assert refused is not None, "resubmission after 61 days was accepted"
    assert refused == 422


def test_fr_t047_pms_afr_069(api, policy):
    """FR-T047 | PMS-AFR-069 | Revision that does not address feedback rejected

    A Needs Revision application with Director feedback is resubmitted without addressing
    the feedback (unchanged content): the resubmission is rejected with a validation error.
    """
    policy()
    app = needs_revision(days_ago=5)
    refused = refusal_status(lambda: app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION, "resubmission without addressing feedback accepted"
    assert refused == 422


def test_fr_t048_pms_afr_070(api, policy):
    """FR-T048 | PMS-AFR-070 | New review cycle starts after resubmission

    After the Applicant resubmits a valid revision, a new review cycle is started: the
    application re-enters review with a new review timeline.
    """
    policy()
    app = needs_revision(days_ago=5)
    assert revise(api, app).status_code == 200
    app_service.transition_application(app.id, "resubmit", principal(APPLICANT_ID, "applicant"))
    app.refresh_from_db()
    assert app.status == sm.RESUBMITTED

    assert assign_director(api, app).status_code == 200
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    deadline = recorded_review_deadline(detail_of(api, app, ADMIN_ID, "pcc_admin"))
    assert deadline is not None, "no review timeline was recorded for the new review cycle"
    assert deadline >= timezone.now().date()


def test_fr_t049_pms_afr_071(api, policy):
    """FR-T049 | PMS-AFR-071 | Version control maintained for revisions

    Application version 1 in Needs Revision: after the Applicant resubmits a revision the
    application has version 2 and version 1 is retained in history.
    """
    policy()
    app = needs_revision(days_ago=5)
    assert app.version == 1
    original_claims = app.claims
    assert revise(api, app).status_code == 200
    app_service.transition_application(app.id, "resubmit", principal(APPLICANT_ID, "applicant"))
    app.refresh_from_db()

    assert app.status == sm.RESUBMITTED
    assert app.version == 2
    assert original_claims in history_payload(api, app), "version 1 is not retained in history"


def test_fr_t050_pms_afr_072(api, policy):
    """FR-T050 | PMS-AFR-072 | Status set to Expired when resubmission deadline expires

    A Needs Revision application 61 days after the decision, not resubmitted: deadline
    processing sets status Expired.
    """
    policy()
    app = needs_revision(days_ago=61)
    result = pms_sweep_deadlines()
    assert result["expired"] == 1
    app.refresh_from_db()
    assert app.status == sm.EXPIRED


# -- Attorney assignment --------------------------------------------------------------


def assign_attorney(api, app, attorney_id: int = ATTORNEY_A_ID, as_user=(ADMIN_ID, "pcc_admin")):
    return api(*as_user).post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": attorney_id},
        format="json")


def test_fr_t051_pms_afr_074(api, policy):
    """FR-T051 | PMS-AFR-074 | PCC_ADMIN assigns Attorney to approved application

    PCC_ADMIN assigns a panel Attorney without conflict to an Approved application: the
    assignment is recorded.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    resp = assign_attorney(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.assigned_attorney_id == ATTORNEY_A_ID
    assert app.status == sm.ASSIGNMENT_OFFERED


def test_fr_t052_pms_afr_074(api, policy):
    """FR-T052 | PMS-AFR-074 | Non-PCC_ADMIN cannot assign attorneys

    A Director's attempt to assign an Attorney to an Approved application is denied and no
    assignment is recorded.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    resp = assign_attorney(api, app, as_user=(DIRECTOR_ID, "director"))
    assert resp.status_code == 403, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.assigned_attorney_id is None
    assert app.status == sm.APPROVED


def test_fr_t053_pms_afr_075(api, policy):
    """FR-T053 | PMS-AFR-075 | Off-panel attorney rejected without exception

    PCC_ADMIN assigns an Attorney who is not on the approved panel, with no exception
    recorded: the assignment is rejected.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, approved=False)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    resp = assign_attorney(api, app)
    app.refresh_from_db()
    assert app.assigned_attorney_id is None
    assert app.status == sm.APPROVED
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t054_pms_afr_075(api, policy):
    """FR-T054 | PMS-AFR-075 | Off-panel attorney allowed with recorded exception

    With an exception recorded for an Attorney who is not on the panel, PCC_ADMIN's
    assignment of that Attorney is accepted.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no panel-exception record (no model, service or "
        "endpoint), so the 'exception recorded' precondition cannot be set up; an "
        "off-panel Attorney is always refused."
    )


def test_fr_t055_pms_afr_076(api, policy):
    """FR-T055 | PMS-AFR-076 | Attorney expertise considered

    For an application in domain D, panel Attorney P (expertise D) is selected/ranked
    ahead of Q (expertise E) at equal workload.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no attorney recommendation/ranking function; "
        "attorney assignment takes an explicit attorney_id only (expertise is stored but "
        "never consulted)."
    )


def test_fr_t056_pms_afr_077(api, policy):
    """FR-T056 | PMS-AFR-077 | Attorney workload considered

    Of two panel Attorneys with matching expertise, the one with the lower workload (P) is
    selected/ranked first.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no attorney recommendation/ranking function; "
        "attorney assignment takes an explicit attorney_id only (workload is only checked "
        "against the policy maximum)."
    )


def test_fr_t057_pms_afr_078(api, policy):
    """FR-T057 | PMS-AFR-078 | Conflict-of-interest check before attorney assignment

    PCC_ADMIN's assignment of a panel Attorney with a recorded conflict is rejected due to
    the conflict of interest.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no attorney conflict-of-interest record, so an "
        "Attorney 'with a recorded conflict' cannot be set up and no conflict check is "
        "performed on attorney assignment."
    )


def test_fr_t058_pms_afr_079(api, policy):
    """FR-T058 | PMS-AFR-079 | Applicant preference considered when attorney on panel

    The Applicant's preferred Attorney P is on the panel and eligible: the preference is
    taken into account (P selected/ranked first).
    """
    pytest.skip(
        "NOT_AUTOMATED: the module records no Applicant attorney preference and has no "
        "attorney recommendation function."
    )


def test_fr_t059_pms_afr_079(api, policy):
    """FR-T059 | PMS-AFR-079 | Applicant preference ignored when attorney not on panel

    The Applicant's preferred Attorney R is not on the panel: R is not selected on the
    basis of the preference.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module records no Applicant attorney preference and has no "
        "attorney recommendation function."
    )


def test_fr_t060_pms_afr_080(api, policy):
    """FR-T060 | PMS-AFR-080 | Assigned Attorney accepts or declines

    An Attorney awaiting a response accepts (case 1) or declines (case 2): the acceptance
    or decline is recorded for the assignment.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    accepted = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    declined = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    for app in (accepted, declined):
        assert assign_attorney(api, app).status_code == 200

    client = api(ATTORNEY_A_ID, "attorney")
    resp = client.post(f"{API}/applications/{accepted.id}/respond-assignment",
                       {"action": "accept"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    resp = client.post(f"{API}/applications/{declined.id}/respond-assignment",
                       {"action": "decline"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)

    accepted.refresh_from_db()
    declined.refresh_from_db()
    assert accepted.status == sm.ATTORNEY_ASSIGNED
    assert accepted.assigned_attorney_id == ATTORNEY_A_ID
    assert declined.status == sm.PENDING_REVIEW
    assert any(f"user={ATTORNEY_A_ID}" in ln and "action=accept_assignment" in ln
               for ln in audit_entries(api, accepted)), "acceptance not recorded"
    assert any(f"user={ATTORNEY_A_ID}" in ln and "action=decline_assignment" in ln
               for ln in audit_entries(api, declined)), "decline not recorded"


def test_fr_t061_pms_afr_081(api, policy):
    """FR-T061 | PMS-AFR-081 | Assignment outcome status recorded

    The Attorney accepts the assignment: the application status is Attorney Assigned.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    assert assign_attorney(api, app).status_code == 200
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.ATTORNEY_ASSIGNED


# -- Attorney assessment ----------------------------------------------------------------


def assessing_application() -> PatentApplication:
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID,
    )


def post_opinion(api, app, recommendation=None):
    body = {"action": "opinion"}
    if recommendation is not None:
        body["recommendation"] = recommendation
    return api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/assessment", body, format="json")


def test_fr_t062_pms_afr_082(api, policy):
    """FR-T062 | PMS-AFR-082 | Attorney records legal/patentability analysis

    An Attorney who has been assigned and has accepted submits an analysis: it is stored on
    the application.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no legal/patentability analysis record or field "
        "(no model, service or endpoint stores analysis text)."
    )


def test_fr_t063_pms_afr_083(api, policy):
    """FR-T063 | PMS-AFR-083 | Attorney records prior-art search

    The Attorney records a prior-art search with database and query: the prior-art search
    record is stored.
    """
    policy()
    app = assessing_application()
    query = "resonator-coupled transmon surface code layout"
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/prior-art/search",
        {"application_id": app.id, "database": "Espacenet", "query": query}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    stored = history_payload(api, app)
    assert query in stored, "the prior-art search record was not stored"
    assert "Espacenet" in stored


def test_fr_t064_pms_afr_084(api, policy):
    """FR-T064 | PMS-AFR-084 | Attorney records novelty, non-obviousness, utility evaluations

    The Attorney submits the three evaluations: all three are stored.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no novelty / non-obviousness / utility evaluation "
        "record or field (no model, service or endpoint stores evaluations)."
    )


def test_fr_t065_pms_afr_085(api, policy):
    """FR-T065 | PMS-AFR-085 | Opinion with valid recommendation accepted

    An opinion with recommendation File Patent / Do Not File / Needs Amendment is accepted
    for each allowed value.
    """
    policy()
    assessing_application()
    for recommendation in ("File Patent", "Do Not File", "Needs Amendment"):
        app = seed_application(
            sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
            assigned_attorney_id=ATTORNEY_A_ID)
        resp = post_opinion(api, app, recommendation)
        assert resp.status_code == 200, (recommendation, resp.status_code, resp.data)


def test_fr_t066_pms_afr_085(api, policy):
    """FR-T066 | PMS-AFR-085 | Opinion with invalid or missing recommendation rejected

    An opinion with recommendation 'Maybe' (and with none) is rejected with a validation
    error.
    """
    policy()
    app = assessing_application()
    for recommendation in ("Maybe", None):
        resp = post_opinion(api, app, recommendation)
        assert resp.status_code == 422, (recommendation, resp.status_code, resp.data)


def test_fr_t067_pms_afr_086(api, policy):
    """FR-T067 | PMS-AFR-086 | Attorney requests additional information

    The Attorney submits an information request: the request is recorded.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no additional-information request record (no "
        "model, service or endpoint)."
    )


def test_fr_t068_pms_afr_087(api, policy):
    """FR-T068 | PMS-AFR-087 | Attorney requests extension

    The Attorney submits an extension request: the request is recorded.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no assessment extension-request record (no model, "
        "service or endpoint)."
    )


def test_fr_t069_pms_afr_088(api, policy):
    """FR-T069 | PMS-AFR-088 | Patentability opinion recorded

    A valid opinion is persisted with its recommendation, the Attorney and a timestamp.
    """
    policy()
    app = assessing_application()
    resp = post_opinion(api, app, "File Patent")
    assert resp.status_code == 200, (resp.status_code, resp.data)

    stored = [ln for ln in audit_entries(api, app) if "File Patent" in ln]
    assert stored, "the opinion was not persisted with its recommendation"
    assert f"user={ATTORNEY_A_ID}" in stored[0]
    datetime.datetime.fromisoformat(stored[0].split(" | ")[0])


def test_fr_t070_pms_afr_089(api, policy, mailoutbox):
    """FR-T070 | PMS-AFR-089 | Stakeholders notified after opinion

    Submitting a valid opinion triggers a notification to the relevant stakeholders (e.g.
    the Applicant).
    """
    policy()
    app = assessing_application()
    before = len(mailoutbox)
    assert post_opinion(api, app, "File Patent").status_code == 200

    sent = mails_about(mailoutbox, app, before)
    assert any(email_of(APPLICANT_ID) in m.to for m in sent), (
        "no notification reached the Applicant after the opinion")


# -- Budget ------------------------------------------------------------------------------


def budget_decision(api, app, entry, decision="APPROVE"):
    return api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": decision, "budget_entry_id": entry.id}, format="json")


def test_fr_t071_pms_afr_090(api, policy):
    """FR-T071 | PMS-AFR-090 | Director reviews budget costs

    The Director views the budget of an Approved application with a proposed budget: the
    budget cost details are returned.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    request_budget(app, "45000.00")
    detail = detail_of(api, app, DIRECTOR_ID, "director")
    entries = detail["budget_entries"]
    assert len(entries) == 1
    assert Decimal(entries[0]["amount"]) == Decimal("45000.00")
    assert entries[0]["entry_type"] == "FILING_FEE"


def test_fr_t072_pms_afr_091(api, policy):
    """FR-T072 | PMS-AFR-091 | Director approves budget

    An Approved application with a budget within the threshold and available funds: the
    Director approves and the budget is recorded as approved.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, "45000.00")
    resp = budget_decision(api, app, req)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == "APPROVED"
    assert budget_service.approved_total(app.id) == Decimal("45000.00")


def test_fr_t073_pms_afr_092(api, policy):
    """FR-T073 | PMS-AFR-092 | Filing fees included in budget

    A budget created with filing fees stores a filing fee component.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    request_budget(app, "20000.00", "FILING_FEE", "GOVERNMENT_FEE")
    entries = detail_of(api, app, DIRECTOR_ID, "director")["budget_entries"]
    assert [e["entry_type"] for e in entries] == ["FILING_FEE"]
    assert Decimal(entries[0]["amount"]) == Decimal("20000.00")


def test_fr_t074_pms_afr_093(api, policy):
    """FR-T074 | PMS-AFR-093 | Attorney fees included in budget

    A budget created with attorney fees stores an attorney fee component.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    request_budget(app, "60000.00", "ATTORNEY_FEE", "PROFESSIONAL_FEE")
    entries = detail_of(api, app, DIRECTOR_ID, "director")["budget_entries"]
    assert [e["entry_type"] for e in entries] == ["ATTORNEY_FEE"]
    assert Decimal(entries[0]["amount"]) == Decimal("60000.00")


def test_fr_t075_pms_afr_094(api, policy):
    """FR-T075 | PMS-AFR-094 | Administrative costs included in budget

    A budget created with administrative costs stores an administrative cost component.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    request_budget(app, "5000.00", "ADMIN_FEE", "ADMINISTRATIVE")
    entries = detail_of(api, app, DIRECTOR_ID, "director")["budget_entries"]
    assert [e["entry_type"] for e in entries] == ["ADMIN_FEE"]
    assert Decimal(entries[0]["amount"]) == Decimal("5000.00")


def test_fr_t076_pms_afr_095(api, policy):
    """FR-T076 | PMS-AFR-095 | Budget above threshold escalated

    With threshold T and a budget total of T+1, the Director's approval escalates the case
    to a higher authority; it is not finalized as approved by the Director alone.
    """
    threshold = Decimal("150000.00")
    policy(threshold=threshold)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, str(threshold + Decimal("0.01")))
    resp = budget_decision(api, app, req)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == "ESCALATED"
    assert PatentBudgetLedger.objects.get(pk=resp.data["id"]).entry_kind == "ESCALATION"
    assert not PatentBudgetLedger.objects.filter(application=app, status="APPROVED").exists()


def test_fr_t077_pms_afr_095(api, policy):
    """FR-T077 | PMS-AFR-095 | Budget equal to threshold not escalated

    With threshold T and a budget total of exactly T the Director approves: no escalation
    and the approval is recorded.
    """
    threshold = Decimal("150000.00")
    policy(threshold=threshold)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, str(threshold))
    resp = budget_decision(api, app, req)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == "APPROVED"
    assert not PatentBudgetLedger.objects.filter(
        application=app, entry_kind="ESCALATION").exists()
    assert budget_service.approved_total(app.id) == threshold


def test_fr_t078_pms_afr_096(api, policy):
    """FR-T078 | PMS-AFR-096 | Budget approval blocked when application not Approved

    A Director's approval of the budget of an Under Review application is rejected.
    """
    policy()
    app = under_review()
    req = request_budget(app, "45000.00")
    resp = budget_decision(api, app, req)
    assert not PatentBudgetLedger.objects.filter(
        application=app, replaces_entry=req).exists(), "a decision was recorded"
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_fr_t079_pms_afr_097(api, policy):
    """FR-T079 | PMS-AFR-097 | Approval blocked when budget not available

    With budget-availability data showing insufficient funds, the Director's approval is
    rejected with an availability error.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module holds no budget-availability data and has no "
        "availability check (no model, service, endpoint or integration), so the "
        "'insufficient funds' precondition cannot be set up."
    )


def test_fr_t080_pms_afr_098(api, policy):
    """FR-T080 | PMS-AFR-098 | Financial transactions logged with authorization level

    The Director approves a budget: the financial log entry includes the transaction
    details and the authorization level.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, "45000.00")
    assert budget_decision(api, app, req).status_code == 200

    entries = [ln for ln in audit_entries(api, app) if "action=budget_decision" in ln]
    assert len(entries) == 1, entries
    line = entries[0]
    assert f"user={DIRECTOR_ID}" in line
    assert "45000" in line and "GOVERNMENT_FEE" in line
    assert "APPROVAL" in line, "the authorization level is not logged"


# -- Filing ------------------------------------------------------------------------------


def test_fr_t081_pms_afr_099(api, policy):
    """FR-T081 | PMS-AFR-099 | Attorney prepares filing package

    The Attorney creates a filing package for an application with approvals and budget
    complete: the filing package is recorded.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no filing-package record (no model, service or "
        "endpoint); only the final external filing details can be recorded."
    )


def test_fr_t082_pms_afr_100(api, policy):
    """FR-T082 | PMS-AFR-100 | Non-compliant filing package rejected

    With patent-office format validation rules configured, a package violating a rule is
    rejected with a format compliance error.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no filing-package submission or configurable "
        "patent-office format rules; format compliance is a constant inside the filing "
        "clearance and cannot be violated through any interface."
    )


def file_application(api, app, **overrides):
    body = {
        "external_filing_id": "IN202611000777",
        "filing_date": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
        "jurisdiction": app.jurisdiction,
        "filing_office": "Indian Patent Office",
        "confirmation": "IPO-ACK-2026-000777",
    }
    body.update(overrides)
    body = {k: v for k, v in body.items() if v is not None}
    return api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", body, format="json")


def test_fr_t083_pms_afr_101(api, policy):
    """FR-T083 | PMS-AFR-101 | Record Indian Patent Office filing

    The Attorney records a filing to the Indian Patent Office for a filing-eligible
    application: the filing is recorded with office = Indian Patent Office.
    """
    policy()
    app = filing_ready(jurisdiction="IN")
    resp = file_application(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.filing_office == "Indian Patent Office"


def test_fr_t084_pms_afr_102(api, policy):
    """FR-T084 | PMS-AFR-102 | Record international filing

    The Attorney records an international filing with a justification: the international
    filing is recorded.
    """
    policy()
    app = filing_ready(jurisdiction="PCT")
    justification = "Commercial partners in EU and US justify PCT national-phase cost."
    resp = file_application(
        api, app, filing_type="international", filing_office="WIPO",
        justification=justification, external_filing_id="PCT/IN2026/050123")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.jurisdiction == "PCT"
    assert app.filing_justification == justification


def test_fr_t085_pms_afr_103(api, policy):
    """FR-T085 | PMS-AFR-103 | International filing without justification rejected

    Recording an international filing without a justification is rejected with a
    validation error.
    """
    policy()
    app = filing_ready(jurisdiction="PCT")
    resp = file_application(api, app, filing_type="international", filing_office="WIPO")
    app.refresh_from_db()
    assert app.status != sm.FILED
    assert app.external_filing_id == ""
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t086_pms_afr_104(api, policy):
    """FR-T086 | PMS-AFR-104 | Filing ID, date and confirmation captured

    Recording a filing with filing ID, filing date and confirmation stores all three
    values on the filing record.
    """
    policy()
    app = filing_ready()
    filing_date = timezone.now().date() - datetime.timedelta(days=2)
    resp = file_application(
        api, app, external_filing_id="IN202611000555", filing_date=filing_date.isoformat(),
        confirmation="IPO-ACK-2026-000555")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.external_filing_id == "IN202611000555"
    assert app.filing_date == filing_date
    assert app.filing_confirmation == "IPO-ACK-2026-000555"


def test_fr_t087_pms_afr_104(api, policy):
    """FR-T087 | PMS-AFR-104 | Filing without filing ID/date/confirmation rejected

    Recording a filing that omits the filing ID is rejected with a validation error.
    """
    policy()
    app = filing_ready()
    resp = file_application(api, app, external_filing_id=None)
    app.refresh_from_db()
    assert app.status != sm.FILED, "a filing without a filing ID was accepted"
    assert app.external_filing_id == ""
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t088_pms_afr_105(api, policy):
    """FR-T088 | PMS-AFR-105 | Status Filed after filing recorded

    Recording a valid filing for a filing-eligible application sets status Filed.
    """
    policy()
    app = filing_ready()
    resp = file_application(api, app)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == sm.FILED
    app.refresh_from_db()
    assert app.status == sm.FILED


def test_fr_t089_pms_afr_106(api, policy):
    """FR-T089 | PMS-AFR-106 | Official patent-office communication logged

    Recording an official communication from the patent office on a Filed application
    stores a communication log entry with the application, date and content.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no patent-office communication log (no model, "
        "service or endpoint for a general communication with date and content); only "
        "office actions (FR-T102) can be recorded."
    )


# -- Post-grant maintenance ----------------------------------------------------------------


def test_fr_t090_pms_afr_107(api, policy):
    """FR-T090 | PMS-AFR-107 | Post-grant tracking activates for Granted patent

    Once an application is Granted, post-grant tracking is active: the granted patent
    (with its grant date) is in the post-grant tracking set.
    """
    policy()
    app = filed_application()
    attorney = principal(ATTORNEY_A_ID, "attorney")
    app_service.transition_application(app.id, "grant", attorney)
    app.refresh_from_db()
    assert app.status == sm.GRANTED
    assert app.grant_date is not None
    assert sel.granted_applications(principal(ADMIN_ID, "pcc_admin")).filter(pk=app.id).exists()


def test_fr_t091_pms_afr_107(api, policy):
    """FR-T091 | PMS-AFR-107 | Post-grant tracking not activated for non-Granted

    For a Filed application, activating post-grant tracking is rejected and no tracking is
    created.
    """
    policy()
    app = filed_application()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.maintenance_state == ""
    assert app.renewal_requested_at is None
    assert not sel.granted_applications(principal(ADMIN_ID, "pcc_admin")).filter(
        pk=app.id).exists()
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_fr_t092_pms_afr_108(api, policy):
    """FR-T092 | PMS-AFR-108 | Maintenance schedule calculated from grant date and jurisdiction

    For a Granted patent with grant date and jurisdiction and schedule rules configured,
    the maintenance schedule dates are computed per the configured rule from the grant date.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no maintenance schedule rules or schedule "
        "calculation (the next due date is supplied by the Attorney), so no schedule can "
        "be configured or computed from grant date and jurisdiction."
    )


def test_fr_t093_pms_afr_109(api, policy):
    """FR-T093 | PMS-AFR-109 | Attorney manages maintenance reminders/deadlines

    For a Granted patent under tracking, the Attorney creates/updates a maintenance
    reminder: the reminder and deadline are stored.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no maintenance reminder record (no model, service "
        "or endpoint to create or update a reminder); reminders are only produced by the "
        "automatic deadline sweep from the stored renewal due date."
    )


def test_fr_t094_pms_afr_110(api, policy):
    """FR-T094 | PMS-AFR-110 | Maintenance action blocked without explicit renewal decision

    With an upcoming maintenance deadline and no renewal decision, the Attorney's
    maintenance action is rejected: a renewal decision is required.
    """
    policy()
    app = granted_application()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": "IPO-ANNUITY-2026-0042"}, format="json")
    app.refresh_from_db()
    assert app.maintenance_state == ""
    assert not app.renewal_history.exists()
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_fr_t095_pms_afr_111(api, policy, mailoutbox):
    """FR-T095 | PMS-AFR-111 | Attorney seeks renewal decision from Director

    The Attorney submits a renewal decision request for a Granted patent with an upcoming
    deadline: the request is recorded and routed to the Director.
    """
    policy()
    app = granted_application()
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.maintenance_state == "DECISION_REQUESTED"
    assert app.renewal_requested_at is not None
    sent = mails_about(mailoutbox, app, before)
    assert any(email_of(DIRECTOR_ID) in m.to for m in sent), (
        "the request was not routed to the Director")


def request_decision(api, app):
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)


def renewal_decision(api, app, renew):
    return api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": renew}, format="json")


def test_fr_t096_pms_afr_112(api, policy):
    """FR-T096 | PMS-AFR-112 | Director decides Renew or Do Not Renew

    With a pending renewal decision request the Director records Renew (case 1) or Do Not
    Renew (case 2): the decision is recorded.
    """
    policy()
    renew_app = granted_application()
    lapse_app = granted_application()
    for app in (renew_app, lapse_app):
        request_decision(api, app)

    resp = renewal_decision(api, renew_app, True)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    resp = renewal_decision(api, lapse_app, False)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert renew_app.renewal_history.get().decision == "RENEW"
    assert lapse_app.renewal_history.get().decision == "DO_NOT_RENEW"
    renew_app.refresh_from_db()
    lapse_app.refresh_from_db()
    assert renew_app.renewal_decision == "RENEW"
    assert lapse_app.renewal_decision == "DO_NOT_RENEW"


def test_fr_t097_pms_afr_112(api, policy):
    """FR-T097 | PMS-AFR-112 | Renewal decision outside allowed set rejected

    With a pending renewal decision request the Director's decision 'Postpone' is rejected
    with a validation error.
    """
    policy()
    app = granted_application()
    request_decision(api, app)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": "Postpone"}, format="json")
    app.refresh_from_db()
    assert app.maintenance_state == "DECISION_REQUESTED"
    assert app.renewal_decision == ""
    assert not app.renewal_history.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t098_pms_afr_113(api, policy):
    """FR-T098 | PMS-AFR-113 | Maintenance action recorded after Renew

    After a Renew decision the Attorney records the maintenance action with transaction
    information and status: the action, transaction and status are stored.
    """
    policy()
    app = granted_application()
    request_decision(api, app)
    assert renewal_decision(api, app, True).status_code == 200
    next_due = app.renewal_due_date + datetime.timedelta(days=365)

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": "IPO-ANNUITY-2026-0042", "next_due_date": next_due.isoformat()},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    entry = app.renewal_history.get()
    assert entry.action_reference == "IPO-ANNUITY-2026-0042"
    assert entry.action_recorded_at is not None
    assert entry.action_recorded_by_user_id == ATTORNEY_A_ID
    assert app.maintenance_state == "RENEWED"


def test_fr_t099_pms_afr_113(api, policy):
    """FR-T099 | PMS-AFR-113 | Maintenance action not recordable after Do Not Renew

    After a Do Not Renew decision the Attorney's maintenance action is rejected.
    """
    policy()
    app = granted_application()
    request_decision(api, app)
    assert renewal_decision(api, app, False).status_code == 200

    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": "IPO-ANNUITY-2026-0043"}, format="json")
    assert resp.status_code == 409, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.maintenance_state == "DO_NOT_RENEW"
    assert app.renewal_history.get().action_reference == ""


def complete_cycle(api, app, next_due: datetime.date):
    request_decision(api, app)
    assert renewal_decision(api, app, True).status_code == 200
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": f"IPO-ANNUITY-{next_due.isoformat()}",
         "next_due_date": next_due.isoformat()}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)


def test_fr_t100_pms_afr_114(api, policy):
    """FR-T100 | PMS-AFR-114 | Renewal history maintained

    After two completed renewal cycles, retrieving the renewal history lists both cycles.
    """
    policy()
    app = granted_application()
    first_due = app.renewal_due_date
    second_due = first_due + datetime.timedelta(days=365)
    third_due = second_due + datetime.timedelta(days=365)
    complete_cycle(api, app, second_due)
    complete_cycle(api, app, third_due)

    detail = detail_of(api, app, DIRECTOR_ID, "director")
    history = detail["renewal_history"]
    assert len(history) == 2
    assert [h["cycle_due_date"] for h in history] == [
        first_due.isoformat(), second_due.isoformat()]
    assert all(h["decision"] == "RENEW" for h in history)


def test_fr_t101_pms_afr_115(api, policy):
    """FR-T101 | PMS-AFR-115 | Next maintenance cycle scheduled after renewal

    When a renewal cycle is completed (maintenance recorded), the next maintenance
    cycle/deadline is created.
    """
    policy()
    app = granted_application()
    due_before = app.renewal_due_date
    next_due = due_before + datetime.timedelta(days=365)
    complete_cycle(api, app, next_due)

    app.refresh_from_db()
    assert app.renewal_due_date == next_due, "the next maintenance cycle was not created"
    assert app.renewal_history.get().next_due_date == next_due


# -- Office actions ------------------------------------------------------------------------


def test_fr_t102_pms_afr_116(api, policy):
    """FR-T102 | PMS-AFR-116 | Office action recorded

    Recording an office action received for a Filed application stores it against the
    application.
    """
    policy()
    app = filed_application()
    resp = record_office_action(api, app)
    assert resp.status_code == 201, (resp.status_code, resp.data)
    oa = OfficeActionRecord.objects.get(pk=resp.data["id"])
    assert oa.application_id == app.id
    assert (oa.action_code, oa.issuing_authority) == ("FER-1", "Indian Patent Office")


def test_fr_t103_pms_afr_117(api, policy):
    """FR-T103 | PMS-AFR-117 | Attorney reviews office action

    The assigned Attorney retrieves a recorded office action: its details are returned.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app).data["id"]
    detail = detail_of(api, app, ATTORNEY_A_ID, "attorney")
    shown = [o for o in detail["office_actions"] if o["id"] == oa_id]
    assert len(shown) == 1
    assert shown[0]["action_code"] == "FER-1"
    assert shown[0]["issuing_authority"] == "Indian Patent Office"
    assert shown[0]["response_deadline"]
    assert shown[0]["status"] == "RECORDED"


def test_fr_t104_pms_afr_118(api, policy):
    """FR-T104 | PMS-AFR-118 | Attorney prepares draft response

    The Attorney saves a draft response to a recorded office action: the draft response is
    stored.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app).data["id"]
    summary = "Distinguish claim 1 over D1 by resonator coupling."
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response", {"response_summary": summary},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert OfficeActionRecord.objects.get(pk=oa_id).response_summary == summary


def test_fr_t105_pms_afr_119(api, policy):
    """FR-T105 | PMS-AFR-119 | Applicant approves response

    For a draft response where the process requires Applicant review, the Applicant's
    approval is recorded.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app, requires_review=True).data["id"]
    assert api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1."}, format="json").status_code == 200
    assert OfficeActionRecord.objects.get(pk=oa_id).status == "AWAITING_APPLICANT"

    resp = api(APPLICANT_ID, "applicant").post(f"{API}/office-actions/{oa_id}/approve")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert OfficeActionRecord.objects.get(pk=oa_id).status == "APPLICANT_APPROVED"


def test_fr_t106_pms_afr_120(api, policy):
    """FR-T106 | PMS-AFR-120 | Attorney finalizes response

    For a draft response (approved if required), the Attorney finalizes it: the response is
    marked final.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no distinct finalize operation or final marker for "
        "an office-action response; saving the draft moves it straight to Response Ready "
        "(or Awaiting Applicant Approval), so a 'draft then finalize' step cannot be "
        "driven."
    )


def test_fr_t107_pms_afr_121(api, policy):
    """FR-T107 | PMS-AFR-121 | Attorney records response submission within deadline

    For a finalized response with the deadline in the future, the Attorney's submission is
    recorded.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app, days=30).data["id"]
    assert api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1."}, format="json").status_code == 200

    oa = oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)
    assert oa.response_deadline > timezone.now().date()
    assert oa.status == "SUBMITTED"
    assert oa.submitted_at is not None


def test_fr_t108_pms_afr_122(api, policy):
    """FR-T108 | PMS-AFR-122 | Extension request recorded when allowed

    For an office action whose process allows extension, the Attorney's extension request
    is recorded.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no office-action extension request (no model, "
        "service or endpoint) and no per-process 'extension allowed' setting."
    )


def test_fr_t109_pms_afr_122(api, policy):
    """FR-T109 | PMS-AFR-122 | Extension rejected when process disallows

    For an office action whose process does not allow extension, the Attorney's extension
    request is rejected.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no office-action extension request (no model, "
        "service or endpoint) and no per-process 'extension allowed' setting."
    )


def test_fr_t110_pms_afr_123(api, policy):
    """FR-T110 | PMS-AFR-123 | Response submission status tracked

    For an office action with a response, recording the submission updates the response
    status to submitted.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app).data["id"]
    assert api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1."}, format="json").status_code == 200
    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)

    detail = detail_of(api, app, APPLICANT_ID, "applicant")
    shown = [o for o in detail["office_actions"] if o["id"] == oa_id]
    assert [o["status"] for o in shown] == ["SUBMITTED"]
    assert shown[0]["submitted_at"]


def test_fr_t111_pms_afr_124(api, policy):
    """FR-T111 | PMS-AFR-124 | Office-action response deadline tracked automatically

    Recording an office action with deadline data tracks the response deadline
    automatically: it is stored and the deadline monitoring picks it up.
    """
    policy()
    app = filed_application()
    today = timezone.now().date()
    deadline = today + datetime.timedelta(days=15)
    resp = record_office_action(api, app, days=15)
    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert resp.data["response_deadline"] == deadline.isoformat()

    assert pms_sweep_deadlines()["alerts"] == 1
