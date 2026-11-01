import pytest
from rest_framework.test import APIClient
from conftest import make_session

pytestmark = pytest.mark.django_db


def test_unauthenticated_request_is_refused():
    client = APIClient()
    response = client.get("/api/v1/badms/status/")
    assert response.status_code == 401


def test_ungranted_module_is_refused(stub_iam):
    stub_iam(make_session(user_id=1001, modules=(), permissions=()))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    response = client.get("/api/v1/badms/status/")
    assert response.status_code == 403


def test_missing_permission_is_refused(stub_iam):
    stub_iam(make_session(user_id=1001, modules=("badms",), permissions=()))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    response = client.get("/api/v1/badms/status/")
    assert response.status_code == 403


def test_authorized_user_can_access_status(stub_iam):
    stub_iam(
        make_session(
            user_id=1001,
            modules=("badms",),
            permissions=("badms.archive.view_self",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")
    response = client.get("/api/v1/badms/status/")
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["module"] == "badms"
    assert response.json()["user_id"] == 1001
