"""Real HTTP-level authorization tests for the ELM API: does
HasModuleGrant('elm') + HasPermission(...) actually gate these endpoints,
using the same stub_iam/APIClient pattern as
modules/placement/tests/test_privilege_escalation.py."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.elm.models import LeaveRequest

pytestmark = pytest.mark.django_db

EMPLOYEE_PERMS = (
    "elm.leave_request.create",
    "elm.leave_request.view_self",
    "elm.leave_request.withdraw",
    "elm.leave_request.cancel",
)
UNIT_HEAD_PERMS = (*EMPLOYEE_PERMS, "elm.leave_request.view", "elm.leave_request.decide")


def _client(stub_iam, uid, perms, modules=("elm",), kind="staff"):
    stub_iam(make_session(user_id=uid, kind=kind, modules=modules, permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_anonymous_request_rejected():
    response = APIClient().get("/api/v1/elm/my-requests")
    assert response.status_code in (401, 403)


def test_module_not_granted_is_rejected(stub_iam):
    """Has every ELM permission string, but the module itself isn't granted."""
    client = _client(stub_iam, 101, EMPLOYEE_PERMS, modules=())
    response = client.get("/api/v1/elm/my-requests")
    assert response.status_code == 403


def test_missing_specific_permission_is_rejected(stub_iam):
    """Module granted, but lacks elm.leave_request.view/.decide."""
    client = _client(stub_iam, 101, EMPLOYEE_PERMS)
    response = client.get("/api/v1/elm/approvals")
    assert response.status_code == 403


def test_user_without_create_permission_cannot_submit(stub_iam):
    """Has view_self (can list), but lacks elm.leave_request.create: the
    POST .../my-requests and GET .../my-requests share a URL but must be
    gated independently."""
    UserRef.objects.create(user_id=101, username="alice", display_name="Alice",
                           kind="staff", is_active=True)
    client = _client(stub_iam, 101, ("elm.leave_request.view_self",))

    response = client.post("/api/v1/elm/my-requests", {
        "category": "CL", "start_date": "2030-01-10", "end_date": "2030-01-10",
        "unit_head_user_id": 999,
    }, format="json")
    assert response.status_code == 403

    # the same, unrelated permission still lets them list their own requests
    listed = client.get("/api/v1/elm/my-requests")
    assert listed.status_code == 200
    assert LeaveRequest.objects.count() == 0


def test_authorized_employee_can_submit_and_list_own_requests(stub_iam):
    UserRef.objects.create(user_id=101, username="alice", display_name="Alice",
                           kind="staff", is_active=True)
    client = _client(stub_iam, 101, EMPLOYEE_PERMS)

    created = client.post("/api/v1/elm/my-requests", {
        "category": "CL", "start_date": "2030-01-10", "end_date": "2030-01-10",
        "unit_head_user_id": 999,
    }, format="json")
    assert created.status_code == 201, created.data

    listed = client.get("/api/v1/elm/my-requests")
    assert listed.status_code == 200
    assert len(listed.data) == 1


def test_authorized_unit_head_can_decide(stub_iam):
    row = LeaveRequest.objects.create(
        applicant_user_id=101, category="CL",
        start_date="2030-01-10", end_date="2030-01-10",
        unit_head_user_id=999, status="pending",
    )
    client = _client(stub_iam, 999, UNIT_HEAD_PERMS)

    response = client.post(f"/api/v1/elm/requests/{row.pk}/decide",
                           {"approve": True}, format="json")
    assert response.status_code == 200, response.data
    row.refresh_from_db()
    assert row.status == "approved"


def test_user_without_decide_permission_cannot_approve(stub_iam):
    """Module granted, has other ELM perms, but not elm.leave_request.decide."""
    row = LeaveRequest.objects.create(
        applicant_user_id=101, category="CL",
        start_date="2030-01-10", end_date="2030-01-10",
        unit_head_user_id=999, status="pending",
    )
    client = _client(stub_iam, 999, EMPLOYEE_PERMS)

    response = client.post(f"/api/v1/elm/requests/{row.pk}/decide",
                           {"approve": True}, format="json")
    assert response.status_code == 403
    row.refresh_from_db()
    assert row.status == "pending"  # unchanged
