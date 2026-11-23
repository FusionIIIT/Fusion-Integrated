"""Spec tests for patents, BR (business rule) strategy, part A.

Generated from the frozen docs/11-patents/spec-tests/BR_DESIGN.json, cases BR-T001..BR-T072.
Every test carries its test_id and source_id in its name and docstring.

Behaviour is driven through the module's public interfaces: the HTTP API where an endpoint
exists, otherwise the service layer (document upload with large payloads, `submit` /
`resubmit` transitions, office-action submission) or the scheduled sweep task. Preconditions
that place an application in a given state are seeded directly, as the module's own journey
tests do.

Refusal status codes, where the design names none, come from
docs/01-architecture/api-conventions.md "Status codes": 409 for "the world is in the wrong
state" (illegal transition, unmet record prerequisite), 422 for invalid input or a
policy-based business-rule refusal, 403 for authenticated-but-not-permitted, 404 for outside
visibility.

A case whose interface does not exist in the module is skipped as NOT_AUTOMATED.
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
    PatentAuditLog,
    PatentBudgetLedger,
    PatentPolicy,
    RenewalHistory,
)
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import documents as doc_service
from modules.patents.services import office_actions as oa_service
from modules.patents.tasks import pms_sweep_deadlines

pytestmark = pytest.mark.django_db

API = "/api/v1/patents"

APPLICANT_ID = 101
COINVENTOR_ID = 102
APPLICANT_B_ID = 103
DIRECTOR_ID = 201
DIRECTOR_2_ID = 202
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
MB = 1024 * 1024
THRESHOLD = Decimal("150000.00")

_seq = itertools.count(1)


# -- Infrastructure -------------------------------------------------------------


def principal(user_id: int, role: str):
    """A real Principal with the registry grants for `role`, for service-level calls."""
    code, perms = ROLE_OF[role]
    return make_principal(
        user_id=user_id, roles=(code,), active_role=code,
        permissions=tuple(perms), modules=("patents",),
    )


#: The identity service's directory: everyone in these cases has an email address, which is
#: where PMS-triggered notifications are sent (BR-PMS-116).
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
    def _make(withdrawal_states=(), threshold=THRESHOLD):
        return PatentPolicy.objects.create(
            is_active=True,
            director_review_days=15,
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
        "application_number": f"PMS-BRA-{next(_seq):04d}",
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
        "status": status,
    }
    defaults.update(fields)
    return PatentApplication.objects.create(**defaults)


def add_coinventor(app, consent: bool = False, user_id: int = COINVENTOR_ID) -> CoInventor:
    return CoInventor.objects.create(
        application=app, user_id=user_id, name="Dr. Sarah Rao",
        email="sarah.rao@example.edu", share_percentage=Decimal("100.00"),
        consent_granted=consent, consent_timestamp=timezone.now() if consent else None,
    )


def budget_request(app, entry_type: str, amount, category: str):
    return budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, entry_type, Decimal(str(amount)), category,
    )


def approve_budget(app, amount=Decimal("45000.00")) -> PatentBudgetLedger:
    """Precondition: a budget request decided Approved by the Director."""
    req = budget_request(app, "FILING_FEE", amount, "GOVERNMENT_FEE")
    return budget_service.decide_budget(principal(DIRECTOR_ID, "director"), req.id, "APPROVE")


def complete_budget(app, filing, attorney, admin) -> list[PatentBudgetLedger]:
    """A budget request with all three required components."""
    return [
        budget_request(app, "FILING_FEE", filing, "GOVERNMENT_FEE"),
        budget_request(app, "ATTORNEY_FEE", attorney, "PROFESSIONAL_FEE"),
        budget_request(app, "ADMIN_FEE", admin, "ADMINISTRATIVE"),
    ]


def decide_via_api(api, app, requests, decision="APPROVE") -> list:
    client = api(DIRECTOR_ID, "director")
    return [
        client.post(f"{API}/applications/{app.id}/budget-decision",
                    {"decision": decision, "budget_entry_id": r.id}, format="json")
        for r in requests
    ]


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
    return [ln for ln in lines if app.application_number in ln]


def refusal_status(fn) -> int | None:
    """Run a service call; return the refusal's HTTP status, or None if it was accepted."""
    try:
        fn()
    except DomainError as err:
        return err.status_code
    return None


def review(api, app, decision, justification=GOOD_JUSTIFICATION, director=DIRECTOR_ID):
    return api(director, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": decision, "justification": justification}, format="json")


def pdf_bytes(size: int) -> bytes:
    return b"%PDF-1.4\n" + b"0" * (size - 9)


def upload_pdf(api, app_id, name="spec.pdf", size=2048):
    pdf = SimpleUploadedFile(name, pdf_bytes(size), "application/pdf")
    return api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app_id}/documents",
        {"document_type": "specification", "file": pdf}, format="multipart")


def application_payload(**overrides):
    body = {
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
        "co_inventors": [{"user_id": APPLICANT_ID, "name": "Asha Verma",
                          "email": "asha@example.edu", "share_percentage": "100.00"}],
    }
    body.update(overrides)
    return body


def _filing_ready_application(consent: bool, jurisdiction: str = "PCT"):
    """Approved, attorney assigned and working the case, budget approved, inventor
    agreements per `consent`."""
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID, jurisdiction=jurisdiction,
    )
    add_coinventor(app, consent=consent)
    approve_budget(app)
    return app


def _granted_application(**fields):
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.GRANTED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        grant_date=timezone.now().date() - datetime.timedelta(days=700),
        renewal_due_date=timezone.now().date() + datetime.timedelta(days=20), **fields,
    )


def _revision_application(status, days_ago, **fields):
    return seed_application(
        status, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=days_ago), **fields,
    )


# -- BR-PMS-003 / 005 / 006: reports and oversight scope ---------------------------------


def test_br_t001_br_pms_003_own_application_permitted(api, policy):
    """BR-T001 | BR-PMS-003 own-application permitted | Applicant can access report
    information for own applications."""
    policy()
    app = seed_application(sm.SUBMITTED, user_id=APPLICANT_ID)
    resp = api(APPLICANT_ID, "applicant").get(f"{API}/reports")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["total_applications"] == 1, resp.data
    own = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert own.status_code == 200


def test_br_t002_br_pms_003_other_application_prohibited(api, policy):
    """BR-T002 | BR-PMS-003 other-application prohibited | Applicant cannot access report
    information for another applicant's application."""
    policy()
    app = seed_application(sm.FILED, user_id=APPLICANT_B_ID,
                           external_filing_id="IN202611000001")
    client = api(APPLICANT_ID, "applicant")
    detail = client.get(f"{API}/applications/{app.id}")
    assert detail.status_code in (403, 404), detail.data
    assert app.application_number not in json.dumps(detail.data, default=str)
    reports = client.get(f"{API}/reports")
    assert reports.status_code in (403, 404) or reports.data["total_applications"] == 0, (
        reports.status_code, reports.data)
    if reports.status_code == 200:
        assert reports.data["filed_count"] == 0


def test_br_t003_br_pms_005_within_scope_permitted(api, policy):
    """BR-T003 | BR-PMS-005 within-scope permitted | Director can access reports/analytics
    within authorized PMS scope."""
    policy()
    seed_application(sm.UNDER_REVIEW, domain_category="Quantum",
                     assigned_director_id=DIRECTOR_ID)
    seed_application(sm.FILED, domain_category="Quantum", assigned_director_id=DIRECTOR_ID,
                     external_filing_id="IN202611000002")
    resp = api(DIRECTOR_ID, "director").get(f"{API}/reports")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["total_applications"] == 2
    assert resp.data["filed_count"] == 1


def test_br_t004_br_pms_005_outside_scope_prohibited(api, policy):
    """BR-T004 | BR-PMS-005 outside-scope prohibited | Director cannot access
    reports/analytics outside authorized scope."""
    policy()
    seed_application(sm.UNDER_REVIEW, domain_category="Quantum",
                     assigned_director_id=DIRECTOR_ID)
    seed_application(sm.FILED, domain_category="Materials",
                     assigned_director_id=DIRECTOR_2_ID, external_filing_id="IN202611000003")
    seed_application(sm.GRANTED, domain_category="Materials",
                     assigned_director_id=DIRECTOR_2_ID)
    resp = api(DIRECTOR_ID, "director").get(f"{API}/reports")
    if resp.status_code == 200:
        assert resp.data["total_applications"] == 1, "domain Y data was not excluded"
        assert resp.data["filed_count"] == 0
        assert resp.data["granted_count"] == 0
    else:
        assert resp.status_code in (403, 404)


def test_br_t005_br_pms_006_in_domain_permitted(api, policy):
    """BR-T005 | BR-PMS-006 in-domain permitted | Director can oversee workflows in own
    domain."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, domain_category="Quantum",
                           assigned_director_id=DIRECTOR_ID)
    resp = api(DIRECTOR_ID, "director").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == sm.UNDER_REVIEW
    queue = sel.applications_pending_director_review(principal(DIRECTOR_ID, "director"))
    assert queue.filter(pk=app.id).exists()


def test_br_t006_br_pms_006_out_of_domain_prohibited(api, policy):
    """BR-T006 | BR-PMS-006 out-of-domain prohibited | Director cannot oversee workflows
    outside own domain."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, domain_category="Materials",
                           assigned_director_id=DIRECTOR_2_ID)
    resp = api(DIRECTOR_ID, "director").get(f"{API}/applications/{app.id}")
    assert resp.status_code in (403, 404), (resp.status_code, resp.data)
    assert app.application_number not in json.dumps(resp.data, default=str)
    queue = sel.applications_pending_director_review(principal(DIRECTOR_ID, "director"))
    assert not queue.filter(pk=app.id).exists()


# -- BR-PMS-014..017: submission validation ------------------------------------------------


def _create_draft(api):
    created = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications", application_payload(), format="json")
    assert created.status_code == 201, created.data
    return created.data["id"]


def test_br_t007_br_pms_014_condition_true(api, policy):
    """BR-T007 | BR-PMS-014 condition-true | PDF supporting document is accepted."""
    policy()
    app_id = _create_draft(api)
    up = upload_pdf(api, app_id, "spec.pdf", size=4096)
    assert up.status_code == 201, up.data
    assert ApplicationDocument.objects.filter(application_id=app_id).count() == 1
    done = app_service.transition_application(
        app_id, "submit", principal(APPLICANT_ID, "applicant"))
    assert done.status == sm.SUBMITTED


def test_br_t008_br_pms_014_condition_false(api, policy):
    """BR-T008 | BR-PMS-014 condition-false | Non-PDF supporting document is rejected."""
    policy()
    app_id = _create_draft(api)
    docx = SimpleUploadedFile(
        "spec.docx", b"PK\x03\x04" + b"0" * 2048,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    up = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app_id}/documents",
        {"document_type": "specification", "file": docx}, format="multipart")
    assert up.status_code == 422, (up.status_code, up.data)
    assert not ApplicationDocument.objects.filter(application_id=app_id).exists()

    # The application is not accepted: it has no valid supporting document.
    refused = refusal_status(lambda: app_service.transition_application(
        app_id, "submit", principal(APPLICANT_ID, "applicant")))
    app = PatentApplication.objects.get(pk=app_id)
    assert app.status == sm.DRAFT, "application with a rejected non-PDF document was accepted"
    assert refused in (409, 422), refused


def test_br_t009_br_pms_015_condition_true_under_50_mb(api, policy):
    """BR-T009 | BR-PMS-015 condition-true (under 50 MB) | Document under 50 MB is
    accepted."""
    policy()
    app = seed_application(sm.DRAFT)
    size = int(49.9 * MB)
    assert size < 50 * MB
    doc = doc_service.upload_document(
        principal(APPLICANT_ID, "applicant"), app.id, "specification", "spec.pdf",
        pdf_bytes(size), "/var/patents/spec.pdf")
    assert doc.file_size_bytes == size
    assert ApplicationDocument.objects.filter(application=app).count() == 1


def test_br_t010_br_pms_015_condition_false_50_mb_or_more(api, policy):
    """BR-T010 | BR-PMS-015 condition-false (50 MB or more) | Document of 50 MB or larger
    is rejected."""
    policy()
    app = seed_application(sm.DRAFT)
    applicant = principal(APPLICANT_ID, "applicant")
    outcomes = {}
    for label, size in (("exactly 50 MB", 50 * MB), ("51 MB", 51 * MB)):
        outcomes[label] = refusal_status(lambda size=size: doc_service.upload_document(
            applicant, app.id, "specification", "spec.pdf", pdf_bytes(size),
            "/var/patents/spec.pdf"))
    stored = list(ApplicationDocument.objects.filter(application=app)
                  .values_list("file_size_bytes", flat=True))
    assert outcomes == {"exactly 50 MB": 422, "51 MB": 422}, (outcomes, stored)
    assert not stored
    assert PatentApplication.objects.get(pk=app.id).status == sm.DRAFT


def test_br_t011_br_pms_016_condition_true(api, policy):
    """BR-T011 | BR-PMS-016 condition-true | Malware-free document passes validation."""
    policy()
    app_id = _create_draft(api)
    up = upload_pdf(api, app_id, "clean.pdf", size=8192)
    assert up.status_code == 201, up.data
    assert ApplicationDocument.objects.filter(application_id=app_id).count() == 1
    done = app_service.transition_application(
        app_id, "submit", principal(APPLICANT_ID, "applicant"))
    assert done.status == sm.SUBMITTED


def test_br_t012_br_pms_016_condition_false(api, policy):
    """BR-T012 | BR-PMS-016 condition-false | Document failing malware validation is
    rejected."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no malware scanner or scan hook to make flag a "
        "file (no scanner in services/documents.py, domain/validation.py or core/files)")


def test_br_t013_br_pms_017_condition_true(api, policy):
    """BR-T013 | BR-PMS-017 condition-true | Complete required fields allow submission."""
    policy()
    before = PatentApplication.objects.count()
    app_id = _create_draft(api)
    assert upload_pdf(api, app_id).status_code == 201
    done = app_service.transition_application(
        app_id, "submit", principal(APPLICANT_ID, "applicant"))
    assert done.status == sm.SUBMITTED
    assert done.application_number
    assert PatentApplication.objects.count() == before + 1
    assert PatentApplication.objects.filter(
        application_number=done.application_number).count() == 1


def test_br_t014_br_pms_017_condition_false(api, policy):
    """BR-T014 | BR-PMS-017 condition-false | Missing required field blocks submission."""
    policy()
    before = PatentApplication.objects.count()
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications", application_payload(claims=""), format="json")
    assert PatentApplication.objects.count() == before, "an application ID was created"
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert "claims" in json.dumps(resp.data).lower(), "error does not identify the field"


# -- BR-PMS-020: filing prerequisite --------------------------------------------------------


def test_br_t015_br_pms_020_condition_true(api, policy):
    """BR-T015 | BR-PMS-020 condition-true | External filing allowed when inventor
    agreements are complete."""
    policy()
    app = _filing_ready_application(consent=True)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", {
            "external_filing_id": "PCT/IN2026/050001",
            "filing_type": "international",
            "justification": "Commercial partners in EU and US justify the PCT route.",
        }, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == "PCT/IN2026/050001"


def test_br_t016_br_pms_020_condition_false(api, policy):
    """BR-T016 | BR-PMS-020 condition-false | External filing blocked when inventor
    agreements incomplete."""
    policy()
    app = _filing_ready_application(consent=False)
    before = app.status
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing",
        {"external_filing_id": "IN202611000123"}, format="json")
    app.refresh_from_db()
    assert app.status == before
    assert app.external_filing_id == ""
    assert resp.status_code == 409, (resp.status_code, resp.data)


# -- BR-PMS-022..027: Director assignment ---------------------------------------------------


def test_br_t017_br_pms_022_condition_true(api, policy):
    """BR-T017 | BR-PMS-022 condition-true | Automatic Director assignment uses configured
    rules and governing criteria."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no automatic Director assignment and no assignment "
        "rules or criteria configuration; assign-director only takes an explicit director_id")


def test_br_t018_br_pms_022_condition_false(api, policy):
    """BR-T018 | BR-PMS-022 condition-false | Automatic Director assignment not performed
    without configured rules."""
    pytest.skip(
        "NOT_AUTOMATED: no automatic Director assignment trigger exists in the services, "
        "API or tasks, so there is nothing to invoke without configured rules")


def test_br_t019_br_pms_023_expertise_criterion(api, policy):
    """BR-T019 | BR-PMS-023 expertise criterion | Director expertise matching is applied in
    assignment."""
    pytest.skip(
        "NOT_AUTOMATED: no Director expertise data and no criteria-based assignment or "
        "recommendation exists; assign-director takes an explicit director_id only")


def test_br_t020_br_pms_024_workload_criterion(api, policy):
    """BR-T020 | BR-PMS-024 workload criterion | Director workload balance is applied in
    assignment."""
    pytest.skip(
        "NOT_AUTOMATED: no Director workload tracking and no criteria-based assignment or "
        "recommendation exists; assign-director takes an explicit director_id only")


def test_br_t021_br_pms_025_conflict_check(api, policy):
    """BR-T021 | BR-PMS-025 conflict check | Conflict-of-interest check is performed before
    Director assignment."""
    policy()
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, user_id=DIRECTOR_ID)   # the candidate Director is a recorded inventor
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert app.assigned_director_id is None, "conflicted Director was assigned"
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert not PatentAuditLog.objects.filter(
        application=app, action_type="assign_director").exists()


def test_br_t022_br_pms_026_condition_true_inventor_prohibited(api, policy):
    """BR-T022 | BR-PMS-026 condition-true (inventor prohibited) | Director listed as
    inventor cannot review."""
    policy()
    app = seed_application(sm.SUBMITTED, user_id=DIRECTOR_ID)   # D authored the application
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert app.assigned_director_id is None
    assert resp.status_code == 422, (resp.status_code, resp.data)

    # D also cannot decide the application as reviewer.
    under_review = seed_application(
        sm.UNDER_REVIEW, user_id=DIRECTOR_ID, assigned_director_id=DIRECTOR_ID)
    decision = review(api, under_review, "APPROVE")
    under_review.refresh_from_db()
    assert decision.status_code >= 400, decision.data
    assert under_review.status == sm.UNDER_REVIEW
    assert not under_review.reviews.exists()


def test_br_t023_br_pms_026_condition_false_non_inventor_permitted(api, policy):
    """BR-T023 | BR-PMS-026 condition-false (non-inventor permitted) | Director not listed
    as inventor can review."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = review(api, app, "APPROVE")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.reviews.filter(director_user_id=DIRECTOR_ID, decision="APPROVE").exists()


def test_br_t024_br_pms_027_condition_true_inventor_prohibited(api, policy):
    """BR-T024 | BR-PMS-027 condition-true (inventor prohibited) | PCC_ADMIN listed as
    inventor cannot act as reviewer."""
    policy()
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, user_id=ADMIN_ID)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": ADMIN_ID},
        format="json")
    app.refresh_from_db()
    assert app.assigned_director_id != ADMIN_ID, "PCC_ADMIN was recorded as reviewer"
    assert app.status == sm.SUBMITTED
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_br_t025_br_pms_027_condition_false_non_inventor(api, policy):
    """BR-T025 | BR-PMS-027 condition-false (non-inventor) | PCC_ADMIN not listed as
    inventor is not blocked by this rule."""
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert app.assigned_director_id == DIRECTOR_ID


# -- BR-PMS-029..031: review decision ---------------------------------------------------------


@pytest.mark.parametrize(("decision", "expected"), [
    ("APPROVE", sm.APPROVED),
    ("REJECT", sm.REJECTED),
    ("NEEDS_REVISION", sm.NEEDS_REVISION),
])
def test_br_t026_br_pms_029_valid_decision_values(api, policy, decision, expected):
    """BR-T026 | BR-PMS-029 valid decision values | Director decision Approve, Reject or
    Needs Revision is accepted."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = review(api, app, decision)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == expected
    assert app.reviews.filter(decision=decision).count() == 1


def test_br_t027_br_pms_029_invalid_decision_value(api, policy):
    """BR-T027 | BR-PMS-029 invalid decision value | Decision outside allowed set is
    rejected."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    statuses = [review(api, app, bad).status_code for bad in ("Hold", "")]
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert not app.reviews.exists()
    assert statuses == [422, 422], statuses


def test_br_t028_br_pms_030_condition_true_at_least_50_chars(api, policy):
    """BR-T028 | BR-PMS-030 condition-true (>=50 chars) | Justification of exactly 50
    characters is accepted."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    text = "a" * 50
    resp = review(api, app, "APPROVE", justification=text)
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.APPROVED
    assert app.reviews.get().justification == text


def test_br_t029_br_pms_030_condition_false_under_50_chars(api, policy):
    """BR-T029 | BR-PMS-030 condition-false (<50 chars) | Justification of 49 characters
    is rejected."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = review(api, app, "APPROVE", justification="a" * 49)
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert not app.reviews.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_br_t030_br_pms_031_review_deadline(api, policy):
    """BR-T030 | BR-PMS-031 review deadline | Review deadline is 15 business days from
    assignment."""
    pytest.skip(
        "NOT_AUTOMATED: no interface exposes a review deadline (no deadline field on the "
        "application or review, none in the API payloads); domain/deadlines.py only has a "
        "calendar-day overdue predicate")


def _decided_on_day(days_ago: int) -> datetime.datetime:
    """The decision date as a calendar day: midnight of the day `days_ago` days before today."""
    day = timezone.localdate() - datetime.timedelta(days=days_ago)
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))


# -- BR-PMS-033..038: revision and resubmission -------------------------------------------------


def test_br_t031_br_pms_033_needs_revision_permitted(api, policy):
    """BR-T031 | BR-PMS-033 Needs Revision permitted | Revision allowed for Needs
    Revision status."""
    policy()
    app = _revision_application(sm.NEEDS_REVISION, days_ago=10)
    version = app.version
    resp = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}",
        {"claims": "1. A resonator-coupled circuit of five transmons."}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.claims == "1. A resonator-coupled circuit of five transmons."
    assert app.version > version


def test_br_t032_br_pms_034_rejected_permitted(api, policy):
    """BR-T032 | BR-PMS-034 Rejected permitted | Revision allowed for Rejected status."""
    policy()
    app = _revision_application(sm.REJECTED, days_ago=10)
    version = app.version
    resp = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}",
        {"claims": "1. A resonator-coupled circuit of five transmons."}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.claims == "1. A resonator-coupled circuit of five transmons."
    assert app.version > version


def test_br_t033_br_pms_035_condition_true_within_60_days(api, policy):
    """BR-T033 | BR-PMS-035 condition-true (within 60 days) | Resubmission on day 60 is
    accepted."""
    policy()
    app = _revision_application(sm.NEEDS_REVISION, days_ago=60)
    app.decision_date = _decided_on_day(60)
    app.save()
    version = app.version
    put = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}",
        {"claims": "1. A resonator-coupled circuit of five transmons."}, format="json")
    assert put.status_code == 200, (put.status_code, put.data)
    done = app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT_ID, "applicant"))
    assert done.status == sm.RESUBMITTED
    assert done.version > version


def test_br_t034_br_pms_035_condition_false_after_60_days(api, policy):
    """BR-T034 | BR-PMS-035 condition-false (after 60 days) | Resubmission on day 61 is
    rejected."""
    policy()
    app = _revision_application(sm.NEEDS_REVISION, days_ago=61)
    app.decision_date = _decided_on_day(61)
    app.save()
    put = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}",
        {"claims": "1. A resonator-coupled circuit of five transmons."}, format="json")
    refused = refusal_status(lambda: app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    assert app.status != sm.RESUBMITTED
    assert put.status_code == 422, (put.status_code, put.data)
    assert refused == 422


def test_br_t035_br_pms_036_condition_true(api, policy):
    """BR-T035 | BR-PMS-036 condition-true | Revision addressing Director feedback is
    accepted."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    feedback = "Claim 1 overlaps prior art D1; narrow it to the resonator-coupled variant."
    assert review(api, app, "NEEDS_REVISION", justification=feedback).status_code == 200
    app.refresh_from_db()
    version = app.version

    revised = "1. A resonator-coupled circuit comprising at least five transmons."
    put = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}", {"claims": revised}, format="json")
    assert put.status_code == 200, (put.status_code, put.data)
    done = app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT_ID, "applicant"))
    assert done.status == sm.RESUBMITTED
    assert done.version > version, "no new version recorded"
    assert done.claims == revised


def test_br_t036_br_pms_036_condition_false(api, policy):
    """BR-T036 | BR-PMS-036 condition-false | Revision not addressing Director feedback is
    rejected."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    feedback = "Claim 1 overlaps prior art D1; narrow it to the resonator-coupled variant."
    assert review(api, app, "NEEDS_REVISION", justification=feedback).status_code == 200
    app.refresh_from_db()
    claims_before = app.claims

    # Resubmitted with no revision made in response to the recorded feedback.
    refused = refusal_status(lambda: app_service.transition_application(
        app.id, "resubmit", principal(APPLICANT_ID, "applicant")))
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION, "an unrevised resubmission was accepted"
    assert app.claims == claims_before
    assert refused == 422, refused


def test_br_t037_br_pms_038_condition_true_period_expired(api, policy):
    """BR-T037 | BR-PMS-038 condition-true (period expired) | Application expires after
    60-day period without resubmission."""
    policy()
    app = _revision_application(sm.NEEDS_REVISION, days_ago=61)
    pms_sweep_deadlines()
    app.refresh_from_db()
    assert app.status == sm.EXPIRED


def test_br_t038_br_pms_038_condition_false_period_not_expired(api, policy):
    """BR-T038 | BR-PMS-038 condition-false (period not expired) | Application does not
    expire within the period."""
    policy()
    app = _revision_application(sm.NEEDS_REVISION, days_ago=30)
    pms_sweep_deadlines()
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION


# -- BR-PMS-040..049: Attorney assignment, opinion ------------------------------------------------


def test_br_t039_br_pms_040_pcc_admin_on_approved_permitted(api, policy, mailoutbox):
    """BR-T039 | BR-PMS-040 PCC_ADMIN on Approved permitted | PCC_ADMIN can assign
    Attorney to Approved application."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    before = len(mailoutbox)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.assigned_attorney_id == ATTORNEY_A_ID
    assert app.status == sm.ASSIGNMENT_OFFERED
    assert PatentAuditLog.objects.filter(application=app, action_type="assign_attorney").exists()
    sent = mails_about(mailoutbox, app, before)
    assert any("u401@example.edu" in m.to for m in sent), "Attorney was not notified"


def test_br_t040_br_pms_040_non_pcc_admin_prohibited(api, policy):
    """BR-T040 | BR-PMS-040 non-PCC_ADMIN prohibited | Non-PCC_ADMIN users cannot assign
    Attorneys."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    for user_id, role in ((DIRECTOR_ID, "director"), (APPLICANT_ID, "applicant")):
        resp = api(user_id, role).post(
            f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
            format="json")
        assert resp.status_code == 403, (role, resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.assigned_attorney_id is None
    assert app.status == sm.APPROVED
    assert not PatentAuditLog.objects.filter(
        application=app, action_type="assign_attorney").exists()


def test_br_t041_br_pms_040_non_approved_application_prohibited(api, policy):
    """BR-T041 | BR-PMS-040 non-Approved application prohibited | Attorney cannot be
    assigned to non-Approved application."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    app.refresh_from_db()
    assert app.assigned_attorney_id is None
    assert app.status == sm.UNDER_REVIEW
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_br_t042_br_pms_041_in_panel_permitted(api, policy):
    """BR-T042 | BR-PMS-041 in-panel permitted | Approved-panel Attorney can be assigned."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.assigned_attorney_id == ATTORNEY_A_ID


def test_br_t043_br_pms_041_out_of_panel_prohibited(api, policy):
    """BR-T043 | BR-PMS-041 out-of-panel prohibited | Non-panel Attorney cannot be
    assigned without exception."""
    policy()
    panel_attorney(ATTORNEY_B_ID, approved=False)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_B_ID},
        format="json")
    app.refresh_from_db()
    assert app.assigned_attorney_id is None
    assert app.status == sm.APPROVED
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_br_t044_br_pms_041_exception(api, policy):
    """BR-T044 | BR-PMS-041 exception | Non-panel Attorney can be assigned with recorded
    institutional exception."""
    pytest.skip(
        "NOT_AUTOMATED: no institutional-exception concept exists; assign-attorney takes only "
        "attorney_id and rejects every non-panel Attorney, with no way to record or reference "
        "an exception")


def test_br_t045_br_pms_042_expertise_criterion(api, policy):
    """BR-T045 | BR-PMS-042 expertise criterion | Attorney expertise matching is applied."""
    pytest.skip(
        "NOT_AUTOMATED: no Attorney recommendation or criteria-based selection interface; "
        "expertise_domains is stored on the panel member but nothing uses it, and assignment "
        "takes an explicit attorney_id")


def test_br_t046_br_pms_043_workload_criterion(api, policy):
    """BR-T046 | BR-PMS-043 workload criterion | Attorney workload is applied."""
    pytest.skip(
        "NOT_AUTOMATED: no Attorney recommendation or criteria-based selection interface; "
        "only a hard workload ceiling is enforced on an explicit attorney_id")


def test_br_t047_br_pms_044_conflict_check(api, policy):
    """BR-T047 | BR-PMS-044 conflict check | Conflict-of-interest check is performed before
    Attorney assignment."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    add_coinventor(app, user_id=ATTORNEY_A_ID)   # the Attorney is a recorded inventor
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    app.refresh_from_db()
    assert app.assigned_attorney_id is None, "conflicted Attorney was assigned"
    assert app.status == sm.APPROVED
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_br_t048_br_pms_045_condition_true_preferred_in_panel(api, policy):
    """BR-T048 | BR-PMS-045 condition-true (preferred in panel) | Applicant preference
    considered when preferred Attorney is in panel."""
    pytest.skip(
        "NOT_AUTOMATED: no Applicant Attorney-preference field or input exists on the "
        "application or any endpoint, and no recommendation interface to consider it")


def test_br_t049_br_pms_045_condition_false_preferred_not_in_panel(api, policy):
    """BR-T049 | BR-PMS-045 condition-false (preferred not in panel) | Applicant
    preference not applied when preferred Attorney is outside panel."""
    pytest.skip(
        "NOT_AUTOMATED: no Applicant Attorney-preference field or input exists on the "
        "application or any endpoint, and no recommendation interface to consider it")


def _assessment_application():
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID,
    )


def _opinion_trace(api, app) -> str:
    """Everything the module exposes about the application, plus its audit lines."""
    detail = api(ADMIN_ID, "pcc_admin").get(f"{API}/applications/{app.id}").data
    return json.dumps(dict(detail), default=str) + json.dumps(audit_entries(api, app))


@pytest.mark.parametrize("recommendation", ["File Patent", "Do Not File", "Needs Amendment"])
def test_br_t050_br_pms_046_valid_recommendation(api, policy, mailoutbox, recommendation):
    """BR-T050 | BR-PMS-046 valid recommendation | Opinion with one of File Patent / Do Not
    File / Needs Amendment is accepted."""
    policy()
    app = _assessment_application()
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/assessment",
        {"action": "finalize", "recommendation": recommendation}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert recommendation in _opinion_trace(api, app), "opinion recommendation not recorded"
    assert mails_about(mailoutbox, app, before), "stakeholders were not notified"


@pytest.mark.parametrize("recommendation", ["Maybe", "", None])
def test_br_t051_br_pms_046_invalid_recommendation(api, policy, recommendation):
    """BR-T051 | BR-PMS-046 invalid recommendation | Opinion without a valid single
    recommendation is rejected."""
    policy()
    app = _assessment_application()
    body = {"action": "finalize"}
    if recommendation is not None:
        body["recommendation"] = recommendation
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/assessment", body, format="json")
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert not PatentAuditLog.objects.filter(
        application=app, action_type__icontains="opinion").exists()


# -- BR-PMS-048..053: budget -----------------------------------------------------------------------


def _assert_budget_refused(api, app, requests):
    responses = decide_via_api(api, app, requests)
    assert not PatentBudgetLedger.objects.filter(application=app, status="APPROVED").exists(), (
        "an incomplete budget was approved")
    assert [r.status_code for r in responses] == [422] * len(requests), (
        [(r.status_code, getattr(r, "data", None)) for r in responses])


def test_br_t052_br_pms_048_missing_filing_fees(api, policy):
    """BR-T052 | BR-PMS-048 missing filing fees | Budget without filing fees is rejected."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = [
        budget_request(app, "ATTORNEY_FEE", "60000.00", "PROFESSIONAL_FEE"),
        budget_request(app, "ADMIN_FEE", "5000.00", "ADMINISTRATIVE"),
    ]
    _assert_budget_refused(api, app, requests)


def test_br_t053_br_pms_049_missing_attorney_fees(api, policy):
    """BR-T053 | BR-PMS-049 missing attorney fees | Budget without attorney fees is
    rejected."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = [
        budget_request(app, "FILING_FEE", "20000.00", "GOVERNMENT_FEE"),
        budget_request(app, "ADMIN_FEE", "5000.00", "ADMINISTRATIVE"),
    ]
    _assert_budget_refused(api, app, requests)


def test_br_t054_br_pms_050_missing_administrative_costs(api, policy):
    """BR-T054 | BR-PMS-050 missing administrative costs | Budget without administrative
    costs is rejected."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = [
        budget_request(app, "FILING_FEE", "20000.00", "GOVERNMENT_FEE"),
        budget_request(app, "ATTORNEY_FEE", "60000.00", "PROFESSIONAL_FEE"),
    ]
    _assert_budget_refused(api, app, requests)


def test_br_t055_br_pms_051_condition_true_exceeds_threshold(api, policy):
    """BR-T055 | BR-PMS-051 condition-true (exceeds threshold) | Total cost above
    threshold is escalated."""
    policy(threshold=THRESHOLD)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = complete_budget(app, "50000.00", "80000.00", "20000.01")
    assert sum(r.amount for r in requests) == THRESHOLD + Decimal("0.01")
    responses = decide_via_api(api, app, requests)
    assert all(r.status_code == 200 for r in responses), [r.data for r in responses]
    escalated = PatentBudgetLedger.objects.filter(
        application=app, entry_kind="ESCALATION", status="ESCALATED")
    assert escalated.exists(), "no escalation recorded for a total cost above the threshold"
    assert budget_service.approved_total(app.id) < THRESHOLD + Decimal("0.01"), (
        "the whole budget was approved by the Director despite exceeding the threshold")


def test_br_t056_br_pms_051_condition_false_at_threshold(api, policy):
    """BR-T056 | BR-PMS-051 condition-false (at threshold) | Total cost equal to threshold
    is not escalated."""
    policy(threshold=THRESHOLD)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = complete_budget(app, "50000.00", "80000.00", "20000.00")
    assert sum(r.amount for r in requests) == THRESHOLD
    responses = decide_via_api(api, app, requests)
    assert [r.status_code for r in responses] == [200, 200, 200], [r.data for r in responses]
    assert [r.data["status"] for r in responses] == ["APPROVED"] * 3
    assert not PatentBudgetLedger.objects.filter(
        application=app, entry_kind="ESCALATION").exists()
    assert budget_service.approved_total(app.id) == THRESHOLD


def test_br_t057_br_pms_052_condition_true(api, policy):
    """BR-T057 | BR-PMS-052 condition-true | Budget approval permitted for Approved
    application."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = complete_budget(app, "20000.00", "60000.00", "5000.00")
    responses = decide_via_api(api, app, requests)
    assert [r.status_code for r in responses] == [200, 200, 200], [r.data for r in responses]
    assert PatentBudgetLedger.objects.filter(
        application=app, entry_kind="APPROVAL", status="APPROVED").count() == 3


def test_br_t058_br_pms_052_condition_false(api, policy):
    """BR-T058 | BR-PMS-052 condition-false | Budget approval prohibited for non-Approved
    application."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    requests = complete_budget(app, "20000.00", "60000.00", "5000.00")
    responses = decide_via_api(api, app, requests)
    assert not PatentBudgetLedger.objects.filter(
        application=app, entry_kind__in=("APPROVAL", "ESCALATION")).exists(), (
        "a budget decision was recorded for an application that is not Approved")
    assert [r.status_code for r in responses] == [409, 409, 409], [r.data for r in responses]


def test_br_t059_br_pms_053_availability_present_sufficient(api, policy):
    """BR-T059 | BR-PMS-053 availability info present - sufficient | Approval proceeds when
    available budget is sufficient."""
    pytest.skip(
        "NOT_AUTOMATED: PMS has no budget-availability information (no model, setting or "
        "integration) that a test could populate as sufficient")


def test_br_t060_br_pms_053_availability_present_insufficient(api, policy):
    """BR-T060 | BR-PMS-053 availability info present - insufficient | Approval blocked
    when available budget is insufficient."""
    pytest.skip(
        "NOT_AUTOMATED: PMS has no budget-availability information (no model, setting or "
        "integration) that a test could populate as insufficient")


def test_br_t061_br_pms_053_availability_absent(api, policy):
    """BR-T061 | BR-PMS-053 availability info absent | Availability validation not applied
    when info is unavailable."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    requests = complete_budget(app, "20000.00", "60000.00", "5000.00")
    responses = decide_via_api(api, app, requests)
    assert [r.status_code for r in responses] == [200, 200, 200], [r.data for r in responses]
    assert [r.data["status"] for r in responses] == ["APPROVED"] * 3


# -- BR-PMS-055 / 056: filing package ---------------------------------------------------------------


def test_br_t062_br_pms_055_compliant_package(api, policy):
    """BR-T062 | BR-PMS-055 compliant package | Compliant filing package recorded as
    ready."""
    pytest.skip(
        "NOT_AUTOMATED: no patent-office format validation rules or filing-package validation "
        "interface exists (filing clearance hard-codes format compliance to true)")


def test_br_t063_br_pms_055_non_compliant_package(api, policy):
    """BR-T063 | BR-PMS-055 non-compliant package | Non-compliant filing package not
    recorded as ready."""
    pytest.skip(
        "NOT_AUTOMATED: no patent-office format validation rules or filing-package validation "
        "interface exists (filing clearance hard-codes format compliance to true), so a "
        "violating package cannot be presented")


def test_br_t064_br_pms_056_international_with_justification(api, policy):
    """BR-T064 | BR-PMS-056 international with justification | International filing with
    justification accepted."""
    policy()
    app = _filing_ready_application(consent=True)
    justification = "Commercial partners in EU and US justify PCT national-phase cost."
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", {
            "external_filing_id": "PCT/IN2026/050124",
            "filing_type": "international",
            "jurisdiction": "PCT",
            "justification": justification,
        }, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.filing_justification == justification


def test_br_t065_br_pms_056_international_without_justification(api, policy):
    """BR-T065 | BR-PMS-056 international without justification | International filing
    without justification rejected."""
    policy()
    app = _filing_ready_application(consent=True)
    before = app.status
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", {
            "external_filing_id": "PCT/IN2026/050125",
            "filing_type": "international",
            "jurisdiction": "PCT",
        }, format="json")
    app.refresh_from_db()
    assert app.status == before
    assert app.external_filing_id == ""
    assert resp.status_code == 422, (resp.status_code, resp.data)


# -- BR-PMS-059..061: post-grant maintenance ---------------------------------------------------------


def test_br_t066_br_pms_059_condition_true(api, policy):
    """BR-T066 | BR-PMS-059 condition-true | Post-grant tracking activates for Granted
    patents."""
    policy()
    app = _granted_application()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["maintenance_state"] == "DECISION_REQUESTED"
    app.refresh_from_db()
    assert app.maintenance_state == "DECISION_REQUESTED"
    tracked = sel.granted_applications(principal(ATTORNEY_A_ID, "attorney"))
    assert tracked.filter(pk=app.id).exists()


def test_br_t067_br_pms_059_condition_false(api, policy):
    """BR-T067 | BR-PMS-059 condition-false | Post-grant tracking not activated for
    non-Granted applications."""
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.FILED, assigned_attorney_id=ATTORNEY_A_ID, external_filing_id="IN202611000123",
        filing_date=timezone.now().date())
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/renewal-request", {}, format="json")
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.maintenance_state == ""
    assert app.renewal_requested_at is None
    assert not RenewalHistory.objects.filter(application=app).exists()
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_br_t068_br_pms_060_schedule_rules_available(api, policy):
    """BR-T068 | BR-PMS-060 schedule rules available | Maintenance schedule computed from
    grant date and jurisdiction."""
    pytest.skip(
        "NOT_AUTOMATED: no jurisdiction maintenance-schedule rules or schedule-generation "
        "interface exists; PMS never derives due dates (the Attorney supplies next_due_date)")


def test_br_t069_br_pms_060_schedule_rules_unavailable(api, policy):
    """BR-T069 | BR-PMS-060 schedule rules unavailable | No schedule computed when rules
    unavailable."""
    pytest.skip(
        "NOT_AUTOMATED: there is no 'generate maintenance-fee schedule' action in the "
        "services, API or tasks to invoke")


@pytest.mark.parametrize(("renew", "outcome"), [(True, "RENEW"), (False, "DO_NOT_RENEW")])
def test_br_t070_br_pms_061_decision_recorded(api, policy, renew, outcome):
    """BR-T070 | BR-PMS-061 decision recorded | Explicit Renew/Do Not Renew decision
    accepted before deadline."""
    policy()
    app = _granted_application()
    due = app.renewal_due_date
    assert due > timezone.now().date()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/renewal-decision", {"renew": renew}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    entry = app.renewal_history.get()
    assert entry.decision == outcome
    assert entry.cycle_due_date == due
    assert entry.decided_by_user_id == DIRECTOR_ID
    assert app.renewal_decision == outcome


def test_br_t071_br_pms_061_decision_missing(api, policy):
    """BR-T071 | BR-PMS-061 decision missing | Maintenance action cannot proceed without
    explicit renewal decision."""
    policy()
    app = _granted_application()
    due = app.renewal_due_date
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/maintenance-action", {
            "reference": "IPO-ANNUITY-2026-0099",
            "next_due_date": (due + datetime.timedelta(days=365)).isoformat(),
        }, format="json")
    app.refresh_from_db()
    assert not app.renewal_history.exists()
    assert app.renewal_due_date == due
    assert app.maintenance_state in ("", "ACTIVE")
    assert resp.status_code == 409, (resp.status_code, resp.data)


# -- BR-PMS-065: office-action response deadline ---------------------------------------------------


def test_br_t072_br_pms_065_within_deadline(api, policy):
    """BR-T072 | BR-PMS-065 within deadline | Response submitted within deadline accepted."""
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        external_filing_id="IN202611000123", filing_date=timezone.now().date())
    today = timezone.now().date()
    deadline = today + datetime.timedelta(days=30)
    created = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/office-actions", {
            "action_code": "FER-1",
            "issuing_authority": "Indian Patent Office",
            "issued_date": today.isoformat(),
            "response_deadline": deadline.isoformat(),
            "requires_applicant_review": False,
        }, format="json")
    assert created.status_code == 201, created.data
    oa_id = created.data["id"]
    drafted = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/office-actions/{oa_id}/response",
        {"response_summary": "Distinguish claim 1 over D1 by resonator coupling."},
        format="json")
    assert drafted.status_code == 200, drafted.data

    oa_service.submit_response(principal(ATTORNEY_A_ID, "attorney"), oa_id)
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert oa.status == "SUBMITTED"
    assert oa.submitted_at is not None
    assert oa.submitted_at.date() <= oa.response_deadline
