"""WF Test Suite 2: Role Validity Lifecycle (BW-SA-03..05, CW-SA-02)."""

from datetime import date, timedelta

import pytest

from modules.systemadmin.models import BasicUserProfile, RoleDefinition
from modules.systemadmin.services.role_service import RoleService
from modules.systemadmin.services.user_service import UserService


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


def ensure_role(code, name, is_singular=False, allowed_user_types=None, is_time_bound=True):
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

# --- BW-SA-03: Immediate Time-Bound Role Assignment to Expiry ---


def test_wf_005_immediate_role_assignment_to_expiry_path():
    """TEST_WF_005 | BW-SA-03: Verify immediate time-bound role assignment to automatic expiry path traversal."""
    u = ensure_test_user("WF_ROLE_005", "faculty")
    role = ensure_role("WF_IMM_EXP", "Immediate Expiry Role")

    # Step 1: Assign immediately effective role
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
    )
    assert a.status == "active"

    # Step 2: Simulate end_date passing and system expiry
    a.end_date = date.today() - timedelta(days=1)
    a.save()
    RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "expired"


# --- BW-SA-04: Future-Dated Role Assignment to Expiry ---


def test_wf_006_future_dated_role_assignment_lifecycle_path():
    """TEST_WF_006 | BW-SA-04: Verify future-dated role assignment lifecycle: scheduled -> active -> expired."""
    u = ensure_test_user("WF_ROLE_006", "faculty")
    role = ensure_role("WF_FUT_EXP", "Future Expiry Role")

    # Step 1: Assign with future start date -> scheduled
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=40),
    )
    assert a.status == "scheduled"

    # Step 2: System activation when start date reached
    a.start_date = date.today()
    a.save()
    RoleService.activate_scheduled_roles()
    a.refresh_from_db()
    assert a.status == "active"

    # Step 3: System expiry when end date reached
    a.end_date = date.today() - timedelta(days=1)
    a.save()
    RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "expired"


# --- BW-SA-05: Role Validity Extension — One Traversal ---


def test_wf_007_role_validity_extension_path():
    """TEST_WF_007 | BW-SA-05: Verify role validity extension workflow traversal: active -> extended -> expired."""
    u = ensure_test_user("WF_ROLE_007", "faculty")
    role = ensure_role("WF_EXT_EXP", "Extension Expiry Role")

    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() - timedelta(days=20),
        end_date=date.today() + timedelta(days=5),
    )
    assert a.status == "active"

    # Extension traversal
    ext = RoleService.extend_role_validity(
        assignment_id=a.id,
        new_end_date=date.today() + timedelta(days=60),
        extension_approval_ref="DIR-WF-EXT-2026",
        reason="Extended research term",
    )
    assert ext.status == "extended"
    assert ext.end_date == date.today() + timedelta(days=60)

    # System expiry when extended date passes
    ext.end_date = date.today() - timedelta(days=1)
    ext.save()
    RoleService.expire_time_bound_roles()
    ext.refresh_from_db()
    assert ext.status == "expired"


# --- CW-SA-02: Time-Bound Role Validity Lifecycle ---


def test_wf_008_cw_role_immediate_to_expiry_branch():
    """TEST_WF_008 | CW-SA-02: Verify composite role lifecycle branch A: immediate assignment progression to expiry."""
    u = ensure_test_user("WF_CW_008", "faculty")
    role = ensure_role("WF_CW_ROLE_A", "CW Role A")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
    )
    assert a.status == "active"
    a.end_date = date.today() - timedelta(days=1)
    a.save()
    RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "expired"


def test_wf_009_cw_role_scheduled_to_active_to_expiry_branch():
    """TEST_WF_009 | CW-SA-02: Verify composite role lifecycle branch B: future-dated assignment activation and expiry progression."""
    u = ensure_test_user("WF_CW_009", "faculty")
    role = ensure_role("WF_CW_ROLE_B", "CW Role B")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today() + timedelta(days=5),
        end_date=date.today() + timedelta(days=35),
    )
    assert a.status == "scheduled"
    a.start_date = date.today()
    a.save()
    RoleService.activate_scheduled_roles()
    a.refresh_from_db()
    assert a.status == "active"
    a.end_date = date.today() - timedelta(days=1)
    a.save()
    RoleService.expire_time_bound_roles()
    a.refresh_from_db()
    assert a.status == "expired"


def test_wf_010_cw_role_extension_branch():
    """TEST_WF_010 | CW-SA-02: Verify composite role lifecycle branch C: extension traversal prior to expiry."""
    u = ensure_test_user("WF_CW_010", "faculty")
    role = ensure_role("WF_CW_ROLE_C", "CW Role C")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=15),
    )
    ext = RoleService.extend_role_validity(
        assignment_id=a.id,
        new_end_date=date.today() + timedelta(days=45),
        extension_approval_ref="APPR-CW-010",
        reason="Term extension",
    )
    assert ext.status == "extended"
    assert ext.end_date == date.today() + timedelta(days=45)


def test_wf_011_cw_role_standard_revocation_branch():
    """TEST_WF_011 | CW-SA-02: Verify composite role lifecycle branch D: early standard revocation with notice."""
    u = ensure_test_user("WF_CW_011", "faculty")
    role = ensure_role("WF_CW_ROLE_D", "CW Role D")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
    )
    revoked = RoleService.revoke_role(
        assignment_id=a.id,
        reason="Scheduled reorganization",
        is_emergency=False,
        effective_date=date.today() + timedelta(days=2),
    )
    # CW-SA-02 / BR-SA-014: Standard revocation with future date remains active until effective date
    assert revoked.status == "active"


def test_wf_012_cw_role_emergency_revocation_branch():
    """TEST_WF_012 | CW-SA-02: Verify composite role lifecycle branch E: emergency revocation immediate traversal."""
    u = ensure_test_user("WF_CW_012", "faculty")
    role = ensure_role("WF_CW_ROLE_E", "CW Role E")
    a = RoleService.assign_role(
        user_id=u.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=90),
    )
    revoked = RoleService.revoke_role(
        assignment_id=a.id,
        reason="Immediate emergency revocation",
        is_emergency=True,
    )
    assert revoked.status == "revoked"


def test_wf_013_cw_role_reassignment_handover_branch():
    """TEST_WF_013 | CW-SA-02: Verify composite role lifecycle branch F: reassignment with task handover."""
    u1 = ensure_test_user("WF_CW_013_A", "faculty")
    u2 = ensure_test_user("WF_CW_013_B", "faculty")
    role = ensure_role("WF_CW_ROLE_F", "CW Role F", is_singular=True)
    a1 = RoleService.assign_role(
        user_id=u1.id,
        role_code=role.code,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=180),
    )
    a2 = RoleService.reassign_role(
        assignment_id=a1.id,
        new_user_id=u2.id,
        effective_date=date.today(),
        reason="Rotational reassignment",
        pending_task_disposition="transfer",
    )
    a1.refresh_from_db()
    assert a1.status == "reassigned"
    assert a2.status == "active"
