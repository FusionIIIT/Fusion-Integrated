"""FR specification cases for administration, role context, and auditability."""
import pytest

from modules.iaa.domain import roles
from modules.iaa.registry import ROLE_GRANTS
from modules.iaa.tests.spec.fr.test_support import (
    ADMIN,
    CREATOR,
    FINANCE,
    IaaHttp,
    client_for_session,
    published_policy,
)

pytestmark = pytest.mark.django_db


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE exposes no role-assignment or role-management endpoint for System "
    "Admin; the configuration API covers policies, financial years, and budget entries only."
))
def test_iaa_t068__afr_iaa_068_admin_manages_iaa_role_assignments():
    """IAA-T068 / AFR-IAA-068: System Admin can manage IAA role assignments."""


def test_iaa_t069__afr_iaa_069_admin_configures_approval_hierarchy_and_thresholds(
        stub_iam, configured):
    """IAA-T069 / AFR-IAA-069: System Admin can update approval routing and thresholds."""
    run = IaaHttp(stub_iam)
    routes = [
        {"kind": "expense", "min_amount": "0", "levels": [roles.HOD, roles.DEAN],
         "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]

    changed = published_policy(run, routes=routes, timeout=24, threshold="30000")
    policies = run.get(ADMIN, "/config/policies")
    stored = next(item for item in policies if item["id"] == changed["id"])

    assert stored["approval_timeout_hours"] == 24
    assert stored["ta_high_value_threshold"] == "30000.00"
    assert stored["routes"] == routes


def test_iaa_t070__afr_iaa_070_admin_configures_financial_year_and_policy(
        stub_iam, configured):
    """IAA-T070 / AFR-IAA-070: System Admin updates financial-year and policy configuration."""
    run = IaaHttp(stub_iam)
    policy = published_policy(run, timeout=36, threshold="28000")

    year = run.post(ADMIN, "/config/financial-years", {
        "code": "2099-2100", "starts_on": "2099-04-01", "ends_on": "2100-03-31",
    }, expected_status=201)
    stored_years = run.get(ADMIN, "/config/financial-years")
    stored_policy = next(item for item in run.get(ADMIN, "/config/policies")
                         if item["id"] == policy["id"])

    assert year["code"] == "2099-2100"
    assert any(item["id"] == year["id"] for item in stored_years)
    assert stored_policy["approval_timeout_hours"] == 36
    assert stored_policy["ta_high_value_threshold"] == "28000.00"


def test_iaa_t071__afr_iaa_071_admin_cannot_access_financial_content_or_approve(
        stub_iam, configured):
    """IAA-T071 / AFR-IAA-071: System Admin is refused financial data and approval unchanged."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    before = run.get(FINANCE, f"/records/{submitted['id']}")

    list_refusal = run.request(ADMIN, "get", "/records")
    detail_refusal = run.request(ADMIN, "get", f"/records/{submitted['id']}")
    approval_refusal = run.request(ADMIN, "post", f"/records/{submitted['id']}/decision", {
        "decision": "approve", "remarks": "Admin approval attempt",
    })
    after = run.get(FINANCE, f"/records/{submitted['id']}")

    assert list_refusal.status_code == 403
    assert detail_refusal.status_code == 403
    assert approval_refusal.status_code == 403
    assert after["status"] == before["status"] == "finance_validated"
    assert after["steps"] == before["steps"]


def test_iaa_t072__afr_iaa_072_role_specific_action_requires_active_role(
        stub_iam, configured):
    """IAA-T072 / AFR-IAA-072: a multi-role user must activate a role before role-specific work."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    before = run.get(FINANCE, f"/records/{submitted['id']}")
    client = client_for_session(
        stub_iam, user_id=301, active_role=None, actor_roles=(roles.HOD, roles.DEAN),
        permissions=ROLE_GRANTS[roles.HOD] + ROLE_GRANTS[roles.DEAN],
    )

    refused = client.post(f"/api/v1/iaa/records/{submitted['id']}/decision", {
        "decision": "approve", "remarks": "No active role selected",
    }, format="json")
    after = run.get(FINANCE, f"/records/{submitted['id']}")

    assert refused.status_code == 404
    assert after["status"] == before["status"] == "finance_validated"
    assert after["steps"] == before["steps"]


def test_iaa_t073__afr_iaa_073_role_change_preserves_historical_identity_and_role(
        stub_iam, configured):
    """IAA-T073 / AFR-IAA-073: changing active roles does not rewrite a prior Finance action."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.post(FINANCE, f"/records/{submitted['id']}/query", {"text": "Please clarify the total."})
    client = client_for_session(
        stub_iam, user_id=201, active_role=roles.AUDITOR,
        actor_roles=(roles.FINANCE, roles.AUDITOR),
        permissions=ROLE_GRANTS[roles.FINANCE] + ROLE_GRANTS[roles.AUDITOR],
    )

    response = client.get(f"/api/v1/iaa/records/{submitted['id']}/history")
    history = response.json()
    finance_action = next(item for item in history if item["action"] == "raise_query")

    assert response.status_code == 200
    assert finance_action["actor_user_id"] == 201
    assert finance_action["actor_role"] == roles.FINANCE


def test_iaa_t074__afr_iaa_074_role_based_access_blocks_unauthorized_features_and_views(
        stub_iam, configured):
    """IAA-T074 / AFR-IAA-074: an unauthorized Basic User cannot reach Finance or report views."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    before = run.get(CREATOR, f"/records/{submitted['id']}")

    finance_refusal = run.request(CREATOR, "post", f"/records/{submitted['id']}/validate", {})
    report_refusal = run.request(CREATOR, "get", "/reports/summary")
    after = run.get(CREATOR, f"/records/{submitted['id']}")

    assert finance_refusal.status_code == 403
    assert report_refusal.status_code == 403
    assert after["status"] == before["status"] == "submitted"


def test_iaa_t075__afr_iaa_075_trail_logs_identity_role_timestamp_action_and_status(
        stub_iam, configured):
    """IAA-T075 / AFR-IAA-075: an operational trail entry logs all specified audit fields."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()

    submit_action = next(item for item in run.history(submitted["id"])
                         if item["action"] == "submit")

    assert submit_action["actor_user_id"] == 101
    assert submit_action["actor_role"] == "faculty"
    assert submit_action["created_at"]
    assert submit_action["action"] == "submit"
    assert submit_action["to_status"] == "submitted"
