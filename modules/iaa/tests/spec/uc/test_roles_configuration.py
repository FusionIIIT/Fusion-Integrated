"""UC specification cases for active roles, administration, and configuration."""
import pytest

from modules.iaa.domain import roles
from modules.iaa.models import TrailEntry
from modules.iaa.tests.spec.uc.test_support import (
    ADMIN,
    FINANCE,
    IaaHttp,
    publish_policy,
)

pytestmark = pytest.mark.django_db


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE has no IAA role-switch endpoint; active_role is supplied by the "
    "external IAM session, and no role-switch event is recorded by this module."
))
def test_iaa_tc_701_01__uc_701_main_success_switch_active_role():
    """IAA-TC-701-01 / IAA-UC-701 Main Success Scenario."""


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE has no IAA role-switch endpoint through which a no-longer-assigned "
    "role can be selected and refused."
))
def test_iaa_tc_701_02__uc_701_selected_role_no_longer_assigned():
    """IAA-TC-701-02 / IAA-UC-701 Alternative Flow - Selected role is no longer assigned."""


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE has no IAA role-switch endpoint or session-invalidation flow to "
    "exercise re-authentication during role switching."
))
def test_iaa_tc_701_03__uc_701_invalid_session_during_role_switch():
    """IAA-TC-701-03 / IAA-UC-701 Exception Flow - Session invalid."""


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE exposes no role-assignment administration endpoint for adding or "
    "removing a user's IAA roles."
))
def test_iaa_tc_702_01__uc_702_main_success_update_role_assignments():
    """IAA-TC-702-01 / IAA-UC-702 Main Success Scenario."""


@pytest.mark.skip(reason=(
    "NOT_AUTOMATED: A8_BASE exposes no role-assignment administration endpoint to submit and "
    "reject an invalid role/user combination."
))
def test_iaa_tc_702_02__uc_702_invalid_role_user_combination():
    """IAA-TC-702-02 / IAA-UC-702 Alternative Flow - Invalid role/user combination."""


def test_iaa_tc_702_03__uc_702_admin_role_administration_cannot_expose_financial_data(
        stub_iam, configured):
    """IAA-TC-702-03 / IAA-UC-702 Exception Flow - Attempt to access operational financial data."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    config = run.get(ADMIN, "/config/policies")

    refused = run.get_response(ADMIN, "/records")
    unchanged = run.get(FINANCE, f"/records/{submitted['id']}")

    assert config
    assert refused.status_code == 403
    assert unchanged["status"] == "finance_validated"


def test_iaa_tc_703_01__uc_703_main_success_configure_approval_routing(
        stub_iam, configured):
    """IAA-TC-703-01 / IAA-UC-703 Main Success Scenario."""
    run = IaaHttp(stub_iam)
    routes = [
        {"kind": "expense", "min_amount": "0", "max_amount": "50000",
         "levels": [roles.HOD], "escalation_designation": roles.DEAN},
        {"kind": "expense", "min_amount": "50000", "levels": [roles.HOD, roles.DEAN],
         "escalation_designation": roles.DIRECTOR},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]

    saved = publish_policy(run, routes=routes, timeout=24)
    stored = next(item for item in run.get(ADMIN, "/config/policies")
                  if item["id"] == saved["id"])
    trail = TrailEntry.objects.get(entity="configuration", entity_id=saved["id"],
                                   action="publish_policy")
    submitted = run.submitted_expense(amount="60000")
    routed = run.validated(submitted["id"])

    assert stored["approval_timeout_hours"] == 24
    assert stored["routes"] == routes
    assert trail.actor_user_id == 501
    assert trail.actor_role == roles.SYSTEM_ADMIN
    assert trail.created_at is not None
    assert routed["route_levels"] == [roles.HOD, roles.DEAN]


def test_iaa_tc_703_02__uc_703_invalid_hierarchy_does_not_replace_prior_configuration(
        stub_iam, configured):
    """IAA-TC-703-02 / IAA-UC-703 Alternative Flow - Invalid/incomplete hierarchy."""
    run = IaaHttp(stub_iam)
    before = run.get(ADMIN, "/config/policies")
    invalid_routes = [
        {"kind": "expense", "min_amount": "0", "levels": [],
         "escalation_designation": roles.DEAN},
        {"kind": "ta", "min_amount": "0", "levels": [roles.HOD],
         "escalation_designation": roles.DEAN},
    ]

    refused = run.post_response(ADMIN, "/config/policies", {
        "approval_timeout_hours": 24, "ta_high_value_threshold": "25000",
        "budget_check_required": True, "request_types": ["voucher", "reimbursement"],
        "required_documents": {"expense": 1, "ta": 1}, "routes": invalid_routes,
        "anomaly_resolvers": {
            "budget": [roles.FINANCE, roles.DEAN],
            "policy": [roles.FINANCE, roles.DIRECTOR],
            "financial": [roles.AUDITOR, roles.DIRECTOR],
        },
    })
    after = run.get(ADMIN, "/config/policies")
    submitted = run.submitted_expense(amount="60000")
    routed = run.validated(submitted["id"])

    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "policy_invalid"
    assert any(item["field"].startswith("routes")
               for item in refused.json()["error"]["details"])
    assert after == before
    assert routed["route_levels"] == [roles.HOD, roles.DEAN]


def test_iaa_tc_703_03__uc_703_configuration_does_not_grant_approval_rights(
        stub_iam, configured):
    """IAA-TC-703-03 / IAA-UC-703 Exception Flow - Configuration does not grant approval rights."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    run.validated(submitted["id"])
    before = run.get(FINANCE, f"/records/{submitted['id']}")

    refused = run.post_response(ADMIN, f"/records/{submitted['id']}/decision", {
        "decision": "approve", "remarks": "Attempt using configuration privilege",
    })
    after = run.get(FINANCE, f"/records/{submitted['id']}")

    assert refused.status_code == 403
    assert after["status"] == before["status"] == "finance_validated"
    assert after["steps"] == before["steps"]


def test_iaa_tc_704_01__uc_704_main_success_configure_financial_year_and_policy(
        stub_iam, configured):
    """IAA-TC-704-01 / IAA-UC-704 Main Success Scenario."""
    run = IaaHttp(stub_iam)
    year = run.post(ADMIN, "/config/financial-years", {
        "code": "2099-2100", "starts_on": "2099-04-01", "ends_on": "2100-03-31",
    }, expected_status=201)
    policy = publish_policy(run, timeout=36, threshold="28000")
    saved_year = next(item for item in run.get(ADMIN, "/config/financial-years")
                      if item["id"] == year["id"])
    saved_policy = next(item for item in run.get(ADMIN, "/config/policies")
                        if item["id"] == policy["id"])
    year_trail = TrailEntry.objects.get(entity="configuration", entity_id=year["id"],
                                        action="add_financial_year")
    policy_trail = TrailEntry.objects.get(entity="configuration", entity_id=policy["id"],
                                          action="publish_policy")

    assert saved_year["code"] == "2099-2100"
    assert saved_policy["approval_timeout_hours"] == 36
    assert saved_policy["ta_high_value_threshold"] == "28000.00"
    assert year_trail.actor_user_id == policy_trail.actor_user_id == 501
    assert year_trail.actor_role == policy_trail.actor_role == roles.SYSTEM_ADMIN


def test_iaa_tc_704_02__uc_704_overlapping_financial_year_is_refused_unchanged(
        stub_iam, configured):
    """IAA-TC-704-02 / IAA-UC-704 Alternative Flow - Invalid/overlapping configuration."""
    run = IaaHttp(stub_iam)
    years_before = run.get(ADMIN, "/config/financial-years")

    refused = run.post_response(ADMIN, "/config/financial-years", {
        "code": "2026-overlap", "starts_on": "2026-10-01", "ends_on": "2027-03-31",
    })
    years_after = run.get(ADMIN, "/config/financial-years")

    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "financial_year_overlap"
    assert years_after == years_before


def test_iaa_tc_704_03__uc_704_configuration_does_not_expose_request_content(
        stub_iam, configured):
    """IAA-TC-704-03 / IAA-UC-704 Exception Flow - Operational request content is not exposed."""
    run = IaaHttp(stub_iam)
    submitted = run.submitted_expense()
    saved_policy = publish_policy(run, timeout=36)

    refused = run.get_response(ADMIN, f"/records/{submitted['id']}")
    finance_view = run.get(FINANCE, f"/records/{submitted['id']}")

    assert saved_policy["approval_timeout_hours"] == 36
    assert refused.status_code == 403
    assert finance_view["status"] == submitted["status"] == "submitted"
