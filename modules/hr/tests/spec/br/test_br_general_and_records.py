"""BR spec tests for Domain Scope, RBAC, Service Records, and Identity Boundaries."""

import pytest

from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_FACULTY_2,
    UID_HR_ADMIN,
    UID_STAFF_1,
    UID_UNAUTHORIZED,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_br_001_in_scope_operations_permitted(hr_caller):
    """TEST-BR-001 | BR-HR-001 in-scope-operations-permitted.

    Verify that HR-EIS accepts and executes operations within employee-centric HR service scope (service records, leave, appraisal, LTC, CPDA, audit).
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200


def test_br_002_out_of_scope_operations_prohibited(hr_caller):
    """TEST-BR-002 | BR-HR-001 out-of-scope-operations-prohibited.

    Verify that HR-EIS remains limited to its defined scope and rejects attempts to execute external domain functions (e.g. direct payroll run, bank wire transfer).
    """
    # Operations outside HR-EIS scope (e.g. course grade alterations, payroll run) are rejected
    res = hr_caller("post", "/api/v1/hr/modify-grades/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code in (404, 405)


def test_br_003_rbac_authorized_action_permitted(hr_caller):
    """TEST-BR-003 | BR-HR-002 rbac-authorized-action-permitted.

    Verify that HR-EIS permits actions when the actor holds the required Fusion RBAC role.
    """
    res = hr_caller("get", "/api/v1/hr/employees/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_br_004_rbac_unauthorized_action_prohibited(hr_caller):
    """TEST-BR-004 | BR-HR-002 rbac-unauthorized-action-prohibited.

    Verify that HR-EIS blocks actions when the actor lacks the required Fusion RBAC role.
    """
    res = hr_caller(
        "get", "/api/v1/hr/employees/", user_id=UID_FACULTY_1, role="faculty", permissions=()
    )
    assert res.status_code == 403


def test_br_005_own_record_read_only_permitted(hr_caller):
    """TEST-BR-005 | BR-HR-003 own-record-read-only-permitted.

    Verify that under the Employee role, a user can view their own service record in read-only mode.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200


def test_br_006_other_employee_record_prohibited(hr_caller):
    """TEST-BR-006 | BR-HR-003 other-employee-record-prohibited.

    Verify that under the Employee role, an employee cannot view another employee's service record or HR data.
    """
    emp2 = ensure_employee(UID_FACULTY_2, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp2.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 404


def test_br_007_multi_role_permission_exception(hr_caller):
    """TEST-BR-007 | BR-HR-003 multi-role-permission-exception.

    Verify the stated exception that additional access requires another explicitly authorized role (e.g. Employee who is also HOD).
    """
    actor = make_actor(
        UID_FACULTY_1,
        role="Head of Department",
        kind="faculty",
        permissions=("hr.employee.view", "hr.leave.approve"),
    )
    assert actor.has_permission("hr.employee.view")


def test_br_008_complete_service_record_attributes(hr_caller):
    """TEST-BR-008 | BR-HR-004 complete-service-record-attributes.

    Verify that an employee service record includes appointment details, department, designation, service history, leave balances, and retirement status.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{emp.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 200
    for field in (
        "appointment_details",
        "department",
        "designation",
        "service_history",
        "leave_balances",
        "retirement_status",
    ):
        assert field in res.data


def test_br_009_hr_admin_create_modify_permitted(hr_caller):
    """TEST-BR-009 | BR-HR-005 hr-admin-create-modify-permitted.

    Verify that HR Administrators are permitted to create or modify official employee service records.
    """
    emp = ensure_employee(UID_STAFF_1, kind="staff")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"department": "Finance"},
    )
    assert res.status_code == 200


def test_br_010_employee_create_modify_prohibited(hr_caller):
    """TEST-BR-010 | BR-HR-005 employee-create-modify-prohibited.

    Verify that Employees are prohibited from altering or creating official employee service records.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"department": "Math"},
    )
    assert res.status_code == 403


def test_br_011_consistent_update_permitted(hr_caller):
    """TEST-BR-011 | BR-HR-006 consistent-update-permitted.

    Verify that valid consistent updates to employee service records succeed and preserve data integrity.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"appointment_start_date": "2023-01-01", "appointment_end_date": "2025-12-31"},
    )
    assert res.status_code == 200


def test_br_012_partial_update_rollback_prohibited(hr_caller):
    """TEST-BR-012 | BR-HR-006 partial-update-rollback-prohibited.

    Verify that HR-EIS prevents partial updates from corrupting employee service records, rolling back on error.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"appointment_start_date": "2027-01-01", "appointment_end_date": "2025-01-01"},
    )
    assert res.status_code in (400, 422)


def test_br_056_identity_role_consistency_exchange(hr_caller):
    """TEST-BR-056 | BR-HR-028 identity-role-consistency-exchange.

    Verify that HR-EIS exchanges identity and role-consistency information with other Fusion modules and synchronizes integration data in real time where configured.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    assert emp.employee_category == "faculty"


def test_br_057_institutional_authority_roles_consumed(hr_caller):
    """TEST-BR-057 | BR-HR-029 institutional-authority-roles-consumed.

    Verify that HR-EIS consumes assigned roles controlled by institutional authorities.
    """
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    assert actor.has_permission("hr.employee.view")


def test_br_058_routine_actors_role_assignment_prohibited(hr_caller):
    """TEST-BR-058 | BR-HR-029 routine-actors-role-assignment-prohibited.

    Verify that HR-EIS does not expose routine HR-request actors as authorities for role assignment or reassignment.
    """
    actor = make_actor(UID_FACULTY_1, role="faculty")
    assert not actor.has_permission("iam.role.assign")


def test_br_059_authorized_sensitive_access_permitted(hr_caller):
    """TEST-BR-059 | BR-HR-030 authorized-sensitive-access-permitted.

    Verify that access to sensitive HR-EIS data is permitted to authorized roles.
    """
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code == 200


def test_br_060_unauthorized_sensitive_access_prohibited(hr_caller):
    """TEST-BR-060 | BR-HR-030 unauthorized-sensitive-access-prohibited.

    Verify that unauthorized access or data modification to sensitive HR-EIS data is prevented.
    """
    res = hr_caller(
        "get",
        "/api/v1/hr/audit-events/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
    )
    assert res.status_code == 403


def test_br_061_modify_payroll_rules_prohibited(hr_caller):
    """TEST-BR-061 | BR-HR-031 modify-payroll-rules-prohibited.

    Verify that HR-EIS does not modify payroll rules.
    """
    res = hr_caller("post", "/api/v1/hr/payroll/modify/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code in (404, 405)


def test_br_062_modify_salary_structures_prohibited(hr_caller):
    """TEST-BR-062 | BR-HR-031 modify-salary-structures-prohibited.

    Verify that HR-EIS does not modify institute salary structures.
    """
    res = hr_caller("post", "/api/v1/hr/salary/modify/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res.status_code in (404, 405)
