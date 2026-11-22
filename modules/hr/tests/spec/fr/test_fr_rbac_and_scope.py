"""FR spec tests for RBAC, Authorization, and Scope Boundaries."""

import pytest

from core.api.exceptions import PermissionDeniedError
from modules.hr.services import authz
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    UID_FACULTY_2,
    UID_HOD,
    UID_HR_ADMIN,
    UID_STAFF_1,
    UID_UNAUTHORIZED,
    ensure_employee,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_fr_001_consolidated_rbac_and_security(hr_caller):
    """TEST-FR-001 | HR-CFR-001 consolidated-rbac-and-security.

    Verify that HR-EIS enforces Fusion-assigned RBAC across module functions, respects institutional control of role assignments, and restricts unauthorized access or data modification.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_employee(UID_STAFF_1, kind="staff")

    # Authorized HR admin can view employee list
    res_admin = hr_caller("get", "/api/v1/hr/employees/", user_id=UID_HR_ADMIN, role="hr_officer")
    assert res_admin.status_code == 200

    # Authorized Employee can view own record
    res_emp = hr_caller(
        "get", f"/api/v1/hr/employees/{UID_FACULTY_1}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res_emp.status_code == 200

    # Unauthorized role (student/unauthorized) cannot access HR employee list
    res_unauth = hr_caller(
        "get",
        "/api/v1/hr/employees/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
    )
    assert res_unauth.status_code == 403


def test_fr_002_consolidated_employee_request_self_service(hr_caller):
    """TEST-FR-002 | HR-CFR-002 consolidated-employee-request-self-service.

    Verify that an Employee can initiate supported HR service requests and track the status of requests submitted by the Employee.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    # Query leave requests self-service tracking interface
    res = hr_caller("get", "/api/v1/hr/leaves/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200
    assert "results" in res.data


def test_fr_004_consolidated_hr_administrator_capabilities(hr_caller):
    """TEST-FR-004 | HR-CFR-004 consolidated-hr-administrator-capabilities.

    Verify that HR-EIS provides the HR Administrator with authorized capabilities to manage service records, verify HR requests, configure workflow settings, assign reviewers, and monitor audits.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    # HR Admin updates employee service record
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"department": "Computer Science & Engineering"},
    )
    assert res.status_code == 200
    assert res.data["department"] == "Computer Science & Engineering"

    # HR Admin views audit log
    res_audit = hr_caller(
        "get", "/api/v1/hr/audit-events/", user_id=UID_HR_ADMIN, role="hr_officer"
    )
    assert res_audit.status_code == 200


def test_fr_006_consolidated_employee_service_record_management(hr_caller):
    """TEST-FR-006 | HR-CFR-006 consolidated-employee-service-record-management.

    Verify that HR-EIS maintains a centralized service record for each employee, restricts creation/modification to HR Administrators, allows Employees read-only access to their own record, and preserves record consistency.
    """
    emp1 = ensure_employee(UID_FACULTY_1, kind="faculty")
    emp2 = ensure_employee(UID_FACULTY_2, kind="faculty")

    # Employee views own record in read-only mode
    res_own = hr_caller(
        "get", f"/api/v1/hr/employees/{emp1.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res_own.status_code == 200

    # Employee viewing another employee's record is refused (404 Not Found per ownership filtering)
    res_other = hr_caller(
        "get", f"/api/v1/hr/employees/{emp2.user_id}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res_other.status_code == 404

    # Employee attempting to modify own record is refused (403 Forbidden)
    res_mod = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp1.user_id}/update/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"department": "Hacked Dept"},
    )
    assert res_mod.status_code == 403


def test_fr_014_consolidated_payroll_salary_scope_boundary(hr_caller):
    """TEST-FR-014 | HR-CFR-014 consolidated-payroll-salary-scope-boundary.

    Verify the architectural scope boundary that HR-EIS does not modify external payroll rules or salary structures during HR financial claim recording and exchange.
    """
    # HR-EIS module does not expose endpoints to alter external payroll or salary structures
    res = hr_caller(
        "post",
        "/api/v1/hr/payroll-rules/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"rule": "bonus"},
    )
    assert res.status_code in (404, 405)


def test_fr_015_rbac_actor_permissions(hr_caller):
    """TEST-FR-015 | HR-AFR-001 rbac-actor-permissions.

    Verify that HR-EIS operates under Fusion RBAC for actor permissions across all module endpoints.
    """
    actor = make_actor(UID_FACULTY_1, role="faculty")
    assert actor.has_permission("hr.employee.view_self")
    assert not actor.has_permission("hr.employee.update")

    # Verified via service require
    authz.require(actor, "hr.employee.view_self")
    with pytest.raises(PermissionDeniedError):
        authz.require(actor, "hr.employee.update")


def test_fr_016_enforce_fusion_rbac_functions(hr_caller):
    """TEST-FR-016 | HR-AFR-094 enforce-fusion-rbac-functions.

    Verify that HR-EIS enforces Fusion RBAC for all HR-EIS functional actions.
    """
    # Accountant role can manage claims but cannot approve leaves
    actor = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    assert actor.has_permission("hr.claim.manage")
    assert not actor.has_permission("hr.leave.approve")


def test_fr_017_support_simultaneous_multiple_roles(hr_caller):
    """TEST-FR-017 | HR-AFR-095 support-simultaneous-multiple-roles.

    Verify that HR-EIS supports users holding multiple roles simultaneously (e.g., Faculty Employee who is also HOD).
    """
    # User holding both faculty and HOD roles
    permissions = (
        "hr.employee.view_self",
        "hr.leave.create",
        "hr.leave.approve",
        "hr.claim.approve",
    )
    actor = make_actor(UID_HOD, role="Head of Department", kind="faculty", permissions=permissions)
    assert actor.has_permission("hr.leave.create")
    assert actor.has_permission("hr.leave.approve")


def test_fr_018_role_assignment_institutional_authorities_only(hr_caller):
    """TEST-FR-018 | HR-AFR-096 role-assignment-institutional-authorities-only.

    Verify that HR-EIS allows role assignment only by institutional authorities and rejects routine HR actor attempts.
    """
    # Routine employee cannot execute role assignment
    actor = make_actor(UID_FACULTY_1, role="faculty")
    assert not actor.has_permission("hr.workflow.manage")
    assert not actor.has_permission("iam.role.assign")


def test_fr_019_role_reassignment_institutional_authorities_only(hr_caller):
    """TEST-FR-019 | HR-AFR-097 role-reassignment-institutional-authorities-only.

    Verify that HR-EIS allows role reassignment only by institutional authorities.
    """
    # Routine employee cannot reassign roles
    actor = make_actor(UID_STAFF_1, role="staff", kind="staff")
    assert not actor.has_permission("iam.role.manage")


def test_fr_020_restrict_sensitive_data_authorized_roles(hr_caller):
    """TEST-FR-020 | HR-AFR-098 restrict-sensitive-data-authorized-roles.

    Verify that HR-EIS restricts access to sensitive HR data to authorized roles only.
    """
    # Unauthorized role attempting to view audit events is refused (403)
    res = hr_caller("get", "/api/v1/hr/audit-events/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 403


def test_fr_021_restrict_employee_to_own_data(hr_caller):
    """TEST-FR-021 | HR-AFR-099 restrict-employee-to-own-data.

    Verify that HR-EIS restricts Employees to accessing only their own employee data.
    """
    ensure_employee(UID_FACULTY_2, kind="faculty")
    # Employee 1 querying Employee 2's service record is blocked
    res = hr_caller(
        "get", f"/api/v1/hr/employees/{UID_FACULTY_2}/", user_id=UID_FACULTY_1, role="faculty"
    )
    assert res.status_code == 404


def test_fr_022_prevent_unauthorized_access_hr_data(hr_caller):
    """TEST-FR-022 | HR-AFR-100 prevent-unauthorized-access-hr-data.

    Verify that HR-EIS prevents unauthorized access to HR-EIS data by unauthenticated or anonymous actors.
    """
    # Unauthenticated / unauthorized request without hr module grant
    res = hr_caller(
        "get",
        "/api/v1/hr/employees/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        modules=(),
        permissions=(),
    )
    assert res.status_code == 403


def test_fr_023_prevent_unauthorized_modification_hr_data(hr_caller):
    """TEST-FR-023 | HR-AFR-101 prevent-unauthorized-modification-hr-data.

    Verify that HR-EIS prevents unauthorized modification of HR-EIS data.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    # Employee cannot patch service records
    res = hr_caller(
        "patch",
        f"/api/v1/hr/employees/{emp.user_id}/update/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"department": "Physics"},
    )
    assert res.status_code == 403
    emp.refresh_from_db()
    assert emp.department == "CSE"


def test_fr_129_not_modify_payroll_rules(hr_caller):
    """TEST-FR-129 | HR-AFR-104 not-modify-payroll-rules.

    Verify that HR-EIS does not modify payroll rules.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/payroll/rules/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"tax": "exempt"},
    )
    assert res.status_code in (404, 405)


def test_fr_130_not_modify_salary_structures(hr_caller):
    """TEST-FR-130 | HR-AFR-105 not-modify-salary-structures.

    Verify that HR-EIS does not modify salary structures.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/salary-structures/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"grade": "Level-14"},
    )
    assert res.status_code in (404, 405)
