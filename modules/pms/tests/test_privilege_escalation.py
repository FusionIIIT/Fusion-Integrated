"""Every endpoint, both gates separately, plus no session at all (BR-PMS-126; Step 5.5)."""
import pytest
from rest_framework.test import APIClient

from modules.pms import registry
from modules.pms.api.urls import urlpatterns
from modules.pms.tests.conftest import Actor

pytestmark = pytest.mark.django_db

# (method, path, the permission the gate names, or a tuple when any one of them admits)
ENDPOINTS = [
    ("get", "applications", "pms.application.view"),
    ("post", "applications", "pms.application.create"),
    ("get", "applications/1", "pms.application.view"),
    ("patch", "applications/1", "pms.application.update"),
    ("post", "applications/1/submit", "pms.application.create"),
    ("get", "applications/1/history", "pms.application.view"),
    ("put", "applications/1/inventors", "pms.inventor.update"),
    ("post", "applications/1/inventors/1/agreement", "pms.inventor.update"),
    ("post", "applications/1/resubmit", "pms.application.update"),
    ("post", "applications/1/withdraw", "pms.withdrawal.create"),
    ("post", "applications/1/appeal", "pms.appeal.create"),
    ("get", "applications/1/director-candidates", "pms.review.assign"),
    ("post", "applications/1/assign-director", "pms.review.assign"),
    ("post", "applications/1/review", "pms.review.approve"),
    ("post", "appeals/1/assign", "pms.review.assign"),
    ("post", "appeals/1/decision", "pms.appeal.review"),
    ("get", "applications/1/attorney-candidates", "pms.attorney.assign"),
    ("post", "applications/1/assign-attorney", "pms.attorney.assign"),
    ("post", "attorney-assignments/1/respond", "pms.attorney_assignment.review"),
    ("get", "directors", "pms.director_profile.update"),
    ("post", "directors", "pms.director_profile.update"),
    ("post", "directors/1/end", "pms.director_profile.update"),
    ("get", "attorney-panel", ("pms.attorney.assign", "pms.attorney_panel.update")),
    ("post", "attorney-panel", "pms.attorney_panel.update"),
    ("get", "attorney-panel/options", "pms.application.create"),
    ("post", "attorney-panel/1/end", "pms.attorney_panel.update"),
    ("post", "applications/1/assessments", "pms.assessment.create"),
    ("post", "assessments/1/finalize", "pms.assessment.create"),
    ("post", "applications/1/legal-requests", "pms.legal_request.create"),
    ("post", "applications/1/legal-advice", "pms.legal_advice.create"),
    ("post", "applications/1/budgets", "pms.budget.create"),
    ("post", "budgets/1/decision", "pms.budget.approve"),
    ("post", "budgets/1/route", "pms.escalation.review"),
    ("post", "budgets/1/external-decision", "pms.escalation.review"),
    ("post", "applications/1/filings", "pms.filing.create"),
    ("post", "applications/1/communications", "pms.communication.create"),
    ("post", "office-actions/1/response", "pms.office_action_response.create"),
    ("post", "office-actions/1/approve", "pms.office_action_response.approve"),
    ("post", "office-actions/1/submission", "pms.office_action_response.update"),
    ("post", "office-actions/1/extension", "pms.office_action_response.update"),
    ("post", "applications/1/maintenance-cycles", "pms.maintenance.update"),
    ("post", "maintenance-cycles/1/request-decision", "pms.maintenance.update"),
    ("post", "maintenance-cycles/1/decision", "pms.renewal.approve"),
    ("post", "maintenance-cycles/1/action", "pms.maintenance.update"),
    ("post", "maintenance-cycles/1/reassign", "pms.renewal.assign"),
    ("get", "applications/1/documents", "pms.document.view"),
    ("post", "applications/1/documents", "pms.document.create"),
    ("get", "documents/versions/1/download", "pms.document.view"),
    ("patch", "documents/1", "pms.document.update"),
    ("post", "prior-art/searches", "pms.prior_art.create"),
    ("get", "applications/1/prior-art", "pms.prior_art.view"),
    ("post", "applications/1/prior-art", "pms.prior_art.create"),
    ("get", "licensing-requests", "pms.licensing_request.view"),
    ("post", "licensing-requests", "pms.licensing_request.create"),
    ("post", "licensing-requests/1/route", "pms.licensing_request.review"),
    ("post", "licensing-requests/1/notes", "pms.licensing_request.review"),
    ("post", "licensing-requests/1/agreement", "pms.licensing_request.review"),
    ("get", "my-work", "pms.application.view"),
    ("get", "deadlines", "pms.escalation.review"),
    ("get", "escalations", "pms.escalation.review"),
    ("post", "escalations/1/handle", "pms.escalation.review"),
    ("get", "oversight", "pms.workflow.view"),
    ("get", "reports/status", "pms.report.view"),
    ("get", "reports/status/export", "pms.report.export"),
    ("get", "report-definitions", "pms.report_definition.create"),
    ("post", "report-definitions", "pms.report_definition.create"),
    ("post", "report-definitions/1/deactivate", "pms.report_definition.create"),
    ("get", "report-runs/1/download", "pms.report.view"),
    ("get", "audit", "pms.audit_log.view"),
    ("get", "audit/export", "pms.audit_log.export"),
    ("get", "reference-data", "pms.application.view"),
    ("get", "policy", "pms.policy.publish"),
    ("post", "policy", "pms.policy.publish"),
    ("get", "setup", "pms.policy.publish"),
    ("get", "acting", "pms.application.view"),
    ("get", "people", ("pms.inventor.update", "pms.director_profile.update",
                       "pms.attorney_panel.update", "pms.policy.publish")),
]
DECLARED = {code for code, _ in registry.PERMISSIONS}
EVERYTHING = sorted(DECLARED)


def test_every_route_is_in_this_table():
    """A new endpoint without a row here fails, so nobody adds one untested."""
    tested = {path.split("/")[0] for _, path, _ in ENDPOINTS}
    routed = {str(p.pattern).split("/")[0] for p in urlpatterns}
    assert routed <= tested
    assert len({(m, p) for m, p, _ in ENDPOINTS}) == len(ENDPOINTS)
    assert len(ENDPOINTS) >= len(urlpatterns)


def _codes(code) -> tuple:
    return code if isinstance(code, tuple) else (code,)


def test_every_permission_in_this_table_is_declared():
    """A typo here would be granted by the fake IAM and denied in production."""
    assert {c for _, _, code in ENDPOINTS for c in _codes(code)} <= DECLARED


def _holder(code: str) -> str:
    """A designation whose own grants include the code, so narrowing keeps it."""
    return next(d for d, codes in registry.ROLE_GRANTS.items() if code in codes)


def _call(actor, method, path):
    fmt = {} if method == "get" else {"data": {}}
    return getattr(actor, method)(path, **fmt)


# BR-PMS-126 PMS-AFR-216 CFR-PMS-025
@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_without_the_module_grant_is_refused(stub_iam, method, path, code):
    actor = Actor(stub_iam, 9001, "pms_pcc_admin", permissions=EVERYTHING, modules=())
    response = _call(actor, method, path)
    assert response.status_code == 403
    assert response.json()["error"]["message"] == "This module is not available to your role."


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_without_the_permission_is_refused(stub_iam, method, path, code):
    designation = _holder(_codes(code)[0])
    actor = Actor(stub_iam, 9001, designation,
                  permissions=[c for c in registry.ROLE_GRANTS[designation]
                               if c not in _codes(code)])
    assert _call(actor, method, path).status_code == 403


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_with_exactly_the_permission_the_gate_lets_you_through(stub_iam, method, path, code):
    for single in _codes(code):
        actor = Actor(stub_iam, 9001, _holder(single), permissions=[single])
        response = _call(actor, method, path)
        gate_refusals = ("This module is not available to your role.",
                         "You do not have permission to perform this action.")
        body = response.json() if response.get("Content-Type", "").startswith(
            "application/json") else {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        assert error.get("message") not in gate_refusals


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_without_a_session_is_401(stub_iam, method, path, code):
    client = APIClient()
    assert getattr(client, method)(f"/api/v1/pms/{path}").status_code == 401


def test_a_cookie_write_without_the_csrf_header_is_403(stub_iam, world):
    from django.conf import settings

    from core.api import csrf

    actor = world["applicant"]
    actor._go()
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "cookie-token"
    assert client.post("/api/v1/pms/applications", {"title": "x"},
                       format="json").status_code == 403
    ok = client.post("/api/v1/pms/applications", {"title": "x"}, format="json",
                     HTTP_X_CSRF_TOKEN=csrf.token_for("cookie-token"))
    assert ok.status_code == 201


def test_writes_are_throttled_429(world, monkeypatch):
    from rest_framework import throttling

    rates = {**throttling.SimpleRateThrottle.THROTTLE_RATES, "pms_write": "2/hour"}
    monkeypatch.setattr(throttling.SimpleRateThrottle, "THROTTLE_RATES", rates)
    a = world["applicant"]
    codes = [a.post("applications", {"title": f"t{i}"}).status_code for i in range(3)]
    assert codes == [201, 201, 429]
    assert a.get("applications").status_code == 200


def test_a_student_cannot_decide_a_review_or_assign(world):
    a = world["applicant"]
    assert a.post("applications/1/review", {"decision": "approve",
                                            "justification": "x" * 60}).status_code == 403
    assert a.post("applications/1/assign-director",
                  {"director_user_id": 1001}).status_code == 403
    assert a.post("policy", {"based_on_version": 0, "payload": {}}).status_code == 403


# PMS-AFR-220
def test_the_role_switch_gives_only_the_acting_roles_view(stub_iam, world):
    """Holding pms_director as well, but acting as student: student permissions only."""
    both = Actor(stub_iam, 2001, "student", also_holds=("pms_director",))
    assert both.get("oversight").status_code == 403
    assert both.post("applications/1/review", {"decision": "approve",
                                                "justification": "x" * 60}).status_code == 403
    assert both.get("applications").status_code == 200


# PMS-AFR-220 BR-PMS-126
def test_the_iams_union_of_roles_is_narrowed_to_the_acting_role(stub_iam, world):
    """The real IAM sends every held role's permissions; PMS must act on the acting one only."""
    union = sorted(set(registry.ROLE_GRANTS["faculty"]) | set(registry.ROLE_GRANTS["pms_director"]))
    as_director = Actor(stub_iam, 2001, "pms_director", permissions=union,
                        also_holds=("Professor",))
    assert as_director.post("applications", {"title": "Mine"}).status_code == 403
    assert as_director.get("acting").json()["role"] == "pms_director"
    assert "pms.application.create" not in as_director.get("acting").json()["permissions"]
    as_professor = Actor(stub_iam, 2001, "pms_director", permissions=union,
                         also_holds=("Professor",))
    as_professor.session = as_professor.session.__class__(**{
        **as_professor.session.__dict__, "active_role": "Professor"})
    assert as_professor.post("applications", {"title": "Mine"}).status_code == 201
    assert as_professor.get("oversight").status_code == 403
    assert as_professor.get("acting").json()["role"] == "faculty"
