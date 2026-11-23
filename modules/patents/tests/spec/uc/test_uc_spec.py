"""Spec tests for patents, UC (use case) strategy.

Generated from the frozen docs/11-patents/spec-tests/UC_DESIGN.json (107 cases).
Every test carries its test_id and source_id in its name and docstring.

Behaviour is driven through the module's public interfaces: the HTTP API where an
endpoint exists, otherwise the service layer (e.g. `submit`, `resubmit` and `grant`
transitions and `submit_response`, which have no endpoint). Preconditions that place an
application in a given state are seeded directly, as the module's own journey tests do.

Refusal status codes, where the design names none, come from
docs/01-architecture/api-conventions.md "Status codes": 409 for "the world is in the
wrong state" (illegal transition, unmet record prerequisite), 422 for invalid input or a
policy-based business-rule refusal, 403 for authenticated but not permitted, 404 for
not found or outside the caller's visibility.

A case is skipped as NOT_AUTOMATED only where the module offers no interface at all to
drive it (no endpoint, service, model, selector or task). A case whose interface exists
but does not meet the design's expected result is left to fail.
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
from modules.patents import tasks as pms_tasks
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    AppealRecord,
    ApplicationDocument,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentAuditLog,
    PatentBudgetLedger,
    PatentPolicy,
    TechnologyTransferRecord,
)
from modules.patents.services import applications as app_service
from modules.patents.services import attorney as attorney_service
from modules.patents.services import budget as budget_service
from modules.patents.services import office_actions as oa_service
from modules.patents.services import policy as policy_service
from modules.patents.services import tech_transfer as tt_service

pytestmark = pytest.mark.django_db

API = "/api/v1/patents"

APPLICANT_ID = 101
COINVENTOR_ID = 102
OTHER_APPLICANT_ID = 103
DIRECTOR_ID = 201
OTHER_DIRECTOR_ID = 202
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
MB50 = 50 * 1024 * 1024

_seq = itertools.count(1)


# -- Infrastructure -------------------------------------------------------------


def principal(user_id: int, role: str):
    """A real Principal with the registry grants for `role`, for service-level calls."""
    code, perms = ROLE_OF[role]
    return make_principal(
        user_id=user_id, roles=(code,), active_role=code,
        permissions=tuple(perms), modules=("patents",),
    )


#: The identity service's directory: everyone who appears in these cases has an email
#: address, which is where PMS-triggered notifications are sent (BR-PMS-116).
DIRECTORY = {
    uid: UserRef(user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
                 kind="faculty", email=f"u{uid}@example.edu")
    for uid in (101, 102, 103, 201, 202, 401, 402, 901)
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
    def _make(withdrawal_states=(), threshold=Decimal("150000.00"), review_days=15):
        return PatentPolicy.objects.create(
            is_active=True,
            director_review_days=review_days,
            revision_resubmission_days=60,
            cost_escalation_threshold=threshold,
            max_attorney_workload=5,
            withdrawal_eligible_states=list(withdrawal_states),
        )
    return _make


def panel_attorney(user_id: int, workload: int = 0, approved: bool = True):
    return AttorneyPanelMember.objects.create(
        user_id=user_id, firm_name=f"Firm {user_id}",
        expertise_domains=["Quantum"], is_approved_panel=approved, active_workload=workload,
    )


def seed_application(status: str, **fields) -> PatentApplication:
    """Seed an application already in `status` (precondition set-up only)."""
    defaults = {
        "user_id": APPLICANT_ID,
        "application_number": f"PMS-UC-{next(_seq):04d}",
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


def request_budget(app, amount=Decimal("45000.00"), entry_type="FILING_FEE",
                   category="GOVERNMENT_FEE") -> PatentBudgetLedger:
    return budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, entry_type, amount, category,
    )


def mails_about(mailoutbox, app, start: int = 0) -> list:
    """Messages issued since `start` that concern this application."""
    marker = app.application_number
    return [
        m for m in mailoutbox[start:]
        if marker in (m.subject or "") or marker in (m.body or "")
    ]


def mailed_to(mails, user_id: int) -> bool:
    return any(f"u{user_id}@example.edu" in m.to for m in mails)


def audit_entries(api, app) -> list[str]:
    """Audit log lines (PCC_ADMIN view) that concern this application."""
    resp = api(ADMIN_ID, "pcc_admin").get(f"{API}/audit-logs")
    assert resp.status_code == 200
    lines = [json.dumps(e, default=str) if not isinstance(e, str) else e
             for e in resp.data.get("audit_logs", [])]
    return [ln for ln in lines if app.application_number in ln]


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


def state_of(app) -> dict:
    """Everything that a refused action must leave untouched."""
    app.refresh_from_db()
    return {
        "status": app.status, "version": app.version,
        "director": app.assigned_director_id, "attorney": app.assigned_attorney_id,
        "filing": app.external_filing_id, "claims": app.claims,
        "reviews": app.reviews.count(), "documents": app.documents.count(),
        "appeals": app.appeals.count(), "budget": app.budget_entries.count(),
        "office_actions": app.office_actions.count(),
        "licensing": app.licensing_records.count(),
        "co_inventors": app.co_inventors.count(),
        "renewal": (app.renewal_decision, app.maintenance_state, app.renewal_history.count()),
    }


def pdf_file(name="spec.pdf", size=2048, body=b""):
    data = (b"%PDF-1.4\n" + body).ljust(size, b"0")
    return SimpleUploadedFile(name, data, "application/pdf")


def upload(client, app_id, file, document_type="specification"):
    return client.post(
        f"{API}/applications/{app_id}/documents",
        {"document_type": document_type, "file": file}, format="multipart",
    )


def submit(app, user_id=APPLICANT_ID):
    return app_service.transition_application(
        app.id, "submit", principal(user_id, "applicant"))


def create_payload(**over):
    body = {
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
        "co_inventors": [
            {"user_id": APPLICANT_ID, "name": "Asha Verma",
             "email": "asha@example.edu", "share_percentage": "60.00"},
            {"user_id": COINVENTOR_ID, "name": "Dr. Sarah Rao",
             "email": "sarah.rao@example.edu", "share_percentage": "40.00"},
        ],
    }
    body.update(over)
    return body


def applicant_history_payload(api, app, user_id=APPLICANT_ID) -> str:
    """What the Applicant can read about the application's history: the detail (minus the
    current status), plus the audit log if the Applicant may open it."""
    client = api(user_id, "applicant")
    detail = dict(client.get(f"{API}/applications/{app.id}").data)
    detail.pop("status", None)
    audit = client.get(f"{API}/audit-logs")
    extra = json.dumps(audit.data, default=str) if audit.status_code == 200 else ""
    return json.dumps(detail, default=str) + extra


def decide(api, app, decision, justification=GOOD_JUSTIFICATION, director=DIRECTOR_ID):
    return api(director, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": decision, "justification": justification}, format="json")


def filing_ready(consent: bool = True, budget: bool = True, jurisdiction: str = "IN",
                 status: str = sm.ASSESSMENT_IN_PROGRESS) -> PatentApplication:
    """An application the Attorney can file: attorney assigned and working the case,
    inventor agreements per `consent`, budget approved per `budget`."""
    if not AttorneyPanelMember.objects.filter(user_id=ATTORNEY_A_ID).exists():
        panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        status, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID, jurisdiction=jurisdiction,
    )
    add_coinventor(app, consent=consent)
    if budget:
        approve_budget(app)
    return app


def file_payload(**over):
    body = {
        "external_filing_id": "IN202611000123",
        "filing_date": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
        "filing_office": "Indian Patent Office",
        "confirmation": "IPO-ACK-2026-000123",
    }
    body.update(over)
    return body


def filed_application(**fields) -> PatentApplication:
    if not AttorneyPanelMember.objects.filter(user_id=ATTORNEY_A_ID).exists():
        panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        external_filing_id="IN202611000123", filing_date=timezone.now().date(), **fields,
    )


def record_office_action(api, app, requires_review: bool):
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


def granted_application(**fields) -> PatentApplication:
    if not AttorneyPanelMember.objects.filter(user_id=ATTORNEY_A_ID).exists():
        panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.GRANTED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        grant_date=timezone.now().date() - datetime.timedelta(days=700),
        renewal_due_date=timezone.now().date() + datetime.timedelta(days=20), **fields,
    )


def appeal_submitted_application():
    app = seed_application(
        sm.APPEAL_SUBMITTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=2),
    )
    AppealRecord.objects.create(
        application=app, applicant_user_id=APPLICANT_ID,
        grounds="D1 does not disclose resonator coupling.",
    )
    return app


def withdrawable(policy, origin=sm.SUBMITTED, **fields) -> PatentApplication:
    policy(withdrawal_states=[origin])
    return seed_application(origin, **fields)


def withdraw(api, app, reason):
    return api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/withdraw", {"reason": reason}, format="json")


def under_review_application(api, **fields) -> PatentApplication:
    """A Submitted application the PCC_ADMIN has assigned to the Director, so that it
    carries recorded history (Submitted, Under Review)."""
    app = seed_application(sm.SUBMITTED, **fields)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    return app


def eicar() -> bytes:
    """The standard anti-malware test string (harmless), split so it is not flagged on disk."""
    return (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$"
            b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")


def age_application(app, days: int) -> None:
    """Move the application's last-update clock `days` into the past."""
    PatentApplication.objects.filter(pk=app.pk).update(
        updated_at=timezone.now() - datetime.timedelta(days=days))


def test_uc_t001_uc_pms_001_main_flow(api, policy, mailoutbox):
    """UC-T001 | UC-PMS-001 Main Flow | Verify a complete application with valid documents is
    accepted and submitted.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    created = client.post(f"{API}/applications", create_payload(), format="json")
    assert created.status_code == 201, created.data
    app = PatentApplication.objects.get(pk=created.data["id"])
    assert app.status == sm.DRAFT
    up = upload(client, app.id, pdf_file(size=2 * 1024 * 1024))
    assert up.status_code == 201, up.data
    assert up.data["sensitivity_level"], "document is not classified by sensitivity"

    before = len(mailoutbox)
    submit(app)
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert app.application_number
    assert PatentApplication.objects.filter(
        application_number=app.application_number).count() == 1
    logs = audit_entries(api, app)
    assert any(sm.DRAFT in ln and sm.SUBMITTED in ln for ln in logs), logs
    assert mails_about(mailoutbox, app, before), "no submission notification was triggered"


def test_uc_t002_uc_pms_001_alternative_flow_1(policy):
    """UC-T002 | UC-PMS-001 Alternative Flow 1 | Verify incomplete required information keeps the
    application unsubmitted.
    """
    policy()
    app = seed_application(sm.DRAFT, claims="")
    before = state_of(app)
    status = refusal_status(lambda: submit(app))
    assert state_of(app) == before
    assert app.status != sm.SUBMITTED
    assert status == 422, "an application with missing claims was accepted"


def test_uc_t003_uc_pms_001_alternative_flow_2(api, policy):
    """UC-T003 | UC-PMS-001 Alternative Flow 2 | Verify a document failing format, size or malware
    validation is rejected.
    """
    policy()
    app = seed_application(sm.DRAFT)
    client = api(APPLICANT_ID, "applicant")
    before = state_of(app)
    invalid = {
        "non-PDF document": SimpleUploadedFile(
            "spec.docx", b"PK\x03\x04" + b"0" * 2048, "application/octet-stream"),
        "PDF of 50 MB": pdf_file(size=MB50),
        "PDF flagged as malware": pdf_file(body=eicar()),
    }
    observed = {label: upload(client, app.id, f).status_code for label, f in invalid.items()}
    assert observed == dict.fromkeys(invalid, 422), observed
    assert state_of(app) == before, "an invalid document was retained"


def test_uc_t004_uc_pms_001_exception_flow_1():
    """UC-T004 | UC-PMS-001 Exception Flow 1 | Verify the application is not accepted when an
    external validation dependency is unavailable.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no malware-scanning service, setting or hook, so an "
        "'unavailable scanner' cannot be configured or simulated through any interface")


def test_uc_t005_uc_pms_002_main_flow(api, policy):
    """UC-T005 | UC-PMS-002 Main Flow | Verify Applicant can view current status, progress and
    history of own application.
    """
    policy()
    app = under_review_application(api)
    assert decide(api, app, "NEEDS_REVISION").status_code == 200
    before, logs_before = state_of(app), PatentAuditLog.objects.count()

    resp = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200
    assert resp.data["status"] == sm.NEEDS_REVISION
    history = applicant_history_payload(api, app)
    for earlier in (sm.SUBMITTED, sm.UNDER_REVIEW):
        assert earlier in history, f"recorded history does not show {earlier}"
    assert state_of(app) == before
    assert PatentAuditLog.objects.count() == logs_before


def test_uc_t006_uc_pms_002_alternative_flow_1(api, policy):
    """UC-T006 | UC-PMS-002 Alternative Flow 1 | Verify Applicant can navigate among their own
    applications and history entries.
    """
    policy()
    first = under_review_application(api)
    second = under_review_application(api)
    client = api(APPLICANT_ID, "applicant")
    listing = client.get(f"{API}/applications")
    assert listing.status_code == 200
    rows = {row["id"]: row for row in listing.data["results"]}
    before = [state_of(first), state_of(second)]
    logs_before = PatentAuditLog.objects.count()

    for app in (first, second):
        assert rows[app.id]["status"] == sm.UNDER_REVIEW
        resp = client.get(f"{API}/applications/{app.id}")
        assert resp.status_code == 200
        assert resp.data["status"] == sm.UNDER_REVIEW
        history = applicant_history_payload(api, app)
        assert sm.SUBMITTED in history, "history entries are not displayed"
    assert [state_of(first), state_of(second)] == before
    assert PatentAuditLog.objects.count() == logs_before


def test_uc_t007_uc_pms_002_exception_flow_1(api, policy):
    """UC-T007 | UC-PMS-002 Exception Flow 1 | Verify access to an unauthorized application record
    is blocked.
    """
    policy()
    app = seed_application(sm.SUBMITTED, user_id=OTHER_APPLICANT_ID)
    before, logs_before = state_of(app), PatentAuditLog.objects.count()
    resp = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 404, resp.data
    assert app.title not in json.dumps(resp.data, default=str)
    assert state_of(app) == before
    assert PatentAuditLog.objects.count() == logs_before


def test_uc_t008_uc_pms_003_main_flow(api, policy, mailoutbox):
    """UC-T008 | UC-PMS-003 Main Flow | Verify Applicant can add inventors with valid ownership
    shares and agreements.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    before = len(mailoutbox)
    created = client.post(f"{API}/applications", create_payload(), format="json")
    assert created.status_code == 201, created.data
    app = PatentApplication.objects.get(pk=created.data["id"])
    stored = {ci.user_id: ci.share_percentage for ci in app.co_inventors.all()}
    assert stored == {APPLICANT_ID: Decimal("60.00"), COINVENTOR_ID: Decimal("40.00")}

    for user_id in (APPLICANT_ID, COINVENTOR_ID):
        resp = api(user_id, "applicant").post(f"{API}/applications/{app.id}/consent")
        assert resp.status_code == 200, resp.data
        assert resp.data["consent_recorded"] is True
    detail = client.get(f"{API}/applications/{app.id}").data
    assert [ci["consent_granted"] for ci in detail["co_inventors"]] == [True, True]
    assert mailed_to(mails_about(mailoutbox, app, before), COINVENTOR_ID), (
        "the affected inventor was not notified of the inventor change")


def test_uc_t009_uc_pms_003_alternative_flow_1():
    """UC-T009 | UC-PMS-003 Alternative Flow 1 | Verify Applicant can update the inventor set or
    ownership shares before filing.
    """
    pytest.skip(
        "NOT_AUTOMATED: no endpoint or service changes an existing application's inventor "
        "set or ownership shares (PUT applications/<id> takes only title, abstract, "
        "description, claims and domain_category)")


def test_uc_t010_uc_pms_003_exception_flow_1(api, policy):
    """UC-T010 | UC-PMS-003 Exception Flow 1 | Verify invalid inventor data or ownership
    percentages are not accepted.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    first = client.post(f"{API}/applications", create_payload(), format="json")
    assert first.status_code == 201, first.data
    app = PatentApplication.objects.get(pk=first.data["id"])
    inventors = list(app.co_inventors.order_by("id").values_list("user_id", "share_percentage"))
    count = PatentApplication.objects.count()

    def person(uid, share):
        return {"user_id": uid, "name": f"Inventor {uid}",
                "email": f"i{uid}@example.edu", "share_percentage": share}

    bad_sets = {
        "total 90": [person(101, "50.00"), person(102, "40.00")],
        "total 110": [person(101, "60.00"), person(102, "50.00")],
        "zero share": [person(101, "100.00"), person(102, "0.00")],
    }
    observed = {
        label: client.post(
            f"{API}/applications", create_payload(co_inventors=people), format="json"
        ).status_code
        for label, people in bad_sets.items()
    }
    assert PatentApplication.objects.count() == count, "an invalid inventor set was committed"
    assert list(app.co_inventors.order_by("id").values_list(
        "user_id", "share_percentage")) == inventors
    assert observed == dict.fromkeys(bad_sets, 422), observed


def test_uc_t011_uc_pms_004_main_flow():
    """UC-T011 | UC-PMS-004 Main Flow | Verify prior-art search returns ranked results and selected
    references attach to the application.
    """
    pytest.skip(
        "NOT_AUTOMATED: POST prior-art/search is a stub that returns an empty result list "
        "for any query: there is no search source to rank results from and no interface "
        "to select and attach references to an application or to read a search session log")


def test_uc_t012_uc_pms_004_alternative_flow_1():
    """UC-T012 | UC-PMS-004 Alternative Flow 1 | Verify Actor may refine keywords/classification
    and repeat the search.
    """
    pytest.skip(
        "NOT_AUTOMATED: POST prior-art/search is a stub with no search source, ranking, "
        "keyword/classification refinement or search-session log to observe")


def test_uc_t013_uc_pms_004_exception_flow_1(api, policy):
    """UC-T013 | UC-PMS-004 Exception Flow 1 | Verify an unavailable external source is not
    represented as queried.
    """
    policy()
    app = seed_application(sm.DRAFT)
    before = state_of(app)
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/prior-art/search", {"query": "surface code transmon"}, format="json")
    if resp.status_code < 400:
        assert resp.data.get("results") == [], "results were fabricated"
        body = json.dumps(resp.data).lower()
        assert not any(w in body for w in ("success", "queried", "completed")), body
    assert state_of(app) == before


def test_uc_t014_uc_pms_005_main_flow(api, policy):
    """UC-T014 | UC-PMS-005 Main Flow | Verify Applicant can revise and resubmit an application
    within the 60-day period.
    """
    policy()
    app = seed_application(
        sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=10))
    app.reviews.create(
        director_user_id=DIRECTOR_ID, decision="NEEDS_REVISION",
        justification="Claim 1 overlaps prior art D1; narrow it to the coupled variant.")
    client = api(APPLICANT_ID, "applicant")
    assert upload(client, app.id, pdf_file()).status_code == 201
    version_before = PatentApplication.objects.get(pk=app.id).version

    revised = "1. A resonator-coupled circuit comprising at least five transmons."
    put = client.put(f"{API}/applications/{app.id}", {"claims": revised}, format="json")
    assert put.status_code == 200, put.data
    revision = upload(client, app.id, pdf_file(body=b"revised"))
    assert revision.status_code == 201, revision.data
    assert revision.data["version"] == 2
    app_service.transition_application(app.id, "resubmit", principal(APPLICANT_ID, "applicant"))

    app.refresh_from_db()
    assert app.status == sm.RESUBMITTED
    assert app.version > version_before
    assert app.claims == revised
    assert sorted(app.documents.values_list("version", flat=True)) == [1, 2]
    # A new review cycle: the PCC_ADMIN can now assign a Director to the resubmission.
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW


def test_uc_t015_uc_pms_005_alternative_flow_1(api, policy):
    """UC-T015 | UC-PMS-005 Alternative Flow 1 | Verify Applicant may save revisions before final
    resubmission.
    """
    policy()
    app = seed_application(
        sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=10))
    reviews = app.reviews.count()
    revised = "1. A resonator-coupled circuit comprising at least five transmons."
    resp = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}", {"claims": revised}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.claims == revised
    assert app.status == sm.NEEDS_REVISION
    assert app.reviews.count() == reviews
    assert not in_active_queue(app), "a new review cycle was started"


def test_uc_t016_uc_pms_005_exception_flow_1(api, policy):
    """UC-T016 | UC-PMS-005 Exception Flow 1 | Verify a late resubmission is rejected and the
    application expires.
    """
    policy()
    observed = {}
    for origin in (sm.NEEDS_REVISION, sm.REJECTED):
        app = seed_application(
            origin, assigned_director_id=DIRECTOR_ID,
            decision_date=timezone.now() - datetime.timedelta(days=61))
        refused = refusal_status(lambda app=app: app_service.transition_application(
            app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
        app.refresh_from_db()
        observed[origin] = (refused, app.status)
    expected = dict.fromkeys((sm.NEEDS_REVISION, sm.REJECTED), (422, sm.EXPIRED))
    assert observed == expected, observed


def test_uc_t017_uc_pms_005_exception_flow_2(api, policy):
    """UC-T017 | UC-PMS-005 Exception Flow 2 | Verify a revision not addressing Director feedback
    is rejected.
    """
    policy()
    app = seed_application(
        sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=5))
    app.reviews.create(
        director_user_id=DIRECTOR_ID, decision="NEEDS_REVISION",
        justification="Claim 1 overlaps prior art D1; narrow it to the coupled variant.")
    before = state_of(app)
    # The Applicant revised nothing, so the recorded feedback is not addressed.
    status = refusal_status(lambda: app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
    assert state_of(app) == before
    assert app.status == sm.NEEDS_REVISION
    assert status == 422, "a revision that ignores the Director feedback was accepted"


def test_uc_t018_uc_pms_006_main_flow(api, policy):
    """UC-T018 | UC-PMS-006 Main Flow | Verify Applicant can withdraw a withdrawal-eligible
    pre-filing application.
    """
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    assert in_active_queue(app)
    reason = "Withdrawing to fold this into a broader continuation filing."
    resp = withdraw(api, app, reason)
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert not in_active_queue(app)
    history = history_payload(api, app)
    assert reason in history, "withdrawal reason not recorded"
    assert sm.UNDER_REVIEW in history and sm.WITHDRAWN in history


def test_uc_t019_uc_pms_006_alternative_flow_1(api, policy):
    """UC-T019 | UC-PMS-006 Alternative Flow 1 | Verify co-inventor consent is recorded when the
    process requires it.
    """
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    add_coinventor(app, consent=False)
    reason = "Withdrawing to fold this into a broader continuation filing."
    consent = api(COINVENTOR_ID, "applicant").post(f"{API}/applications/{app.id}/consent")
    assert consent.status_code == 200, consent.data
    assert consent.data["consent_recorded"] is True
    resp = withdraw(api, app, reason)
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN
    assert app.co_inventors.get().consent_granted is True
    history = history_payload(api, app)
    assert reason in history, "withdrawal history not recorded"
    assert "1/1 granted" in history, "co-inventor consent not part of the withdrawal history"


def test_uc_t020_uc_pms_006_exception_flow_1(api, policy):
    """UC-T020 | UC-PMS-006 Exception Flow 1 | Verify withdrawal is blocked for a non-eligible
    status.
    """
    policy(withdrawal_states=sorted(sm.PRE_FILING_STATES))
    app = seed_application(
        sm.FILED, external_filing_id="IN202611000123", filing_date=timezone.now().date())
    before = state_of(app)
    resp = withdraw(api, app, "No longer commercially relevant.")
    assert state_of(app) == before
    assert app.status == sm.FILED
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_uc_t021_uc_pms_007_main_flow(api, policy, mailoutbox):
    """UC-T021 | UC-PMS-007 Main Flow | Verify PCC_ADMIN assigns a Submitted application to an
    eligible Director.
    """
    policy(review_days=15)
    app = seed_application(sm.SUBMITTED)
    before = len(mailoutbox)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == sm.UNDER_REVIEW
    assert resp.data["assigned_director_id"] == DIRECTOR_ID
    assert mailed_to(mails_about(mailoutbox, app, before), DIRECTOR_ID), (
        "the Director was not notified of the assignment")
    assert any("assign_director" in ln for ln in audit_entries(api, app))

    # The 15-day review deadline is running: the deadline sweep flags it only once passed.
    age_application(app, 14)
    assert pms_tasks.pms_sweep_deadlines()["overdue_reviews"] == 0
    age_application(app, 16)
    assert pms_tasks.pms_sweep_deadlines()["overdue_reviews"] == 1


def test_uc_t022_uc_pms_007_alternative_flow_1():
    """UC-T022 | UC-PMS-007 Alternative Flow 1 | Verify configured automatic routing assigns the
    application using the same rules.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no automatic-routing configuration or trigger; "
        "Director assignment exists only as the manual PCC_ADMIN assign-director action")


def test_uc_t023_uc_pms_007_exception_flow_1(api, policy, mailoutbox):
    """UC-T023 | UC-PMS-007 Exception Flow 1 | Verify application stays Submitted when no eligible
    assignment exists.
    """
    policy()
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, consent=False, user_id=OTHER_DIRECTOR_ID)
    before = state_of(app)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director",
        {"director_id": OTHER_DIRECTOR_ID}, format="json")
    assert state_of(app) == before
    assert app.status == sm.SUBMITTED and app.assigned_director_id is None
    assert resp.status_code == 422, (resp.status_code, resp.data)
    raised = audit_entries(api, app) or mailed_to(mails_about(mailoutbox, app), ADMIN_ID)
    assert raised, "no exceptional case was recorded or raised for the PCC_ADMIN"


def test_uc_t024_uc_pms_008_main_flow(api, policy):
    """UC-T024 | UC-PMS-008 Main Flow | Verify assigned Director can approve with a justification
    of at least 50 characters.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = under_review_application(api)
    resp = decide(api, app, "APPROVE")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.APPROVED
    assert app.reviews.get().justification == GOOD_JUSTIFICATION
    logs = audit_entries(api, app)
    assert any(sm.UNDER_REVIEW in ln and sm.APPROVED in ln for ln in logs), logs
    offered = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert offered.status_code == 200, offered.data
    assert offered.data["status"] == sm.ASSIGNMENT_OFFERED


def test_uc_t025_uc_pms_008_alternative_flow_1(api, policy, mailoutbox):
    """UC-T025 | UC-PMS-008 Alternative Flow 1 | Verify Reject outcome is recorded and feedback
    sent to Applicant.
    """
    policy()
    app = under_review_application(api)
    reason = "The claimed layout is anticipated by D1 and lacks an inventive step overall."
    before = len(mailoutbox)
    resp = decide(api, app, "REJECT", reason)
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.REJECTED
    logs = audit_entries(api, app)
    assert any(sm.UNDER_REVIEW in ln and sm.REJECTED in ln for ln in logs), logs
    seen = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert any(r["justification"] == reason for r in seen.data["reviews"])
    sent = mails_about(mailoutbox, app, before)
    assert mailed_to(sent, APPLICANT_ID) and any(reason in m.body for m in sent), (
        "detailed feedback was not sent to the Applicant")


def test_uc_t026_uc_pms_008_alternative_flow_1(api, policy, mailoutbox):
    """UC-T026 | UC-PMS-008 Alternative Flow 1 | Verify Needs Revision outcome is recorded and
    feedback sent to Applicant.
    """
    policy()
    app = under_review_application(api)
    reason = "Claim 1 overlaps prior art D1; narrow it to the resonator-coupled variant."
    before = len(mailoutbox)
    resp = decide(api, app, "NEEDS_REVISION", reason)
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    logs = audit_entries(api, app)
    assert any(sm.UNDER_REVIEW in ln and sm.NEEDS_REVISION in ln for ln in logs), logs
    seen = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert any(r["justification"] == reason for r in seen.data["reviews"])
    sent = mails_about(mailoutbox, app, before)
    assert mailed_to(sent, APPLICANT_ID) and any(reason in m.body for m in sent), (
        "detailed feedback was not sent to the Applicant")


def test_uc_t027_uc_pms_008_exception_flow_1(api, policy):
    """UC-T027 | UC-PMS-008 Exception Flow 1 | Verify a decision without required justification is
    not accepted.
    """
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    before = state_of(app)
    observed = {}
    for label, text in (("short", "Looks novel enough."), ("empty", "")):
        assert len(text) < 50
        observed[label] = decide(api, app, "APPROVE", text).status_code
    assert state_of(app) == before
    assert observed == {"short": 422, "empty": 422}, observed


def test_uc_t028_uc_pms_008_exception_flow_2(api, policy):
    """UC-T028 | UC-PMS-008 Exception Flow 2 | Verify a conflicted or unassigned Director cannot
    submit a decision.
    """
    policy()
    outcomes = {}
    for label, actor_id in (
        ("unassigned Director", OTHER_DIRECTOR_ID),
        ("Director who is a co-inventor", COINVENTOR_ID),
        ("Director who is the author", APPLICANT_ID),
    ):
        app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
        add_coinventor(app, consent=False, user_id=COINVENTOR_ID)
        before = state_of(app)
        status = decide(api, app, "APPROVE", director=actor_id).status_code
        outcomes[label] = (status, state_of(app) == before)
    assert outcomes == {
        "unassigned Director": (404, True),
        "Director who is a co-inventor": (403, True),
        "Director who is the author": (403, True),
    }, outcomes


def test_uc_t029_uc_pms_009_main_flow(api, policy, mailoutbox):
    """UC-T029 | UC-PMS-009 Main Flow | Verify Director approves a within-threshold budget for an
    Approved application.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = [
        request_budget(app, Decimal("20000.00"), "FILING_FEE", "GOVERNMENT_FEE"),
        request_budget(app, Decimal("60000.00"), "ATTORNEY_FEE", "PROFESSIONAL_FEE"),
        request_budget(app, Decimal("5000.00"), "ADMIN_FEE", "ADMINISTRATIVE"),
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
        assert row.status == "APPROVED" and row.entry_kind == "APPROVAL"
        assert row.authorized_by_user_id == DIRECTOR_ID
        assert row.amount == row.replaces_entry.amount and row.currency
    lines = [ln for ln in audit_entries(api, app) if "action=budget_decision" in ln]
    assert len(lines) == 3 and all(f"user={DIRECTOR_ID}" in ln for ln in lines), lines
    assert mails_about(mailoutbox, app, before), "no budget notification was triggered"


def test_uc_t030_uc_pms_009_alternative_flow_1(api, policy, mailoutbox):
    """UC-T030 | UC-PMS-009 Alternative Flow 1 | Verify Director can record Budget Rejected for a
    within-threshold cost.
    """
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, Decimal("45000.00"))
    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "REJECT", "budget_entry_id": req.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "REJECTED"
    row = PatentBudgetLedger.objects.get(application=app, replaces_entry=req)
    assert row.status == "REJECTED" and row.authorized_by_user_id == DIRECTOR_ID
    lines = [ln for ln in audit_entries(api, app) if "action=budget_decision" in ln]
    assert len(lines) == 1 and "REJECTED" in lines[0] and f"user={DIRECTOR_ID}" in lines[0]
    assert mails_about(mailoutbox, app, before), "no budget notification was triggered"


def test_uc_t031_uc_pms_009_alternative_flow_2(api, policy, mailoutbox):
    """UC-T031 | UC-PMS-009 Alternative Flow 2 | Verify above-threshold cost is escalated instead
    of decided.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, Decimal("200000.00"))
    assert req.amount > Decimal("150000.00")
    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "APPROVE", "budget_entry_id": req.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "ESCALATED"
    row = PatentBudgetLedger.objects.get(pk=resp.data["id"])
    assert row.entry_kind == "ESCALATION" and row.replaces_entry_id == req.id
    assert not PatentBudgetLedger.objects.filter(application=app, status="APPROVED").exists()
    assert not PatentBudgetLedger.objects.filter(application=app, status="REJECTED").exists()
    assert budget_service.approved_total(app.id) == Decimal("0")
    assert mails_about(mailoutbox, app, before), "the escalation was not notified"


def test_uc_t032_uc_pms_009_exception_flow_1():
    """UC-T032 | UC-PMS-009 Exception Flow 1 | Verify approval is not recorded when
    budget-availability validation fails.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module holds no budget-availability data (no budget pool, "
        "allocation or balance): the ledger records only requests and decisions, so "
        "'availability data available and insufficient' cannot be set up or validated")


def test_uc_t033_uc_pms_010_main_flow(api, policy, mailoutbox):
    """UC-T033 | UC-PMS-010 Main Flow | Verify PCC_ADMIN assigns an approved-panel Attorney to an
    Approved application.
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
    app.refresh_from_db()
    assert app.assigned_attorney_id == ATTORNEY_A_ID
    assert mailed_to(mails_about(mailoutbox, app, before), ATTORNEY_A_ID), (
        "the Attorney was not notified of the offered assignment")


def test_uc_t034_uc_pms_010_alternative_flow_1(api, policy):
    """UC-T034 | UC-PMS-010 Alternative Flow 1 | Verify Applicant-preferred Attorney is considered
    only when in the approved panel.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    panel_attorney(ATTORNEY_B_ID, approved=False)
    panel_app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    other_app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    admin = api(ADMIN_ID, "pcc_admin")
    # The Applicant's stated preferences are the two Attorneys assigned below.
    before = state_of(other_app)
    blocked = admin.post(
        f"{API}/applications/{other_app.id}/assign-attorney",
        {"attorney_id": ATTORNEY_B_ID}, format="json")
    assert state_of(other_app) == before, "a non-panel Attorney was recorded"
    # The design names no code: a refused rule is a 409 or a 422, never an acceptance.
    assert blocked.status_code in (409, 422), (blocked.status_code, blocked.data)

    allowed = admin.post(
        f"{API}/applications/{panel_app.id}/assign-attorney",
        {"attorney_id": ATTORNEY_A_ID}, format="json")
    assert allowed.status_code == 200, allowed.data
    panel_app.refresh_from_db()
    assert panel_app.status == sm.ASSIGNMENT_OFFERED
    assert panel_app.assigned_attorney_id == ATTORNEY_A_ID


def test_uc_t035_uc_pms_010_alternative_flow_2():
    """UC-T035 | UC-PMS-010 Alternative Flow 2 | Verify a recorded institutional exception permits
    a non-panel Attorney.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no institutional-exception record or interface; "
        "attorney assignment accepts approved panel members only, so a non-panel assignment "
        "under a recorded exception cannot be set up")


def test_uc_t036_uc_pms_010_exception_flow_1(api, policy):
    """UC-T036 | UC-PMS-010 Exception Flow 1 | Verify assignment is not recorded when
    conflict-of-interest constraint fails.
    """
    policy()
    panel_attorney(COINVENTOR_ID)   # on the panel, but also an inventor of this application
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    add_coinventor(app, consent=False, user_id=COINVENTOR_ID)
    before = state_of(app)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": COINVENTOR_ID},
        format="json")
    assert state_of(app) == before, "an Attorney with a conflict of interest was assigned"
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_uc_t037_uc_pms_011_main_flow(api, policy):
    """UC-T037 | UC-PMS-011 Main Flow | Verify Attorney acceptance sets Attorney Assigned."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    offer = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert offer.status_code == 200, offer.data
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.ATTORNEY_ASSIGNED
    assert app.assigned_attorney_id == ATTORNEY_A_ID
    logs = audit_entries(api, app)
    assert any("accept_assignment" in ln and sm.ATTORNEY_ASSIGNED in ln for ln in logs), logs


def test_uc_t038_uc_pms_011_alternative_flow_1(api, policy, mailoutbox):
    """UC-T038 | UC-PMS-011 Alternative Flow 1 | Verify Attorney decline records Pending Review and
    notifies PCC_ADMIN.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    offer = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert offer.status_code == 200, offer.data
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "decline"},
        format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.PENDING_REVIEW
    logs = audit_entries(api, app)
    assert any("decline_assignment" in ln and sm.PENDING_REVIEW in ln for ln in logs), logs
    assert mailed_to(mails_about(mailoutbox, app, before), ADMIN_ID), (
        "the PCC_ADMIN was not notified of the decline")


def test_uc_t039_uc_pms_011_exception_flow_1(api, policy):
    """UC-T039 | UC-PMS-011 Exception Flow 1 | Verify response without an active assignment is not
    accepted.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID)
    panel_attorney(ATTORNEY_B_ID)
    app = seed_application(
        sm.ASSIGNMENT_OFFERED, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_B_ID)
    before = state_of(app)
    workloads = list(AttorneyPanelMember.objects.order_by("id").values_list("active_workload"))
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"}, format="json")
    assert state_of(app) == before
    assert list(AttorneyPanelMember.objects.order_by("id").values_list(
        "active_workload")) == workloads
    assert resp.status_code == 404, (resp.status_code, resp.data)


def test_uc_t040_uc_pms_012_main_flow(api, policy, mailoutbox):
    """UC-T040 | UC-PMS-012 Main Flow | Verify Attorney records patentability opinion with a
    supported recommendation.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID)
    marker = "OPINION-MARKER-7731"
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/assessment", {
        "action": "record_opinion",
        "novelty": "Novel over D1 and D2.",
        "non_obviousness": "Inventive step supported by the coupling arrangement.",
        "utility": "Industrially applicable to fault-tolerant qubit arrays.",
        "opinion": f"{marker}: claims 1-5 are patentable as drafted.",
        "recommendation": "File Patent",
    }, format="json")
    assert resp.status_code == 200, resp.data
    stored = history_payload(api, app)
    assert marker in stored and "File Patent" in stored, "the opinion was not recorded"
    sent = mails_about(mailoutbox, app, before)
    assert sent, "relevant stakeholders were not notified"


def test_uc_t041_uc_pms_012_alternative_flow_1(api, policy):
    """UC-T041 | UC-PMS-012 Alternative Flow 1 | Verify Attorney may request additional information
    or extension.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID)
    marker = "INFO-REQUEST-MARKER-5512"
    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/assessment", {
        "action": "request_information",
        "request": f"{marker}: need the lab notebook entries and a 30-day extension.",
    }, format="json")
    assert resp.status_code == 200, resp.data
    assert marker in history_payload(api, app), "the request was not recorded"


def test_uc_t042_uc_pms_012_exception_flow_1(api, policy):
    """UC-T042 | UC-PMS-012 Exception Flow 1 | Verify opinion without a supported recommendation is
    not finalized.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID)
    client = api(ATTORNEY_A_ID, "attorney")
    marker = "PRIOR-OPINION-MARKER-2290"
    valid = client.post(f"{API}/applications/{app.id}/assessment", {
        "action": "record_opinion", "opinion": f"{marker}: patentable.",
        "recommendation": "File Patent"}, format="json")
    assert valid.status_code == 200, valid.data
    before = state_of(app)

    observed = {
        "no recommendation": client.post(f"{API}/applications/{app.id}/assessment", {
            "action": "record_opinion", "opinion": "Opinion without a recommendation."},
            format="json").status_code,
        "unsupported recommendation": client.post(
            f"{API}/applications/{app.id}/assessment", {
                "action": "record_opinion", "opinion": "Unsupported value.",
                "recommendation": "Maybe File"}, format="json").status_code,
    }
    assert observed == {"no recommendation": 422, "unsupported recommendation": 422}, observed
    assert state_of(app) == before
    assert marker in history_payload(api, app), "the prior legal-review record was lost"


def test_uc_t043_uc_pms_013_main_flow(api, policy, mailoutbox):
    """UC-T043 | UC-PMS-013 Main Flow | Verify national filing is recorded and status set to Filed.

    """
    policy()
    app = filing_ready()
    payload = file_payload()
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", payload, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == payload["external_filing_id"]
    assert app.filing_date.isoformat() == payload["filing_date"]
    assert app.filing_confirmation == payload["confirmation"]
    logs = audit_entries(api, app)
    assert any(sm.ASSESSMENT_IN_PROGRESS in ln and sm.FILED in ln for ln in logs), logs
    assert mails_about(mailoutbox, app, before), "no filing confirmation was triggered"


def test_uc_t044_uc_pms_013_alternative_flow_1(api, policy):
    """UC-T044 | UC-PMS-013 Alternative Flow 1 | Verify international filing requires additional
    justification.
    """
    policy()
    app = filing_ready(jurisdiction="IN")
    client = api(ATTORNEY_A_ID, "attorney")
    payload = file_payload(jurisdiction="PCT", filing_type="international",
                           external_filing_id="PCT/IN2026/050123")
    before = state_of(app)
    refused = client.post(f"{API}/applications/{app.id}/filing", payload, format="json")
    assert state_of(app) == before, "an unjustified international filing was recorded"
    assert refused.status_code == 422, (refused.status_code, refused.data)

    justification = "Commercial partners in EU and US justify PCT national-phase cost."
    accepted = client.post(
        f"{API}/applications/{app.id}/filing",
        {**payload, "justification": justification}, format="json")
    assert accepted.status_code == 200, accepted.data
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == payload["external_filing_id"]
    assert app.filing_justification == justification


def test_uc_t045_uc_pms_013_exception_flow_1(api, policy):
    """UC-T045 | UC-PMS-013 Exception Flow 1 | Verify filing is blocked when a prerequisite is
    missing.
    """
    policy()
    observed = {}
    for label, kwargs in (("agreements incomplete", {"consent": False}),
                          ("budget approval missing", {"budget": False})):
        app = filing_ready(**kwargs)
        before = state_of(app)
        resp = api(ATTORNEY_A_ID, "attorney").post(
            f"{API}/applications/{app.id}/filing", file_payload(), format="json")
        observed[label] = (resp.status_code, state_of(app) == before, app.status == sm.FILED)
    assert observed == {
        "agreements incomplete": (409, True, False),
        "budget approval missing": (409, True, False),
    }, observed


def test_uc_t046_uc_pms_013_exception_flow_2(api, policy):
    """UC-T046 | UC-PMS-013 Exception Flow 2 | Verify filing is not recorded as Filed without
    external confirmation.
    """
    policy()
    app = filing_ready()
    before = state_of(app)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", {}, format="json")
    app.refresh_from_db()
    assert app.status != sm.FILED, "a filing without confirmation was recorded as Filed"
    assert state_of(app) == before
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_uc_t047_uc_pms_014_main_flow(api, policy, mailoutbox):
    """UC-T047 | UC-PMS-014 Main Flow | Verify recording an office action logs it and creates
    office-action tracking.
    """
    policy()
    app = filed_application()
    before = len(mailoutbox)
    today = timezone.now().date()
    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/office-actions", {
        "action_code": "FER-1",
        "issuing_authority": "Indian Patent Office",
        "issued_date": today.isoformat(),
        "response_deadline": (today + datetime.timedelta(days=180)).isoformat(),
        "requires_applicant_review": False,
        "document_id": "IPO-DOC-2026-0042",
    }, format="json")
    assert resp.status_code == 201, resp.data
    oa = OfficeActionRecord.objects.get(pk=resp.data["id"])
    assert oa.application_id == app.id and oa.action_code == "FER-1"
    assert oa.status == "RECORDED", "office-action tracking was not created"
    assert any("office_action_recorded" in ln for ln in audit_entries(api, app))
    assert mails_about(mailoutbox, app, before), "no office-action notification was triggered"


def test_uc_t048_uc_pms_014_alternative_flow_1():
    """UC-T048 | UC-PMS-014 Alternative Flow 1 | Verify non-office-action communication is recorded
    without response path.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module records office actions only (POST applications/<id>/"
        "office-actions); it has no communication-type field or interface for logging a "
        "non-office-action official communication")


def test_uc_t049_uc_pms_014_exception_flow_1(api, policy):
    """UC-T049 | UC-PMS-014 Exception Flow 1 | Verify invalid/unrelated communication data is not
    attached to another application.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    own = seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID)
    other = seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_B_ID)
    before = (state_of(own), state_of(other))
    today = timezone.now().date()
    body = {
        "action_code": "FER-1", "issuing_authority": "Indian Patent Office",
        "issued_date": today.isoformat(),
        "response_deadline": (today + datetime.timedelta(days=180)).isoformat(),
    }
    client = api(ATTORNEY_A_ID, "attorney")
    observed = {
        "another application": client.post(
            f"{API}/applications/{other.id}/office-actions", body,
            format="json").status_code,
        "unknown application": client.post(
            f"{API}/applications/999999/office-actions", body, format="json").status_code,
    }
    assert observed == {"another application": 404, "unknown application": 404}, observed
    assert (state_of(own), state_of(other)) == before
    assert not OfficeActionRecord.objects.exists()


def test_uc_t050_uc_pms_015_main_flow(api, policy):
    """UC-T050 | UC-PMS-015 Main Flow | Verify response submission when Applicant review is
    required and approved.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app, requires_review=True)
    client = api(ATTORNEY_A_ID, "attorney")
    resp = client.post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert resp.status_code == 200, resp.data
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert oa.status == "AWAITING_APPLICANT", "the draft is not awaiting Applicant approval"
    approved = api(APPLICANT_ID, "applicant").post(f"{API}/office-actions/{oa_id}/approve")
    assert approved.status_code == 200, approved.data
    oa.refresh_from_db()
    assert oa.status == "APPLICANT_APPROVED"

    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)
    oa.refresh_from_db()
    assert oa.status == "SUBMITTED" and oa.submitted_at is not None
    logs = " ".join(audit_entries(api, app))
    for action in ("office_action_response_drafted", "office_action_response_approved",
                   "office_action_response_submitted"):
        assert action in logs, f"audit missing {action}"


def test_uc_t051_uc_pms_015_alternative_flow_1():
    """UC-T051 | UC-PMS-015 Alternative Flow 1 | Verify Attorney can record an extension request
    when permitted.
    """
    pytest.skip(
        "NOT_AUTOMATED: no endpoint, service or model records an office-action extension "
        "request or its status (office actions carry only a response deadline and status)")


def test_uc_t052_uc_pms_015_exception_flow_1(api, policy):
    """UC-T052 | UC-PMS-015 Exception Flow 1 | Verify response cannot be marked submitted without
    required Applicant approval.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app, requires_review=True)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert resp.status_code == 200, resp.data
    status = refusal_status(lambda: oa_service.submit_response(
        principal(ATTORNEY_A_ID, "attorney"), oa_id))
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert oa.status == "AWAITING_APPLICANT" and oa.submitted_at is None
    assert status == 409, "a response without Applicant approval was marked submitted"


def test_uc_t053_uc_pms_015_exception_flow_2(api, policy, mailoutbox):
    """UC-T053 | UC-PMS-015 Exception Flow 2 | Verify missed response deadline is handled by
    escalation rules without legal outcome.
    """
    policy()
    app = filed_application()
    today = timezone.now().date()
    oa = OfficeActionRecord.objects.create(
        application=app, action_code="FER-1", issuing_authority="Indian Patent Office",
        issued_date=today - datetime.timedelta(days=200),
        response_deadline=today - datetime.timedelta(days=1), status="RECORDED")
    app_before = state_of(app)
    pms_tasks.pms_sweep_deadlines()

    oa.refresh_from_db()
    assert state_of(app) == app_before, "a legal outcome was recorded on the application"
    assert oa.status == "RECORDED" and oa.submitted_at is None
    handled = [ln for ln in audit_entries(api, app) if "escalat" in ln.lower()]
    handled += [m for m in mails_about(mailoutbox, app) if "escalat" in m.subject.lower()]
    assert handled, "the missed deadline was not handled by escalation"


def test_uc_t054_uc_pms_016_main_flow():
    """UC-T054 | UC-PMS-016 Main Flow | Verify PCC_ADMIN views calculated deadlines and alerts and
    handles a delayed item.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no deadline-monitoring view or endpoint (reports "
        "return only three counts), so the calculated deadlines, 30/15/5-day alerts and "
        "routing of a delayed item cannot be driven or observed through an interface")


def test_uc_t055_uc_pms_016_alternative_flow_1():
    """UC-T055 | UC-PMS-016 Alternative Flow 1 | Verify no deadline is fabricated when rules/data
    are unavailable.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no deadline-monitoring view or endpoint, so an item "
        "lacking deadline rules cannot be opened or flagged as requiring configuration")


def test_uc_t056_uc_pms_016_exception_flow_1():
    """UC-T056 | UC-PMS-016 Exception Flow 1 | Verify missed deadline is escalated per configured
    chain.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no escalation-chain configuration or model, so a "
        "'configured chain' and the escalation record per that chain cannot be set up or "
        "observed")


def test_uc_t057_uc_pms_017_main_flow(api, policy):
    """UC-T057 | UC-PMS-017 Main Flow | Verify Renew decision leads to recorded maintenance action
    and next cycle.
    """
    policy()
    app = granted_application()
    due_before = app.renewal_due_date
    assert due_before is not None, "no maintenance schedule exists for the granted patent"
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
    entry = app.renewal_history.get()
    assert entry.decision == "RENEW" and entry.cycle_due_date == due_before
    assert entry.action_reference == "IPO-ANNUITY-2026-0042"
    assert app.renewal_due_date == next_due, "the next cycle was not scheduled"
    logs = " ".join(audit_entries(api, app))
    for action in ("renewal_decision_requested", "renewal_decision",
                   "maintenance_action_recorded"):
        assert action in logs


def test_uc_t058_uc_pms_017_alternative_flow_1(api, policy):
    """UC-T058 | UC-PMS-017 Alternative Flow 1 | Verify Do Not Renew results in no approved
    maintenance action.
    """
    policy()
    app = granted_application()
    due_before = app.renewal_due_date
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, resp.data
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": False}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["maintenance_state"] == "DO_NOT_RENEW"
    before = state_of(app)

    refused = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action",
        {"reference": "IPO-ANNUITY-2026-0043",
         "next_due_date": (due_before + datetime.timedelta(days=365)).isoformat()},
        format="json")
    assert refused.status_code == 409, refused.data
    assert state_of(app) == before
    entry = app.renewal_history.get()
    assert entry.decision == "DO_NOT_RENEW" and entry.action_recorded_at is None
    assert app.renewal_due_date == due_before


def test_uc_t059_uc_pms_017_exception_flow_1(api, policy):
    """UC-T059 | UC-PMS-017 Exception Flow 1 | Verify no maintenance schedule is fabricated without
    rules/data.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        jurisdiction="XX", external_filing_id="XX-2026-1", filing_date=timezone.now().date())
    granted = app_service.transition_application(
        app.id, "grant", principal(ATTORNEY_A_ID, "attorney"))
    assert granted.status == sm.GRANTED
    pms_tasks.pms_sweep_deadlines()
    app.refresh_from_db()
    assert app.renewal_due_date is None, "a maintenance due date was fabricated"
    assert app.maintenance_state in ("", "ACTIVE")
    assert not app.renewal_history.exists()


def test_uc_t060_uc_pms_018_main_flow(api, policy, mailoutbox):
    """UC-T060 | UC-PMS-018 Main Flow | Verify Director records Renew decision."""
    policy()
    app = granted_application()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, resp.data
    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": True}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.renewal_decision == "RENEW"
    assert app.renewal_history.get().decision == "RENEW"
    seen = api(ATTORNEY_A_ID, "attorney").get(f"{API}/applications/{app.id}")
    assert seen.status_code == 200
    assert seen.data["renewal_decision"] == "RENEW"
    assert seen.data["maintenance_state"] == "RENEWAL_APPROVED"
    assert mailed_to(mails_about(mailoutbox, app, before), ATTORNEY_A_ID)


def test_uc_t061_uc_pms_018_alternative_flow_1(api, policy):
    """UC-T061 | UC-PMS-018 Alternative Flow 1 | Verify Director records Do Not Renew decision."""
    policy()
    app = granted_application()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, resp.data
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": False}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.renewal_decision == "DO_NOT_RENEW"
    assert app.maintenance_state == "DO_NOT_RENEW"
    assert app.renewal_history.get().decision == "DO_NOT_RENEW"
    assert any("renewal_decision" in ln for ln in audit_entries(api, app))


def test_uc_t062_uc_pms_018_exception_flow_1(api, policy):
    """UC-T062 | UC-PMS-018 Exception Flow 1 | Verify renewal decision rejected for non-Granted
    patent.
    """
    policy()
    app = filed_application()
    before = state_of(app)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": True}, format="json")
    assert state_of(app) == before
    assert app.renewal_decision == "" and not app.renewal_history.exists()
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_uc_t063_uc_pms_019_main_flow(api, policy):
    """UC-T063 | UC-PMS-019 Main Flow | Verify document upload creates next version and archives
    previous.
    """
    policy()
    app = seed_application(sm.DRAFT)
    client = api(APPLICANT_ID, "applicant")
    first = upload(client, app.id, pdf_file(body=b"first"))
    assert first.status_code == 201, first.data
    assert first.data["version"] == 1
    second = upload(client, app.id, pdf_file(body=b"second"))
    assert second.status_code == 201, second.data
    assert second.data["version"] == 2
    assert second.data["uploaded_by_user_id"] == APPLICANT_ID
    assert second.data["created_at"], "the upload time was not recorded"

    detail = client.get(f"{API}/applications/{app.id}")
    assert detail.status_code == 200
    assert sorted(d["version"] for d in detail.data["documents"]) == [1, 2]
    previous = ApplicationDocument.objects.get(application=app, version=1)
    assert previous.file_name == "spec.pdf"


def test_uc_t064_uc_pms_019_alternative_flow_1(api, policy):
    """UC-T064 | UC-PMS-019 Alternative Flow 1 | Verify Applicant can edit documents only in Needs
    Revision status.
    """
    policy()
    client = api(APPLICANT_ID, "applicant")
    revision = seed_application(
        sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=3))
    review = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    before = state_of(review)
    observed = {
        "Needs Revision": upload(client, revision.id, pdf_file()).status_code,
        "Under Review": upload(client, review.id, pdf_file()).status_code,
    }
    assert observed == {"Needs Revision": 201, "Under Review": 409}, observed
    assert state_of(review) == before


def test_uc_t065_uc_pms_019_alternative_flow_2(api, policy):
    """UC-T065 | UC-PMS-019 Alternative Flow 2 | Verify other roles upload/access versions only
    where permitted.
    """
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    assigned = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID)
    other = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_B_ID)
    client = api(ATTORNEY_A_ID, "attorney")
    other_before = state_of(other)
    observed = {
        "access assigned": client.get(f"{API}/applications/{assigned.id}").status_code,
        "upload assigned": upload(client, assigned.id, pdf_file()).status_code,
    }
    blocked = {
        "access other": client.get(f"{API}/applications/{other.id}").status_code,
        "upload other": upload(client, other.id, pdf_file()).status_code,
    }
    assert observed == {"access assigned": 200, "upload assigned": 201}, observed
    # Not permitted is 403 (no grant) or 404 (outside the Attorney's visibility).
    assert all(code in (403, 404) for code in blocked.values()), blocked
    assert state_of(other) == other_before


def test_uc_t066_uc_pms_019_exception_flow_1(api, policy):
    """UC-T066 | UC-PMS-019 Exception Flow 1 | Verify unauthorized upload/access is blocked and
    logged.
    """
    policy()
    app = seed_application(sm.DRAFT)
    ApplicationDocument.objects.create(
        application=app, document_type="specification", file_name="spec.pdf",
        file_size_bytes=2048, storage_path="/var/patents/spec.pdf", version=1,
        uploaded_by_user_id=APPLICANT_ID)
    before = state_of(app)
    intruder = api(OTHER_APPLICANT_ID, "applicant")
    upload_status = upload(intruder, app.id, pdf_file()).status_code
    read = intruder.get(f"{API}/applications/{app.id}")
    assert (upload_status, read.status_code) == (404, 404)
    assert "spec.pdf" not in json.dumps(read.data, default=str)
    assert state_of(app) == before, "a version was created"
    assert audit_entries(api, app), "the blocked attempt was not logged"


def test_uc_t067_uc_pms_020_main_flow(api, policy, mailoutbox):
    """UC-T067 | UC-PMS-020 Main Flow | Verify licensing request is submitted and routed."""
    policy()
    app = filed_application()
    before = len(mailoutbox)
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "LICENSING",
        "partner_name": "Acme Quantum Ltd", "terms_summary": "Exclusive field-of-use licence.",
    }, format="json")
    assert resp.status_code == 201, resp.data
    record = TechnologyTransferRecord.objects.get(pk=resp.data["id"])
    assert record.request_type == "LICENSING" and record.applicant_user_id == APPLICANT_ID
    seen = api(DIRECTOR_ID, "director").get(f"{API}/applications/{app.id}")
    assert [r["id"] for r in seen.data["licensing_records"]] == [record.id]
    routed = (mailed_to(mails_about(mailoutbox, app, before), DIRECTOR_ID)
              or record.status != "SUBMITTED")
    assert routed, "the request was not routed to the Director"
    assert audit_entries(api, app), "no routing/tracking state was recorded"


def test_uc_t068_uc_pms_020_alternative_flow_1(api, policy, mailoutbox):
    """UC-T068 | UC-PMS-020 Alternative Flow 1 | Verify technology-transfer request uses same
    submission goal.
    """
    policy()
    app = filed_application()
    before = len(mailoutbox)
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "TECHNOLOGY_TRANSFER",
        "partner_name": "Acme Quantum Ltd", "terms_summary": "Know-how transfer.",
    }, format="json")
    assert resp.status_code == 201, resp.data
    record = TechnologyTransferRecord.objects.get(pk=resp.data["id"])
    assert record.request_type == "TECHNOLOGY_TRANSFER"
    routed = (mailed_to(mails_about(mailoutbox, app, before), DIRECTOR_ID)
              or record.status != "SUBMITTED")
    assert routed, "the request was not routed to the Director"
    assert audit_entries(api, app), "no routing/tracking state was recorded"


def test_uc_t069_uc_pms_020_exception_flow_1(api, policy, mailoutbox):
    """UC-T069 | UC-PMS-020 Exception Flow 1 | Verify no committee decision is invented when
    routing target undetermined.
    """
    policy()
    app = seed_application(sm.FILED, external_filing_id="IN202611000123",
                           filing_date=timezone.now().date())
    assert app.assigned_director_id is None
    before = len(mailoutbox)
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "LICENSING",
        "partner_name": "Acme Quantum Ltd",
    }, format="json")
    assert resp.status_code == 201, resp.data
    record = TechnologyTransferRecord.objects.get(pk=resp.data["id"])
    assert record.status not in ("APPROVED", "REJECTED"), "a review outcome was invented"
    assert not mails_about(mailoutbox, app, before)
    assert app.reviews.count() == 0


def test_uc_t070_uc_pms_021_main_flow(api, policy):
    """UC-T070 | UC-PMS-021 Main Flow | Verify Director records negotiation information and final
    agreement for routed request.
    """
    policy()
    app = filed_application()
    created = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "LICENSING",
        "partner_name": "Acme Quantum Ltd"}, format="json")
    assert created.status_code == 201, created.data
    agreement = "Final agreement: 3% royalty, 5-year exclusive field-of-use licence."
    record = tt_service.review_tech_transfer_request(
        principal(DIRECTOR_ID, "director"), created.data["id"], "NEGOTIATING",
        terms_summary=agreement)
    record.refresh_from_db()
    assert record.terms_summary == agreement
    assert record.confidentiality_level
    outsider = api(OTHER_APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert outsider.status_code == 404, "the licence record is not confidential"


def test_uc_t071_uc_pms_021_alternative_flow_1(api, policy):
    """UC-T071 | UC-PMS-021 Alternative Flow 1 | Verify committee-routed request allows PMS to
    record resulting information.
    """
    policy()
    app = filed_application()
    created = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "LICENSING",
        "partner_name": "Acme Quantum Ltd"}, format="json")
    assert created.status_code == 201, created.data
    result = "Committee minute 14: licence terms agreed in principle, royalty 3%."
    record = tt_service.review_tech_transfer_request(
        principal(DIRECTOR_ID, "director"), created.data["id"], "NEGOTIATING",
        terms_summary=result)
    record.refresh_from_db()
    assert record.terms_summary == result
    assert record.status not in ("APPROVED", "REJECTED"), "a PMS decision was invented"


def test_uc_t072_uc_pms_021_exception_flow_1(api, policy):
    """UC-T072 | UC-PMS-021 Exception Flow 1 | Verify PMS does not record unstated
    approval/rejection semantics.
    """
    policy()
    app = filed_application()
    record = TechnologyTransferRecord.objects.create(
        application=app, applicant_user_id=APPLICANT_ID, request_type="LICENSING",
        partner_name="Acme Quantum Ltd", status="SUBMITTED")
    observed = {}
    for outcome in ("APPROVED", "REJECTED"):
        observed[outcome] = refusal_status(
            lambda outcome=outcome: tt_service.review_tech_transfer_request(
                principal(DIRECTOR_ID, "director"), record.id, outcome))
    record.refresh_from_db()
    assert record.status == "SUBMITTED", "an approval/rejection outcome was recorded"
    assert observed == {"APPROVED": 422, "REJECTED": 422}, observed


def test_uc_t073_uc_pms_022_main_flow(api, policy, mailoutbox):
    """UC-T073 | UC-PMS-022 Main Flow | Verify eligible appeal against rejection is recorded."""
    policy()
    app = seed_application(
        sm.REJECTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=5))
    before = len(mailoutbox)
    grounds = "D1 does not disclose resonator coupling."
    justification = "Claim 1 requires coupling absent from D1, so novelty holds."
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/appeal",
        {"grounds": grounds, "justification": justification}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED
    appeal = app.appeals.get()
    assert appeal.status == "SUBMITTED" and appeal.grounds == grounds
    assert justification in history_payload(api, app), "the justification was not recorded"
    assert mailed_to(mails_about(mailoutbox, app, before), DIRECTOR_ID)


def test_uc_t074_uc_pms_022_exception_flow_1(api, policy):
    """UC-T074 | UC-PMS-022 Exception Flow 1 | Verify appeal for non-Rejected application or
    outside period is not accepted.
    """
    policy()
    approved = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    expired = seed_application(
        sm.REJECTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=400))
    before = (state_of(approved), state_of(expired))
    client = api(APPLICANT_ID, "applicant")
    body = {"grounds": "D1 does not disclose resonator coupling.",
            "justification": "Claim 1 requires coupling absent from D1."}
    observed = {
        "approved": client.post(
            f"{API}/applications/{approved.id}/appeal", body, format="json").status_code,
        "period expired": client.post(
            f"{API}/applications/{expired.id}/appeal", body, format="json").status_code,
    }
    assert observed == {"approved": 409, "period expired": 422}, observed
    assert (state_of(approved), state_of(expired)) == before, "an appeal was accepted"


def test_uc_t075_uc_pms_023_main_flow(api, policy, mailoutbox):
    """UC-T075 | UC-PMS-023 Main Flow | Verify Director records Uphold Rejection outcome."""
    policy()
    app = appeal_submitted_application()
    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "UPHOLD"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    appeal = app.appeals.get()
    assert appeal.status == "UPHOLD" and appeal.director_user_id == DIRECTOR_ID
    assert appeal.decided_at is not None
    assert app.status == sm.REJECTION_UPHELD
    assert mailed_to(mails_about(mailoutbox, app, before), APPLICANT_ID), (
        "the next step (notifying the Applicant of the outcome) was not initiated")


def test_uc_t076_uc_pms_023_alternative_flow_1(api, policy, mailoutbox):
    """UC-T076 | UC-PMS-023 Alternative Flow 1 | Verify Director records Remand for Amendment
    outcome.
    """
    policy()
    app = appeal_submitted_application()
    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "REMAND"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    appeal = app.appeals.get()
    assert appeal.status == "REMAND" and appeal.decided_at is not None
    assert app.status == sm.REMANDED
    assert mailed_to(mails_about(mailoutbox, app, before), APPLICANT_ID), (
        "the next step (notifying the Applicant of the outcome) was not initiated")


def test_uc_t077_uc_pms_023_alternative_flow_1(api, policy):
    """UC-T077 | UC-PMS-023 Alternative Flow 1 | Verify Director records Modify Decision outcome."""
    policy()
    app = appeal_submitted_application()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "MODIFY"}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    appeal = app.appeals.get()
    assert appeal.status == "MODIFY" and appeal.decided_at is not None
    assert app.status == sm.DECISION_MODIFIED


def test_uc_t078_uc_pms_023_exception_flow_1(api, policy):
    """UC-T078 | UC-PMS-023 Exception Flow 1 | Verify unsupported appeal outcome is rejected."""
    policy()
    app = appeal_submitted_application()
    before = state_of(app)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision",
        {"outcome": "OVERTURN_AND_GRANT"}, format="json")
    appeal = app.appeals.get()
    assert state_of(app) == before and app.status == sm.APPEAL_SUBMITTED
    assert appeal.status == "SUBMITTED" and appeal.decided_at is None
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_uc_t079_uc_pms_024_main_flow(api, policy):
    """UC-T079 | UC-PMS-024 Main Flow | Verify PCC_ADMIN generates a system-wide report and access
    is logged.
    """
    policy()
    seed_application(sm.SUBMITTED)
    filed_application()
    granted_application()
    snapshot = list(PatentApplication.objects.order_by("id").values_list(
        "id", "status", "version"))
    admin = api(ADMIN_ID, "pcc_admin")
    resp = admin.get(f"{API}/reports")
    assert resp.status_code == 200, resp.data
    assert resp.data["total_applications"] == PatentApplication.objects.count()
    assert resp.data["filed_count"] == PatentApplication.objects.filter(status=sm.FILED).count()
    assert resp.data["granted_count"] == PatentApplication.objects.filter(
        status=sm.GRANTED).count()
    assert list(PatentApplication.objects.order_by("id").values_list(
        "id", "status", "version")) == snapshot
    lines = admin.get(f"{API}/audit-logs").data["audit_logs"]
    assert any("report" in ln.lower() for ln in lines), "report access was not logged"


def test_uc_t080_uc_pms_024_alternative_flow_1():
    """UC-T080 | UC-PMS-024 Alternative Flow 1 | Verify available report types can be generated."""
    pytest.skip(
        "NOT_AUTOMATED: GET reports is a single summary (three counts); the module has no "
        "financial/budget, deadline, inventor, portfolio or workload report type to select "
        "or generate")


def test_uc_t081_uc_pms_024_exception_flow_1(api, policy):
    """UC-T081 | UC-PMS-024 Exception Flow 1 | Verify unauthorized or unavailable data is not
    included or fabricated.
    """
    policy()
    admin = api(ADMIN_ID, "pcc_admin")
    empty = admin.get(f"{API}/reports")
    assert empty.status_code == 200
    assert (empty.data["total_applications"], empty.data["filed_count"],
            empty.data["granted_count"]) == (0, 0, 0), "data was fabricated"

    seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.UNDER_REVIEW, assigned_director_id=OTHER_DIRECTOR_ID)
    seed_application(sm.FILED, assigned_director_id=OTHER_DIRECTOR_ID)
    assert api(APPLICANT_ID, "applicant").get(f"{API}/reports").status_code == 403
    scoped = api(DIRECTOR_ID, "director").get(f"{API}/reports")
    assert scoped.status_code == 200
    assert scoped.data["total_applications"] == 1, "out-of-scope data was included"


def test_uc_t082_uc_pms_025_main_flow():
    """UC-T082 | UC-PMS-025 Main Flow | Verify PCC_ADMIN updates PMS role mapping and change is
    audited.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no PMS role-mapping administration: roles are "
        "granted by the identity service and PMS exposes no endpoint or service to assign "
        "the Director role to a user")


def test_uc_t083_uc_pms_025_alternative_flow_1(api, policy):
    """UC-T083 | UC-PMS-025 Alternative Flow 1 | Verify PCC_ADMIN can set configurable values (e.g.
    threshold).
    """
    policy(threshold=Decimal("150000.00"))
    old = PatentPolicy.objects.get(is_active=True)
    new = policy_service.supersede_policy(cost_escalation_threshold=Decimal("250000.00"))
    old.refresh_from_db()
    assert new.is_active and new.cost_escalation_threshold == Decimal("250000.00")
    assert not old.is_active and old.superseded_by_id == new.id
    assert PatentPolicy.objects.get(is_active=True).pk == new.pk
    audited = [
        e for e in PatentAuditLog.objects.all()
        if any(word in e.action_type.lower() for word in ("polic", "config", "threshold"))
        or "threshold" in json.dumps(e.details).lower()
    ]
    assert audited, "the configuration change was not audited"


def test_uc_t084_uc_pms_025_exception_flow_1():
    """UC-T084 | UC-PMS-025 Exception Flow 1 | Verify platform/HR data is not changed and
    single-PCC_ADMIN rule enforced.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no PCC_ADMIN account administration: it neither "
        "stores nor counts PCC_ADMIN holders, so 'add a second active PCC_ADMIN' cannot be "
        "attempted through any PMS interface")


def test_uc_t085_uc_pms_026_main_flow(api, policy):
    """UC-T085 | UC-PMS-026 Main Flow | Verify PCC_ADMIN maintains attorney panel and expertise
    mapping.
    """
    policy()
    admin = principal(ADMIN_ID, "pcc_admin")
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    first = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert first.status_code >= 400, "an Attorney outside the panel was assigned"

    member = attorney_service.register_panel_member(
        admin, ATTORNEY_A_ID, "Quantum IP LLP", ["Quantum", "Photonics"])
    assert member.is_approved_panel and member.expertise_domains == ["Quantum", "Photonics"]
    listed = api(ADMIN_ID, "pcc_admin").get(f"{API}/attorney-panel")
    assert listed.status_code == 200
    assert ATTORNEY_A_ID in [m["user_id"] for m in listed.data["results"]]
    second = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert second.status_code == 200, second.data
    assert second.data["status"] == sm.ASSIGNMENT_OFFERED


def test_uc_t086_uc_pms_026_alternative_flow_1():
    """UC-T086 | UC-PMS-026 Alternative Flow 1 | Verify institutional exception is recorded
    separately for non-panel assignment.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no institutional-exception record or interface "
        "(AttorneyPanelMember holds only the approved-panel flag), so an exception recorded "
        "separately from the panel cannot be created or observed")


def test_uc_t087_uc_pms_026_exception_flow_1(api, policy):
    """UC-T087 | UC-PMS-026 Exception Flow 1 | Verify unauthorized panel change is not committed."""
    policy()
    observed = {}
    for role, user_id in (("director", DIRECTOR_ID), ("attorney", ATTORNEY_A_ID),
                          ("applicant", APPLICANT_ID)):
        observed[role] = refusal_status(
            lambda role=role, user_id=user_id: attorney_service.register_panel_member(
                principal(user_id, role), ATTORNEY_B_ID, "Rogue Firm", ["Quantum"]))
    assert not AttorneyPanelMember.objects.exists(), "an unauthorized change was committed"
    assert observed == {"director": 403, "attorney": 403, "applicant": 403}, observed
    listing = api(APPLICANT_ID, "applicant").get(f"{API}/attorney-panel")
    assert listing.status_code == 403


def test_uc_t088_uc_pms_027_main_flow():
    """UC-T088 | UC-PMS-027 Main Flow | Verify PCC_ADMIN handles exceptional case and handling is
    recorded.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no exceptional-case record or routing interface; "
        "the only PCC_ADMIN exception handling is tracking an escalated budget case, which "
        "does not cover 'no eligible assignee'")


def test_uc_t089_uc_pms_027_alternative_flow_1():
    """UC-T089 | UC-PMS-027 Alternative Flow 1 | Verify conflict-of-interest and delayed-action
    escalations are visible and handled.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no listing of conflict-of-interest or "
        "delayed-action escalation cases and no interface to review, resolve or route them")


def test_uc_t090_uc_pms_027_exception_flow_1(api, policy):
    """UC-T090 | UC-PMS-027 Exception Flow 1 | Verify PCC_ADMIN cannot record unstated external
    decisions.
    """
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = request_budget(app, Decimal("200000.00"))
    escalated = budget_service.decide_budget(
        principal(DIRECTOR_ID, "director"), req.id, "APPROVE")
    assert escalated.status == "ESCALATED"
    rows = list(PatentBudgetLedger.objects.filter(application=app).order_by("id")
                .values_list("id", "status"))

    via_api = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "APPROVE", "budget_entry_id": req.id}, format="json").status_code
    via_service = refusal_status(lambda: budget_service.decide_budget(
        principal(ADMIN_ID, "pcc_admin"), req.id, "APPROVE"))
    current = list(PatentBudgetLedger.objects.filter(application=app).order_by("id")
                   .values_list("id", "status"))
    assert current == rows, f"a higher-authority decision was recorded: {current}"
    assert budget_service.approved_total(app.id) == Decimal("0")
    assert (via_api, via_service) == (403, 403)


def test_uc_t091_uc_pms_028_main_flow(api, policy):
    """UC-T091 | UC-PMS-028 Main Flow | Verify PCC_ADMIN views audit records with required fields.

    """
    policy()
    app = under_review_application(api)
    assert decide(api, app, "APPROVE").status_code == 200
    admin = api(ADMIN_ID, "pcc_admin")
    rows_before = PatentAuditLog.objects.count()
    first = [ln for ln in admin.get(f"{API}/audit-logs").data["audit_logs"]
             if app.application_number in ln]
    assert len(first) >= 2, first
    for line in first:
        fields = dict(part.split("=", 1) for part in line.split(" | ")[1:6])
        stamp = line.split(" | ")[0]
        assert datetime.datetime.fromisoformat(stamp)
        assert set(fields) == {"user", "action", "application", "previous", "new"}, line
        assert fields["application"] == app.application_number
    assigned = next(ln for ln in first if "action=assign_director" in ln)
    assert f"user={ADMIN_ID}" in assigned
    assert "previous=submitted" in assigned and "new=under_review" in assigned
    approved = next(ln for ln in first if "action=submit_review" in ln)
    assert f"user={DIRECTOR_ID}" in approved
    assert "previous=under_review" in approved and "new=approved" in approved
    second = [ln for ln in admin.get(f"{API}/audit-logs").data["audit_logs"]
              if app.application_number in ln]
    assert second == first and PatentAuditLog.objects.count() == rows_before


def test_uc_t092_uc_pms_028_alternative_flow_1(api, policy):
    """UC-T092 | UC-PMS-028 Alternative Flow 1 | Verify Director audit access is limited to
    authorized domain.
    """
    policy()
    mine = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    theirs = seed_application(sm.UNDER_REVIEW, assigned_director_id=OTHER_DIRECTOR_ID)
    for app in (mine, theirs):
        PatentAuditLog.objects.create(
            application=app, actor_user_id=ADMIN_ID, action_type="assign_director",
            previous_state=sm.SUBMITTED, new_state=sm.UNDER_REVIEW)
    resp = api(DIRECTOR_ID, "director").get(f"{API}/audit-logs")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    lines = resp.data["audit_logs"]
    assert any(mine.application_number in ln for ln in lines)
    assert not any(theirs.application_number in ln for ln in lines), (
        "an out-of-domain audit record was shown")


def test_uc_t093_uc_pms_028_exception_flow_1(api, policy):
    """UC-T093 | UC-PMS-028 Exception Flow 1 | Verify unauthorized audit access is blocked."""
    policy()
    app = seed_application(sm.SUBMITTED)
    PatentAuditLog.objects.create(
        application=app, actor_user_id=ADMIN_ID, action_type="assign_director",
        previous_state=sm.SUBMITTED, new_state=sm.UNDER_REVIEW)
    resp = api(APPLICANT_ID, "applicant").get(f"{API}/audit-logs")
    assert resp.status_code == 403, (resp.status_code, resp.data)
    assert app.application_number not in json.dumps(resp.data, default=str)


def test_uc_t094_uc_pms_029_main_flow(api, policy):
    """UC-T094 | UC-PMS-029 Main Flow | Verify Applicant approval of draft response is recorded."""
    policy()
    app = filed_application()
    oa = OfficeActionRecord.objects.create(
        application=app, action_code="FER-1", issuing_authority="Indian Patent Office",
        issued_date=timezone.now().date(),
        response_deadline=timezone.now().date() + datetime.timedelta(days=90),
        requires_applicant_review=True, status="AWAITING_APPLICANT",
        response_summary="Distinguish claim 1 over D1 by resonator coupling.")
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/office-actions/{oa.id}/approve")
    assert resp.status_code == 200, resp.data
    oa.refresh_from_db()
    assert oa.status == "APPLICANT_APPROVED"
    assert any("office_action_response_approved" in ln for ln in audit_entries(api, app))
    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa.id)
    oa.refresh_from_db()
    assert oa.status == "SUBMITTED"


def test_uc_t095_uc_pms_029_alternative_flow_1(api, policy):
    """UC-T095 | UC-PMS-029 Alternative Flow 1 | Verify response can be finalized without Applicant
    review when not required.
    """
    policy()
    app = filed_application()
    oa_id = record_office_action(api, app, requires_review=False)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert resp.status_code == 200, resp.data
    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert oa.status == "SUBMITTED" and oa.submitted_at is not None
    logs = " ".join(audit_entries(api, app))
    assert "office_action_response_submitted" in logs
    assert "AWAITING_APPLICANT" not in logs and "office_action_response_approved" not in logs


def test_uc_t096_uc_pms_029_exception_flow_1(api, policy):
    """UC-T096 | UC-PMS-029 Exception Flow 1 | Verify response without recorded approval is not
    treated as approved.
    """
    policy()
    app = filed_application()
    oa = OfficeActionRecord.objects.create(
        application=app, action_code="FER-1", issuing_authority="Indian Patent Office",
        issued_date=timezone.now().date(),
        response_deadline=timezone.now().date() + datetime.timedelta(days=90),
        requires_applicant_review=True, status="AWAITING_APPLICANT",
        response_summary="Distinguish claim 1 over D1 by resonator coupling.")
    shown = api(ATTORNEY_A_ID, "attorney").get(f"{API}/applications/{app.id}")
    state = next(o for o in shown.data["office_actions"] if o["id"] == oa.id)["status"]
    assert state == "AWAITING_APPLICANT", "shown as Applicant-approved without approval"
    status = refusal_status(lambda: oa_service.submit_response(
        principal(ATTORNEY_A_ID, "attorney"), oa.id))
    oa.refresh_from_db()
    assert oa.status == "AWAITING_APPLICANT" and oa.submitted_at is None
    assert status == 409, "finalization without approval was not blocked"


def test_uc_t097_uc_pms_030_main_flow(api, policy):
    """UC-T097 | UC-PMS-030 Main Flow | Verify Applicant report contains only own applications."""
    policy()
    seed_application(sm.SUBMITTED)
    seed_application(sm.DRAFT)
    seed_application(sm.SUBMITTED, user_id=OTHER_APPLICANT_ID)
    resp = api(APPLICANT_ID, "applicant").get(f"{API}/reports")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["total_applications"] == 2, "the report is not limited to own applications"


def test_uc_t098_uc_pms_030_alternative_flow_1():
    """UC-T098 | UC-PMS-030 Alternative Flow 1 | Verify export option provided only where
    supported.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no report export (GET reports returns JSON counts "
        "only, with no export format, parameter or file endpoint)")


def test_uc_t099_uc_pms_030_exception_flow_1(api, policy):
    """UC-T099 | UC-PMS-030 Exception Flow 1 | Verify access to another Applicant's report data is
    blocked.
    """
    policy()
    other = seed_application(sm.SUBMITTED, user_id=OTHER_APPLICANT_ID)
    client = api(APPLICANT_ID, "applicant")
    report = client.get(f"{API}/reports", {"user_id": OTHER_APPLICANT_ID})
    detail = client.get(f"{API}/applications/{other.id}")
    assert report.status_code in (403, 404), "another Applicant's report data was served"
    assert detail.status_code == 404
    assert other.title not in json.dumps(detail.data, default=str)


def test_uc_t100_uc_pms_031_main_flow(api, policy):
    """UC-T100 | UC-PMS-031 Main Flow | Verify Director generates in-scope report and access is
    logged.
    """
    policy()
    seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.FILED, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.UNDER_REVIEW, assigned_director_id=OTHER_DIRECTOR_ID)
    resp = api(DIRECTOR_ID, "director").get(f"{API}/reports")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["total_applications"] == 2
    assert resp.data["filed_count"] == 1
    lines = api(ADMIN_ID, "pcc_admin").get(f"{API}/audit-logs").data["audit_logs"]
    assert any("report" in ln.lower() for ln in lines), "report access was not logged"


def test_uc_t101_uc_pms_031_alternative_flow_1():
    """UC-T101 | UC-PMS-031 Alternative Flow 1 | Verify authorized Director can export a report."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no report export (GET reports returns JSON counts "
        "only, with no export format, parameter or file endpoint)")


def test_uc_t102_uc_pms_031_exception_flow_1():
    """UC-T102 | UC-PMS-031 Exception Flow 1 | Verify unauthorized report scope is blocked."""
    pytest.skip(
        "NOT_AUTOMATED: GET reports takes no scope or domain parameter: a Director can only "
        "receive the report scoped by assignment, so an out-of-domain scope cannot be "
        "requested through any interface")


def test_uc_t103_uc_pms_032_main_flow(api, policy):
    """UC-T103 | UC-PMS-032 Main Flow | Verify Director views domain workflow oversight."""
    policy()
    review = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    approved = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.UNDER_REVIEW, assigned_director_id=OTHER_DIRECTOR_ID)
    before = (state_of(review), state_of(approved))
    listing = api(DIRECTOR_ID, "director").get(f"{API}/applications")
    assert listing.status_code == 200
    states = {row["id"]: row["status"] for row in listing.data["results"]}
    assert states == {review.id: sm.UNDER_REVIEW, approved.id: sm.APPROVED}
    pending = sel.applications_pending_director_review(principal(DIRECTOR_ID, "director"))
    assert [a.id for a in pending] == [review.id]
    assert (state_of(review), state_of(approved)) == before


def test_uc_t104_uc_pms_032_exception_flow_1(api, policy):
    """UC-T104 | UC-PMS-032 Exception Flow 1 | Verify out-of-domain information is not disclosed."""
    policy()
    mine = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    outside = seed_application(
        sm.UNDER_REVIEW, assigned_director_id=OTHER_DIRECTOR_ID, title="Out-of-domain title")
    client = api(DIRECTOR_ID, "director")
    listing = client.get(f"{API}/applications")
    assert [row["id"] for row in listing.data["results"]] == [mine.id]
    assert "Out-of-domain title" not in json.dumps(listing.data, default=str)
    detail = client.get(f"{API}/applications/{outside.id}")
    assert detail.status_code == 404
    assert "Out-of-domain title" not in json.dumps(detail.data, default=str)
    pending = sel.applications_pending_director_review(principal(DIRECTOR_ID, "director"))
    assert outside.id not in [a.id for a in pending]


def test_uc_t105_uc_pms_033_main_flow():
    """UC-T105 | UC-PMS-033 Main Flow | Verify Attorney records legal advice associated with
    application.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no legal-advice record: there is no model, service "
        "or endpoint for an Attorney to record a legal advice note (the assessment endpoint "
        "is a stub that stores nothing and has no advice action)")


def test_uc_t106_uc_pms_033_alternative_flow_1():
    """UC-T106 | UC-PMS-033 Alternative Flow 1 | Verify legal advice recording does not change
    application status at any stage.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no legal-advice record: there is no model, service "
        "or endpoint for an Attorney to record legal advice at any lifecycle stage")


def test_uc_t107_uc_pms_033_exception_flow_1():
    """UC-T107 | UC-PMS-033 Exception Flow 1 | Verify unauthorized access or invalid reference
    prevents storage.
    """
    pytest.skip(
        "NOT_AUTOMATED: the module has no legal-advice record: there is no model, service "
        "or endpoint to attempt recording advice (authorized, unauthorized or against an "
        "unknown application)")
