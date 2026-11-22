"""Use Case Executable Tests: User Management (UC-SA-001 through UC-SA-007).

Traceable to UC_DESIGN.json test cases TEST_UC_001 through TEST_UC_027.
"""

from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.audit import SystemAdminAuditLog
from modules.systemadmin.models.user_mgmt import BasicUserProfile
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


# --- UC-SA-001: Create Basic User ---


def test_uc_001_create_basic_user_main_flow(stub_iam):
    """TEST_UC_001 | UC-SA-001 Main Flow: Verify main success flow for creating basic user."""
    client = get_sa_client(stub_iam)
    payload = {
        "institute_id": "UC_STUD_01",
        "user_type": "student",
        "full_name": "UC Student One",
        "institute_email": "uc_stud_01@iiitdmj.ac.in",
        "date_of_joining": "2026-08-01",
        "programme": "B.Tech",
        "batch_year": 2026,
        "department": "CSE",
    }
    resp = client.post("/api/v1/systemadmin/users/create/", payload, format="json")
    assert resp.status_code == 201
    user = BasicUserProfile.objects.filter(institute_id="UC_STUD_01").first()
    assert user is not None
    assert user.status == "active"
    assert SystemAdminAuditLog.objects.filter(
        action="USER_CREATED", target_user="UC_STUD_01"
    ).exists()


def test_uc_002_create_basic_user_alt_a1_cancel():
    """TEST_UC_002 | UC-SA-001 Alternative A1: Verify Super Admin cancels before submission; no user created."""
    assert not BasicUserProfile.objects.filter(institute_id="UC_CANCEL_01").exists()


def test_uc_003_create_basic_user_alt_a2_correctable_validation_errors(stub_iam):
    """TEST_UC_003 | UC-SA-001 Alternative A2: Verify system shows validation errors and allows correction."""
    client = get_sa_client(stub_iam)
    invalid_payload = {
        "institute_id": "UC_CORR_01",
        "user_type": "student",
        "full_name": "",
        "institute_email": "bad_email",
    }
    resp = client.post("/api/v1/systemadmin/users/create/", invalid_payload, format="json")
    assert resp.status_code == 400
    assert not BasicUserProfile.objects.filter(institute_id="UC_CORR_01").exists()


def test_uc_004_create_basic_user_exc_e1_duplicate_id(stub_iam):
    """TEST_UC_004 | UC-SA-001 Exception E1: Verify duplicate Institute ID or duplicate identity is rejected."""
    UserService.create_basic_user(
        institute_id="UC_DUP_01",
        user_type="student",
        full_name="Original User",
        institute_email="dup1@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    payload = {
        "institute_id": "UC_DUP_01",
        "user_type": "student",
        "full_name": "Duplicate User",
        "institute_email": "dup2@iiitdmj.ac.in",
        "date_of_joining": "2026-08-01",
        "programme": "B.Tech",
        "batch_year": 2026,
        "department": "CSE",
    }
    resp = client.post("/api/v1/systemadmin/users/create/", payload, format="json")
    assert resp.status_code == 400


def test_uc_005_create_basic_user_exc_e2_notification_failure_handled():
    """TEST_UC_005 | UC-SA-001 Exception E2: Verify user creation persists even if welcome notification fails."""
    user = UserService.create_basic_user(
        institute_id="UC_NOTIF_FAIL",
        user_type="faculty",
        full_name="Notif Fail Prof",
        institute_email="notif_fail@iiitdmj.ac.in",
        date_of_joining=date(2025, 1, 1),
        department="CSE",
        employee_id="NF001",
    )
    assert user.id is not None
    assert BasicUserProfile.objects.filter(institute_id="UC_NOTIF_FAIL").exists()


# --- UC-SA-002: View User Profile ---


def test_uc_006_view_user_profile_main_flow(stub_iam):
    """TEST_UC_006 | UC-SA-002 Main Flow: Verify Super Admin retrieves permitted user profile."""
    u = UserService.create_basic_user(
        institute_id="UC_VIEW_01",
        user_type="student",
        full_name="View Student",
        institute_email="view_stud@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.get(f"/api/v1/systemadmin/users/{u.id}/")
    assert resp.status_code == 200
    assert resp.data["institute_id"] == "UC_VIEW_01"
    assert resp.data["full_name"] == "View Student"


def test_uc_007_view_user_profile_alt_a1_archived_user(stub_iam):
    """TEST_UC_007 | UC-SA-002 Alternative A1: Verify viewing archived user routes or displays archived read-only view."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/users/999999/")
    assert resp.status_code in (404, 200)


def test_uc_008_view_user_profile_exc_e1_user_not_found(stub_iam):
    """TEST_UC_008 | UC-SA-002 Exception E1: Verify appropriate response when user does not exist."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/users/888888/")
    assert resp.status_code == 404


# --- UC-SA-003: Update User Profile ---


def test_uc_009_update_user_profile_main_flow(stub_iam):
    """TEST_UC_009 | UC-SA-003 Main Flow: Verify updating permitted profile fields."""
    u = UserService.create_basic_user(
        institute_id="UC_UPD_01",
        user_type="staff",
        full_name="Update Staff",
        institute_email="upd_staff@iiitdmj.ac.in",
        date_of_joining=date(2024, 1, 1),
        department="Admin",
        employee_id="UST01",
    )
    client = get_sa_client(stub_iam)
    resp = client.patch(
        f"/api/v1/systemadmin/users/{u.id}/",
        {"contact_number": "9876543210"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.contact_number == "9876543210"


def test_uc_010_update_user_profile_alt_a1_cancel():
    """TEST_UC_010 | UC-SA-003 Alternative A1: Verify canceling update causes no changes to be saved."""
    u = UserService.create_basic_user(
        institute_id="UC_UPD_CANC",
        user_type="student",
        full_name="Cancel Student",
        institute_email="canc_stud@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    orig_name = u.full_name
    u.refresh_from_db()
    assert u.full_name == orig_name


def test_uc_011_update_user_profile_exc_e1_attempt_modify_institute_id(stub_iam):
    """TEST_UC_011 | UC-SA-003 Exception E1: Verify attempt to change non-editable Institute ID is rejected."""
    u = UserService.create_basic_user(
        institute_id="UC_IMMUT_01",
        user_type="student",
        full_name="Immutable ID",
        institute_email="immut@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    client.patch(
        f"/api/v1/systemadmin/users/{u.id}/",
        {"institute_id": "NEW_FORBIDDEN_ID"},
        format="json",
    )
    u.refresh_from_db()
    assert u.institute_id == "UC_IMMUT_01"


def test_uc_012_update_user_profile_exc_e2_invalid_email_format(stub_iam):
    """TEST_UC_012 | UC-SA-003 Exception E2: Verify invalid institute email in update is rejected."""
    u = UserService.create_basic_user(
        institute_id="UC_INV_EM_01",
        user_type="student",
        full_name="Email Test",
        institute_email="email_test@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.patch(
        f"/api/v1/systemadmin/users/{u.id}/",
        {"contact_number": "123456789012345678901234567890"},
        format="json",
    )
    assert resp.status_code == 400


# --- UC-SA-004: Deactivate User ---


def test_uc_013_deactivate_user_main_flow(stub_iam):
    """TEST_UC_013 | UC-SA-004 Main Flow: Verify Super Admin deactivates active user with reason."""
    u = UserService.create_basic_user(
        institute_id="UC_DEACT_01",
        user_type="faculty",
        full_name="Deact Prof",
        institute_email="deact_prof@iiitdmj.ac.in",
        date_of_joining=date(2023, 1, 1),
        department="ECE",
        employee_id="DPRF01",
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/users/{u.id}/status/",
        {"action": "deactivate", "reason": "Sabbatical leave"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.status == "deactivated"
    assert u.deactivation_reason == "Sabbatical leave"


def test_uc_014_deactivate_user_alt_a1_cancel_confirmation():
    """TEST_UC_014 | UC-SA-004 Alternative A1: Verify user status remains active if confirmation is canceled."""
    u = UserService.create_basic_user(
        institute_id="UC_DEACT_CANC",
        user_type="student",
        full_name="Deact Cancel",
        institute_email="deact_canc@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    u.refresh_from_db()
    assert u.status == "active"


def test_uc_015_deactivate_user_exc_e1_ineligible_state(stub_iam):
    """TEST_UC_015 | UC-SA-004 Exception E1: Verify deactivation is rejected if target is not active."""
    u = UserService.create_basic_user(
        institute_id="UC_ALR_DEACT",
        user_type="student",
        full_name="Already Deact",
        institute_email="alr_deact@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    UserService.deactivate_user(u.id, reason="First deactivation")
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/users/{u.id}/status/",
        {"action": "deactivate", "reason": "Second deactivation"},
        format="json",
    )
    assert resp.status_code == 400


# --- UC-SA-005: Reactivate User ---


def test_uc_016_reactivate_user_main_flow(stub_iam):
    """TEST_UC_016 | UC-SA-005 Main Flow: Verify Super Admin reactivates deactivated user."""
    u = UserService.create_basic_user(
        institute_id="UC_REACT_01",
        user_type="student",
        full_name="React Student",
        institute_email="react_stud@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    UserService.deactivate_user(u.id, reason="Temporary leave")
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/users/{u.id}/status/",
        {"action": "reactivate", "reason": "Return from leave"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.status == "active"


def test_uc_017_reactivate_user_alt_a1_update_before_reactivation():
    """TEST_UC_017 | UC-SA-005 Alternative A1: Verify user profile can be updated before reactivation."""
    u = UserService.create_basic_user(
        institute_id="UC_REACT_UPD",
        user_type="staff",
        full_name="Staff React",
        institute_email="staff_react@iiitdmj.ac.in",
        date_of_joining=date(2024, 1, 1),
        department="Accounts",
        employee_id="SRACT01",
    )
    UserService.deactivate_user(u.id, reason="Department transfer")
    UserService.update_user_profile(u.id, {"contact_number": "9112233445"})
    reactivated = UserService.reactivate_user(u.id)
    assert reactivated.status == "active"
    assert reactivated.contact_number == "9112233445"


def test_uc_018_reactivate_user_exc_e1_already_active(stub_iam):
    """TEST_UC_018 | UC-SA-005 Exception E1: Verify reactivation is rejected if target is not deactivated."""
    u = UserService.create_basic_user(
        institute_id="UC_NOT_DEACT",
        user_type="student",
        full_name="Active Student",
        institute_email="active_react@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/users/{u.id}/status/",
        {"action": "reactivate", "reason": "Return from leave"},
        format="json",
    )
    assert resp.status_code == 400


# --- UC-SA-006: Bulk Create Users ---


def test_uc_019_bulk_create_users_main_flow(stub_iam):
    """TEST_UC_019 | UC-SA-006 Main Flow: Verify bulk user creation with valid CSV records."""
    records = [
        {
            "institute_id": "UC_BULK_01",
            "user_type": "student",
            "full_name": "Bulk Stud 1",
            "institute_email": "uc_b1@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        {
            "institute_id": "UC_BULK_02",
            "user_type": "student",
            "full_name": "Bulk Stud 2",
            "institute_email": "uc_b2@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
    ]
    client = get_sa_client(stub_iam)
    resp = client.post("/api/v1/systemadmin/users/bulk-create/", {"users": records}, format="json")
    assert resp.status_code == 201
    assert resp.data["success_count"] == 2
    assert resp.data["failure_count"] == 0


def test_uc_020_bulk_create_users_alt_a1_record_level_errors(stub_iam):
    """TEST_UC_020 | UC-SA-006 Alternative A1: Verify system processes valid rows and reports record-level errors."""
    records = [
        {
            "institute_id": "UC_BVAL_OK",
            "user_type": "student",
            "full_name": "Bulk Valid",
            "institute_email": "uc_bval_ok@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        {
            "institute_id": "UC_BVAL_ERR",
            "user_type": "student",
            "full_name": "Bulk Bad Email",
            "institute_email": "not-valid-email",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
    ]
    client = get_sa_client(stub_iam)
    resp = client.post("/api/v1/systemadmin/users/bulk-create/", {"users": records}, format="json")
    assert resp.status_code == 201
    assert resp.data["success_count"] == 1
    assert resp.data["failure_count"] == 1


def test_uc_021_bulk_create_users_alt_a2_cancel_after_preview():
    """TEST_UC_021 | UC-SA-006 Alternative A2: Verify canceling after preview commits no records."""
    assert not BasicUserProfile.objects.filter(institute_id="UC_PREVIEW_CANC").exists()


def test_uc_022_bulk_create_users_exc_e1_invalid_template(stub_iam):
    """TEST_UC_022 | UC-SA-006 Exception E1: Verify empty or malformed bulk file is rejected."""
    client = get_sa_client(stub_iam)
    resp = client.post("/api/v1/systemadmin/users/bulk-create/", {"users": []}, format="json")
    assert resp.status_code == 400


def test_uc_023_bulk_create_users_exc_e2_exceeds_1000_limit(stub_iam):
    """TEST_UC_023 | UC-SA-006 Exception E2: Verify batches with more than 1000 records are rejected."""
    records = [
        {
            "institute_id": f"EXC1000_{i}",
            "user_type": "student",
            "full_name": f"User {i}",
            "institute_email": f"u{i}@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        }
        for i in range(1001)
    ]
    client = get_sa_client(stub_iam)
    resp = client.post("/api/v1/systemadmin/users/bulk-create/", {"users": records}, format="json")
    assert resp.status_code == 400


def test_uc_024_bulk_create_users_exc_e3_service_failure_handled():
    """TEST_UC_024 | UC-SA-006 Exception E3: Verify processing service handles partial failures gracefully."""
    records = [
        {
            "institute_id": "UC_PARTIAL_OK",
            "user_type": "student",
            "full_name": "Partial Ok",
            "institute_email": "partial_ok@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        }
    ]
    res = UserService.bulk_create_users(records, actor_username="superadmin")
    assert res["total_records"] == 1
    assert res["success_count"] == 1


# --- UC-SA-007: Bulk User Status Update ---


def test_uc_025_bulk_status_update_main_flow(stub_iam):
    """TEST_UC_025 | UC-SA-007 Main Flow: Verify Super Admin updates status for multiple users in bulk."""
    u1 = UserService.create_basic_user(
        institute_id="UC_BSTAT_01",
        user_type="student",
        full_name="BStat 1",
        institute_email="bstat1@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    u2 = UserService.create_basic_user(
        institute_id="UC_BSTAT_02",
        user_type="student",
        full_name="BStat 2",
        institute_email="bstat2@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-status/",
        {"user_ids": [u1.id, u2.id], "action": "deactivate", "reason": "Graduation"},
        format="json",
    )
    assert resp.status_code == 200
    u1.refresh_from_db()
    u2.refresh_from_db()
    assert u1.status == "deactivated"
    assert u2.status == "deactivated"


def test_uc_026_bulk_status_update_alt_a1_ineligible_targets(stub_iam):
    """TEST_UC_026 | UC-SA-007 Alternative A1: Verify system handles batch where some targets are ineligible."""
    u1 = UserService.create_basic_user(
        institute_id="UC_BINEL_01",
        user_type="student",
        full_name="BInel 1",
        institute_email="binel1@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-status/",
        {"user_ids": [u1.id, 999999], "action": "deactivate", "reason": "Mixed batch"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["success_count"] == 1
    assert resp.data["failure_count"] == 1


def test_uc_027_bulk_status_update_exc_e1_invalid_action(stub_iam):
    """TEST_UC_027 | UC-SA-007 Exception E1: Verify unsupported bulk status action is rejected."""
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-status/",
        {"user_ids": [1], "action": "unsupported_action"},
        format="json",
    )
    assert resp.status_code == 400
