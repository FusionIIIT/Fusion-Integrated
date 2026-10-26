```python
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveAccount, LeaveRequest

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), kind="student", uid=1001):
    stub_iam(make_session(user_id=uid, kind=kind, permissions=permissions,
                          modules=("leave",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def leave_data():
    LeaveAccount.objects.create(user_id="1001", category="CL", balance=10.0)
    LeaveRequest.objects.create(applicant_id="1001", category="CL",
                               start_date="2023-04-01", end_date="2023-04-05")
    LeaveAccount.objects.create(user_id="1002", category="CL", balance=10.0)
    LeaveRequest.objects.create(applicant_id="1002", category="CL",
                               start_date="2023-04-06", end_date="2023-04-10")


def test_missing_module_permission(stub_iam):
    client = _client(stub_iam, permissions=["leave.resumption.create"])
    response = client.get("/api/leave/accounts/")
    assert response.status_code == 403


def test_leave_account_list(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.account.view"])
    response = client.get("/api/leave/accounts/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_leave_request_list(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.request.view"])
    response = client.get("/api/leave/requests/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_resumption_submit_permission(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.resumption.create"])
    response = client.post("/api/leave/resumptions/", {
        "action": "SUBMIT",
        "actual_date": "2023-04-15",
        "notes": "Late due to travel"
    })
    assert response.status_code == 403


def test_resumption_review_permission(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.resumption.review"])
    response = client.post("/api/leave/resumptions/", {
        "action": "REVIEW",
        "remarks": "Approved"
    })
    assert response.status_code == 403


def test_resumption_submit(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.resumption.create"])
    response = client.post("/api/leave/resumptions/", {
        "action": "SUBMIT",
        "actual_date": "2023-04-15",
        "notes": "Late due to travel"
    })
    assert response.status_code == 201


def test_resumption_review(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.resumption.review"])
    response = client.post("/api/leave/resumptions/", {
        "action": "REVIEW",
        "remarks": "Approved"
    })
    assert response.status_code == 201


def test_resumption_invalid_action(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.resumption.create"])
    response = client.post("/api/leave/resumptions/", {
        "action": "INVALID",
        "actual_date": "2023-04-15",
        "notes": "Late due to travel"
    })
    assert response.status_code == 400


def test_leave_request_detail(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.request.view"])
    response = client.get("/api/leave/requests/1/")
    assert response.status_code == 200
    assert response.json()["applicant_id"] == "1001"


def test_leave_request_detail_unauthorized(leave_data, stub_iam):
    client = _client(stub_iam)
    response = client.get("/api/leave/requests/1/")
    assert response.status_code == 403


def test_leave_account_detail(leave_data, stub_iam):
    client = _client(stub_iam, permissions=["leave.account.view"])
    response = client.get("/api/leave/accounts/1/")
    assert response.status_code == 200
    assert response.json()["user_id"] == "1001"


def test_leave_account_detail_unauthorized(leave_data, stub_iam):
    client = _client(stub_iam)
    response = client.get("/api/leave/accounts/1/")
    assert response.status_code == 403


def test_resumption_submit_with_invalid_date(leave_data,