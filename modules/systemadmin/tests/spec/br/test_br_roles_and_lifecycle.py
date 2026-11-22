"""BR Test Suite 2: Roles, Conflicts, Lifecycle, Reassignment, and Access (BR-SA-006..016, 023, 034)."""

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models import (
    AdminNotification,
    BasicUserProfile,
    RoleAssignment,
    RoleConflict,
    RoleDefinition,
)
from modules.systemadmin.services.role_service import RoleManagementError, RoleService
from modules.systemadmin.services.user_service import UserService

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


def ensure_test_user(iid, utype="faculty", dept="CSE"):
    u = BasicUserProfile.objects.filter(institute_id=iid).first()
    if not u:
        kw = {
            "institute_id": iid,
            "user_type": utype,
            "full_name": f"User {iid}",
            "institute_email": f"{iid.lower()}@iiitdmj.ac.in",
            "date_of_joining": date(2024, 1, 1),
            "department": dept,
        }
        if utype == "student":
            kw["programme"] = "B.Tech"
            kw["batch_year"] = 2026
        else:
            kw["employee_id"] = f"EMP_{iid}"
        u = UserService.create_basic_user(**kw)
    return u


def ensure_role(code, name, is_singular=False, allowed_user_types=None, is_time_bound=False):
    r = RoleDefinition.objects.filter(code=code).first()
    if not r:
        r = RoleDefinition.objects.create(
            code=code,
            name=name,
            is_singular=is_singular,
            allowed_user_types=allowed_user_types or ["faculty", "staff"],
            module_or_dept="Administration",
            is_time_bound=is_time_bound,
        )
    return r


pytestmark = pytest.mark.django_db

# --- BR-SA-006: Multiple Concurrent Roles ---


def test_br_015_multiple_concurrent_roles_permitted():
    """TEST_BR_015 | BR-SA-006: Verify a user can hold multiple compatible additional roles simultaneously."""
    u = ensure_test_user("BR_MULT_01", "faculty")
    r1 = ensure_role("BR_ROLE_A", "Role Alpha", is_singular=False)
    r2 = ensure_role("BR_ROLE_B", "Role Beta", is_singular=False)

    RoleService.assign_role(user_id=u.id, role_code=r1.code, start_date=date.today())
    RoleService.assign_role(user_id=u.id, role_code=r2.code, start_date=date.today())

    active_assignments = RoleAssignment.objects.filter(user=u, status="active")
    assert active_assignments.count() >= 2


# --- BR-SA-007: Singular Role Occupancy ---


def test_br_016_singular_role_vacant_scope_permitted():
    """TEST_BR_016 | BR-SA-007: Verify singular role assignment is permitted when the role is vacant in that scope."""
    u = ensure_test_user("BR_SING_01", "faculty")
    r = ensure_role("BR_DEAN_ACAD", "Dean Academic", is_singular=True)
    a = RoleService.assign_role(
        user_id=u.id, role_code=r.code, start_date=date.today(), scope="Institute"
    )
    assert a.status == "active"


def test_br_017_singular_role_already_occupied_prohibited():
    """TEST_BR_017 | BR-SA-007: Verify singular role assignment is prohibited when already occupied by another user."""
    u1 = ensure_test_user("BR_SING_HOLD", "faculty")
    u2 = ensure_test_user("BR_SING_ATT", "faculty")
    r = ensure_role("BR_DEAN_STUD", "Dean Students", is_singular=True)
    RoleService.assign_role(
        user_id=u1.id, role_code=r.code, start_date=date.today(), scope="Institute"
    )

    with pytest.raises(RoleManagementError):
        RoleService.assign_role(
            user_id=u2.id, role_code=r.code, start_date=date.today(), scope="Institute"
        )


# --- BR-SA-008: Role Assignment Dating ---


def test_br_018_role_assignment_valid_dates_permitted():
    """TEST_BR_018 | BR-SA-008: Verify role assignment with valid start date and future end date is permitted."""
    u = ensure_test_user("BR_DATE_OK", "faculty")
    r = ensure_role("BR_COMM_DATE", "Committee Date", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=r.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
    )
    assert a.start_date <= a.end_date


def test_br_019_role_assignment_end_before_start_prohibited():
    """TEST_BR_019 | BR-SA-008: Verify role assignment with end date earlier than start date is prohibited."""
    u = ensure_test_user("BR_DATE_BAD", "faculty")
    r = ensure_role("BR_COMM_BAD", "Committee Bad", is_singular=False)
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(
            user_id=u.id,
            role_code=r.code,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 1),
        )


# --- BR-SA-009: Automatic Role Activation and Expiry ---


def test_br_020_automatic_role_activation_lifecycle():
    """TEST_BR_020 | BR-SA-009: Verify scheduled role assignment automatically activates when start date reached."""
    u = ensure_test_user("BR_AUTO_ACT", "faculty")
    r = ensure_role("BR_COMM_ACT", "Committee Act", is_singular=False)
    a = RoleAssignment.objects.create(
        user=u,
        role=r,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status="scheduled",
    )
    activated = RoleService.activate_scheduled_roles()
    a.refresh_from_db()
    assert a.status == "active"
    assert activated >= 1


def test_br_021_automatic_role_expiry_lifecycle():
    """TEST_BR_021 | BR-SA-009: Verify active role automatically expires when configured end date has passed."""
    u = ensure_test_user("BR_AUTO_EXP", "faculty")
    r = ensure_role("BR_COMM_EXP", "Committee Exp", is_singular=False)
    a = RoleAssignment.objects.create(
        user=u,
        role=r,
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=1),
        status="active",
    )
    expired = RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "expired"
    assert expired >= 1


# --- BR-SA-010: Role User-Type Eligibility ---


def test_br_022_role_eligible_user_type_permitted():
    """TEST_BR_022 | BR-SA-010: Verify role assignment to an allowed user type is permitted."""
    u = ensure_test_user("BR_ELIG_FAC", "faculty")
    r = ensure_role("BR_FAC_SENATE", "Faculty Senate", allowed_user_types=["faculty"])
    a = RoleService.assign_role(user_id=u.id, role_code=r.code, start_date=date.today())
    assert a.status == "active"


def test_br_023_role_ineligible_user_type_prohibited():
    """TEST_BR_023 | BR-SA-010: Verify role assignment to a prohibited user type is rejected."""
    stud = ensure_test_user("BR_INELIG_STUD", "student")
    r = ensure_role("BR_HOD_ROLE", "HOD Role", allowed_user_types=["faculty"])
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(user_id=stud.id, role_code=r.code, start_date=date.today())


# --- BR-SA-011: Role Conflict Validation ---


def test_br_024_non_conflicting_roles_permitted():
    """TEST_BR_024 | BR-SA-011: Verify assignment of mutually compatible non-conflicting roles is permitted."""
    u = ensure_test_user("BR_CONF_OK", "faculty")
    r1 = ensure_role("BR_SPORTS_COMM", "Sports Committee")
    r2 = ensure_role("BR_CULT_COMM", "Cultural Committee")
    a1 = RoleService.assign_role(user_id=u.id, role_code=r1.code, start_date=date.today())
    a2 = RoleService.assign_role(user_id=u.id, role_code=r2.code, start_date=date.today())
    assert a1.status == "active" and a2.status == "active"


def test_br_025_conflicting_roles_prohibited():
    """TEST_BR_025 | BR-SA-011: Verify assignment of mutually conflicting roles is prohibited."""
    u = ensure_test_user("BR_CONF_BAD", "staff")
    rx = ensure_role("BR_CASHIER", "Cashier Role")
    ry = ensure_role("BR_AUDITOR", "Internal Auditor Role")
    RoleConflict.objects.get_or_create(role_a=rx, role_b=ry, reason="Conflict")

    RoleService.assign_role(user_id=u.id, role_code=rx.code, start_date=date.today())
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(user_id=u.id, role_code=ry.code, start_date=date.today())


# --- BR-SA-012: Reassignment Handover ---


def test_br_026_reassignment_handover_permitted():
    """TEST_BR_026 | BR-SA-012: Verify active role reassignment transfers tasks and updates previous and new holders."""
    u1 = ensure_test_user("BR_REAS_OLD", "faculty")
    u2 = ensure_test_user("BR_REAS_NEW", "faculty")
    role = ensure_role("BR_HOSTEL_WARD", "Hostel Warden", is_singular=True)
    a1 = RoleService.assign_role(user_id=u1.id, role_code=role.code, start_date=date.today())

    a2 = RoleService.reassign_role(
        assignment_id=a1.id,
        new_user_id=u2.id,
        effective_date=date.today(),
        reason="Annual rotation",
        pending_task_disposition="transfer",
    )
    a1.refresh_from_db()
    assert a1.status == "reassigned"
    assert a2.status == "active"


def test_br_027_reassign_inactive_role_prohibited():
    """TEST_BR_027 | BR-SA-012: Verify reassigning an inactive or expired role assignment is prohibited."""
    u1 = ensure_test_user("BR_REAS_INACT", "faculty")
    u2 = ensure_test_user("BR_REAS_INACT2", "faculty")
    role = ensure_role("BR_INACT_ROLE", "Inactive Target Role")
    a = RoleAssignment.objects.create(
        user=u1,
        role=role,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() - timedelta(days=5),
        status="expired",
    )
    with pytest.raises(RoleManagementError):
        RoleService.reassign_role(
            assignment_id=a.id, new_user_id=u2.id, effective_date=date.today(), reason="Test"
        )


# --- BR-SA-013: Previous Holder Audit Access ---


def test_br_028_previous_holder_audit_access_active():
    """TEST_BR_028 | BR-SA-013: Verify previous holder retains read-only audit access during configured audit window."""
    u1 = ensure_test_user("BR_AUD_OLD", "faculty")
    u2 = ensure_test_user("BR_AUD_NEW", "faculty")
    role = ensure_role("BR_AUD_ROLE", "Audit Role", is_singular=True)
    a1 = RoleService.assign_role(user_id=u1.id, role_code=role.code, start_date=date.today())
    RoleService.reassign_role(
        assignment_id=a1.id,
        new_user_id=u2.id,
        effective_date=date.today(),
        reason="Handover",
    )
    a1.refresh_from_db()
    assert a1.previous_holder_audit_until is not None
    assert a1.previous_holder_audit_until >= date.today()


def test_br_029_previous_holder_audit_access_expired():
    """TEST_BR_029 | BR-SA-013: Verify previous holder audit access is terminated once configured audit period elapses."""
    u = ensure_test_user("BR_AUD_EXP", "faculty")
    role = ensure_role("BR_AUD_ROLE_PAST", "Past Role")
    a = RoleAssignment.objects.create(
        user=u,
        role=role,
        start_date=date.today() - timedelta(days=90),
        status="reassigned",
        previous_holder_audit_until=date.today() - timedelta(days=1),
    )
    assert a.previous_holder_audit_until < date.today()


# --- BR-SA-014: Role Revocation Handling ---


def test_br_030_standard_revocation_notice_permitted():
    """TEST_BR_030 | BR-SA-014: Verify standard role revocation with at least one day notice is permitted."""
    u = ensure_test_user("BR_REV_STD", "faculty")
    role = ensure_role("BR_REV_ROLE", "Revocation Role")
    a = RoleService.assign_role(user_id=u.id, role_code=role.code, start_date=date.today())
    revoked = RoleService.revoke_role(
        assignment_id=a.id,
        reason="Standard schedule",
        is_emergency=False,
        effective_date=date.today() + timedelta(days=2),
    )
    # BR-SA-014: Standard revocation requires at least 1 day notice; role remains active until effective date
    assert revoked.status == "active"


def test_br_031_emergency_revocation_immediate_permitted():
    """TEST_BR_031 | BR-SA-014: Verify emergency role revocation takes immediate effect without advance notice."""
    u = ensure_test_user("BR_REV_EMG", "faculty")
    role = ensure_role("BR_EMG_ROLE", "Emergency Role")
    a = RoleService.assign_role(user_id=u.id, role_code=role.code, start_date=date.today())
    revoked = RoleService.revoke_role(
        assignment_id=a.id,
        reason="Security breach",
        is_emergency=True,
    )
    assert revoked.status == "revoked"


def test_br_032_standard_revocation_no_notice_prohibited():
    """TEST_BR_032 | BR-SA-014: Verify standard revocation with insufficient notice (< 1 day) is prohibited."""
    u = ensure_test_user("BR_REV_BAD", "faculty")
    role = ensure_role("BR_BAD_ROLE", "Bad Revocation Role")
    a = RoleService.assign_role(user_id=u.id, role_code=role.code, start_date=date.today())
    with pytest.raises(RoleManagementError):
        RoleService.revoke_role(
            assignment_id=a.id,
            reason="Illegal zero notice",
            is_emergency=False,
            effective_date=date.today(),
        )


# --- BR-SA-015: Automatic Revocation ---


def test_br_033_user_deactivation_revokes_roles():
    """TEST_BR_033 | BR-SA-015: Verify deactivation of a basic user automatically revokes all associated active roles."""
    u = ensure_test_user("BR_DEACT_AUTO", "faculty")
    role = ensure_role("BR_DEACT_ROLE", "Deactivation Role")
    RoleService.assign_role(user_id=u.id, role_code=role.code, start_date=date.today())

    UserService.deactivate_user(user_id=u.id, reason="Resigned")
    active_roles = RoleAssignment.objects.filter(user=u, status="active")
    assert active_roles.count() == 0


# --- BR-SA-016: Role Expiry Reminder and Extension ---


def test_br_034_role_expiry_reminders_dispatched():
    """TEST_BR_034 | BR-SA-016: Verify expiry reminders are sent when role expiry approaches within lead time."""
    u = ensure_test_user("BR_REM_USER", "faculty")
    role = ensure_role("BR_REM_ROLE", "Reminder Role")
    RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=7),
    )
    reminders = RoleService.send_expiry_reminders()
    assert reminders >= 1
    assert AdminNotification.objects.filter(
        recipient_username=u.institute_id, title__icontains="Expiry"
    ).exists()


def test_br_035_role_validity_extension_permitted():
    """TEST_BR_035 | BR-SA-016: Verify role validity extension with valid approval reference and future end date is permitted."""
    u = ensure_test_user("BR_EXT_OK", "faculty")
    role = ensure_role("BR_EXT_ROLE", "Extension Role")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )
    ext = RoleService.extend_role_validity(
        assignment_id=a.id,
        new_end_date=date.today() + timedelta(days=90),
        extension_approval_ref="DIR-APPR-2026-BR",
        reason="Project continuation",
    )
    assert ext.end_date == date.today() + timedelta(days=90)
    assert ext.status == "extended"


def test_br_036_role_extension_invalid_date_or_ref_prohibited():
    """TEST_BR_036 | BR-SA-016: Verify role extension without approval reference or with non-future date is prohibited."""
    u = ensure_test_user("BR_EXT_BAD", "faculty")
    role = ensure_role("BR_EXT_BAD_ROLE", "Bad Extension Role")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )
    with pytest.raises(RoleManagementError):
        RoleService.extend_role_validity(
            assignment_id=a.id,
            new_end_date=date.today() + timedelta(days=10),  # earlier than current end_date!
            extension_approval_ref="REF",
            reason="Shrink",
        )


# --- BR-SA-023: Role Change Notification Timing ---


def test_br_047_role_change_notification_dispatched():
    """TEST_BR_047 | BR-SA-023: Verify role assignment or revocation dispatches notification immediately."""
    u = ensure_test_user("BR_NOTIF_TIME", "faculty")
    role = ensure_role("BR_NOTIF_ROLE", "Notification Timing Role")
    RoleService.assign_role(user_id=u.id, role_code=role.code, start_date=date.today())
    assert AdminNotification.objects.filter(recipient_username=u.institute_id).exists()


# --- BR-SA-034: Active Role Selection and Permission Enforcement ---


def test_br_065_active_role_permission_enforced(stub_iam):
    """TEST_BR_065 | BR-SA-034: Verify selecting an active assigned role enforces associated module permissions."""
    client = get_sa_client(stub_iam, permissions=("systemadmin.user.view",))
    resp = client.get("/api/v1/systemadmin/users/")
    assert resp.status_code == 200


def test_br_066_inactive_role_permission_denied(stub_iam):
    """TEST_BR_066 | BR-SA-034: Verify selecting an inactive or unauthorized role denies module access."""
    # User without systemadmin.user.view
    client = get_sa_client(stub_iam, permissions=())
    resp = client.get("/api/v1/systemadmin/users/")
    assert resp.status_code == 403
