"""Spec tests TC-BR-021 .. TC-BR-040 (financial rules, reports, closure)."""

import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.rspc.models import Project, ProjectFundTransaction
from modules.rspc.registry import ROLE_GRANTS
from modules.rspc.services import finance as finance_services

NO_DELEGATION = (
    "NOT_AUTOMATED: the implementation has no delegated-powers limit, Director escalation "
    "path or Dean-RSPC financial approval state (the disburse-approve endpoint is a stub "
    "that records nothing), so this behaviour cannot be exercised"
)
NO_AUDIT = (
    "NOT_AUTOMATED: the implementation has no audit/reporting record of financial lifecycle "
    "events (creation, verification, approval, escalation); only the fund ledger exists"
)
NO_PROCUREMENT = (
    "NOT_AUTOMATED: the implementation has no procurement request or approval-hierarchy "
    "interface; a project without a budget head cannot be submitted for any request"
)
NO_REPORTS = (
    "NOT_AUTOMATED: the implementation has no progress-report or utilization-report model, "
    "reporting schedule, reminder or report-history endpoint"
)


def _client(stub_iam, user_id, role):
    session = make_session(
        user_id=user_id,
        kind="faculty",
        roles=(role,),
        active_role=role,
        permissions=ROLE_GRANTS[role],
        modules=("rspc",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def _project(user_id=10, status="active", code="RSPC/BR/001"):
    today = datetime.date.today()
    return Project.objects.create(
        user_id=user_id,
        project_code=code,
        project_type="sponsored",
        title="Sanctioned Research Project",
        department="CSE",
        funding_agency="SERB",
        sanction_order_no="SO/2026/1",
        sanction_date=today,
        start_date=today,
        end_date=today + datetime.timedelta(days=365),
        sanctioned_amount=Decimal("100000.00"),
        status=status,
    )


def _funded_project():
    """Head with 100000 allocated and 20000 committed, i.e. 80000 remaining."""
    project = _project()
    head = finance_services.allocate_budget_head(
        project=project,
        head_type="equipment",
        allocated_amount=Decimal("100000.00"),
        actor_user_id=100,
    )
    head.committed_amount = Decimal("20000.00")
    head.save(update_fields=["committed_amount"])
    return project, head


def _disburse(client, project, amount):
    return client.post(
        f"/api/v1/rspc/projects/{project.id}/disburse/",
        data={
            "head_type": "equipment",
            "amount": amount,
            "reference_no": "REQ-001",
            "description": "Request",
        },
        format="json",
    )


@pytest.mark.skip(reason=NO_DELEGATION)
def test_tc_br_021_dean_approves_within_delegated_powers():
    """TC-BR-021 / BR-RSPC-032 within delegated powers."""


@pytest.mark.skip(reason=NO_DELEGATION)
def test_tc_br_022_dean_blocked_beyond_delegated_powers():
    """TC-BR-022 / BR-RSPC-032 beyond delegated powers."""


@pytest.mark.skip(reason=NO_DELEGATION)
def test_tc_br_023_delegated_limit_boundary():
    """TC-BR-023 / BR-RSPC-032 delegated limit boundary."""


@pytest.mark.skip(reason=NO_DELEGATION)
def test_tc_br_024_escalation_condition_met_routes_to_director():
    """TC-BR-024 / BR-RSPC-033 escalation condition met."""


@pytest.mark.skip(reason=NO_DELEGATION)
def test_tc_br_025_escalation_condition_not_met_not_routed():
    """TC-BR-025 / BR-RSPC-033 condition not met."""


@pytest.mark.skip(reason=NO_AUDIT)
def test_tc_br_026_lifecycle_events_logged():
    """TC-BR-026 / BR-RSPC-034 lifecycle events logged."""


@pytest.mark.django_db
def test_tc_br_027_request_within_sanctioned_budget_passes(stub_iam):
    """TC-BR-027 / BR-RSPC-035 within sanctioned budget.

    Fund request against the sanctioned budget head (80000 remaining) for 50000.
    """
    project, head = _funded_project()

    resp = _disburse(_client(stub_iam, 10, "faculty"), project, "50000.00")

    assert resp.status_code == 201
    head.refresh_from_db()
    assert head.spent_amount == Decimal("50000.00")
    assert ProjectFundTransaction.objects.filter(transaction_type="disbursement").count() == 1


@pytest.mark.django_db
def test_tc_br_028_request_exceeding_sanctioned_budget_fails(stub_iam):
    """TC-BR-028 / BR-RSPC-035 exceeds sanctioned budget.

    80000 remaining, request 80000.01. Validation refusal carries 422 (api-conventions).
    """
    project, head = _funded_project()

    resp = _disburse(_client(stub_iam, 10, "faculty"), project, "80000.01")

    assert resp.status_code == 422
    head.refresh_from_db()
    assert head.spent_amount == Decimal("0.00")
    assert not ProjectFundTransaction.objects.filter(transaction_type="disbursement").exists()


@pytest.mark.django_db
def test_tc_br_029_request_equal_to_remaining_budget_accepted(stub_iam):
    """TC-BR-029 / BR-RSPC-035 budget boundary (amount equals remaining budget of 80000)."""
    project, head = _funded_project()

    resp = _disburse(_client(stub_iam, 10, "faculty"), project, "80000.00")

    assert resp.status_code == 201
    head.refresh_from_db()
    assert head.available_balance == Decimal("0.00")


@pytest.mark.skip(reason=NO_PROCUREMENT)
def test_tc_br_030_budget_not_represented_no_budget_rejection():
    """TC-BR-030 / BR-RSPC-035 budget not represented."""


@pytest.mark.skip(reason=NO_PROCUREMENT)
def test_tc_br_031_procurement_routed_through_applicable_hierarchy():
    """TC-BR-031 / BR-RSPC-036 applicable hierarchy."""


@pytest.mark.skip(reason=NO_PROCUREMENT)
def test_tc_br_032_approval_by_stage_not_in_hierarchy_rejected():
    """TC-BR-032 / BR-RSPC-036 stage not in hierarchy."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_033_reporting_schedule_pending_and_reminder():
    """TC-BR-033 / BR-RSPC-037 schedule represented."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_034_report_submitted_before_due_not_pending():
    """TC-BR-034 / BR-RSPC-037 report submitted before due."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_035_no_schedule_no_pending_status():
    """TC-BR-035 / BR-RSPC-037 no schedule represented."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_036_progress_report_history_shown_to_authorized_actor():
    """TC-BR-036 / BR-RSPC-038 authorized actor."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_037_progress_report_history_denied_to_unauthorized_actor():
    """TC-BR-037 / BR-RSPC-038 unauthorized actor."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_038_utilization_history_shown_to_authorized_actor():
    """TC-BR-038 / BR-RSPC-039 authorized actor."""


@pytest.mark.skip(reason=NO_REPORTS)
def test_tc_br_039_utilization_history_denied_to_unauthorized_actor():
    """TC-BR-039 / BR-RSPC-039 unauthorized actor."""


@pytest.mark.django_db
def test_tc_br_040_approved_closure_archives_project_with_audit_trail(stub_iam):
    """TC-BR-040 / BR-RSPC-043 closure approved."""
    project, _head = _funded_project()
    tx_before = list(ProjectFundTransaction.objects.values_list("id", flat=True))
    assert tx_before

    r1 = _client(stub_iam, 10, "faculty").post(
        f"/api/v1/rspc/projects/{project.id}/closure/", data={"remarks": "Done"}, format="json"
    )
    r2 = _client(stub_iam, 100, "Dean (RSPC)").post(
        f"/api/v1/rspc/projects/{project.id}/closure/approve/"
    )

    assert (r1.status_code, r2.status_code) == (201, 200)
    project.refresh_from_db()
    assert project.status == "closed"
    closure = project.closure_record
    assert closure.status == "approved"
    assert closure.closed_at is not None
    assert closure.closed_by_user_id == 100
    tx_after = list(ProjectFundTransaction.objects.values_list("id", flat=True))
    assert tx_after == tx_before
