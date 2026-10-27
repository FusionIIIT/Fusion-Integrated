from datetime import date
from decimal import Decimal

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveRequest, LeaveWorkflowAction
from modules.elm.services.routing import RouteStep, SubmissionRoute

pytestmark = pytest.mark.django_db

BASE = "/api/v1/elm"


class FakeRouteResolver:
    def resolve_route(self, *, applicant, leave_type, start_date, end_date):
        return SubmissionRoute(
            (
                RouteStep("UNIT_HEAD", 201),
                RouteStep("SANCTIONING_AUTHORITY", 202),
            )
        )


class FakeBalanceProvider:
    def get_available_balance(self, *, user_id, leave_type):
        return Decimal("20")


def _client(stub_iam, *, user_id=101, kind="staff", permissions=None):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=kind,
            roles=(kind,),
            modules=("elm",),
            permissions=permissions
            or (
                "elm.request.create",
                "elm.request.view_self",
                "elm.request.withdraw",
            ),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")
    return client


def _request(
    *,
    user_id,
    status=LeaveRequest.Status.PENDING_UNIT_HEAD,
    leave_type="EL",
    start=date(2025, 10, 1),
    end=date(2025, 10, 1),
):
    return LeaveRequest.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        purpose="Personal leave",
        chargeable_days="1",
        status=status,
    )


def test_metadata_endpoint_remains_available_to_authenticated_users(stub_iam):
    response = _client(stub_iam).get(f"{BASE}/")

    assert response.status_code == 200
    assert response.json()["label"] == "elm"


def test_submission_api_fails_closed_when_production_routing_is_unconfigured(
    stub_iam,
):
    client = _client(stub_iam)
    response = client.post(
        f"{BASE}/requests/",
        {
            "leave_type": "EL",
            "start_date": "2025-10-03",
            "end_date": "2025-10-06",
            "purpose": "Personal leave",
        },
        format="json",
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "elm_dependency_unavailable"
    assert LeaveRequest.objects.count() == 0


def test_submission_endpoint_persists_when_test_integrations_resolve_required_inputs(
    stub_iam,
):
    with override_settings(
        ELM_SUBMISSION_ROUTING_RESOLVER=FakeRouteResolver(),
        ELM_BALANCE_PROVIDER=FakeBalanceProvider(),
    ):
        response = _client(stub_iam).post(
            f"{BASE}/requests/",
            {
                "leave_type": "EL",
                "start_date": "2025-10-03",
                "end_date": "2025-10-06",
                "purpose": "Personal leave",
            },
            format="json",
        )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == LeaveRequest.objects.get().pk
    assert body["status"] == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert body["chargeable_days"] == "4.00"
    assert LeaveRequest.objects.get().user_id == 101


def test_unauthenticated_submission_is_rejected():
    response = APIClient().post(
        f"{BASE}/requests/",
        {
            "leave_type": "EL",
            "start_date": "2025-10-03",
            "end_date": "2025-10-06",
            "purpose": "Personal leave",
        },
        format="json",
    )

    assert response.status_code == 401
    assert LeaveRequest.objects.count() == 0


def test_client_cannot_supply_applicant_identity(stub_iam):
    response = _client(stub_iam).post(
        f"{BASE}/requests/",
        {
            "user_id": 999,
            "leave_type": "EL",
            "start_date": "2025-10-03",
            "end_date": "2025-10-06",
            "purpose": "Personal leave",
        },
        format="json",
    )

    assert response.status_code == 400
    assert LeaveRequest.objects.count() == 0


@pytest.mark.parametrize(
    "payload",
    (
        {
            "leave_type": "INVALID",
            "start_date": "2025-10-01",
            "end_date": "2025-10-01",
            "purpose": "Reason",
        },
        {
            "leave_type": "EL",
            "start_date": "2025-10-02",
            "end_date": "2025-10-01",
            "purpose": "Reason",
        },
        {
            "leave_type": "EL",
            "start_date": "2025-10-01",
            "end_date": "2025-10-01",
            "purpose": "   ",
        },
    ),
)
def test_invalid_submission_fields_return_client_error_without_persistence(stub_iam, payload):
    response = _client(stub_iam).post(f"{BASE}/requests/", payload, format="json")

    assert response.status_code == 400
    assert LeaveRequest.objects.count() == 0


def test_request_list_is_own_only_stable_and_filterable(stub_iam):
    own_old = _request(user_id=101, start=date(2025, 10, 1))
    own_new = _request(
        user_id=101,
        status=LeaveRequest.Status.WITHDRAWN,
        start=date(2025, 11, 1),
        end=date(2025, 11, 2),
    )
    foreign = _request(user_id=202)
    client = _client(stub_iam)

    all_rows = client.get(f"{BASE}/requests/").json()["results"]
    filtered = client.get(
        f"{BASE}/requests/?status=WITHDRAWN&leave_type=EL&from_date=2025-11-02"
    ).json()["results"]

    assert [row["id"] for row in all_rows] == [own_new.pk, own_old.pk]
    assert [row["id"] for row in filtered] == [own_new.pk]
    assert all(row["id"] != foreign.pk for row in all_rows)


@pytest.mark.parametrize(
    "query",
    (
        "?status=UNKNOWN",
        "?leave_type=OTHER",
        "?from_date=not-a-date",
        "?from_date=2025-12-01&to_date=2025-11-01",
    ),
)
def test_invalid_request_filters_return_400(stub_iam, query):
    response = _client(stub_iam).get(f"{BASE}/requests/{query}")

    assert response.status_code == 400


def test_foreign_request_detail_is_hidden(stub_iam):
    foreign = _request(user_id=202)

    response = _client(stub_iam).get(f"{BASE}/requests/{foreign.pk}/")

    assert response.status_code == 404


def test_requester_can_withdraw_own_pending_request(stub_iam):
    request = _request(user_id=101)

    response = _client(stub_iam).post(
        f"{BASE}/requests/{request.pk}/withdraw/",
        {"reason": "Plans changed"},
        format="json",
    )

    request.refresh_from_db()
    assert response.status_code == 200
    assert request.status == LeaveRequest.Status.WITHDRAWN
    assert request.workflow_actions.get().actor_user_id == 101


def test_requester_cannot_withdraw_another_employees_request(stub_iam):
    foreign = _request(user_id=202)

    response = _client(stub_iam).post(f"{BASE}/requests/{foreign.pk}/withdraw/", {}, format="json")

    foreign.refresh_from_db()
    assert response.status_code == 404
    assert foreign.status == LeaveRequest.Status.PENDING_UNIT_HEAD
    assert foreign.workflow_actions.count() == 0


def test_history_detail_is_read_only_and_contains_recorded_actions(stub_iam):
    request = _request(user_id=101)
    action = LeaveWorkflowAction.objects.create(
        request=request,
        from_status="DRAFT",
        to_status=LeaveRequest.Status.PENDING_UNIT_HEAD,
        action=LeaveWorkflowAction.Action.SUBMITTED,
        actor_user_id=101,
        actor_role="staff",
        reason="Submitted",
    )
    before = (request.status, request.workflow_actions.count())

    response = _client(stub_iam).get(f"{BASE}/requests/{request.pk}/")

    request.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["workflow_actions"][0]["action"] == "SUBMITTED"
    assert response.json()["workflow_actions"][0]["actor_role"] == "staff"
    assert "actor_user_id" not in response.json()["workflow_actions"][0]
    assert action.pk is not None
    assert (request.status, request.workflow_actions.count()) == before


def test_read_endpoints_reject_anonymous_users():
    assert APIClient().get(f"{BASE}/requests/").status_code == 401
    assert APIClient().get(f"{BASE}/requests/99999/").status_code == 401
