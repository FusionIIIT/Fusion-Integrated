"""FR spec tests for Centralized Employee Service Records."""

import pytest

from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_HR_ADMIN,
    UID_STAFF_1,
    ensure_employee,
)

pytestmark = pytest.mark.django_db


def test_fr_038_hr_admin_manage_master_service_records(hr_caller):
    """TEST-FR-038 | HR-AFR-010 hr-admin-manage-master-service-records.

    Verify that HR-EIS allows the HR Administrator to manage employee master and service records.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"department": "Mechanical"},
    )
    assert res.status_code == 200
    assert res.data["department"] == "Mechanical"


def test_fr_047_employee_view_own_service_record(hr_caller):
    """TEST-FR-047 | HR-AFR-003 employee-view-own-service-record.

    Verify that HR-EIS allows an Employee to view the Employee's own service records.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{UID_FACULTY_1}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert res.data["user_id"] == UID_FACULTY_1


def test_fr_048_maintain_centralized_service_record(hr_caller):
    """TEST-FR-048 | HR-AFR-019 maintain-centralized-service-record.

    Verify that HR-EIS maintains a centralized service record for each employee.
    """
    emp = ensure_employee(UID_STAFF_1, kind="staff", department="Accounts", designation="Assistant")
    assert emp.pk is not None
    assert emp.employee_category == "staff"


def test_fr_049_include_appointment_details_service_record(hr_caller):
    """TEST-FR-049 | HR-AFR-020 include-appointment-details-service-record.

    Verify that HR-EIS includes appointment details in the employee service record.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert "appointment_details" in res.data


def test_fr_050_include_department_service_record(hr_caller):
    """TEST-FR-050 | HR-AFR-021 include-department-service-record.

    Verify that HR-EIS includes department in the employee service record.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty", department="ECE")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert res.data["department"] == "ECE"


def test_fr_051_include_designation_service_record(hr_caller):
    """TEST-FR-051 | HR-AFR-022 include-designation-service-record.

    Verify that HR-EIS includes designation in the employee service record.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty", designation="Associate Professor")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert res.data["designation"] == "Associate Professor"


def test_fr_052_include_service_history_service_record(hr_caller):
    """TEST-FR-052 | HR-AFR-023 include-service-history-service-record.

    Verify that HR-EIS includes service history in the employee service record.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert "service_history" in res.data


def test_fr_053_include_leave_balances_service_record(hr_caller):
    """TEST-FR-053 | HR-AFR-024 include-leave-balances-service-record.

    Verify that HR-EIS includes leave balances in the employee service record.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert "leave_balances" in res.data


def test_fr_054_include_retirement_status_service_record(hr_caller):
    """TEST-FR-054 | HR-AFR-025 include-retirement-status-service-record.

    Verify that HR-EIS includes retirement status in the employee service record.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    assert "retirement_status" in res.data


def test_fr_055_restrict_creation_service_records_hr_admin(hr_caller):
    """TEST-FR-055 | HR-AFR-026 restrict-creation-service-records-hr-admin.

    Verify that HR-EIS restricts creation of employee service records to HR Administrators and blocks other actors.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/employees/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"user_id": 3001, "department": "Civil"},
    )
    assert res.status_code == 403


def test_fr_056_restrict_modification_service_records_hr_admin(hr_caller):
    """TEST-FR-056 | HR-AFR-027 restrict-modification-service-records-hr-admin.

    Verify that HR-EIS restricts modification of employee service records to HR Administrators and blocks other actors.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"designation": "Director"},
    )
    assert res.status_code == 403


def test_fr_057_employee_view_own_service_record_read_only(hr_caller):
    """TEST-FR-057 | HR-AFR-028 employee-view-own-service-record-read-only.

    Verify that HR-EIS allows Employees to view their own service records in read-only mode.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    res_put = hr_caller(
        "put",
        f"/api/v1/hr/employees/{emp.user_id}/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"department": "New"},
    )
    assert res_put.status_code in (403, 405)


def test_fr_058_preserve_service_record_consistency(hr_caller):
    """TEST-FR-058 | HR-AFR-102 preserve-service-record-consistency.

    Verify that HR-EIS preserves service record consistency during updates.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"appointment_start_date": "2024-01-01", "appointment_end_date": "2024-12-31"},
    )
    assert res.status_code == 200
    emp.refresh_from_db()
    assert str(emp.appointment_start_date) == "2024-01-01"


def test_fr_059_prevent_partial_updates_corrupting_records(hr_caller):
    """TEST-FR-059 | HR-AFR-103 prevent-partial-updates-corrupting-records.

    Verify that HR-EIS prevents partial updates from corrupting service records.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"appointment_start_date": "2026-05-01", "appointment_end_date": "2026-01-01"},
    )
    assert res.status_code in (400, 422)


def test_fr_060_not_permit_employees_alter_official_records(hr_caller):
    """TEST-FR-060 | HR-AFR-107 not-permit-employees-alter-official-records.

    Verify that HR-EIS does not permit Employees to alter official service records.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"retirement_status": "Retired"},
    )
    assert res.status_code == 403
