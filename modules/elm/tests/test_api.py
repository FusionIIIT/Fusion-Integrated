
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveTypePolicy

pytestmark = pytest.mark.django_db

BASE_URL = "/api/v1/elm/"


def authenticated_client(stub_iam, *, permissions=(), modules=("leave_elm",)):
    stub_iam(
        make_session(
            user_id=101,
            permissions=permissions,
            modules=modules,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return client


def test_requests_reject_unauthenticated_user():
    response = APIClient().get(BASE_URL + "requests")
    assert response.status_code == 401


def test_requests_reject_user_without_elm_module_grant(stub_iam):
    client = authenticated_client(
        stub_iam,
        permissions=("leave_elm.application.view_self",),
        modules=(),
    )
    response = client.get(BASE_URL + "requests")
    assert response.status_code == 403


def test_requests_reject_user_without_view_permission(stub_iam):
    client = authenticated_client(stub_iam)
    response = client.get(BASE_URL + "requests")
    assert response.status_code == 403


def test_request_rejects_end_date_before_start_date(stub_iam):
    client = authenticated_client(
        stub_iam,
        permissions=("leave_elm.application.apply",),
    )
    leave_type = LeaveTypePolicy.objects.create(
        code=LeaveTypePolicy.CL,
        annual_allowance="8.00",
        carry_forward=False,
        continuous_calendar_days=False,
        employee_category="any",
    )

    response = client.post(
        BASE_URL + "requests",
        {
            "leave_type": leave_type.pk,
            "start_date": "2026-11-10",
            "end_date": "2026-11-09",
            "start_session": "full",
            "end_session": "full",
            "reason": "Personal work",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "end_date" in str(response.json())


def test_substitute_consent_rejects_non_boolean_accept(stub_iam):
    client = authenticated_client(stub_iam)

    response = client.post(
        BASE_URL + "requests/1/substitute-response",
        {"accept": "yes"},
        format="json",
    )

    assert response.status_code == 400
    assert "accept" in str(response.json())
