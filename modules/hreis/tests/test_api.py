from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    LeaveBalanceEntry,
    NotificationRecord,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, user_id, permissions, role="faculty", kind="faculty"):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            roles=(role,),
            active_role=role,
            modules=("hreis",),
            permissions=permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")
    return client


def test_hr_uc_003_submit_and_hr_uc_005_scope_request_status(stub_iam):
    EmployeeServiceRecord.objects.create(user_id=41, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload={
            "approval_routes": {"leave": {"faculty": ["HOD (CSE)"]}},
            "eligible_leave_types": {"faculty": ["earned"]},
        },
    )
    LeaveBalanceEntry.objects.create(
        user_id=41,
        leave_type="earned",
        delta_days="5",
        reason="Opening balance",
        actor_user_id=99,
    )
    client = _client(stub_iam, 41, ("hreis.request.create", "hreis.request.view"))
    response = client.post(
        "/api/v1/hreis/requests",
        {
            "request_type": "leave",
            "data": {
                "leave_type": "earned",
                "duration_days": "2",
                "justification": "Personal leave",
            },
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="leave-request-41",
    )
    assert response.status_code == 201
    request_id = response.data["id"]
    assert client.get(f"/api/v1/hreis/requests/{request_id}").status_code == 200
    own = client.get("/api/v1/hreis/requests")
    assert own.status_code == 200
    assert [row["id"] for row in own.data["results"]] == [request_id]

    other = _client(stub_iam, 42, ("hreis.request.view",))
    assert other.get(f"/api/v1/hreis/requests/{request_id}").status_code == 404
    assert other.get("/api/v1/hreis/requests").data["results"] == []
    authority = _client(stub_iam, 90, ("hreis.request.review",), role="HOD (CSE)", kind="staff")
    decided = authority.post(
        f"/api/v1/hreis/requests/{request_id}/transition",
        {"event": "approve"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="approve-leave-41",
    )
    assert decided.status_code == 200
    assert decided.data["state"] == "approved_leave_balance_updated"


def test_hr_uc_003_requires_idempotency_key(stub_iam):
    EmployeeServiceRecord.objects.create(user_id=43, employee_category="faculty")
    client = _client(stub_iam, 43, ("hreis.request.create",))
    response = client.post(
        "/api/v1/hreis/requests",
        {"request_type": "leave", "data": {}},
        format="json",
    )
    assert response.status_code == 400


def test_hr_uc_001_employee_records_are_self_scoped(stub_iam):
    EmployeeServiceRecord.objects.create(user_id=44, employee_category="faculty")
    EmployeeServiceRecord.objects.create(user_id=45, employee_category="faculty")
    client = _client(stub_iam, 44, ("hreis.employee.view",))
    page = client.get("/api/v1/hreis/employees")
    assert page.status_code == 200
    assert [row["user_id"] for row in page.data["results"]] == [44]
    assert client.get("/api/v1/hreis/employees/45").status_code == 404


def test_hr_uc_002_hr_admin_can_create_and_update_service_records(stub_iam):
    client = _client(
        stub_iam,
        90,
        ("hreis.employee.manage",),
        role="hradmin",
        kind="staff",
    )
    response = client.put(
        "/api/v1/hreis/employees/46",
        {"employee_category": "teaching_staff", "department_code": "CSE"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["user_id"] == 46
    assert response.data["department_code"] == "CSE"


def test_hr_uc_017_policy_api_and_hradmin_guard(stub_iam):
    admin = _client(
        stub_iam,
        90,
        ("hreis.policy.view", "hreis.policy.manage"),
        role="hradmin",
        kind="staff",
    )
    response = admin.post(
        "/api/v1/hreis/policies",
        {
            "policy_name": "hr",
            "version": 1,
            "effective_from": date.today().isoformat(),
            "payload": {"approval_routes": {}},
        },
        format="json",
    )
    assert response.status_code == 201
    assert admin.get("/api/v1/hreis/policies").status_code == 200
    employee = _client(stub_iam, 47, ("hreis.policy.view",))
    assert (
        employee.post(
            "/api/v1/hreis/policies",
            {
                "policy_name": "other",
                "version": 1,
                "effective_from": date.today().isoformat(),
                "payload": {"approval_routes": {}},
            },
            format="json",
        ).status_code
        == 403
    )


def test_hr_uc_019_notification_and_hr_uc_018_audit_scopes(stub_iam):
    NotificationRecord.objects.create(user_id=48, topic="request.submitted")
    NotificationRecord.objects.create(user_id=49, topic="request.submitted")
    AuditEvent.objects.create(
        user_id=48,
        actor_user_id=90,
        actor_role="hradmin",
        action="policy_created",
        resource_type="policy",
        resource_id=1,
    )
    client = _client(
        stub_iam,
        48,
        ("hreis.notification.view", "hreis.audit.view"),
        role="hradmin",
        kind="staff",
    )
    notifications = client.get("/api/v1/hreis/notifications")
    assert notifications.status_code == 200
    assert len(notifications.data["results"]) == 1
    assert notifications.data["results"][0]["topic"] == "request.submitted"
    assert client.get("/api/v1/hreis/audit-events").status_code == 200


def test_hr_uc_004_authority_and_claim_api_permissions(stub_iam):
    reviewer = _client(stub_iam, 50, ("hreis.request.review",), role="HOD (CSE)")
    response = reviewer.post(
        "/api/v1/hreis/requests/999/transition",
        {"event": "approve"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="authority-key-50",
    )
    assert response.status_code == 404
    no_access = _client(stub_iam, 51, ())
    assert no_access.get("/api/v1/hreis/requests").status_code == 403


def test_employee_and_leave_balance_admin_endpoints(stub_iam):
    EmployeeServiceRecord.objects.create(user_id=52, employee_category="faculty")
    hr = _client(
        stub_iam,
        90,
        ("hreis.employee.view", "hreis.employee.manage", "hreis.leave_balance.manage"),
        role="hradmin",
        kind="staff",
    )
    assert hr.get("/api/v1/hreis/employees/52").status_code == 200
    balances = hr.get("/api/v1/hreis/leave-balances?user_id=52")
    assert balances.status_code == 200
    assert balances.data == []
    assert hr.get("/api/v1/hreis/leave-balances?user_id=bad").status_code == 400
    adjusted = hr.post(
        "/api/v1/hreis/leave-balances",
        {"user_id": 52, "leave_type": "earned", "delta_days": "4", "reason": "Opening"},
        format="json",
    )
    assert adjusted.status_code == 201
    assert adjusted.data["user_id"] == 52


def test_request_list_rejects_unknown_type_filter(stub_iam):
    client = _client(stub_iam, 53, ("hreis.request.view",))
    assert client.get("/api/v1/hreis/requests?request_type=unknown").status_code == 400
