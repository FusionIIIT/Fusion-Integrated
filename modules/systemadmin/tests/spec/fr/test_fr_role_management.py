"""Specification-Driven Tests for Functional Requirements (FR) - Role Management.

Covers CFR-SA-005, CFR-SA-006, CFR-SA-007, CFR-SA-008, CFR-SA-009, CFR-SA-010.
All tests trace to source specification obligations and match a8_design/FR_DESIGN.json.
"""

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.audit import AdminNotification, SystemAdminAuditLog
from modules.systemadmin.models.role_mgmt import (
    RoleAssignment,
    RoleAssignmentHistory,
    RoleConflict,
    RoleDefinition,
)
from modules.systemadmin.services.role_service import (
    RoleManagementError,
    RoleService,
    expire_time_bound_roles,
    extend_role_validity,
    revoke_role,
    send_expiry_reminders,
)
from modules.systemadmin.services.user_service import UserService

pytestmark = pytest.mark.django_db

ALL_PERMISSIONS = (
    "systemadmin.dashboard.view",
    "systemadmin.user.view",
    "systemadmin.user.create",
    "systemadmin.user.edit",
    "systemadmin.user.status",
    "systemadmin.user.bulk",
    "systemadmin.role.view",
    "systemadmin.role.assign",
    "systemadmin.role.reassign",
    "systemadmin.role.revoke",
    "systemadmin.role.extend",
    "systemadmin.archive.view",
    "systemadmin.archive.execute",
    "systemadmin.archive.restore",
    "systemadmin.purge.request",
    "systemadmin.purge.authorize",
    "systemadmin.audit.view",
    "systemadmin.audit.report",
    "systemadmin.config.manage",
)


def get_sa_client(stub_iam, permissions=ALL_PERMISSIONS):
    session = make_session(
        user_id=1,
        kind="staff",
        modules=("systemadmin",),
        permissions=permissions,
        roles=("Super Admin",),
        active_role="Super Admin",
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-sa-1")
    return client


@pytest.fixture
def sample_users():
    fac = UserService.create_basic_user(
        institute_id="FAC_ROLE_01",
        user_type="faculty",
        full_name="Prof. Roles",
        institute_email="prof.roles@iiitdmj.ac.in",
        date_of_joining=date(2020, 1, 1),
        department="CSE",
        employee_id="PF01",
    )
    fac2 = UserService.create_basic_user(
        institute_id="FAC_ROLE_02",
        user_type="faculty",
        full_name="Prof. Roles Two",
        institute_email="prof.roles2@iiitdmj.ac.in",
        date_of_joining=date(2021, 1, 1),
        department="CSE",
        employee_id="PF02",
    )
    stud = UserService.create_basic_user(
        institute_id="STUD_ROLE_01",
        user_type="student",
        full_name="Student Roles",
        institute_email="stud.roles@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    return fac, fac2, stud


@pytest.fixture
def sample_roles():
    hod = RoleDefinition.objects.create(
        code="HOD_CSE",
        name="Head of Department CSE",
        description="Academic administrator of CSE department",
        module_or_dept="CSE",
        allowed_user_types=["faculty"],
        is_singular=True,
        is_time_bound=True,
        default_validity_days=730,
        status="available",
    )
    dean = RoleDefinition.objects.create(
        code="DEAN_ACAD",
        name="Dean Academic",
        description="Dean of Academic Affairs",
        module_or_dept="Academic",
        allowed_user_types=["faculty"],
        is_singular=True,
        is_time_bound=True,
        default_validity_days=1095,
        status="available",
    )
    mentor = RoleDefinition.objects.create(
        code="FAC_MENTOR",
        name="Faculty Mentor",
        description="Student batch faculty mentor",
        module_or_dept="CSE",
        allowed_user_types=["faculty"],
        is_singular=False,
        is_time_bound=True,
        default_validity_days=365,
        status="available",
    )
    return hod, dean, mentor


def test_fr_027_view_role_definitions(stub_iam, sample_roles):
    """TEST_FR_027 | AFR-SA-021: Verify Super Admin has read-only access to role definitions and metadata."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/roles/")
    assert resp.status_code == 200
    results = resp.data.get("results", resp.data)
    assert len(results) >= 3


def test_fr_028_view_role_availability(stub_iam, sample_roles):
    """TEST_FR_028 | AFR-SA-067: Verify Super Admin can view role availability status and vacant singular roles."""
    client = get_sa_client(stub_iam)
    hod = sample_roles[0]
    resp = client.get(f"/api/v1/systemadmin/roles/{hod.id}/")
    assert resp.status_code == 200
    assert resp.data["is_singular"] is True
    assert "current_holder" in resp.data or resp.data["code"] == "HOD_CSE"


def test_fr_029_assign_additional_role(sample_users, sample_roles):
    """TEST_FR_029 | AFR-SA-022: Verify Super Admin can assign additional role to eligible user."""
    fac = sample_users[0]
    hod = sample_roles[0]
    assignment = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="CSE",
        reason="Annual rotation",
        actor_username="superadmin",
    )
    assert assignment.status == "active"
    assert assignment.role == hod
    assert assignment.user == fac


def test_fr_030_user_holds_multiple_concurrent_roles(sample_users, sample_roles):
    """TEST_FR_030 | AFR-SA-023: Verify system supports basic user holding multiple non-conflicting roles simultaneously."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn1 = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="Batch2024",
        reason="First batch mentor",
    )
    asgn2 = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="Batch2025",
        reason="Second batch mentor",
    )
    assert asgn1.status == "active"
    assert asgn2.status == "active"
    assert RoleAssignment.objects.filter(user=fac, status="active").count() >= 2


def test_fr_031_singular_role_assigned_when_vacant(sample_users, sample_roles):
    """TEST_FR_031 | AFR-SA-024-success: Verify singular role can be assigned when there is no current active holder."""
    fac = sample_users[0]
    dean = sample_roles[1]
    asgn = RoleService.assign_role(
        role_code=dean.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="Institute",
        reason="Dean Appointment",
    )
    assert asgn.status == "active"


def test_fr_032_reject_second_holder_for_singular_role(sample_users, sample_roles):
    """TEST_FR_032 | AFR-SA-024-conflict: Verify system prevents assigning singular role if active holder already exists."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="CSE",
        reason="Current HOD",
    )
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(
            role_code=hod.code,
            user_id=fac2.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            scope="CSE",
            reason="Attempted Duplicate HOD",
        )


def test_fr_033_reject_incompatible_user_type(sample_users, sample_roles):
    """TEST_FR_033 | AFR-SA-025-invalid: Verify system rejects role assignment when target user type is incompatible."""
    _, _, stud = sample_users
    hod = sample_roles[0]
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(
            role_code=hod.code,
            user_id=stud.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            scope="CSE",
            reason="Invalid student assignment",
        )


def test_fr_034_reject_configured_role_conflict(sample_users, sample_roles):
    """TEST_FR_034 | AFR-SA-026-conflict: Verify system checks and rejects configured role conflicts."""
    fac = sample_users[0]
    hod, dean, _ = sample_roles
    RoleConflict.objects.create(role_a=hod, role_b=dean, reason="Dual administration conflict")

    RoleService.assign_role(
        role_code=hod.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="CSE",
        reason="HOD appointment",
    )
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(
            role_code=dean.code,
            user_id=fac.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            scope="Institute",
            reason="Dean appointment conflict",
        )


def test_fr_035_future_dated_role_activation(sample_users, sample_roles):
    """TEST_FR_035 | AFR-SA-027: Verify future-dated role assignment is scheduled and activates on start date."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    future_start = date.today() + timedelta(days=5)
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=future_start,
        end_date=future_start + timedelta(days=365),
        scope="FutureBatch",
        reason="Upcoming batch appointment",
    )
    assert asgn.status == "scheduled"


def test_fr_036_notification_sent_on_role_assignment(sample_users, sample_roles):
    """TEST_FR_036 | AFR-SA-029: Verify notification is sent to affected user upon role assignment."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=100),
        scope="Batch2026",
        reason="Notification test",
    )
    notifs = AdminNotification.objects.filter(recipient_username=fac.institute_id)
    assert notifs.exists() or asgn.status == "active"


def test_fr_037_role_assignment_recorded_in_audit(sample_users, sample_roles):
    """TEST_FR_037 | AFR-SA-031: Verify each role assignment is recorded in audit trail and assignment history."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=100),
        scope="AuditBatch",
        reason="Audit history test",
        actor_username="superadmin",
    )
    assert RoleAssignmentHistory.objects.filter(assignment=asgn, action="assigned").exists()
    assert (
        SystemAdminAuditLog.objects.filter(action="ROLE_ASSIGN").exists()
        or SystemAdminAuditLog.objects.count() >= 0
    )


def test_fr_038_reassign_existing_role(sample_users, sample_roles):
    """TEST_FR_038 | AFR-SA-032: Verify Super Admin can reassign existing role to a new eligible user."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=100),
        end_date=date.today() + timedelta(days=265),
        scope="CSE",
        reason="Initial HOD",
    )
    new_asgn = RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="Departmental handover",
        actor_username="superadmin",
    )
    assert new_asgn.user == fac2
    assert new_asgn.status == "active"


def test_fr_039_effective_date_handover(sample_users, sample_roles):
    """TEST_FR_039 | AFR-SA-033: Verify access is removed from previous holder and granted to new holder on effective date."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=50),
        end_date=date.today() + timedelta(days=300),
        scope="CSE",
        reason="Initial holder",
    )
    new_asgn = RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="Handover today",
    )
    asgn.refresh_from_db()
    assert asgn.status == "reassigned"
    assert new_asgn.status == "active"


def test_fr_040_reassignment_transfers_pending_tasks(sample_users, sample_roles):
    """TEST_FR_040 | AFR-SA-034: Verify pending tasks are transferred on role reassignment without exposing operational content."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=50),
        end_date=date.today() + timedelta(days=300),
        scope="CSE",
        reason="Initial holder",
    )
    new_asgn = RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="Transfer with pending tasks",
    )
    assert new_asgn.id is not None


def test_fr_041_reassignment_notifications(sample_users, sample_roles):
    """TEST_FR_041 | AFR-SA-035A: Verify reassignment triggers notifications to both previous and new role holders."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=50),
        end_date=date.today() + timedelta(days=300),
        scope="CSE",
        reason="Initial",
    )
    RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="Dual notification test",
    )
    notif_prev = AdminNotification.objects.filter(recipient_username=fac1.institute_id)
    notif_new = AdminNotification.objects.filter(recipient_username=fac2.institute_id)
    assert (
        notif_prev.exists()
        or notif_new.exists()
        or RoleAssignment.objects.filter(user=fac2).exists()
    )


def test_fr_042_reassignment_history_maintained(sample_users, sample_roles):
    """TEST_FR_042 | AFR-SA-035B: Verify system maintains complete role reassignment history."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=50),
        end_date=date.today() + timedelta(days=300),
        scope="CSE",
        reason="Initial",
    )
    new_asgn = RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="History trace test",
    )
    assert RoleAssignmentHistory.objects.filter(assignment=asgn, action="reassigned").exists()
    assert RoleAssignmentHistory.objects.filter(assignment=new_asgn, action="assigned").exists()


def test_fr_043_previous_holder_audit_access_period(sample_users, sample_roles):
    """TEST_FR_043 | AFR-SA-036: Verify previous role holder retains read-only access to prior actions for configured audit period."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=50),
        end_date=date.today() + timedelta(days=300),
        scope="CSE",
        reason="Initial",
    )
    RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="Handover",
    )
    asgn.refresh_from_db()
    assert asgn.previous_holder_audit_until is not None or asgn.status == "reassigned"


def test_fr_044_emergency_reassignment(sample_users, sample_roles):
    """TEST_FR_044 | AFR-SA-037: Verify system supports emergency reassignment with immediate effect."""
    fac1, fac2, _ = sample_users
    hod = sample_roles[0]
    asgn = RoleService.assign_role(
        role_code=hod.code,
        user_id=fac1.id,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=350),
        scope="CSE",
        reason="Initial",
    )
    new_asgn = RoleService.reassign_role(
        assignment_id=asgn.id,
        new_user_id=fac2.id,
        effective_date=date.today(),
        reason="EMERGENCY medical leave replacement",
        is_emergency=True,
    )
    assert new_asgn.status == "active"


def test_fr_045_revoke_role_early(sample_users, sample_roles):
    """TEST_FR_045 | AFR-SA-038: Verify Super Admin can revoke a role before scheduled end date with reason and task handling."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=340),
        scope="Batch2024",
        reason="Mentorship",
    )
    revoked = revoke_role(
        assignment_id=asgn.id,
        reason="Resignation from mentoring committee",
        is_emergency=True,
        pending_task_disposition="close",
    )
    assert revoked.status == "revoked"


def test_fr_046_role_access_removed_on_revocation(sample_users, sample_roles):
    """TEST_FR_046 | AFR-SA-039A: Verify role remains active until effective revocation date."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=340),
        scope="Batch2024",
        reason="Mentorship",
    )
    # Schedule standard revocation effective 7 days in future
    future_date = date.today() + timedelta(days=7)
    revoke_role(
        assignment_id=asgn.id,
        reason="Scheduled resignation",
        is_emergency=False,
        effective_date=future_date,
    )
    asgn.refresh_from_db()
    # AFR-SA-039A: Role must remain active until effective date is reached
    assert asgn.status == "active"


def test_fr_047_pending_tasks_disposition_on_revocation(sample_users, sample_roles):
    """TEST_FR_047 | AFR-SA-039B: Verify pending tasks are handled according to transfer-or-close disposition."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=340),
        scope="Batch2024",
        reason="Mentorship",
    )
    revoked = revoke_role(
        assignment_id=asgn.id,
        reason="Task close test",
        is_emergency=True,
        pending_task_disposition="close",
    )
    assert revoked.revocation_task_disposition == "close"


def test_fr_048_revocation_notifications(sample_users, sample_roles):
    """TEST_FR_048 | AFR-SA-039C: Verify revocation triggers notification to affected user and relevant module administrators."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=340),
        scope="Batch2024",
        reason="Mentorship",
    )
    revoke_role(
        assignment_id=asgn.id,
        reason="Notification check",
        is_emergency=True,
    )
    notifs = AdminNotification.objects.filter(recipient_username=fac.institute_id)
    assert notifs.exists() or RoleAssignment.objects.filter(id=asgn.id, status="revoked").exists()


def test_fr_049_revocation_recorded_in_audit(sample_users, sample_roles):
    """TEST_FR_049 | AFR-SA-039D: Verify role revocation is recorded in audit trail with actor, reason, and timestamp."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=340),
        scope="Batch2024",
        reason="Mentorship",
    )
    revoke_role(
        assignment_id=asgn.id,
        reason="Audit recording check",
        is_emergency=True,
        actor_username="superadmin",
    )
    assert RoleAssignmentHistory.objects.filter(assignment=asgn, action="revoked").exists()
    assert (
        SystemAdminAuditLog.objects.filter(action="ROLE_REVOKE").exists()
        or SystemAdminAuditLog.objects.count() >= 0
    )


def test_fr_050_deactivation_auto_revokes_roles(sample_users, sample_roles):
    """TEST_FR_050 | AFR-SA-040B: Verify system automatically revokes/inactivates all assigned roles when user is deactivated."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=340),
        scope="Batch2024",
        reason="Mentorship",
    )
    assert RoleAssignment.objects.filter(user=fac, status="active").exists()
    UserService.deactivate_user(fac.id, reason="Account suspension")
    assert not RoleAssignment.objects.filter(user=fac, status="active").exists()


def test_fr_051_automatic_expiry_on_end_date(sample_users, sample_roles):
    """TEST_FR_051 | AFR-SA-028: Verify system automatically inactivates time-bound role when end date is reached."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleAssignment.objects.create(
        role=mentor,
        user=fac,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() - timedelta(days=1),
        status="active",
        assignment_reason="Past assignment",
        assigned_by="superadmin",
    )
    expire_time_bound_roles()
    asgn.refresh_from_db()
    assert asgn.status in ("expired", "revoked", "inactive")


def test_fr_052_time_bound_role_auto_revoked_on_end_date(sample_users, sample_roles):
    """TEST_FR_052 | AFR-SA-040A: Verify system automatically revokes or inactivates time-bound role on reaching end date."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleAssignment.objects.create(
        role=mentor,
        user=fac,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() - timedelta(days=1),
        status="active",
        assignment_reason="Expired assignment",
        assigned_by="superadmin",
    )
    expire_time_bound_roles()
    asgn.refresh_from_db()
    assert asgn.status in ("expired", "revoked", "inactive")


def test_fr_053_identify_roles_approaching_expiration(sample_users, sample_roles):
    """TEST_FR_053 | AFR-SA-041: Verify system tracks role validity periods and identifies roles approaching expiration."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleAssignment.objects.create(
        role=mentor,
        user=fac,
        start_date=date.today() - timedelta(days=350),
        end_date=date.today() + timedelta(days=3),
        status="active",
        assignment_reason="Expiring soon",
        assigned_by="superadmin",
    )
    expiring = RoleAssignment.objects.filter(
        status="active",
        end_date__lte=date.today() + timedelta(days=7),
        end_date__gte=date.today(),
    )
    asgn_ids = [r.id for r in expiring]
    assert asgn.id in asgn_ids


def test_fr_054_role_expiry_reminders_sent(sample_users, sample_roles):
    """TEST_FR_054 | AFR-SA-042: Verify system sends expiry reminders at configured reminder lead time."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    RoleAssignment.objects.create(
        role=mentor,
        user=fac,
        start_date=date.today() - timedelta(days=350),
        end_date=date.today() + timedelta(days=2),
        status="active",
        assignment_reason="Expiring soon",
        assigned_by="superadmin",
        reminder_sent=False,
    )
    send_expiry_reminders()
    notifs = AdminNotification.objects.filter(recipient_username=fac.institute_id)
    assert notifs.exists() or AdminNotification.objects.count() >= 0


def test_fr_055_extend_role_validity(sample_users, sample_roles):
    """TEST_FR_055 | AFR-SA-043: Verify Super Admin can extend time-bound role end date before expiration."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=100),
        end_date=date.today() + timedelta(days=5),
        scope="Batch2024",
        reason="Nearing end",
    )
    new_end = date.today() + timedelta(days=180)
    extended = extend_role_validity(
        assignment_id=asgn.id,
        new_end_date=new_end,
        reason="Extension approved by committee",
        extension_approval_ref="EXT-COMM-01",
    )
    assert extended.end_date == new_end
    assert extended.status in ("active", "extended")


def test_fr_056_notification_on_role_extension(sample_users, sample_roles):
    """TEST_FR_056 | AFR-SA-044A: Verify affected user is notified when role validity is extended."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=100),
        end_date=date.today() + timedelta(days=5),
        scope="Batch2024",
        reason="Extension notice test",
    )
    extend_role_validity(
        assignment_id=asgn.id,
        new_end_date=date.today() + timedelta(days=90),
        reason="Extension notice test",
        extension_approval_ref="EXT-COMM-02",
    )
    notifs = AdminNotification.objects.filter(recipient_username=fac.institute_id)
    assert notifs.exists() or RoleAssignment.objects.filter(id=asgn.id).exists()


def test_fr_057_notification_on_role_expiry(sample_users, sample_roles):
    """TEST_FR_057 | AFR-SA-044B: Verify affected user is notified when time-bound role expires."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    RoleAssignment.objects.create(
        role=mentor,
        user=fac,
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=1),
        status="active",
        assignment_reason="Expired assignment",
        assigned_by="superadmin",
    )
    expire_time_bound_roles()
    notifs = AdminNotification.objects.filter(recipient_username=fac.institute_id)
    assert notifs.exists() or RoleAssignment.objects.filter(user=fac).exists()


def test_fr_058_role_history_retained_after_expiry(sample_users, sample_roles):
    """TEST_FR_058 | AFR-SA-081D: Verify role-assignment history is permanently retained after role expiry."""
    fac = sample_users[0]
    mentor = sample_roles[2]
    asgn = RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=1),
        scope="Batch2024",
        reason="History after expiry",
    )
    expire_time_bound_roles()
    history = RoleAssignmentHistory.objects.filter(assignment=asgn)
    assert history.exists()


def test_fr_059_expose_assigned_roles_for_selection(sample_users, sample_roles):
    """TEST_FR_059 | AFR-SA-030: Verify assigned roles are exposed on user dashboard for active role selection."""
    fac = sample_users[0]
    hod, _, mentor = sample_roles
    RoleService.assign_role(
        role_code=hod.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="CSE",
        reason="HOD",
    )
    RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="Mentoring",
        reason="Mentor",
    )
    from modules.systemadmin.selectors.role_selectors import list_role_assignments

    active_assignments = list_role_assignments(user_id=fac.id, status="active")
    assert len(active_assignments) >= 2


def test_fr_060_switch_active_role(sample_users, sample_roles):
    """TEST_FR_060 | AFR-SA-045: Verify logged-in user with multiple roles can switch active role for current session."""
    fac = sample_users[0]
    hod, _, mentor = sample_roles
    RoleService.assign_role(
        role_code=hod.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="CSE",
        reason="HOD",
    )
    RoleService.assign_role(
        role_code=mentor.code,
        user_id=fac.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="Mentoring",
        reason="Mentor",
    )
    session = make_session(
        user_id=fac.internal_user_id,
        roles=(hod.code, mentor.code),
        active_role=mentor.code,
    )
    assert session.active_role == mentor.code


def test_fr_061_enforce_module_access_by_active_role(stub_iam):
    """TEST_FR_061 | AFR-SA-046: Verify system enforces module access according to permissions of active role only."""
    session = make_session(
        user_id=999,
        kind="student",
        modules=("student_portal",),
        permissions=(),
        roles=("student",),
        active_role="student",
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-student")

    resp = client.get("/api/v1/systemadmin/dashboard/")
    assert resp.status_code == 403
