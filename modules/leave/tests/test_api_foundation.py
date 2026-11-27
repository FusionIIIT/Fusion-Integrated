import pytest
from rest_framework.test import APIClient

from conftest import make_session


@pytest.mark.django_db
def test_leave_health_authenticated_with_grant(stub_iam):
    client = APIClient()
    session = make_session(
        user_id=1005,
        modules=("leave",),
        permissions=("leave.request.view_self",),
    )
    stub_iam(session=session)

    res = client.get("/api/v1/leave/health/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 200
    assert res.json() == {"status": "active", "module": "leave"}


@pytest.mark.django_db
def test_leave_health_forbidden_without_module_grant(stub_iam):
    client = APIClient()
    session = make_session(
        user_id=1005,
        modules=(),  # No leave module grant
        permissions=("leave.request.view_self",),
    )
    stub_iam(session=session)

    res = client.get("/api/v1/leave/health/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 403


@pytest.mark.django_db
def test_leave_health_forbidden_without_permission(stub_iam):
    client = APIClient()
    session = make_session(
        user_id=1005,
        modules=("leave",),
        permissions=(),  # No view_self permission
    )
    stub_iam(session=session)

    res = client.get("/api/v1/leave/health/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 403
