"""HTTP-level tests for HR resources using the project's authenticated API stack."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.hr.models import EmployeeRecord, LeaveBalance
from modules.hr.services import appraisals, configuration, employees, notifications

pytestmark = pytest.mark.django_db


def test_hr_api_resources_complete_employee_claim_appraisal_and_leave_flows(stub_iam, monkeypatch):
    directory_people = {
        1001: SimpleNamespace(kind="staff"),
        2002: SimpleNamespace(kind="faculty"),
        88: SimpleNamespace(kind="staff"),
    }
    active_employee_ids = set(directory_people)
    for service in (employees, configuration, appraisals, notifications):
        monkeypatch.setattr(
            service.directory,
            "get_users",
            lambda user_ids, people=directory_people: {
                uid: people[uid] for uid in user_ids if uid in people
            },
        )
        monkeypatch.setattr(
            service.directory,
            "held_employee_ids",
            lambda ids=active_employee_ids: set(ids),
        )

    employee = EmployeeRecord.objects.create(
        user_id=1001,
        employee_category="staff",
        department="Research",
        designation="Officer",
        created_by_user_id=7,
        updated_by_user_id=7,
    )
    client = APIClient()
    request_number = 0

    def call(method, path, *, user_id=7, permissions=(), data=None):
        nonlocal request_number
        request_number += 1
        stub_iam(
            make_session(
                user_id=user_id,
                kind="staff",
                modules=("hr",),
                permissions=permissions,
                roles=("staff",),
                active_role="staff",
            ),
            users={},
        )
        client.credentials(HTTP_AUTHORIZATION=f"Token hr-api-{request_number}")
        operation = getattr(client, method)
        return operation(path, data=data, format="json") if data is not None else operation(path)

    # Employee list/create/detail/update paths and their returned records.
    assert (
        call("get", "/api/v1/hr/employees/", permissions=("hr.employee.view",)).status_code == 200
    )
    created_employee = call(
        "post",
        "/api/v1/hr/employees/create/",
        permissions=("hr.employee.create", "hr.employment.manage"),
        data={"user_id": 2002, "department": "Science", "designation": "Faculty"},
    )
    assert created_employee.status_code == 201, created_employee.data
    assert (
        call(
            "get",
            "/api/v1/hr/employees/1001/",
            user_id=1001,
            permissions=("hr.employee.view_self",),
        ).status_code
        == 200
    )
    assert (
        call(
            "patch",
            "/api/v1/hr/employees/1001/update/",
            permissions=("hr.employee.update",),
            data={"department": "Physics"},
        ).status_code
        == 200
    )
    assert (
        call("get", "/api/v1/hr/employees/9999/", permissions=("hr.employee.view",)).status_code
        == 404
    )

    # A single-authority LTC workflow exercises create, list, detail, verify,
    # decide, processing, integration status, and audit history endpoints.
    assert (
        call(
            "post",
            "/api/v1/hr/workflow-routes/save/",
            permissions=("hr.workflow.manage",),
            data={
                "employee_category": "staff",
                "request_type": "ltc_reimbursement",
                "steps": [{"approver_user_id": 88, "authority_label": "HOD"}],
            },
        ).status_code
        == 200
    )
    assert (
        call("get", "/api/v1/hr/workflow-routes/", permissions=("hr.workflow.manage",)).status_code
        == 200
    )
    claim_create = call(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=1001,
        permissions=("hr.claim.create",),
        data={"request_type": "ltc_reimbursement", "form_data": {"destination": "Delhi"}},
    )
    assert claim_create.status_code == 201
    claim_id = claim_create.data["id"]
    assert call("get", "/api/v1/hr/claims/", permissions=("hr.claim.view",)).status_code == 200
    assert (
        call(
            "get",
            f"/api/v1/hr/claims/{claim_id}/",
            user_id=1001,
            permissions=("hr.claim.view_self",),
        ).status_code
        == 200
    )
    assert call("get", "/api/v1/hr/claims/9999/", permissions=("hr.claim.view",)).status_code == 404
    assert (
        call("get", "/api/v1/hr/claims/9999/history/", permissions=("hr.claim.view",)).status_code
        == 404
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/claims/{claim_id}/verify/",
            permissions=("hr.claim.verify",),
            data={"verified": True, "note": "Complete"},
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/claims/{claim_id}/decision/",
            user_id=88,
            permissions=("hr.claim.approve",),
            data={"action": "approve"},
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/claims/{claim_id}/processing/",
            permissions=("hr.claim.manage",),
            data={"financially_correct": True, "details": {"voucher": "V-1"}},
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/claims/{claim_id}/integration-status/",
            permissions=("hr.claim.manage",),
            data={"system": "finance", "external_status": "Paid"},
        ).status_code
        == 201
    )
    assert (
        call(
            "get", f"/api/v1/hr/claims/{claim_id}/history/", permissions=("hr.claim.view",)
        ).status_code
        == 200
    )

    # Appraisal window, submission, reviewer assignment, finalization and read APIs.
    now = timezone.now()
    assert (
        call(
            "post",
            "/api/v1/hr/appraisal-windows/save/",
            permissions=("hr.workflow.manage",),
            data={
                "period": "2026",
                "opens_at": (now - timedelta(days=1)).isoformat(),
                "closes_at": (now + timedelta(days=1)).isoformat(),
                "is_active": True,
            },
        ).status_code
        == 200
    )
    assert (
        call(
            "get", "/api/v1/hr/appraisal-windows/", permissions=("hr.workflow.manage",)
        ).status_code
        == 200
    )
    appraisal_create = call(
        "post",
        "/api/v1/hr/appraisals/create/",
        user_id=1001,
        permissions=("hr.appraisal.create",),
        data={"period": "2026", "form_data": {"accomplishment": "Published"}},
    )
    assert appraisal_create.status_code == 201
    appraisal_id = appraisal_create.data["id"]
    assert (
        call("get", "/api/v1/hr/appraisals/", permissions=("hr.appraisal.assign",)).status_code
        == 200
    )
    assert (
        call(
            "get", f"/api/v1/hr/appraisals/{appraisal_id}/", permissions=("hr.appraisal.assign",)
        ).status_code
        == 200
    )
    assert (
        call("get", "/api/v1/hr/appraisals/9999/", permissions=("hr.appraisal.assign",)).status_code
        == 404
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/appraisals/{appraisal_id}/reviewers/",
            permissions=("hr.appraisal.assign",),
            data={"reviewer_user_ids": [88]},
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/appraisals/{appraisal_id}/review/",
            user_id=88,
            permissions=("hr.appraisal.review",),
            data={"action": "finalize", "note": "Reviewed"},
        ).status_code
        == 200
    )

    # Audit and addressed notification listing plus notice publication.
    assert (
        call("get", "/api/v1/hr/audit-events/", permissions=("hr.audit.view",)).status_code == 200
    )
    assert (
        call(
            "get",
            "/api/v1/hr/notifications/",
            user_id=1001,
            permissions=("hr.notification.view",),
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            "/api/v1/hr/notices/",
            permissions=("hr.notification.manage",),
            data={"recipient_user_ids": [1001], "subject": "Schedule", "body": "See notice."},
        ).status_code
        == 201
    )

    # Leave balance management and the employee request/approval endpoints.
    assert (
        call(
            "post",
            "/api/v1/hr/workflow-routes/save/",
            permissions=("hr.workflow.manage",),
            data={
                "employee_category": "staff",
                "request_type": "leave_casual",
                "steps": [{"approver_user_id": 88, "authority_label": "HOD"}],
            },
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            "/api/v1/hr/leave-balances/save/",
            permissions=("hr.leave_balance.manage",),
            data={
                "employee_user_id": employee.user_id,
                "leave_type": "casual",
                "available_days": "8.00",
                "is_eligible": True,
            },
        ).status_code
        == 200
    )
    assert (
        call(
            "get", "/api/v1/hr/leave-balances/", permissions=("hr.leave_balance.manage",)
        ).status_code
        == 200
    )
    leave_create = call(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=1001,
        permissions=("hr.leave.create",),
        data={"leave_type": "casual", "duration_days": "1.50", "justification": "Family"},
    )
    assert leave_create.status_code == 201, leave_create.data
    leave_id = leave_create.data["id"]
    assert (
        call(
            "get", "/api/v1/hr/leaves/", user_id=1001, permissions=("hr.leave.view_self",)
        ).status_code
        == 200
    )
    assert (
        call(
            "post",
            f"/api/v1/hr/leaves/{leave_id}/decision/",
            user_id=88,
            permissions=("hr.leave.approve",),
            data={"action": "approve"},
        ).status_code
        == 200
    )
    assert LeaveBalance.objects.get(
        employee=employee, leave_type="casual"
    ).available_days == Decimal("6.50")


def test_hr_api_serializer_errors_are_reported_as_client_errors(stub_iam):
    client = APIClient()
    session = make_session(
        user_id=7,
        kind="staff",
        modules=("hr",),
        permissions=("hr.employee.create", "hr.claim.create", "hr.leave.create"),
        roles=("staff",),
        active_role="staff",
    )
    stub_iam(session)
    client.credentials(HTTP_AUTHORIZATION="Token invalid-payloads")
    assert (
        client.post(
            "/api/v1/hr/employees/create/",
            {
                "user_id": 1001,
                "department": "Research",
                "designation": "Officer",
                "appointment_start_date": "2026-08-01",
                "appointment_end_date": "2026-07-31",
            },
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/hr/claims/create/",
            {
                "request_type": "ltc_reimbursement",
                "form_data": {"destination": "Delhi"},
                "supporting_document_links": ["https://evil.example/file"],
            },
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/hr/leaves/create/",
            {"leave_type": "other", "duration_days": "0", "justification": ""},
            format="json",
        ).status_code
        == 400
    )
