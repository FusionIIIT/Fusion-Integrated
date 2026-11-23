"""Spec tests for patents, FR (functional requirement) strategy, second half.

Generated from the frozen docs/11-patents/spec-tests/FR_DESIGN.json: cases FR-T112 to
FR-T222 (the last 111 cases, in file order). Every test carries its test_id and source_id
in its name and docstring.

Behaviour is driven through the module's public interfaces: the HTTP API where an endpoint
exists, otherwise the service layer or the deadline sweep task. Preconditions that place an
application in a given state are seeded directly, as the module's own journey tests do.

Refusal status codes, where the design names none, come from
docs/01-architecture/api-conventions.md "Status codes": 409 for "the world is in the wrong
state" (illegal transition, unmet record prerequisite), 422 for invalid input or a
policy-based business-rule refusal.

Cases whose interface does not exist in the module (no endpoint, service, model or task
for the behaviour, or no seam to supply the stubbed external source the case needs) are
written as skipped tests with a NOT_AUTOMATED reason.
"""
from __future__ import annotations

import datetime
import itertools
import json
import logging
import re
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from freezegun import freeze_time
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
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentAuditLog,
    PatentBudgetLedger,
    PatentPolicy,
    TechnologyTransferRecord,
)
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import tech_transfer as tt_service
from modules.patents.tasks import pms_sweep_deadlines

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
OUTSIDER_ID = 555

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

    def as_(user_id: int, role: str | None = None, *, permissions=(), modules=("patents",)):
        if role is None:
            session = make_session(
                user_id=user_id, roles=(), active_role="",
                permissions=tuple(permissions), modules=tuple(modules),
            )
        else:
            code, perms = ROLE_OF[role]
            session = make_session(
                user_id=user_id, roles=(code,), active_role=code,
                permissions=tuple(perms), modules=("patents",),
            )
        stub_iam(session, users=DIRECTORY)
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
        "application_number": f"PMS-FRB-{next(_seq):04d}",
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
        application=app, user_id=user_id, name="Dr. Sarah Rao",
        email="sarah.rao@example.edu", share_percentage=Decimal(share),
        consent_granted=consent, consent_timestamp=timezone.now() if consent else None,
    )


def seed_document(app, version: int, doc_type: str = "specification") -> ApplicationDocument:
    return ApplicationDocument.objects.create(
        application=app, document_type=doc_type, file_name=f"spec_v{version}.pdf",
        file_size_bytes=2048, storage_path=f"/var/patents/app_{app.id}/spec_v{version}.pdf",
        version=version, uploaded_by_user_id=app.user_id,
    )


def approve_budget(app, amount=Decimal("45000.00")) -> PatentBudgetLedger:
    """Precondition: a budget request decided Approved by the Director."""
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE", amount, "GOVERNMENT_FEE",
    )
    return budget_service.decide_budget(principal(DIRECTOR_ID, "director"), req.id, "APPROVE")


def filing_ready(consent: bool = True, budget: bool = True, jurisdiction: str = "IN"):
    """Attorney assigned and working the case, inventor agreements per `consent`, budget
    approved when `budget` (otherwise only a pending, undecided request exists)."""
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.ASSESSMENT_IN_PROGRESS, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID, jurisdiction=jurisdiction,
    )
    add_coinventor(app, consent=consent)
    if budget:
        approve_budget(app)
    else:
        budget_service.record_budget_entry(
            principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE",
            Decimal("45000.00"), "GOVERNMENT_FEE",
        )
    return app


def filing_payload(**extra) -> dict:
    payload = {
        "external_filing_id": "IN202611000123",
        "filing_date": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
        "jurisdiction": "IN",
        "filing_office": "Indian Patent Office",
        "confirmation": "IPO-ACK-2026-000123",
    }
    payload.update(extra)
    return payload


def mails_about(mailoutbox, app, start: int = 0) -> list:
    """Messages issued since `start` that concern this application."""
    marker = app.application_number
    return [
        m for m in mailoutbox[start:]
        if marker in (m.subject or "") or marker in (m.body or "")
    ]


def mails_to(mailoutbox, app, user_id: int, start: int = 0) -> list:
    address = f"u{user_id}@example.edu"
    return [m for m in mails_about(mailoutbox, app, start) if address in m.to]


def audit_lines(api, app=None) -> list[str]:
    """Audit log lines (PCC_ADMIN view); those concerning `app` when it is given."""
    resp = api(ADMIN_ID, "pcc_admin").get(f"{API}/audit-logs")
    assert resp.status_code == 200
    lines = [json.dumps(e, default=str) if not isinstance(e, str) else e
             for e in resp.data.get("audit_logs", [])]
    if app is None:
        return lines
    return [ln for ln in lines if app.application_number in ln]


def line_action(line: str) -> str:
    found = re.search(r"action=(\S+)", line)
    return found.group(1) if found else ""


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


def create_payload(**extra) -> dict:
    payload = {
        "title": "Topological qubit layout",
        "abstract": "A surface-code layout for superconducting transmon qubits.",
        "description": "Detailed description of resonator coupling and error syndromes.",
        "claims": "1. A circuit comprising at least five coupled transmons.",
        "domain_category": "Quantum",
    }
    payload.update(extra)
    return payload


def inventor(name: str | None, share: str, email: str = "inv@example.edu") -> dict:
    data = {"name": name, "email": email, "share_percentage": share}
    return {k: v for k, v in data.items() if v is not None}


def _pdf(name: str = "spec.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"%PDF-1.4\n" + b"0" * 2048, "application/pdf")


def upload(api, app_id: int, name: str = "spec.pdf", doc_type: str = "specification"):
    """The Applicant uploads a document (a new version when one of that type exists)."""
    return api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app_id}/documents",
        {"document_type": doc_type, "file": _pdf(name)}, format="multipart")


def _withdraw(api, app, reason, user_id: int = APPLICANT_ID):
    return api(user_id, "applicant").post(
        f"{API}/applications/{app.id}/withdraw", {"reason": reason}, format="json")


def sweep_after(days: int) -> dict:
    """Run the daily deadline sweep as if `days` days from now had arrived."""
    with freeze_time(timezone.now() + datetime.timedelta(days=days)):
        return pms_sweep_deadlines()


def _appeal_submitted_application(**fields):
    app = seed_application(
        sm.APPEAL_SUBMITTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=2), **fields,
    )
    AppealRecord.objects.create(
        application=app, applicant_user_id=APPLICANT_ID,
        grounds="D1 does not disclose resonator coupling.",
    )
    return app


def _rejected_application(**fields):
    return seed_application(
        sm.REJECTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=3), **fields,
    )


def _record_office_action(api, app, days_to_deadline: int, requires_review: bool = False):
    today = timezone.now().date()
    resp = api(ATTORNEY_A_ID, "attorney").post(f"{API}/applications/{app.id}/office-actions", {
        "action_code": "FER-1",
        "issuing_authority": "Indian Patent Office",
        "issued_date": today.isoformat(),
        "response_deadline": (today + datetime.timedelta(days=days_to_deadline)).isoformat(),
        "requires_applicant_review": requires_review,
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data["id"]


def _filed_application():
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.FILED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        external_filing_id="IN202611000123", filing_date=timezone.now().date(),
    )


def _attorney_assigned_application():
    panel_attorney(ATTORNEY_A_ID, workload=1)
    return seed_application(
        sm.ATTORNEY_ASSIGNED, assigned_director_id=DIRECTOR_ID,
        assigned_attorney_id=ATTORNEY_A_ID,
    )


# -- PMS-AFR-125..131: withdrawal -----------------------------------------------------


def test_fr_t112_pms_afr_125_applicant_withdraws_pre_filing_application(api, policy):
    """FR-T112 | PMS-AFR-125 | Applicant withdraws pre-filing application."""
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = _withdraw(api, app, "Withdrawing to fold this into a broader continuation filing.")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN


def test_fr_t113_pms_afr_126_withdrawal_rejected_after_filing_stage(api, policy):
    """FR-T113 | PMS-AFR-126 | Withdrawal rejected after filing stage."""
    policy(withdrawal_states=sorted(sm.PRE_FILING_STATES))
    app = seed_application(sm.FILED, external_filing_id="IN202611000123",
                           filing_date=timezone.now().date())
    resp = _withdraw(api, app, "No longer commercially relevant.")
    app.refresh_from_db()
    assert app.status == sm.FILED
    assert resp.status_code == 409, (resp.status_code, resp.data)
    assert not PatentAuditLog.objects.filter(application=app, action_type="withdraw").exists()


def test_fr_t114_pms_afr_127_withdrawal_without_reason_rejected(api, policy):
    """FR-T114 | PMS-AFR-127 | Withdrawal without reason rejected."""
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = _withdraw(api, app, "")
    app.refresh_from_db()
    assert app.status == sm.UNDER_REVIEW
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert not PatentAuditLog.objects.filter(application=app, action_type="withdraw").exists()


def test_fr_t115_pms_afr_128_coinventor_consent_recorded_for_withdrawal(api, policy):
    """FR-T115 | PMS-AFR-128 | Co-inventor consent recorded for withdrawal."""
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)
    add_coinventor(app, consent=False)

    resp = api(COINVENTOR_ID, "applicant").post(f"{API}/applications/{app.id}/consent")
    assert resp.status_code == 200, resp.data
    assert resp.data["consent_recorded"] is True

    resp = _withdraw(api, app, "Withdrawing to fold this into a broader continuation filing.")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN

    detail = api(ADMIN_ID, "pcc_admin").get(f"{API}/applications/{app.id}").data
    assert detail["co_inventors"]
    assert all(ci["consent_granted"] and ci["consent_timestamp"]
               for ci in detail["co_inventors"])
    withdrawal = [ln for ln in audit_lines(api, app) if line_action(ln) == "withdraw"]
    assert withdrawal, "withdrawal was not recorded"
    assert "1/1" in withdrawal[0], f"consent not recorded with the withdrawal: {withdrawal[0]}"


def test_fr_t116_pms_afr_129_status_withdrawn_after_permitted_withdrawal(api, policy):
    """FR-T116 | PMS-AFR-129 | Status Withdrawn after permitted withdrawal."""
    policy(withdrawal_states=[sm.SUBMITTED])
    app = seed_application(sm.SUBMITTED)
    resp = _withdraw(api, app, "Withdrawing to fold this into a broader continuation filing.")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["status"] == sm.WITHDRAWN
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN


def test_fr_t117_pms_afr_130_withdrawn_application_removed_from_active_queue(api, policy):
    """FR-T117 | PMS-AFR-130 | Withdrawn application removed from active queue."""
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    assert in_active_queue(app), "precondition: application is in the active queue"
    resp = _withdraw(api, app, "Withdrawing to fold this into a broader continuation filing.")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert not in_active_queue(app)


def test_fr_t118_pms_afr_131_withdrawal_history_maintained(api, policy):
    """FR-T118 | PMS-AFR-131 | Withdrawal history maintained."""
    policy(withdrawal_states=[sm.UNDER_REVIEW])
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    reason = "Withdrawing to fold this into a broader continuation filing."
    assert _withdraw(api, app, reason).status_code == 200

    history = [ln for ln in audit_lines(api, app) if line_action(ln) == "withdraw"]
    assert history, "no withdrawal entry in the history"
    entry = history[0]
    assert reason in entry
    assert f"user={APPLICANT_ID}" in entry
    assert timezone.now().date().isoformat() in entry


# -- PMS-AFR-132..140: inventors and consent ------------------------------------------


def test_fr_t119_pms_afr_132_applicant_manages_multiple_inventors(api, policy):
    """FR-T119 | PMS-AFR-132 | Applicant manages multiple inventors."""
    policy()
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/applications", create_payload(
        co_inventors=[
            inventor("Asha Verma", "60.00", "asha@example.edu"),
            inventor("Dr. Sarah Rao", "40.00", "sarah@example.edu"),
        ]), format="json")
    assert resp.status_code == 201, resp.data
    detail = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{resp.data['id']}").data
    assert sorted(ci["name"] for ci in detail["co_inventors"]) == ["Asha Verma", "Dr. Sarah Rao"]


def test_fr_t120_pms_afr_133_applicant_manages_ownership_shares(api, policy):
    """FR-T120 | PMS-AFR-133 | Applicant manages ownership shares."""
    policy()
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/applications", create_payload(
        co_inventors=[
            inventor("Asha Verma", "60.00", "asha@example.edu"),
            inventor("Dr. Sarah Rao", "40.00", "sarah@example.edu"),
        ]), format="json")
    assert resp.status_code == 201, resp.data
    app = PatentApplication.objects.get(pk=resp.data["id"])
    shares = {ci.name: ci.share_percentage for ci in app.co_inventors.all()}
    assert shares == {"Asha Verma": Decimal("60.00"), "Dr. Sarah Rao": Decimal("40.00")}


def test_fr_t121_pms_afr_134_invalid_inventor_information_rejected(api, policy):
    """FR-T121 | PMS-AFR-134 | Invalid inventor information rejected."""
    policy()
    before = PatentApplication.objects.count()
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/applications", create_payload(
        co_inventors=[inventor(None, "100.00", "asha@example.edu")]), format="json")
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert PatentApplication.objects.count() == before
    assert not CoInventor.objects.exists()


def test_fr_t122_pms_afr_135_invalid_ownership_percentages_rejected(api, policy):
    """FR-T122 | PMS-AFR-135 | Invalid ownership percentages rejected."""
    policy()
    client = api(APPLICANT_ID, "applicant")
    for shares in (("60.00", "60.00"), ("110.00", "-10.00")):
        resp = client.post(f"{API}/applications", create_payload(co_inventors=[
            inventor("Asha Verma", shares[0], "asha@example.edu"),
            inventor("Dr. Sarah Rao", shares[1], "sarah@example.edu"),
        ]), format="json")
        assert resp.status_code == 422, (shares, resp.status_code, resp.data)
    assert not PatentApplication.objects.exists()
    assert not CoInventor.objects.exists()


def test_fr_t123_pms_afr_136_filing_blocked_without_inventor_consent(api, policy):
    """FR-T123 | PMS-AFR-136 | Filing blocked without inventor consent."""
    policy()
    app = filing_ready(consent=False)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", filing_payload(), format="json")
    app.refresh_from_db()
    assert app.status == sm.ASSESSMENT_IN_PROGRESS
    assert app.external_filing_id == ""
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_fr_t124_pms_afr_137_esignature_collected_for_consent():
    """FR-T124 | PMS-AFR-137 | E-signature collected for consent."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no e-signature configuration, endpoint or field; the "
        "consent interfaces (POST consent, consent-token, consent/confirm) accept no "
        "signature and nothing stores one"
    )


def test_fr_t125_pms_afr_138_invalid_esignature_rejected():
    """FR-T125 | PMS-AFR-138 | Invalid e-signature rejected."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no e-signature configuration, endpoint or field to "
        "submit a signature to, so a tampered signature cannot be presented"
    )


def test_fr_t126_pms_afr_140_affected_parties_notified_on_inventor_change():
    """FR-T126 | PMS-AFR-140 | Affected parties notified on inventor change."""
    pytest.skip(
        "NOT_AUTOMATED: no endpoint or service changes inventor information on an existing "
        "application (PUT /applications/<id> takes no co_inventors; the only inventor "
        "interfaces are creation and consent)"
    )


# -- PMS-AFR-141..149: prior-art search ------------------------------------------------


def test_fr_t127_pms_afr_141_applicant_searches_prior_art(api, policy):
    """FR-T127 | PMS-AFR-141 | Applicant searches prior art."""
    policy()
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/prior-art/search", {"query": "transmon resonator coupling"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["results"], "the search returned no results"


def test_fr_t128_pms_afr_142_attorney_searches_prior_art(api, policy):
    """FR-T128 | PMS-AFR-142 | Attorney searches prior art."""
    policy()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/prior-art/search", {"query": "transmon resonator coupling"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert resp.data["results"], "the search returned no results"


def test_fr_t129_pms_afr_143_patent_database_queried():
    """FR-T129 | PMS-AFR-143 | Patent database queried."""
    pytest.skip(
        "NOT_AUTOMATED: the search endpoint has no search-source configuration or "
        "injection seam, so a stub patent database cannot be supplied or observed"
    )


def test_fr_t130_pms_afr_144_publication_database_queried():
    """FR-T130 | PMS-AFR-144 | Publication database queried."""
    pytest.skip(
        "NOT_AUTOMATED: the search endpoint has no search-source configuration or "
        "injection seam, so a stub publication database cannot be supplied or observed"
    )


def test_fr_t131_pms_afr_145_results_displayed_with_relevance_ranking():
    """FR-T131 | PMS-AFR-145 | Results displayed with relevance ranking."""
    pytest.skip(
        "NOT_AUTOMATED: no search-source seam exists to make a source return several "
        "results, and the search response has no relevance ranking field"
    )


def test_fr_t132_pms_afr_146_selected_references_attached_to_application():
    """FR-T132 | PMS-AFR-146 | Selected references attached to application."""
    pytest.skip(
        "NOT_AUTOMATED: no endpoint, service or model attaches a prior-art reference to an "
        "application"
    )


def test_fr_t133_pms_afr_147_search_sessions_logged(api, policy):
    """FR-T133 | PMS-AFR-147 | Search sessions logged."""
    policy()
    query = "quantum transmon surface code"
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/prior-art/search", {"query": query}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)

    entries = [ln for ln in audit_lines(api) if query in ln]
    assert entries, "no search session log entry with the query"
    entry = entries[0]
    assert f"user={APPLICANT_ID}" in entry
    assert timezone.now().date().isoformat() in entry


def test_fr_t134_pms_afr_148_keyword_optimization_supported():
    """FR-T134 | PMS-AFR-148 | Keyword optimization supported."""
    pytest.skip(
        "NOT_AUTOMATED: no endpoint or service offers keyword optimization; the search "
        "endpoint only echoes the query"
    )


def test_fr_t135_pms_afr_149_classification_mapping_supported():
    """FR-T135 | PMS-AFR-149 | Classification mapping supported."""
    pytest.skip("NOT_AUTOMATED: no endpoint or service offers classification mapping")


# -- PMS-AFR-150..157: documents --------------------------------------------------------


def test_fr_t136_pms_afr_150_document_version_history_maintained(api, policy):
    """FR-T136 | PMS-AFR-150 | Document version history maintained."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    seed_document(app, 2)
    detail = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert detail.status_code == 200
    assert sorted(d["version"] for d in detail.data["documents"]) == [1, 2]


def test_fr_t137_pms_afr_151_permitted_upload_of_new_version(api, policy):
    """FR-T137 | PMS-AFR-151 | Permitted upload of new version."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert app.documents.count() == 2


def test_fr_t138_pms_afr_151_upload_rejected_when_role_or_status_not_permitted(api, policy):
    """FR-T138 | PMS-AFR-151 | Upload rejected when role/status not permitted."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 409, (resp.status_code, resp.data)
    assert app.documents.count() == 1


def test_fr_t139_pms_afr_152_automatic_version_numbering(api, policy):
    """FR-T139 | PMS-AFR-152 | Automatic version numbering."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 201, (resp.status_code, resp.data)
    assert resp.data["version"] == 2


def test_fr_t140_pms_afr_153_previous_versions_archived(api, policy):
    """FR-T140 | PMS-AFR-153 | Previous versions archived."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    assert upload(api, app.id).status_code == 201
    detail = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}").data
    by_version = {d["version"]: d for d in detail["documents"]}
    assert sorted(by_version) == [1, 2], "version 1 is not retained alongside version 2"
    assert by_version[1]["file_name"] == "spec_v1.pdf"


def test_fr_t141_pms_afr_154_previous_versions_accessible_per_rules(api, policy):
    """FR-T141 | PMS-AFR-154 | Previous versions accessible per rules."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    seed_document(app, 2)
    resp = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200
    assert 1 in [d["version"] for d in resp.data["documents"]]


def test_fr_t142_pms_afr_154_previous_version_access_denied_to_unauthorized_role(
        api, policy):
    """FR-T142 | PMS-AFR-154 | Previous version access denied to unauthorized role."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    seed_document(app, 2)
    resp = api(OTHER_APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 404, (resp.status_code, resp.data)
    assert not sel.documents_for(principal(OTHER_APPLICANT_ID, "applicant")).exists()


def test_fr_t143_pms_afr_155_document_modifications_logged(api, policy):
    """FR-T143 | PMS-AFR-155 | Document modifications logged."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    assert upload(api, app.id).status_code == 201
    entries = [ln for ln in audit_lines(api, app) if "document" in line_action(ln)]
    assert entries, "no audit entry for the document modification"
    assert f"user={APPLICANT_ID}" in entries[0]
    assert timezone.now().date().isoformat() in entries[0]


def test_fr_t144_pms_afr_156_document_access_controlled_by_role_and_status(api, policy):
    """FR-T144 | PMS-AFR-156 | Document access controlled by role and status."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    client = api(OUTSIDER_ID)
    assert client.get(f"{API}/applications/{app.id}").status_code == 403
    outsider_upload = client.post(
        f"{API}/applications/{app.id}/documents",
        {"document_type": "specification", "file": _pdf()}, format="multipart")
    assert outsider_upload.status_code == 403
    assert app.documents.count() == 1


def test_fr_t145_pms_afr_157_applicant_edits_documents_in_needs_revision(api, policy):
    """FR-T145 | PMS-AFR-157 | Applicant edits documents in Needs Revision."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 201, (resp.status_code, resp.data)


def test_fr_t146_pms_afr_157_applicant_edit_blocked_in_other_status(api, policy):
    """FR-T146 | PMS-AFR-157 | Applicant edit blocked in other status."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 409, (resp.status_code, resp.data)
    assert app.documents.count() == 1


# -- PMS-AFR-158..164: licensing and technology transfer -----------------------------


def test_fr_t147_pms_afr_158_applicant_submits_licensing_request(api, policy):
    """FR-T147 | PMS-AFR-158 | Applicant submits licensing request."""
    policy()
    app = seed_application(sm.GRANTED, assigned_director_id=DIRECTOR_ID)
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "LICENSING",
        "partner_name": "Quantum Devices Pvt Ltd",
    }, format="json")
    assert resp.status_code == 201, (resp.status_code, resp.data)
    rec = TechnologyTransferRecord.objects.get(pk=resp.data["id"])
    assert (rec.application_id, rec.request_type) == (app.id, "LICENSING")
    assert rec.applicant_user_id == APPLICANT_ID


def test_fr_t148_pms_afr_159_applicant_submits_technology_transfer_request(api, policy):
    """FR-T148 | PMS-AFR-159 | Applicant submits technology-transfer request."""
    policy()
    app = seed_application(sm.GRANTED, assigned_director_id=DIRECTOR_ID)
    resp = api(APPLICANT_ID, "applicant").post(f"{API}/tech-transfer", {
        "application_id": app.id, "request_type": "TECHNOLOGY_TRANSFER",
        "partner_name": "Quantum Devices Pvt Ltd",
    }, format="json")
    assert resp.status_code == 201, (resp.status_code, resp.data)
    rec = TechnologyTransferRecord.objects.get(pk=resp.data["id"])
    assert (rec.application_id, rec.request_type) == (app.id, "TECHNOLOGY_TRANSFER")


def test_fr_t149_pms_afr_160_request_routed_to_committee_or_director():
    """FR-T149 | PMS-AFR-160 | Request routed to committee/Director."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no routing configuration and records no routing "
        "target for a licensing request, so 'routed to the configured committee or "
        "Director' has no interface to set up or observe"
    )


def test_fr_t150_pms_afr_161_negotiation_information_tracked(policy):
    """FR-T150 | PMS-AFR-161 | Negotiation information tracked."""
    policy()
    app = seed_application(sm.GRANTED, assigned_director_id=DIRECTOR_ID)
    rec = tt_service.submit_tech_transfer_request(
        principal(APPLICANT_ID, "applicant"), app.id, "LICENSING", "Quantum Devices Pvt Ltd")
    terms = "Partner proposes a 5 percent royalty and a two year exclusivity window."
    tt_service.review_tech_transfer_request(
        principal(DIRECTOR_ID, "director"), rec.id, "NEGOTIATING", terms)
    rec.refresh_from_db()
    assert rec.status == "NEGOTIATING"
    assert rec.terms_summary == terms


def test_fr_t151_pms_afr_162_final_agreement_documented(policy):
    """FR-T151 | PMS-AFR-162 | Final agreement documented."""
    policy()
    app = seed_application(sm.GRANTED, assigned_director_id=DIRECTOR_ID)
    rec = tt_service.submit_tech_transfer_request(
        principal(APPLICANT_ID, "applicant"), app.id, "LICENSING", "Quantum Devices Pvt Ltd")
    director = principal(DIRECTOR_ID, "director")
    tt_service.review_tech_transfer_request(director, rec.id, "NEGOTIATING", "Draft terms.")
    agreement = "Final agreement: 4 percent royalty, non-exclusive, five year term."
    tt_service.review_tech_transfer_request(director, rec.id, "APPROVED", agreement)
    rec.refresh_from_db()
    assert rec.status == "APPROVED"
    assert rec.terms_summary == agreement


def test_fr_t152_pms_afr_163_financial_info_shared_via_integration():
    """FR-T152 | PMS-AFR-163 | Financial info shared via integration."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no financial integration (no client, setting or "
        "seam), and the final-agreement service takes no financial data"
    )


def test_fr_t153_pms_afr_164_license_records_confidentiality_enforced(api, policy):
    """FR-T153 | PMS-AFR-164 | License records confidentiality enforced."""
    policy()
    app = seed_application(sm.GRANTED, assigned_director_id=DIRECTOR_ID)
    rec = tt_service.submit_tech_transfer_request(
        principal(APPLICANT_ID, "applicant"), app.id, "LICENSING", "Quantum Devices Pvt Ltd")
    assert rec.confidentiality_level == "confidential"

    for user_id, role in ((OTHER_APPLICANT_ID, "applicant"), (OTHER_DIRECTOR_ID, "director"),
                          (ATTORNEY_B_ID, "attorney")):
        resp = api(user_id, role).get(f"{API}/applications/{app.id}")
        assert resp.status_code == 404, (role, resp.status_code)
        assert not sel.tech_transfers_for(principal(user_id, role)).exists()


# -- PMS-AFR-165..171: appeals ---------------------------------------------------------


def test_fr_t154_pms_afr_165_applicant_files_appeal_against_rejection(api, policy):
    """FR-T154 | PMS-AFR-165 | Applicant files appeal against rejection."""
    policy()
    app = _rejected_application()
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/appeal",
        {"grounds": "D1 does not disclose resonator coupling, so novelty holds."},
        format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED
    assert app.appeals.count() == 1


def test_fr_t155_pms_afr_166_late_appeal_rejected(api, policy):
    """FR-T155 | PMS-AFR-166 | Late appeal rejected."""
    policy()
    app = seed_application(
        sm.REJECTED, assigned_director_id=DIRECTOR_ID,
        decision_date=timezone.now() - datetime.timedelta(days=3650),
    )
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/appeal",
        {"grounds": "D1 does not disclose resonator coupling, so novelty holds."},
        format="json")
    app.refresh_from_db()
    assert app.status == sm.REJECTED
    assert not app.appeals.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t156_pms_afr_167_appeal_without_grounds_rejected(api, policy):
    """FR-T156 | PMS-AFR-167 | Appeal without grounds/justification rejected."""
    policy()
    app = _rejected_application()
    resp = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications/{app.id}/appeal", {}, format="json")
    app.refresh_from_db()
    assert app.status == sm.REJECTED
    assert not app.appeals.exists()
    assert resp.status_code == 422, (resp.status_code, resp.data)


def test_fr_t157_pms_afr_168_director_reviews_appeal(api, policy):
    """FR-T157 | PMS-AFR-168 | Director reviews appeal."""
    policy()
    app = _appeal_submitted_application()
    seed_document(app, 1)
    resp = api(DIRECTOR_ID, "director").get(f"{API}/applications/{app.id}")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert [a["grounds"] for a in resp.data["appeals"]] == [
        "D1 does not disclose resonator coupling."]
    assert [d["file_name"] for d in resp.data["documents"]] == ["spec_v1.pdf"]


def test_fr_t158_pms_afr_169_director_chooses_allowed_appeal_outcome(api, policy):
    """FR-T158 | PMS-AFR-169 | Director chooses allowed appeal outcome."""
    policy()
    expected = {
        "UPHOLD": sm.REJECTION_UPHELD,
        "REMAND": sm.REMANDED,
        "MODIFY": sm.DECISION_MODIFIED,
    }
    for outcome, status in expected.items():
        app = _appeal_submitted_application()
        resp = api(DIRECTOR_ID, "director").post(
            f"{API}/applications/{app.id}/appeal-decision", {"outcome": outcome},
            format="json")
        assert resp.status_code == 200, (outcome, resp.status_code, resp.data)
        app.refresh_from_db()
        assert app.status == status, outcome


def test_fr_t159_pms_afr_169_invalid_appeal_outcome_rejected(api, policy):
    """FR-T159 | PMS-AFR-169 | Invalid appeal outcome rejected."""
    policy()
    app = _appeal_submitted_application()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "Dismiss"}, format="json")
    app.refresh_from_db()
    assert app.status == sm.APPEAL_SUBMITTED
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert app.appeals.get().decided_at is None


def test_fr_t160_pms_afr_170_appeal_outcome_recorded(api, policy):
    """FR-T160 | PMS-AFR-170 | Appeal outcome recorded."""
    policy()
    app = _appeal_submitted_application()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "UPHOLD"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    appeal = AppealRecord.objects.get(application=app)
    assert appeal.status == "UPHOLD"
    assert appeal.decided_at is not None
    assert appeal.director_user_id == DIRECTOR_ID


def test_fr_t161_pms_afr_171_next_step_initiated_after_outcome(api, policy):
    """FR-T161 | PMS-AFR-171 | Next step initiated after outcome."""
    policy()
    app = _appeal_submitted_application()
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/appeal-decision", {"outcome": "REMAND"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.REMANDED
    seen = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert seen.data["status"] == sm.REMANDED


# -- PMS-AFR-172..181: deadlines -------------------------------------------------------


def test_fr_t162_pms_afr_172_review_deadline_calculated_and_monitored(api, policy):
    """FR-T162 | PMS-AFR-172 | Review deadline calculated and monitored."""
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data

    assert sweep_after(14)["overdue_reviews"] == 0
    assert sweep_after(16)["overdue_reviews"] == 1


def test_fr_t163_pms_afr_173_revision_deadline_calculated_and_monitored(api, policy):
    """FR-T163 | PMS-AFR-173 | Revision deadline calculated and monitored."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "NEEDS_REVISION", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    decided = app.decision_date
    assert decided is not None

    assert sweep_after(59)["expired"] == 0
    app.refresh_from_db()
    assert app.status == sm.NEEDS_REVISION
    with freeze_time(decided + datetime.timedelta(days=60, minutes=1)):
        assert pms_sweep_deadlines()["expired"] == 1
    app.refresh_from_db()
    assert app.status == sm.EXPIRED


def test_fr_t164_pms_afr_174_office_action_deadline_monitored(api, policy):
    """FR-T164 | PMS-AFR-174 | Office-action deadline monitored."""
    policy()
    app = _filed_application()
    _record_office_action(api, app, days_to_deadline=30)
    assert pms_sweep_deadlines()["alerts"] == 1


def test_fr_t165_pms_afr_175_maintenance_fee_deadline_monitored():
    """FR-T165 | PMS-AFR-175 | Maintenance-fee deadline monitored."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no maintenance schedule rules or configuration "
        "to compute a maintenance deadline from (the due date is supplied by the "
        "Attorney by design, BR-PMS-060), so 'schedule rules configured' cannot be set up"
    )


def test_fr_t166_pms_afr_176_alert_generated_30_days_before_deadline(api, policy):
    """FR-T166 | PMS-AFR-176 | Alert generated 30 days before deadline."""
    policy()
    app = _filed_application()
    _record_office_action(api, app, days_to_deadline=30)
    assert pms_sweep_deadlines()["alerts"] == 1


def test_fr_t167_pms_afr_177_alert_generated_15_days_before_deadline(api, policy):
    """FR-T167 | PMS-AFR-177 | Alert generated 15 days before deadline."""
    policy()
    app = _filed_application()
    _record_office_action(api, app, days_to_deadline=15)
    assert pms_sweep_deadlines()["alerts"] == 1


def test_fr_t168_pms_afr_178_alert_generated_5_days_before_deadline(api, policy):
    """FR-T168 | PMS-AFR-178 | Alert generated 5 days before deadline."""
    policy()
    app = _filed_application()
    _record_office_action(api, app, days_to_deadline=5)
    assert pms_sweep_deadlines()["alerts"] == 1


def test_fr_t169_pms_afr_179_deadline_notification_sent_to_stakeholders(
        api, policy, mailoutbox):
    """FR-T169 | PMS-AFR-179 | Deadline notification sent to stakeholders."""
    policy()
    app = _filed_application()
    _record_office_action(api, app, days_to_deadline=5)
    before = len(mailoutbox)
    assert pms_sweep_deadlines()["alerts"] == 1
    assert mails_about(mailoutbox, app, before), "no deadline notification was issued"


def test_fr_t170_pms_afr_180_missed_deadline_escalated_per_chain():
    """FR-T170 | PMS-AFR-180 | Missed deadline escalated per chain."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no escalation-chain configuration, so 'escalation "
        "chain configured' and 'the next level in the configured chain' cannot be set up "
        "or observed"
    )


def test_fr_t171_pms_afr_181_deadline_tracking_logged(api, policy, caplog):
    """FR-T171 | PMS-AFR-181 | Deadline tracking logged."""
    policy()
    app = _filed_application()
    oa_id = _record_office_action(api, app, days_to_deadline=15)
    with caplog.at_level(logging.INFO):
        assert pms_sweep_deadlines()["alerts"] == 1
    logged = [r.getMessage() for r in caplog.records
              if r.name.startswith("fusion.patents") and f"office_action={oa_id}" in r.getMessage()]
    audited = [ln for ln in audit_lines(api, app) if "deadline" in line_action(ln)]
    assert logged or audited, "no deadline tracking log entry was created"


# -- PMS-AFR-182..191: reports ---------------------------------------------------------


def test_fr_t172_pms_afr_182_status_and_progress_report_for_admin_and_director(api, policy):
    """FR-T172 | PMS-AFR-182 | PCC_ADMIN and Director generate application status and
    progress reports."""
    policy()
    seed_application(sm.FILED, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.GRANTED, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_application(sm.UNDER_REVIEW, assigned_director_id=OTHER_DIRECTOR_ID)

    admin = api(ADMIN_ID, "pcc_admin").get(f"{API}/reports")
    assert admin.status_code == 200, (admin.status_code, admin.data)
    assert admin.data["total_applications"] == 4
    assert admin.data["filed_count"] == 1
    assert admin.data["granted_count"] == 1

    director = api(DIRECTOR_ID, "director").get(f"{API}/reports")
    assert director.status_code == 200, (director.status_code, director.data)
    assert director.data["total_applications"] == 3
    assert director.data["filed_count"] == 1
    assert director.data["granted_count"] == 1


def test_fr_t173_pms_afr_183_financial_and_budget_report():
    """FR-T173 | PMS-AFR-183 | PCC_ADMIN and Director generate financial and budget
    reports."""
    pytest.skip(
        "NOT_AUTOMATED: GET /reports returns only total/filed/granted application counts; "
        "no financial or budget report exists and the endpoint has no report-type selector"
    )


def test_fr_t174_pms_afr_184_deadline_and_pending_action_report():
    """FR-T174 | PMS-AFR-184 | PCC_ADMIN and Director generate deadline and pending action
    reports."""
    pytest.skip(
        "NOT_AUTOMATED: GET /reports returns only total/filed/granted application counts; "
        "no deadline or pending-action report exists and the endpoint has no report-type "
        "selector"
    )


def test_fr_t175_pms_afr_185_inventor_and_coinventor_report():
    """FR-T175 | PMS-AFR-185 | PCC_ADMIN and Director generate inventor and co-inventor
    reports."""
    pytest.skip(
        "NOT_AUTOMATED: GET /reports returns only total/filed/granted application counts; "
        "no inventor or co-inventor report exists and the endpoint has no report-type "
        "selector"
    )


def test_fr_t176_pms_afr_186_patent_portfolio_analysis_report():
    """FR-T176 | PMS-AFR-186 | PCC_ADMIN and Director generate patent portfolio analysis
    reports."""
    pytest.skip(
        "NOT_AUTOMATED: GET /reports returns only total/filed/granted application counts; "
        "no portfolio analysis report exists and the endpoint has no report-type selector"
    )


def test_fr_t177_pms_afr_187_workload_and_assignment_report():
    """FR-T177 | PMS-AFR-187 | PCC_ADMIN and Director generate workload and assignment
    reports."""
    pytest.skip(
        "NOT_AUTOMATED: GET /reports returns only total/filed/granted application counts; "
        "no workload or assignment report exists and the endpoint has no report-type "
        "selector"
    )


def test_fr_t178_pms_afr_182_system_wide_reports_restricted_to_admin_and_director(
        api, policy):
    """FR-T178 | PMS-AFR-182 | System-wide reports restricted to PCC_ADMIN/Director."""
    policy()
    seed_application(sm.FILED)
    resp = api(APPLICANT_ID, "applicant").get(f"{API}/reports")
    assert resp.status_code == 403, (resp.status_code, resp.data)
    assert "total_applications" not in json.dumps(resp.data, default=str)


def test_fr_t179_pms_afr_188_authorized_user_schedules_report():
    """FR-T179 | PMS-AFR-188 | Authorized user schedules report."""
    pytest.skip("NOT_AUTOMATED: no endpoint, service or model schedules a report")


def test_fr_t180_pms_afr_189_authorized_user_exports_report():
    """FR-T180 | PMS-AFR-189 | Authorized user exports report."""
    pytest.skip(
        "NOT_AUTOMATED: no endpoint or service exports a report (GET /reports returns JSON "
        "counts only; there is no export format or export action)"
    )


def test_fr_t181_pms_afr_190_authorized_user_customizes_report():
    """FR-T181 | PMS-AFR-190 | Authorized user customizes report."""
    pytest.skip(
        "NOT_AUTOMATED: GET /reports accepts no field or filter parameters; no report "
        "customization interface exists"
    )


def test_fr_t182_pms_afr_191_report_access_logged(api, policy):
    """FR-T182 | PMS-AFR-191 | Report access logged."""
    policy()
    seed_application(sm.FILED)
    assert api(ADMIN_ID, "pcc_admin").get(f"{API}/reports").status_code == 200
    entries = [ln for ln in audit_lines(api) if "report" in line_action(ln)]
    assert entries, "no access log entry for the report"
    assert f"user={ADMIN_ID}" in entries[0]


# -- PMS-AFR-192..204: notification triggers -------------------------------------------


def test_fr_t183_pms_afr_192_email_triggered_for_application_submission(
        api, policy, mailoutbox):
    """FR-T183 | PMS-AFR-192 | Email triggered for application submission."""
    policy()
    created = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications", create_payload(), format="json")
    assert created.status_code == 201, created.data
    app = PatentApplication.objects.get(pk=created.data["id"])
    before = len(mailoutbox)
    app_service.transition_application(app.id, "submit", principal(APPLICANT_ID, "applicant"))
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert mails_to(mailoutbox, app, APPLICANT_ID, before), (
        "no submission email was triggered for the Applicant")


def test_fr_t184_pms_afr_193_email_triggered_for_application_status_change(
        api, policy, mailoutbox):
    """FR-T184 | PMS-AFR-193 | Email triggered for application status change."""
    policy()
    app = _attorney_assigned_application()
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/assessment", {"action": "start"}, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    app.refresh_from_db()
    assert app.status == sm.ASSESSMENT_IN_PROGRESS
    assert mails_about(mailoutbox, app, before), "no status-change email was triggered"


def test_fr_t185_pms_afr_194_email_triggered_for_assignment_to_director(
        api, policy, mailoutbox):
    """FR-T185 | PMS-AFR-194 | Email triggered for assignment to Director."""
    policy()
    app = seed_application(sm.SUBMITTED)
    before = len(mailoutbox)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert mails_to(mailoutbox, app, DIRECTOR_ID, before), (
        "the assigned Director was not emailed")


def test_fr_t186_pms_afr_195_email_triggered_for_assignment_to_attorney(
        api, policy, mailoutbox):
    """FR-T186 | PMS-AFR-195 | Email triggered for assignment to Attorney."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    before = len(mailoutbox)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": ATTORNEY_A_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert mails_to(mailoutbox, app, ATTORNEY_A_ID, before), (
        "the assigned Attorney was not emailed")


def test_fr_t187_pms_afr_196_email_triggered_for_review_decision(api, policy, mailoutbox):
    """FR-T187 | PMS-AFR-196 | Email triggered for review decision."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    before = len(mailoutbox)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    assert mails_to(mailoutbox, app, APPLICANT_ID, before), (
        "the Applicant was not emailed the review decision")


def test_fr_t188_pms_afr_197_email_triggered_for_budget_approval_or_rejection(
        api, policy, mailoutbox):
    """FR-T188 | PMS-AFR-197 | Email triggered for budget approval or rejection."""
    policy()
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    admin = principal(ADMIN_ID, "pcc_admin")
    to_approve = budget_service.record_budget_entry(
        admin, app.id, "FILING_FEE", Decimal("20000.00"), "GOVERNMENT_FEE")
    to_reject = budget_service.record_budget_entry(
        admin, app.id, "ATTORNEY_FEE", Decimal("30000.00"), "PROFESSIONAL_FEE")
    client = api(DIRECTOR_ID, "director")

    before = len(mailoutbox)
    resp = client.post(f"{API}/applications/{app.id}/budget-decision",
                       {"decision": "APPROVE", "budget_entry_id": to_approve.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert mails_about(mailoutbox, app, before), "no budget approval email was triggered"

    before = len(mailoutbox)
    resp = client.post(f"{API}/applications/{app.id}/budget-decision",
                       {"decision": "REJECT", "budget_entry_id": to_reject.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert mails_about(mailoutbox, app, before), "no budget rejection email was triggered"


def test_fr_t189_pms_afr_198_email_triggered_for_filing_confirmation(
        api, policy, mailoutbox):
    """FR-T189 | PMS-AFR-198 | Email triggered for filing confirmation."""
    policy()
    app = filing_ready()
    before = len(mailoutbox)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", filing_payload(), format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    assert mails_to(mailoutbox, app, APPLICANT_ID, before), (
        "no filing confirmation email was triggered for the Applicant")


def test_fr_t190_pms_afr_199_email_triggered_for_office_action(api, policy, mailoutbox):
    """FR-T190 | PMS-AFR-199 | Email triggered for office action."""
    policy()
    app = _filed_application()
    before = len(mailoutbox)
    _record_office_action(api, app, days_to_deadline=180)
    assert mails_about(mailoutbox, app, before), "no office action email was triggered"


def test_fr_t191_pms_afr_200_email_triggered_for_deadline_reminder(api, policy, mailoutbox):
    """FR-T191 | PMS-AFR-200 | Email triggered for deadline reminder."""
    policy()
    app = _filed_application()
    _record_office_action(api, app, days_to_deadline=15)
    before = len(mailoutbox)
    pms_sweep_deadlines()
    assert mails_about(mailoutbox, app, before), "no deadline reminder email was triggered"


def test_fr_t192_pms_afr_201_email_triggered_for_deadline_escalation(
        api, policy, mailoutbox):
    """FR-T192 | PMS-AFR-201 | Email triggered for deadline escalation."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    before = len(mailoutbox)
    assert sweep_after(16)["overdue_reviews"] == 1
    assert mails_about(mailoutbox, app, before), "no deadline escalation email was triggered"


def test_fr_t193_pms_afr_202_email_triggered_for_maintenance_fee_reminder(
        api, policy, mailoutbox):
    """FR-T193 | PMS-AFR-202 | Email triggered for maintenance-fee reminder."""
    policy()
    panel_attorney(ATTORNEY_A_ID, workload=1)
    app = seed_application(
        sm.GRANTED, assigned_director_id=DIRECTOR_ID, assigned_attorney_id=ATTORNEY_A_ID,
        grant_date=timezone.now().date() - datetime.timedelta(days=700),
        renewal_due_date=timezone.now().date() + datetime.timedelta(days=30),
    )
    before = len(mailoutbox)
    pms_sweep_deadlines()
    assert mails_about(mailoutbox, app, before), (
        "no maintenance-fee reminder email was triggered")


def test_fr_t194_pms_afr_203_email_triggered_for_document_update(api, policy, mailoutbox):
    """FR-T194 | PMS-AFR-203 | Email triggered for document update."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    before = len(mailoutbox)
    assert upload(api, app.id).status_code == 201
    assert mails_about(mailoutbox, app, before), "no document update email was triggered"


def test_fr_t195_pms_afr_204_email_triggered_for_document_version_change(
        api, policy, mailoutbox):
    """FR-T195 | PMS-AFR-204 | Email triggered for document version change."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    before = len(mailoutbox)
    resp = upload(api, app.id)
    assert resp.status_code == 201, resp.data
    assert resp.data["version"] == 2
    assert mails_about(mailoutbox, app, before), (
        "no document version change email was triggered")


# -- PMS-AFR-207..213: audit trail ------------------------------------------------------


def test_fr_t196_pms_afr_207_audit_trail_of_pms_actions(api, policy):
    """FR-T196 | PMS-AFR-207 | Audit trail of PMS actions."""
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    assert audit_lines(api, app), "no audit entry for the PMS action"


def test_fr_t197_pms_afr_208_user_actions_logged(api, policy):
    """FR-T197 | PMS-AFR-208 | User actions logged."""
    policy()
    created = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications", create_payload(), format="json")
    assert created.status_code == 201, created.data
    app = PatentApplication.objects.get(pk=created.data["id"])
    entries = audit_lines(api, app)
    assert entries, "no log entry for the Applicant's action"
    assert f"user={APPLICANT_ID}" in entries[0]


def test_fr_t198_pms_afr_209_status_changes_logged(api, policy):
    """FR-T198 | PMS-AFR-209 | Status changes logged."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    entries = audit_lines(api, app)
    assert any(sm.UNDER_REVIEW in ln and sm.APPROVED in ln for ln in entries), entries


def test_fr_t199_pms_afr_210_document_modifications_logged(api, policy):
    """FR-T199 | PMS-AFR-210 | Document modifications logged."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 201, resp.data
    entries = [ln for ln in audit_lines(api, app) if "document" in line_action(ln)]
    assert entries, "no log entry for the document modification"


def test_fr_t200_pms_afr_211_audit_log_has_required_attributes(api, policy):
    """FR-T200 | PMS-AFR-211 | Audit log has required attributes."""
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    entries = [ln for ln in audit_lines(api, app) if line_action(ln) == "assign_director"]
    assert entries, "no audit entry for the assignment"
    entry = entries[0]
    assert f"user={ADMIN_ID}" in entry
    assert line_action(entry)
    assert app.application_number in entry
    assert f"previous={sm.SUBMITTED}" in entry
    assert f"new={sm.UNDER_REVIEW}" in entry
    stamp = entry.split(" | ")[0]
    assert datetime.datetime.fromisoformat(stamp)


def test_fr_t201_pms_afr_212_critical_audit_records_immutable(api, policy):
    """FR-T201 | PMS-AFR-212 | Critical audit records immutable."""
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    entry = PatentAuditLog.objects.get(application=app, action_type="assign_director")
    original = (entry.action_type, entry.previous_state, entry.new_state, entry.actor_user_id)

    entry.action_type = "tampered"
    with pytest.raises(Exception):  # noqa: B017 - any refusal counts
        entry.save()
    with pytest.raises(Exception):  # noqa: B017
        entry.delete()
    with pytest.raises(Exception):  # noqa: B017
        PatentAuditLog.objects.filter(pk=entry.pk).update(action_type="tampered")
    with pytest.raises(Exception):  # noqa: B017
        PatentAuditLog.objects.filter(pk=entry.pk).delete()

    stored = PatentAuditLog.objects.get(pk=entry.pk)
    assert (stored.action_type, stored.previous_state, stored.new_state,
            stored.actor_user_id) == original


def test_fr_t202_pms_afr_213_audit_logs_retrievable_for_compliance(api, policy):
    """FR-T202 | PMS-AFR-213 | Audit logs retrievable for compliance."""
    policy()
    app = seed_application(sm.SUBMITTED)
    resp = api(ADMIN_ID, "pcc_admin").post(
        f"{API}/applications/{app.id}/assign-director", {"director_id": DIRECTOR_ID},
        format="json")
    assert resp.status_code == 200, resp.data
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/review-decision",
        {"decision": "APPROVE", "justification": GOOD_JUSTIFICATION}, format="json")
    assert resp.status_code == 200, resp.data
    logs = api(ADMIN_ID, "pcc_admin").get(f"{API}/audit-logs")
    assert logs.status_code == 200
    assert len(audit_lines(api, app)) >= 2


# -- PMS-AFR-216..232: access, governance and system boundaries ---------------------------


def test_fr_t203_pms_afr_216_user_without_valid_pms_role_denied(api, policy):
    """FR-T203 | PMS-AFR-216 | User without valid PMS role denied."""
    policy()
    app = seed_application(sm.SUBMITTED)
    for modules in ((), ("patents",)):
        client = api(OUTSIDER_ID, modules=modules)
        assert client.get(f"{API}/applications").status_code == 403, modules
        assert client.get(f"{API}/applications/{app.id}").status_code == 403, modules
        created = client.post(f"{API}/applications", create_payload(), format="json")
        assert created.status_code == 403, modules
    assert PatentApplication.objects.count() == 1


def test_fr_t204_pms_afr_217_attorney_assignment_blocked_before_director_approval(
        api, policy):
    """FR-T204 | PMS-AFR-217 | Attorney assignment blocked before Director approval."""
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


def test_fr_t205_pms_afr_218_filing_blocked_before_approvals_and_budget(api, policy):
    """FR-T205 | PMS-AFR-218 | Filing blocked before approvals and budget."""
    policy()
    app = filing_ready(consent=True, budget=False)
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", filing_payload(), format="json")
    app.refresh_from_db()
    assert app.status == sm.ASSESSMENT_IN_PROGRESS
    assert app.external_filing_id == ""
    assert resp.status_code == 409, (resp.status_code, resp.data)


def test_fr_t206_pms_afr_220_confidential_information_rbac_enforced(api, policy):
    """FR-T206 | PMS-AFR-220 | Confidential info RBAC enforced."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    assert ApplicationDocument.objects.get(application=app).sensitivity_level == "confidential"
    for user_id, role in ((OTHER_DIRECTOR_ID, "director"), (ATTORNEY_B_ID, "attorney"),
                          (OTHER_APPLICANT_ID, "applicant")):
        resp = api(user_id, role).get(f"{API}/applications/{app.id}")
        assert resp.status_code == 404, (role, resp.status_code)
        assert not sel.documents_for(principal(user_id, role)).exists()
    assert api(DIRECTOR_ID, "director").get(f"{API}/applications/{app.id}").status_code == 200


def test_fr_t207_pms_afr_221_only_one_active_pcc_admin():
    """FR-T207 | PMS-AFR-221 | Only one active PCC_ADMIN."""
    pytest.skip(
        "NOT_AUTOMATED: PCC_ADMIN role holders are managed by the identity service, not by "
        "the patents module; the module has no endpoint, service or model through which a "
        "second PCC_ADMIN could be activated"
    )


def test_fr_t208_pms_afr_222_multiple_directors_handle_reviews_by_domain(api, policy):
    """FR-T208 | PMS-AFR-222 | Multiple Directors handle reviews by domain."""
    policy()
    quantum = seed_application(sm.SUBMITTED, domain_category="Quantum")
    biotech = seed_application(sm.SUBMITTED, domain_category="Biotech")
    client = api(ADMIN_ID, "pcc_admin")
    for app, director in ((quantum, DIRECTOR_ID), (biotech, OTHER_DIRECTOR_ID)):
        resp = client.post(f"{API}/applications/{app.id}/assign-director",
                           {"director_id": director}, format="json")
        assert resp.status_code == 200, resp.data
    quantum.refresh_from_db()
    biotech.refresh_from_db()
    assert quantum.assigned_director_id == DIRECTOR_ID
    assert biotech.assigned_director_id == OTHER_DIRECTOR_ID

    first = sel.applications_pending_director_review(principal(DIRECTOR_ID, "director"))
    second = sel.applications_pending_director_review(principal(OTHER_DIRECTOR_ID, "director"))
    assert list(first.values_list("pk", flat=True)) == [quantum.pk]
    assert list(second.values_list("pk", flat=True)) == [biotech.pk]


def test_fr_t209_pms_afr_223_multiple_panel_attorneys_conduct_assessments(api, policy):
    """FR-T209 | PMS-AFR-223 | Multiple panel Attorneys conduct assessments."""
    policy()
    panel_attorney(ATTORNEY_A_ID)
    panel_attorney(ATTORNEY_B_ID)
    first = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    second = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    for app, attorney in ((first, ATTORNEY_A_ID), (second, ATTORNEY_B_ID)):
        resp = api(ADMIN_ID, "pcc_admin").post(
            f"{API}/applications/{app.id}/assign-attorney", {"attorney_id": attorney},
            format="json")
        assert resp.status_code == 200, resp.data
        resp = api(attorney, "attorney").post(
            f"{API}/applications/{app.id}/respond-assignment", {"action": "accept"},
            format="json")
        assert resp.status_code == 200, resp.data
        resp = api(attorney, "attorney").post(
            f"{API}/applications/{app.id}/assessment", {"action": "start"}, format="json")
        assert resp.status_code == 200, resp.data
    for app, attorney in ((first, ATTORNEY_A_ID), (second, ATTORNEY_B_ID)):
        app.refresh_from_db()
        assert app.status == sm.ASSESSMENT_IN_PROGRESS
        assert app.assigned_attorney_id == attorney


def test_fr_t210_pms_afr_224_multiple_applicants_submit_applications(api, policy):
    """FR-T210 | PMS-AFR-224 | Multiple Applicants submit applications."""
    policy()
    submitted = []
    for user_id in (APPLICANT_ID, OTHER_APPLICANT_ID):
        created = api(user_id, "applicant").post(
            f"{API}/applications", create_payload(), format="json")
        assert created.status_code == 201, created.data
        app = app_service.transition_application(
            created.data["id"], "submit", principal(user_id, "applicant"))
        submitted.append(app)
    assert [a.status for a in submitted] == [sm.SUBMITTED, sm.SUBMITTED]
    assert [a.user_id for a in submitted] == [APPLICANT_ID, OTHER_APPLICANT_ID]
    assert len({a.application_number for a in submitted}) == 2


def test_fr_t211_pms_afr_225_invalid_status_transition_rejected(api, policy):
    """FR-T211 | PMS-AFR-225 | Invalid status transition rejected."""
    policy()
    app = seed_application(sm.SUBMITTED)
    status = refusal_status(lambda: app_service.transition_application(
        app.id, "set_status", principal(ADMIN_ID, "pcc_admin"),
        payload={"to_status": sm.FILED}))
    assert status == 409
    resp = api(APPLICANT_ID, "applicant").put(
        f"{API}/applications/{app.id}", {"status": sm.FILED}, format="json")
    assert resp.status_code >= 400
    app.refresh_from_db()
    assert app.status == sm.SUBMITTED
    assert app.external_filing_id == ""


def test_fr_t212_pms_afr_226_escalation_for_delayed_actions(api, policy, mailoutbox):
    """FR-T212 | PMS-AFR-226 | Escalation for delayed actions."""
    policy()
    app = seed_application(sm.UNDER_REVIEW, assigned_director_id=DIRECTOR_ID)
    before = len(mailoutbox)
    assert sweep_after(16)["overdue_reviews"] == 1
    escalated = [ln for ln in audit_lines(api, app) if "escalat" in line_action(ln)]
    notified = [m for m in mails_about(mailoutbox, app, before)
                if "escalat" in (m.subject or "").lower()]
    assert escalated or notified, "the delayed review was not escalated"


def test_fr_t213_pms_afr_236_director_rejects_budget(api, policy, mailoutbox):
    """FR-T213 | PMS-AFR-236 | Director rejects budget."""
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
    assert mails_about(mailoutbox, app, before), "no budget rejection notification"


def test_fr_t214_pms_afr_237_dashboards_provided():
    """FR-T214 | PMS-AFR-237 | Dashboards provided."""
    pytest.skip(
        "NOT_AUTOMATED: the module has no dashboard endpoint or service (the only "
        "analytics interface is GET /reports with three application counts)"
    )


def test_fr_t215_pms_afr_238_historical_data_analysis_provided():
    """FR-T215 | PMS-AFR-238 | Historical data analysis provided."""
    pytest.skip("NOT_AUTOMATED: the module has no historical analysis endpoint or service")


def test_fr_t216_pms_afr_239_trend_reporting_provided():
    """FR-T216 | PMS-AFR-239 | Trend reporting provided."""
    pytest.skip("NOT_AUTOMATED: the module has no trend report endpoint or service")


def test_fr_t217_pms_afr_206_pms_triggers_email_and_does_not_report_delivery(
        api, policy, mailoutbox):
    """FR-T217 | PMS-AFR-206 | PMS triggers the notification email and does not itself own
    or report email delivery."""
    policy()
    created = api(APPLICANT_ID, "applicant").post(
        f"{API}/applications", create_payload(), format="json")
    assert created.status_code == 201, created.data
    app = PatentApplication.objects.get(pk=created.data["id"])
    before = len(mailoutbox)
    app_service.transition_application(app.id, "submit", principal(APPLICANT_ID, "applicant"))

    sent = mails_to(mailoutbox, app, APPLICANT_ID, before)
    assert sent, "the submission email was not handed to the email backend"

    detail = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}").data
    recorded = json.dumps(detail, default=str) + json.dumps(audit_lines(api, app))
    fields = " ".join(f.name for f in PatentApplication._meta.get_fields())
    for word in ("deliver", "bounce"):
        assert word not in recorded.lower()
        assert word not in fields.lower()


def test_fr_t218_pms_afr_228_pms_records_patent_office_data(api, policy):
    """FR-T218 | PMS-AFR-228 | PMS records patent-office filing, status and communication
    data while the patent-office system stays external."""
    policy()
    app = filing_ready()
    payload = filing_payload()
    client = api(ATTORNEY_A_ID, "attorney")
    resp = client.post(f"{API}/applications/{app.id}/filing", payload, format="json")
    assert resp.status_code == 200, (resp.status_code, resp.data)
    oa_id = _record_office_action(api, app, days_to_deadline=180)

    app.refresh_from_db()
    assert app.status == sm.FILED
    assert app.external_filing_id == payload["external_filing_id"]
    assert app.filing_date.isoformat() == payload["filing_date"]
    assert app.filing_confirmation == payload["confirmation"]
    oa = OfficeActionRecord.objects.get(pk=oa_id)
    assert (oa.application_id, oa.action_code) == (app.id, "FER-1")
    assert oa.issuing_authority == "Indian Patent Office"


def test_fr_t219_pms_afr_229_pms_records_financial_metadata(api, policy):
    """FR-T219 | PMS-AFR-229 | PMS records budget, authorization and transaction metadata
    while the financial system stays external."""
    policy(threshold=Decimal("150000.00"))
    app = seed_application(sm.APPROVED, assigned_director_id=DIRECTOR_ID)
    req = budget_service.record_budget_entry(
        principal(ADMIN_ID, "pcc_admin"), app.id, "FILING_FEE",
        Decimal("45000.00"), "GOVERNMENT_FEE")
    resp = api(DIRECTOR_ID, "director").post(
        f"{API}/applications/{app.id}/budget-decision",
        {"decision": "APPROVE", "budget_entry_id": req.id}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "APPROVED"

    row = PatentBudgetLedger.objects.get(application=app, replaces_entry=req)
    assert row.status == "APPROVED"
    assert row.entry_kind == "APPROVAL"
    assert row.authorized_by_user_id == DIRECTOR_ID
    assert (row.amount, row.currency, row.category) == (
        Decimal("45000.00"), "INR", "GOVERNMENT_FEE")
    assert row.created_at is not None
    assert not PatentBudgetLedger.objects.filter(
        application=app, entry_kind="DISBURSEMENT").exists()


def test_fr_t220_pms_afr_230_pms_stores_document_version_access_and_audit_metadata(
        api, policy):
    """FR-T220 | PMS-AFR-230 | PMS stores document versions, access and audit metadata
    while the document-management system stays external."""
    policy()
    app = seed_application(sm.NEEDS_REVISION, assigned_director_id=DIRECTOR_ID)
    seed_document(app, 1)
    resp = upload(api, app.id)
    assert resp.status_code == 201, resp.data
    assert resp.data["version"] == 2
    detail = api(APPLICANT_ID, "applicant").get(f"{API}/applications/{app.id}")
    assert detail.status_code == 200
    assert sorted(d["version"] for d in detail.data["documents"]) == [1, 2]

    actions = [line_action(ln) for ln in audit_lines(api, app)]
    assert any("document" in a for a in actions), f"no modification audit entry: {actions}"
    assert any(re.search(r"access|view|read|download", a) for a in actions), (
        f"no access audit entry: {actions}")


def test_fr_t221_pms_afr_231_external_prior_art_results_not_stored_unless_attached():
    """FR-T221 | PMS-AFR-231 | External prior-art results are not stored as PMS-owned
    records unless attached."""
    pytest.skip(
        "NOT_AUTOMATED: the search endpoint has no source seam to return stub results R1 "
        "and R2, and no interface attaches a reference to an application"
    )


def test_fr_t222_pms_afr_232_filing_not_recorded_without_filing_details(api, policy):
    """FR-T222 | PMS-AFR-232 | PMS does not record an application as Filed without the
    recorded filing details/confirmation."""
    policy()
    app = filing_ready()
    resp = api(ATTORNEY_A_ID, "attorney").post(
        f"{API}/applications/{app.id}/filing", {}, format="json")
    app.refresh_from_db()
    assert app.status != sm.FILED
    assert app.status == sm.ASSESSMENT_IN_PROGRESS
    assert app.external_filing_id == ""
    assert app.filing_date is None
    assert app.filing_confirmation == ""
    assert resp.status_code == 422, (resp.status_code, resp.data)
    assert not PatentAuditLog.objects.filter(
        application=app, action_type="file_external").exists()
