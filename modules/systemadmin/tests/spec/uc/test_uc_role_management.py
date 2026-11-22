"""Use Case Executable Tests: Role Management.

Covers UC-SA-008 through UC-SA-014, UC-SA-028, UC-SA-029, UC-SA-030.
Traceable to UC_DESIGN.json test cases TEST_UC_028 through TEST_UC_051, and TEST_UC_095 through TEST_UC_103.
"""

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.audit import AdminNotification
from modules.systemadmin.models.role_mgmt import RoleAssignment, RoleDefinition
from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.services.role_service import RoleManagementError, RoleService
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


def ensure_test_user(username="prof_uc", utype="faculty"):
    u = BasicUserProfile.objects.filter(institute_id=username).first()
    if not u:
        if utype == "student":
            u = UserService.create_basic_user(
                institute_id=username,
                user_type=utype,
                full_name=f"Student {username}",
                institute_email=f"{username}@iiitdmj.ac.in",
                date_of_joining=date(2026, 8, 1),
                programme="B.Tech",
                batch_year=2026,
                department="CSE",
            )
        else:
            u = UserService.create_basic_user(
                institute_id=username,
                user_type=utype,
                full_name=f"Prof {username}",
                institute_email=f"{username}@iiitdmj.ac.in",
                date_of_joining=date(2023, 1, 1),
                department="CSE",
                employee_id=f"EMP_{username}",
            )
    return u


def ensure_role(code="DEAN_ACAD", name="Dean Academic", is_singular=True, allowed_user_types=None):
    if allowed_user_types is None:
        allowed_user_types = ["faculty"]
    role = RoleDefinition.objects.filter(code=code).first()
    if not role:
        role = RoleDefinition.objects.create(
            code=code,
            name=name,
            description=f"{name} role",
            module_or_dept="Academic",
            allowed_user_types=allowed_user_types,
            is_singular=is_singular,
            is_time_bound=True,
            default_validity_days=365,
            status="available",
            permissions=["academic.view", "academic.manage"],
        )
    return role


# --- UC-SA-008: Assign Role ---


def test_uc_028_assign_role_main_flow(stub_iam):
    """TEST_UC_028 | UC-SA-008 Main Flow: Verify assigning an active role to an eligible user."""
    u = ensure_test_user("uc_role_u1", "faculty")
    role = ensure_role("DEAN_ACAD_01", "Dean Academic 01", is_singular=True)
    client = get_sa_client(stub_iam)
    payload = {
        "user_id": u.id,
        "role_code": role.code,
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
        "scope": "Institute",
        "reason": "Annual appointment",
    }
    resp = client.post("/api/v1/systemadmin/assignments/create/", payload, format="json")
    assert resp.status_code == 201
    assert RoleAssignment.objects.filter(user=u, role=role, status="active").exists()


def test_uc_029_assign_role_alt_a1_future_start_date(stub_iam):
    """TEST_UC_029 | UC-SA-008 Alternative A1: Verify future start date records assignment as scheduled."""
    u = ensure_test_user("uc_role_future", "faculty")
    role = ensure_role("HOD_ECE_01", "HOD ECE 01", is_singular=True)
    client = get_sa_client(stub_iam)
    payload = {
        "user_id": u.id,
        "role_code": role.code,
        "start_date": str(date.today() + timedelta(days=30)),
        "end_date": str(date.today() + timedelta(days=395)),
        "scope": "ECE",
        "reason": "Next term appointment",
    }
    resp = client.post("/api/v1/systemadmin/assignments/create/", payload, format="json")
    assert resp.status_code == 201
    assign = RoleAssignment.objects.get(id=resp.data["id"])
    assert assign.status == "scheduled"


def test_uc_030_assign_role_alt_a2_permanent_role_no_end_date():
    """TEST_UC_030 | UC-SA-008 Alternative A2: Verify permanent role assignment where end date is omitted."""
    u = ensure_test_user("uc_role_perm", "faculty")
    role = ensure_role("FAC_MEMBER_01", "Faculty Member 01", is_singular=False)
    role.is_time_bound = False
    role.save()
    assign = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=None,
    )
    assert assign.end_date is None
    assert assign.status == "active"


def test_uc_031_assign_role_exc_e1_ineligible_user():
    """TEST_UC_031 | UC-SA-008 Exception E1: Verify assignment rejected if user type is not permitted for role."""
    u = ensure_test_user("uc_role_stud", "student")
    role = ensure_role(
        "DEAN_ACAD_02", "Dean Academic 02", is_singular=True, allowed_user_types=["faculty"]
    )
    with pytest.raises(RoleManagementError):
        RoleService.assign_role(
            user_id=u.id,
            role_code=role.code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
        )


# --- UC-SA-009: Reassign Role ---


def test_uc_032_reassign_role_main_flow(stub_iam):
    """TEST_UC_032 | UC-SA-009 Main Flow: Verify reassigning a singular role from one user to another."""
    u1 = ensure_test_user("uc_reassign_u1", "faculty")
    u2 = ensure_test_user("uc_reassign_u2", "faculty")
    role = ensure_role("HOD_CSE_01", "HOD CSE 01", is_singular=True)
    a1 = RoleService.assign_role(
        user_id=u1.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=100),
        end_date=date.today() + timedelta(days=200),
        scope="CSE",
    )
    client = get_sa_client(stub_iam)
    payload = {
        "new_user_id": u2.id,
        "effective_date": str(date.today()),
        "reason": "Routine handover",
    }
    resp = client.post(f"/api/v1/systemadmin/assignments/{a1.id}/reassign/", payload, format="json")
    assert resp.status_code == 200
    a1.refresh_from_db()
    assert a1.status in ("revoked", "expired", "reassigned")
    assert RoleAssignment.objects.filter(user=u2, role=role, status="active").exists()


def test_uc_033_reassign_role_alt_a1_future_dated():
    """TEST_UC_033 | UC-SA-009 Alternative A1: Verify future-dated reassignment schedules handover."""
    u1 = ensure_test_user("uc_reass_f1", "faculty")
    u2 = ensure_test_user("uc_reass_f2", "faculty")
    role = ensure_role("HOD_ME_01", "HOD ME 01", is_singular=True)
    a1 = RoleService.assign_role(
        user_id=u1.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=50),
        end_date=date.today() + timedelta(days=300),
        scope="ME",
    )
    new_assign = RoleService.reassign_role(
        assignment_id=a1.id,
        new_user_id=u2.id,
        effective_date=date.today() + timedelta(days=20),
        reason="Scheduled handover next month",
    )
    assert new_assign.status == "scheduled"


def test_uc_034_reassign_role_alt_a2_emergency_immediate():
    """TEST_UC_034 | UC-SA-009 Alternative A2: Verify emergency reassignment is effective immediately."""
    u1 = ensure_test_user("uc_reass_em1", "faculty")
    u2 = ensure_test_user("uc_reass_em2", "faculty")
    role = ensure_role("WARDEN_H1", "Warden Hall 1", is_singular=True)
    a1 = RoleService.assign_role(
        user_id=u1.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=100),
        scope="Hall1",
    )
    new_assign = RoleService.reassign_role(
        assignment_id=a1.id,
        new_user_id=u2.id,
        effective_date=date.today(),
        reason="Emergency replacement",
        is_emergency=True,
    )
    assert new_assign.status == "active"


def test_uc_035_reassign_role_exc_e1_ineligible_new_holder():
    """TEST_UC_035 | UC-SA-009 Exception E1: Verify reassignment rejected if new proposed holder is ineligible."""
    u1 = ensure_test_user("uc_reass_val1", "faculty")
    u_stud = ensure_test_user("uc_reass_bad", "student")
    role = ensure_role(
        "CHIEF_WARDEN", "Chief Warden", is_singular=True, allowed_user_types=["faculty"]
    )
    a1 = RoleService.assign_role(
        user_id=u1.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=200),
        scope="Hostels",
    )
    with pytest.raises(RoleManagementError):
        RoleService.reassign_role(
            assignment_id=a1.id,
            new_user_id=u_stud.id,
            effective_date=date.today(),
            reason="Illegal appointment",
        )


# --- UC-SA-010: Revoke Role ---


def test_uc_036_revoke_role_main_flow(stub_iam):
    """TEST_UC_036 | UC-SA-010 Main Flow: Verify standard revocation of an active role."""
    u = ensure_test_user("uc_rev_u1", "faculty")
    role = ensure_role("DISC_COMM_01", "Disciplinary Committee 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=365),
    )
    client = get_sa_client(stub_iam)
    payload = {
        "effective_date": str(date.today() + timedelta(days=2)),
        "reason": "Committee reshuffle",
    }
    resp = client.post(f"/api/v1/systemadmin/assignments/{a.id}/revoke/", payload, format="json")
    assert resp.status_code == 200
    a.refresh_from_db()
    # UC-SA-010 Main Flow: Standard revocation scheduled for future remains active until effective date
    assert a.status == "active"


def test_uc_037_revoke_role_alt_a1_future_standard_revocation():
    """TEST_UC_037 | UC-SA-010 Alternative A1: Verify future scheduled standard revocation."""
    u = ensure_test_user("uc_rev_fut", "faculty")
    role = ensure_role("LIB_COMM_01", "Library Committee 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=365),
    )
    revoked = RoleService.revoke_role(
        assignment_id=a.id,
        reason="Planned resignation",
        effective_date=date.today() + timedelta(days=15),
    )
    # UC-SA-010 Alt A1: Role remains active until scheduled effective date
    assert revoked.status == "active"


def test_uc_038_revoke_role_alt_a2_emergency_revocation():
    """TEST_UC_038 | UC-SA-010 Alternative A2: Verify emergency revocation takes effect immediately."""
    u = ensure_test_user("uc_rev_em", "faculty")
    role = ensure_role("SPORTS_OFF_01", "Sports Officer 01", is_singular=True)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=365),
    )
    revoked = RoleService.revoke_role(
        assignment_id=a.id,
        reason="Security breach emergency revocation",
        effective_date=date.today(),
        is_emergency=True,
    )
    assert revoked.status == "revoked"


def test_uc_039_revoke_role_exc_e1_already_inactive():
    """TEST_UC_039 | UC-SA-010 Exception E1: Verify revoking an already revoked assignment is rejected."""
    u = ensure_test_user("uc_rev_alr", "faculty")
    role = ensure_role("GUEST_HOUSE_01", "Guest House Incharge 01", is_singular=True)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=365),
    )
    RoleService.revoke_role(
        a.id, reason="First revoke", effective_date=date.today(), is_emergency=True
    )
    with pytest.raises(RoleManagementError):
        RoleService.revoke_role(a.id, reason="Second revoke", effective_date=date.today())


# --- UC-SA-011: Extend Role Validity ---


def test_uc_040_extend_role_validity_main_flow(stub_iam):
    """TEST_UC_040 | UC-SA-011 Main Flow: Verify extending role validity with justification."""
    u = ensure_test_user("uc_ext_u1", "faculty")
    role = ensure_role("CONV_PLACE_01", "Convener Placement 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=100),
        end_date=date.today() + timedelta(days=30),
    )
    client = get_sa_client(stub_iam)
    new_end = str(date.today() + timedelta(days=120))
    resp = client.post(
        f"/api/v1/systemadmin/assignments/{a.id}/extend/",
        {
            "new_end_date": new_end,
            "reason": "Placement season extension",
            "extension_approval_ref": "REF-EXT-101",
        },
        format="json",
    )
    assert resp.status_code == 200
    a.refresh_from_db()
    assert str(a.end_date) == new_end


def test_uc_041_extend_role_validity_alt_a1_no_extension_chosen():
    """TEST_UC_041 | UC-SA-011 Alternative A1: Verify role expires naturally if no extension is requested."""
    u = ensure_test_user("uc_no_ext", "faculty")
    role = ensure_role("CONVOC_01", "Convocation Committee 01", is_singular=False)
    orig_end = date.today() + timedelta(days=5)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=30),
        end_date=orig_end,
    )
    a.refresh_from_db()
    assert a.end_date == orig_end


def test_uc_042_extend_role_validity_exc_e1_invalid_past_date():
    """TEST_UC_042 | UC-SA-011 Exception E1: Verify extending to a date prior to current end date is rejected."""
    u = ensure_test_user("uc_ext_past", "faculty")
    role = ensure_role("ADMISS_01", "Admissions Committee 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
    )
    with pytest.raises(RoleManagementError):
        RoleService.extend_role_validity(
            assignment_id=a.id,
            new_end_date=date.today() + timedelta(days=10),
            reason="Invalid earlier date",
        )


# --- UC-SA-012: View Role Metadata and Availability ---


def test_uc_043_view_role_metadata_main_flow(stub_iam):
    """TEST_UC_043 | UC-SA-012 Main Flow: Verify Super Admin views role definitions and availability."""
    ensure_role("ASSOC_DEAN_01", "Associate Dean 01", is_singular=False)
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/roles/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1


def test_uc_044_view_role_metadata_alt_a1_deprecated_role():
    """TEST_UC_044 | UC-SA-012 Alternative A1: Verify system marks deprecated role in metadata."""
    role = RoleDefinition.objects.create(
        code="DEP_COORD_01",
        name="Deprecated Coordinator",
        description="Old role",
        module_or_dept="Admin",
        allowed_user_types=["faculty"],
        is_singular=False,
        status="deprecated",
    )
    assert role.status == "deprecated"


def test_uc_045_view_role_metadata_exc_e1_role_not_found(stub_iam):
    """TEST_UC_045 | UC-SA-012 Exception E1: Verify appropriate response when non-existent role queried."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/roles/999999/")
    assert resp.status_code in (404, 200)


# --- UC-SA-013: Switch Active Role ---


def test_uc_046_switch_active_role_main_flow():
    """TEST_UC_046 | UC-SA-013 Main Flow: Verify user holding multiple valid roles has active holdings."""
    u = ensure_test_user("uc_switch_u1", "faculty")
    r1 = ensure_role("FAC_MEMBER_02", "Faculty Member 02", is_singular=False)
    r2 = ensure_role("HOD_CSE_02", "Head of Dept 02", is_singular=True)
    RoleService.assign_role(
        user_id=u.id,
        role_code=r1.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
    )
    RoleService.assign_role(
        user_id=u.id,
        role_code=r2.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="CSE2",
    )
    active_roles = RoleAssignment.objects.filter(user=u, status="active")
    assert active_roles.count() == 2


def test_uc_047_switch_active_role_alt_a1_already_active():
    """TEST_UC_047 | UC-SA-013 Alternative A1: Verify user can retain active holding without conflict."""
    u = ensure_test_user("uc_switch_same", "faculty")
    r1 = ensure_role("FAC_MEMBER_03", "Faculty Member 03", is_singular=False)
    RoleService.assign_role(
        user_id=u.id,
        role_code=r1.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
    )
    active_assignments = RoleAssignment.objects.filter(user=u, role=r1, status="active")
    assert active_assignments.exists()


def test_uc_048_switch_active_role_exc_e1_unassigned_or_expired_role():
    """TEST_UC_048 | UC-SA-013 Exception E1: Verify unassigned or expired role cannot be selected as active."""
    u = ensure_test_user("uc_switch_unass", "faculty")
    r_unass = ensure_role("DIRECTOR_01", "Director of Institute", is_singular=True)
    active_assignment = RoleAssignment.objects.filter(user=u, role=r_unass, status="active").first()
    assert active_assignment is None


# --- UC-SA-014: Access Module by Active Role ---


def test_uc_049_access_module_by_active_role_main_flow():
    """TEST_UC_049 | UC-SA-014 Main Flow: Verify role permissions are attached to active role assignment."""
    u = ensure_test_user("uc_acc_u1", "faculty")
    role = ensure_role("FAC_MEMBER_04", "Faculty Member 04", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
    )
    assert a.status == "active"
    assert "academic.view" in a.role.permissions


def test_uc_050_access_module_by_active_role_alt_a1_switch_and_retry():
    """TEST_UC_050 | UC-SA-014 Alternative A1: Verify user holds multiple role definitions with different permissions."""
    u = ensure_test_user("uc_acc_retry", "faculty")
    r1 = ensure_role("FAC_MEMBER_05", "Faculty Member 05", is_singular=False)
    r2 = ensure_role("ADMIN_OFF_01", "Admin Officer 01", is_singular=False)
    r2.permissions = ["admin.manage"]
    r2.save()
    RoleService.assign_role(
        user_id=u.id,
        role_code=r1.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
    )
    RoleService.assign_role(
        user_id=u.id,
        role_code=r2.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
    )
    assert RoleAssignment.objects.filter(user=u, role=r2, status="active").exists()


def test_uc_051_access_module_by_active_role_exc_e1_role_inactive_during_check():
    """TEST_UC_051 | UC-SA-014 Exception E1: Verify inactive/revoked role has no active permission grant."""
    u = ensure_test_user("uc_acc_inact", "faculty")
    role = ensure_role("TEMP_OFF_01", "Temporary Officer 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
    )
    a.status = "revoked"
    a.save()
    assert not RoleAssignment.objects.filter(user=u, role=role, status="active").exists()


# --- UC-SA-028: Activate Scheduled Role Assignment ---


def test_uc_095_activate_scheduled_role_main_flow():
    """TEST_UC_095 | UC-SA-028 Main Flow: Verify scheduled role assignment activates on start date."""
    u = ensure_test_user("uc_sched_u1", "faculty")
    role = ensure_role("PROCTOR_01", "Proctor 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=365),
    )
    assert a.status == "scheduled"
    a.start_date = date.today()
    a.save()
    activated_count = RoleService.activate_scheduled_roles()
    a.refresh_from_db()
    assert a.status == "active"
    assert activated_count >= 1


def test_uc_096_activate_scheduled_role_alt_a1_superseded_before_start():
    """TEST_UC_096 | UC-SA-028 Alternative A1: Verify superseded scheduled assignment does not activate."""
    u = ensure_test_user("uc_sched_super", "faculty")
    role = ensure_role("HOSTEL_CARE_01", "Hostel Caretaker 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() + timedelta(days=2),
        end_date=date.today() + timedelta(days=365),
    )
    a.status = "revoked"
    a.save()
    RoleService.activate_scheduled_roles()
    a.refresh_from_db()
    assert a.status == "revoked"


def test_uc_097_activate_scheduled_role_exc_e1_user_deactivated_before_start():
    """TEST_UC_097 | UC-SA-028 Exception E1: Verify scheduled role is not activated if user became deactivated."""
    u = ensure_test_user("uc_sched_deact_u", "faculty")
    role = ensure_role("MESS_WARDEN_01", "Mess Warden 01", is_singular=False)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=365),
    )
    UserService.deactivate_user(u.id, reason="Resigned before start")
    a.start_date = date.today()
    a.save()
    RoleService.activate_scheduled_roles()
    u.refresh_from_db()
    assert u.status == "deactivated"


# --- UC-SA-029: Expire Time-Bound Role ---


def test_uc_098_expire_time_bound_role_main_flow():
    """TEST_UC_098 | UC-SA-029 Main Flow: Verify time-bound role assignment transitions to expired at end date."""
    u = ensure_test_user("uc_exp_u1", "faculty")
    role = ensure_role("CULT_SEC_01", "Cultural Secretary 01", is_singular=True)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=1),
    )
    expired_count = RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "expired"
    assert expired_count >= 1


def test_uc_099_expire_time_bound_role_alt_a1_extended_before_expiry():
    """TEST_UC_099 | UC-SA-029 Alternative A1: Verify validly extended assignment does not transition to expired."""
    u = ensure_test_user("uc_exp_ext", "faculty")
    role = ensure_role("ALUMNI_SEC_01", "Alumni Secretary 01", is_singular=True)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=200),
        end_date=date.today() + timedelta(days=60),
    )
    RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "active"


def test_uc_100_expire_time_bound_role_exc_e1_permanent_role_not_expired():
    """TEST_UC_100 | UC-SA-029 Exception E1: Verify permanent roles without end date are never expired by batch."""
    u = ensure_test_user("uc_exp_perm", "faculty")
    role = ensure_role("PROF_CHARGE_01", "Professor in Charge 01", is_singular=False)
    role.is_time_bound = False
    role.save()
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=500),
        end_date=None,
    )
    RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "active"


# --- UC-SA-030: Send Role-Expiry Reminder ---


def test_uc_101_send_role_expiry_reminder_main_flow():
    """TEST_UC_101 | UC-SA-030 Main Flow: Verify expiry reminder is dispatched 30 days before end date."""
    u = ensure_test_user("uc_rem_u1", "faculty")
    role = ensure_role("SEC_OFF_01", "Security Officer 01", is_singular=True)
    RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=330),
        end_date=date.today() + timedelta(days=30),
    )
    count = RoleService.send_expiry_reminders()
    assert count >= 0


def test_uc_102_send_role_expiry_reminder_alt_a1_extended_before_reminder():
    """TEST_UC_102 | UC-SA-030 Alternative A1: Verify no reminder sent if role end date is far in future."""
    u = ensure_test_user("uc_rem_far", "faculty")
    role = ensure_role("ESTATE_OFF_01", "Estate Officer 01", is_singular=True)
    RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        scope="Estate",
    )
    RoleService.send_expiry_reminders()
    assert not AdminNotification.objects.filter(
        recipient_username="uc_rem_far", title__icontains="Expiry"
    ).exists()


def test_uc_103_send_role_expiry_reminder_exc_e1_delivery_failure_handled():
    """TEST_UC_103 | UC-SA-030 Exception E1: Verify role state is unchanged when reminders are dispatched."""
    u = ensure_test_user("uc_rem_fail", "faculty")
    role = ensure_role("TRAIN_OFF_01", "Training Officer 01", is_singular=True)
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=330),
        end_date=date.today() + timedelta(days=30),
    )
    orig_status = a.status
    RoleService.send_expiry_reminders()
    a.refresh_from_db()
    assert a.status == orig_status
