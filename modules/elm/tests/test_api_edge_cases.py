from datetime import date
from decimal import Decimal

import pytest
from django.urls import resolve
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveBalance, LeaveRequest, SubstituteAssignment

pytestmark = pytest.mark.django_db

BASE = "/api/v1/elm"


def _client(stub_iam, *, user=101, modules=("elm",), permissions=("elm.leave.view_self",), kind="faculty"):
    stub_iam(make_session(user_id=user, modules=modules, permissions=permissions,
                          kind=kind, roles=(kind,)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token elm-test")
    return client


def _balance(*, user=101, category="CL", year=2026, balance="8"):
    value = Decimal(balance)
    return LeaveBalance.objects.create(user_id=user, category=category, year=year,
                                       credited=value, availed=Decimal("0"), balance=value)


def _request(*, user=101, status="under_review", start=date(2026, 8, 1)):
    return LeaveRequest.objects.create(user_id=user, category="CL", start_date=start,
                                       end_date=start, leave_days=Decimal("1"),
                                       purpose="Test", status=status)


def test_all_elm_routes_resolve_to_expected_endpoints():
    routes = {
        "catalog": "elm-catalog", "balances": "elm-my-balances", "requests": "elm-my-requests",
        "requests/1": "elm-request-detail", "requests/1/withdraw": "elm-request-withdraw",
        "requests/1/cancel": "elm-request-cancel", "tasks/substitute": "elm-substitute-tasks",
        "tasks/substitute/1/respond": "elm-substitute-respond", "tasks/review": "elm-review-tasks",
        "tasks/review/1/decision": "elm-review-decision", "requests/1/extend": "elm-request-extend",
        "requests/1/print": "elm-request-print", "requests/1/resumption": "elm-request-resumption",
        "tasks/resumption/1/review": "elm-resumption-review", "admin/offline-record": "elm-offline-record",
        "processing/year-end": "elm-year-end-processing",
    }
    for path, route_name in routes.items():
        assert resolve(f"{BASE}/{path}").url_name == route_name


@pytest.mark.parametrize("path", ["catalog", "balances", "requests", "tasks/substitute"])
def test_self_service_routes_require_authentication(path):
    assert APIClient().get(f"{BASE}/{path}").status_code == 401


def test_catalog_requires_module_grant_and_view_permission(stub_iam):
    assert _client(stub_iam, modules=()).get(f"{BASE}/catalog").status_code == 403
    assert _client(stub_iam, permissions=("elm.leave.apply",)).get(f"{BASE}/catalog").status_code == 403


def test_leave_balances_are_scoped_to_authenticated_user(stub_iam):
    _balance(user=101)
    _balance(user=202)
    response = _client(stub_iam).get(f"{BASE}/balances")
    assert response.status_code == 200
    assert {row["user_id"] for row in response.data} == {101}


def test_balances_are_scoped_to_current_year(stub_iam):
    from django.utils import timezone

    _balance(year=timezone.now().year)
    _balance(year=timezone.now().year - 1, category="EL")
    response = _client(stub_iam).get(f"{BASE}/balances")
    assert len(response.data) == 1
    assert response.data[0]["year"] == timezone.now().year


def test_request_list_is_scoped_to_authenticated_user(stub_iam):
    _request(user=101)
    _request(user=202, start=date(2026, 8, 2))
    response = _client(stub_iam).get(f"{BASE}/requests")
    assert response.status_code == 200
    assert {row["user_id"] for row in response.data} == {101}


def test_request_detail_hides_foreign_and_missing_ids(stub_iam):
    foreign = _request(user=202)
    client = _client(stub_iam)
    assert client.get(f"{BASE}/requests/{foreign.pk}").status_code == 404
    assert client.get(f"{BASE}/requests/999999").status_code == 404


def test_substitute_task_list_contains_only_callers_pending_assignments(stub_iam):
    own_req = _request(user=202)
    other_req = _request(user=303, start=date(2026, 8, 2))
    SubstituteAssignment.objects.create(leave_request=own_req, substitute_id=101, status="pending")
    SubstituteAssignment.objects.create(leave_request=other_req, substitute_id=101, status="accepted")
    SubstituteAssignment.objects.create(leave_request=other_req, substitute_id=404, status="pending")
    response = _client(stub_iam).get(f"{BASE}/tasks/substitute")
    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [own_req.pk]


def test_review_task_list_contains_reviewable_statuses_only(stub_iam):
    under = _request(status="under_review")
    recommended = _request(status="recommended", start=date(2026, 8, 2))
    _request(status="sanctioned", start=date(2026, 8, 3))
    response = _client(stub_iam, permissions=("elm.leave.review",)).get(f"{BASE}/tasks/review")
    assert response.status_code == 200
    assert {row["id"] for row in response.data} == {under.pk, recommended.pk}


@pytest.mark.parametrize("payload", [
    {},
    {"category": "CL", "start_date": "nope", "end_date": "2026-08-01", "purpose": "Test"},
    {"category": "CL", "start_date": "2026-08-01", "end_date": "not-a-date", "purpose": "Test"},
    {"category": "CL", "start_date": "2026-08-01", "end_date": "2026-08-01", "purpose": ""},
])
def test_apply_request_serializer_returns_400_for_bad_input(stub_iam, payload):
    response = _client(stub_iam, permissions=("elm.leave.view_self",)).post(
        f"{BASE}/requests", payload, format="json")
    assert response.status_code == 400


@pytest.mark.parametrize("permission,path,method", [
    ("elm.leave.view_self", "requests/1/withdraw", "post"),
    ("elm.leave.view_self", "requests/1/cancel", "post"),
    ("elm.leave.view_self", "tasks/review", "get"),
    ("elm.leave.apply", "admin/offline-record", "post"),
    ("elm.leave.review", "processing/year-end", "post"),
])
def test_sensitive_endpoints_enforce_action_permissions(stub_iam, permission, path, method):
    response = getattr(_client(stub_iam, permissions=(permission,)), method)(f"{BASE}/{path}", {}, format="json")
    assert response.status_code == 403


def test_print_view_only_exposes_owners_application(stub_iam):
    foreign = _request(user=202)
    assert _client(stub_iam).get(f"{BASE}/requests/{foreign.pk}/print").status_code == 404


def test_extend_missing_end_date_returns_400(stub_iam):
    assert _client(stub_iam, permissions=("elm.leave.apply",)).post(
        f"{BASE}/requests/1/extend", {}, format="json").status_code == 400


def test_resumption_missing_date_returns_400(stub_iam):
    assert _client(stub_iam, permissions=("elm.leave.apply",)).post(
        f"{BASE}/requests/1/resumption", {}, format="json").status_code == 400


def test_read_only_endpoints_reject_mutation_methods(stub_iam):
    client = _client(stub_iam)
    for method in ("put", "patch", "delete"):
        assert getattr(client, method)(f"{BASE}/catalog", {}, format="json").status_code == 405
