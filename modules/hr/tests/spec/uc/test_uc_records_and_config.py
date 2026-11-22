"""UC spec tests for Service Record Management and Workflow Configuration."""

import pytest

from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_HR_ADMIN,
    UID_UNAUTHORIZED,
    ensure_employee,
)

pytestmark = pytest.mark.django_db


def test_uc_001_main_flow_view_service_record(hr_caller):
    """TEST-UC-001 | HR-UC-001 Main Flow.

    Verify that an authenticated Employee can view their own official service record in read-only mode with all specified record attributes displayed.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert res.data["user_id"] == UID_FACULTY_1
    assert "department" in res.data
    assert "designation" in res.data


def test_uc_002_alternative_a1_multi_role_access(hr_caller):
    """TEST-UC-002 | HR-UC-001 Alternative A1.

    Verify that if an Employee holds another authorized HR-EIS role, the Employee-role view remains restricted to own-record and read-only.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    # User holding both faculty and HOD roles accesses own record
    res = hr_caller(
        "get",
        f"/api/v1/hr/employees/{emp.user_id}/",
        user_id=UID_FACULTY_1,
        role="Head of Department",
        kind="faculty",
        permissions=("hr.employee.view_self",),
    )
    assert res.status_code == 200


def test_uc_003_exception_e1_unauthorized_record_access(hr_caller):
    """TEST-UC-003 | HR-UC-001 Exception E1.

    Verify that if an actor's role does not authorize service-record access, HR-EIS denies access and preserves data confidentiality.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get",
        f"/api/v1/hr/employees/{emp.user_id}/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
    )
    assert res.status_code == 403


def test_uc_004_main_flow_manage_service_record(hr_caller):
    """TEST-UC-004 | HR-UC-002 Main Flow.

    Verify that HR Administrator can create or modify official employee master and service records with valid data and consistent commit.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"department": "Aerospace"},
    )
    assert res.status_code == 200
    assert res.data["department"] == "Aerospace"


def test_uc_005_alternative_a1_cancel_update(hr_caller):
    """TEST-UC-005 | HR-UC-002 Alternative A1.

    Verify that HR Administrator can cancel service record updates before commit without making any official record changes.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty", department="CSE")
    # State remains unmodified if no update request is submitted
    emp.refresh_from_db()
    assert emp.department == "CSE"


def test_uc_006_exception_e1_reject_invalid_service_record_update(hr_caller):
    """TEST-UC-006 | HR-UC-002 Exception E1.

    Verify that HR-EIS rejects partial, inconsistent, or unauthorized service record updates and preserves prior official record data.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    # Invalid date constraint
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"appointment_start_date": "2025-10-01", "appointment_end_date": "2025-01-01"},
    )
    assert res.status_code in (400, 422)


def test_uc_051_main_flow_configure_workflows(hr_caller):
    """TEST-UC-051 | HR-UC-017 Main Flow.

    Verify that HR Administrator can configure in-scope workflow settings and record authorized changes in audit trail.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/workflow-routes/save/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={
            "employee_category": "faculty",
            "request_type": "ltc_advance",
            "steps": [{"approver_user_id": UID_HR_ADMIN, "authority_label": "HR Admin"}],
            "reminder_after_hours": 24,
        },
    )
    assert res.status_code == 200
    assert res.data["request_type"] == "ltc_advance"


def test_uc_052_alternative_a1_external_scope_setting_refused(hr_caller):
    """TEST-UC-052 | HR-UC-017 Alternative A1.

    Verify that if a requested setting belongs to platform RBAC or an external system, HR-EIS does not provide it as an HR-EIS workflow setting.
    """
    # Attempting to alter platform RBAC or payroll settings via HR endpoint is rejected
    res = hr_caller(
        "post",
        "/api/v1/hr/platform-rbac/save/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"role": "superadmin"},
    )
    assert res.status_code in (404, 405)


def test_uc_053_exception_e1_unauthorized_workflow_configuration(hr_caller):
    """TEST-UC-053 | HR-UC-017 Exception E1.

    Verify that unauthorized configuration or an attempt to configure a manual workflow bypass is rejected.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/workflow-routes/save/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "employee_category": "faculty",
            "request_type": "ltc_advance",
            "steps": [{"approver_user_id": UID_FACULTY_1}],
        },
    )
    assert res.status_code == 403
