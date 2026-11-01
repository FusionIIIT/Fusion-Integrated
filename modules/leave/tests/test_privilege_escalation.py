"""Every endpoint, with a principal who should not reach it.

Both gates are exercised separately, because a principal that has one and not
the other is a different refusal and only one of them is usually implemented.
Every positive test needs its negative twin, and a typo'd permission code in a
test is granted by the fake and denied in production, so the codes used here
are asserted against the registry.
"""
import pytest

from modules.leave.registry import PERMISSIONS
from modules.leave.tests.conftest import EMPLOYEE_PERMISSIONS, leave_client

pytestmark = pytest.mark.django_db

DECLARED = {code for code, _ in PERMISSIONS}

#: (method, path, the code the endpoint demands)
ENDPOINTS = [
    ("get", "/api/v1/leave/balances", "leave.balance.view"),
    ("get", "/api/v1/leave/requests", "leave.request.view"),
    ("post", "/api/v1/leave/requests", "leave.request.view"),
    ("get", "/api/v1/leave/requests/1", "leave.request.view"),
    ("get", "/api/v1/leave/requests/1/history", "leave.request.view"),
    ("post", "/api/v1/leave/requests/1/withdraw", "leave.request.delete"),
    ("post", "/api/v1/leave/requests/1/decision", "leave.request.review"),
    ("post", "/api/v1/leave/requests/1/cancellation", "leave.cancellation.create"),
    ("post", "/api/v1/leave/requests/1/extension", "leave.extension.create"),
    ("post", "/api/v1/leave/requests/1/substitute", "leave.request.create"),
    ("post", "/api/v1/leave/requests/1/resumption", "leave.resumption.create"),
    ("post", "/api/v1/leave/requests/1/resumption/review",
     "leave.resumption.review"),
    ("get", "/api/v1/leave/requests/1/export", "leave.application.export"),
    ("get", "/api/v1/leave/queue", "leave.request.review"),
    ("get", "/api/v1/leave/substitute-requests", "leave.substitute.review"),
    ("post", "/api/v1/leave/substitute-requests/1/respond", "leave.substitute.review"),
    ("get", "/api/v1/leave/calendar", "leave.calendar.view"),
    ("post", "/api/v1/leave/calendar/publish", "leave.calendar.publish"),
    ("get", "/api/v1/leave/policy", "leave.policy.update"),
    ("put", "/api/v1/leave/policy", "leave.policy.update"),
    ("get", "/api/v1/leave/policy/hierarchy", "leave.policy.update"),
    ("post", "/api/v1/leave/policy/vacation-periods", "leave.policy.update"),
    ("get", "/api/v1/leave/sla-thresholds", "leave.threshold.update"),
    ("put", "/api/v1/leave/sla-thresholds", "leave.threshold.update"),
    ("get", "/api/v1/leave/records", "leave.record.view"),
    ("post", "/api/v1/leave/records/offline", "leave.record.update"),
    ("post", "/api/v1/leave/records/adjustment", "leave.record.update"),
]


def test_the_codes_this_suite_uses_are_the_ones_the_module_declares():
    used = {code for _, _, code in ENDPOINTS} | set(EMPLOYEE_PERMISSIONS)
    assert used <= DECLARED, f"undeclared in the test suite: {sorted(used - DECLARED)}"


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_a_principal_without_the_permission_is_refused(stub_iam, configured,
                                                       method, path, code):
    client = leave_client(stub_iam, user_id=9, permissions=(), active_role="")
    response = getattr(client, method)(path, {}, format="json")
    assert response.status_code == 403, (
        f"{method.upper()} {path} should need {code}, got "
        f"{response.status_code}")


@pytest.mark.parametrize(("method", "path", "code"), ENDPOINTS)
def test_a_principal_with_the_permission_but_no_module_grant_is_refused(
        stub_iam, configured, method, path, code):
    """The module gate is separate from the permission gate."""
    client = leave_client(stub_iam, user_id=9, permissions=(code,), modules=(),
                          active_role="")
    response = getattr(client, method)(path, {}, format="json")
    assert response.status_code == 403


def test_an_employee_cannot_publish_a_calendar(configured, employee):
    response = employee().post("/api/v1/leave/calendar/publish",
                               {"year": 2026, "days": [{"date": "2026-01-26"}]},
                               format="json")
    assert response.status_code == 403


def test_an_employee_cannot_adjust_a_balance(configured, employee):
    response = employee().post("/api/v1/leave/records/adjustment",
                               {"user_id": 1001, "category": "CL", "year": 2026,
                                "days": 3, "reason": "goodwill"}, format="json")
    assert response.status_code == 403


def test_the_caller_is_never_the_supplier_of_their_own_user_id(configured,
                                                               employee):
    """Applying always files against the credential, never a body field."""
    from modules.leave.models import LeaveRequest
    from modules.leave.tests.test_request_flow import apply_leave

    apply_leave(employee(user_id=1001), user_id=2002)
    assert list(LeaveRequest.objects.values_list("user_id", flat=True)) == [1001]
