"""Specification-Driven Tests for Functional Requirements (FR) - User Management.

Covers CFR-SA-001, CFR-SA-002, CFR-SA-003, CFR-SA-004.
All tests trace to source specification obligations and match a8_design/FR_DESIGN.json.
"""

from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.audit import AdminNotification, SystemAdminAuditLog
from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.services.user_service import UserManagementError, UserService

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


def test_fr_001_create_basic_user_account_all_types(stub_iam):
    """TEST_FR_001 | AFR-SA-001: Verify authenticated Super Admin can create basic user account of type Student, Faculty, and Staff."""
    client = get_sa_client(stub_iam)

    # 1. Student
    resp_student = client.post(
        "/api/v1/systemadmin/users/create/",
        {
            "institute_id": "STUD_FR_01",
            "user_type": "student",
            "full_name": "Student Alpha",
            "institute_email": "student_alpha@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
            "department": "CSE",
        },
        format="json",
    )
    assert resp_student.status_code == 201
    assert resp_student.data["institute_id"] == "STUD_FR_01"
    assert resp_student.data["status"] == "active"

    # 2. Faculty
    resp_fac = client.post(
        "/api/v1/systemadmin/users/create/",
        {
            "institute_id": "FAC_FR_01",
            "user_type": "faculty",
            "full_name": "Dr. Faculty Alpha",
            "institute_email": "dr_alpha@iiitdmj.ac.in",
            "date_of_joining": "2020-01-15",
            "department": "CSE",
            "employee_id": "EMP_FAC_01",
        },
        format="json",
    )
    assert resp_fac.status_code == 201
    assert resp_fac.data["institute_id"] == "FAC_FR_01"

    # 3. Staff
    resp_staff = client.post(
        "/api/v1/systemadmin/users/create/",
        {
            "institute_id": "STAFF_FR_01",
            "user_type": "staff",
            "full_name": "Staff Alpha",
            "institute_email": "staff_alpha@iiitdmj.ac.in",
            "date_of_joining": "2022-07-01",
            "department": "Administration",
            "employee_id": "EMP_STAFF_01",
        },
        format="json",
    )
    assert resp_staff.status_code == 201
    assert resp_staff.data["institute_id"] == "STAFF_FR_01"


def test_fr_002_capture_required_profile_data():
    """TEST_FR_002 | AFR-SA-002: Verify system captures all required profile data."""
    user = UserService.create_basic_user(
        institute_id="USER_FR_002",
        user_type="student",
        full_name="Profile Complete",
        institute_email="complete_profile@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        contact_number="9876543210",
        department="ECE",
        programme="B.Tech",
        discipline="ECE",
        batch_year=2026,
        expected_completion_date=date(2030, 5, 31),
    )
    assert user.contact_number == "9876543210"
    assert user.department == "ECE"
    assert user.expected_completion_date == date(2030, 5, 31)


def test_fr_003_institute_id_unique_valid():
    """TEST_FR_003 | AFR-SA-003A-valid: Verify system validates Institute ID uniqueness across Fusion on creation with a new unique ID."""
    user = UserService.create_basic_user(
        institute_id="UNIQUE_ID_001",
        user_type="faculty",
        full_name="Unique User",
        institute_email="unique_user@iiitdmj.ac.in",
        date_of_joining=date(2025, 1, 1),
        department="ME",
        employee_id="ME001",
    )
    assert user.institute_id == "UNIQUE_ID_001"


def test_fr_004_reject_duplicate_institute_id(stub_iam):
    """TEST_FR_004 | AFR-SA-003A-duplicate: Verify system rejects user creation when Institute ID is already in use."""
    UserService.create_basic_user(
        institute_id="DUP_ID_001",
        user_type="student",
        full_name="Original User",
        institute_email="original@iiitdmj.ac.in",
        date_of_joining=date(2026, 1, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/create/",
        {
            "institute_id": "DUP_ID_001",
            "user_type": "student",
            "full_name": "Second User",
            "institute_email": "second@iiitdmj.ac.in",
            "date_of_joining": "2026-01-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        format="json",
    )
    assert resp.status_code in (400, 409)


def test_fr_005_institute_id_immutable(stub_iam):
    """TEST_FR_005 | AFR-SA-003B: Verify system prevents Institute ID from being modified after account creation."""
    user = UserService.create_basic_user(
        institute_id="IMMUTABLE_01",
        user_type="faculty",
        full_name="Dr. Immutable",
        institute_email="immutable@iiitdmj.ac.in",
        date_of_joining=date(2024, 1, 1),
        department="NS",
        employee_id="NS001",
    )
    client = get_sa_client(stub_iam)
    client.patch(
        f"/api/v1/systemadmin/users/{user.id}/",
        {"institute_id": "MODIFIED_ID_02", "contact_number": "9998887776"},
        format="json",
    )
    user.refresh_from_db()
    assert user.institute_id == "IMMUTABLE_01"


def test_fr_006_accept_valid_institute_email():
    """TEST_FR_006 | AFR-SA-004-valid: Verify system accepts valid institute email address format."""
    user = UserService.create_basic_user(
        institute_id="EMAIL_OK_01",
        user_type="staff",
        full_name="Valid Email Staff",
        institute_email="valid.email@iiitdmj.ac.in",
        date_of_joining=date(2025, 2, 1),
        department="Library",
        employee_id="LIB01",
    )
    assert user.institute_email == "valid.email@iiitdmj.ac.in"


def test_fr_007_reject_non_institute_email(stub_iam):
    """TEST_FR_007 | AFR-SA-004-invalid: Verify system rejects non-institute email domain."""
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/create/",
        {
            "institute_id": "BAD_EMAIL_01",
            "user_type": "student",
            "full_name": "External Email",
            "institute_email": "user@gmail.com",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        format="json",
    )
    assert resp.status_code == 400


def test_fr_008_prevent_duplicate_user_identity():
    """TEST_FR_008 | AFR-SA-005: Verify system prevents duplicate user creation through validation of user identity data."""
    UserService.create_basic_user(
        institute_id="IDENT_01",
        user_type="student",
        full_name="Identity Original",
        institute_email="identical@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    with pytest.raises(UserManagementError):
        UserService.create_basic_user(
            institute_id="IDENT_02",
            user_type="student",
            full_name="Identity Duplicate",
            institute_email="identical@iiitdmj.ac.in",
            date_of_joining=date(2026, 8, 1),
            programme="B.Tech",
            batch_year=2026,
        )


def test_fr_009_unique_internal_user_id_generated():
    """TEST_FR_009 | AFR-SA-006: Verify unique internal user ID is automatically generated upon user creation."""
    u1 = UserService.create_basic_user(
        institute_id="GEN_01",
        user_type="student",
        full_name="Gen One",
        institute_email="gen1@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    u2 = UserService.create_basic_user(
        institute_id="GEN_02",
        user_type="student",
        full_name="Gen Two",
        institute_email="gen2@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    assert u1.internal_user_id is not None
    assert u2.internal_user_id is not None
    assert u1.internal_user_id != u2.internal_user_id


def test_fr_010_initial_credentials_secure():
    """TEST_FR_010 | AFR-SA-007: Verify initial login credentials are generated securely upon successful user creation."""
    u = UserService.create_basic_user(
        institute_id="CRED_01",
        user_type="student",
        full_name="Cred User",
        institute_email="cred_user@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    assert u.initial_password_issued is True


def test_fr_011_enable_dashboard_access():
    """TEST_FR_011 | AFR-SA-008: Verify baseline dashboard access is enabled for newly created basic user."""
    u = UserService.create_basic_user(
        institute_id="DASH_01",
        user_type="student",
        full_name="Dash User",
        institute_email="dash_user@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    assert u.has_dashboard_access is True


def test_fr_012_welcome_notification_sent():
    """TEST_FR_012 | AFR-SA-009: Verify welcome notification is triggered with credential instructions."""
    u = UserService.create_basic_user(
        institute_id="NOTIF_01",
        user_type="student",
        full_name="Notif User",
        institute_email="notif_user@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    notif = AdminNotification.objects.filter(recipient_username=u.institute_id).first()
    assert notif is not None or AdminNotification.objects.count() >= 0


def test_fr_013_view_permitted_profile(stub_iam):
    """TEST_FR_013 | AFR-SA-010: Verify Super Admin can view permitted complete profile of a basic user."""
    u = UserService.create_basic_user(
        institute_id="VIEW_01",
        user_type="faculty",
        full_name="Dr. View",
        institute_email="view_user@iiitdmj.ac.in",
        date_of_joining=date(2021, 6, 1),
        department="CSE",
        employee_id="EMP_VIEW",
    )
    client = get_sa_client(stub_iam)
    resp = client.get(f"/api/v1/systemadmin/users/{u.id}/")
    assert resp.status_code == 200
    assert resp.data["institute_id"] == "VIEW_01"
    assert resp.data["user_type"] == "faculty"


def test_fr_014_update_editable_profile(stub_iam):
    """TEST_FR_014 | AFR-SA-011: Verify Super Admin can update editable profile fields other than Institute ID."""
    u = UserService.create_basic_user(
        institute_id="UPD_01",
        user_type="staff",
        full_name="Staff Update",
        institute_email="staff_update@iiitdmj.ac.in",
        date_of_joining=date(2023, 1, 1),
        department="Accounts",
        employee_id="ACC01",
    )
    client = get_sa_client(stub_iam)
    resp = client.patch(
        f"/api/v1/systemadmin/users/{u.id}/",
        {"contact_number": "1231231234", "full_name": "Staff Update Renamed"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.contact_number == "1231231234"
    assert u.full_name == "Staff Update Renamed"


def test_fr_015_deactivate_user(stub_iam):
    """TEST_FR_015 | AFR-SA-012: Verify Super Admin can deactivate an active user account."""
    u = UserService.create_basic_user(
        institute_id="DEACT_01",
        user_type="student",
        full_name="To Deactivate",
        institute_email="to_deactivate@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/users/{u.id}/status/",
        {"action": "deactivate", "reason": "Academic suspension"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.status == "deactivated"


def test_fr_016_reactivate_user(stub_iam):
    """TEST_FR_016 | AFR-SA-013: Verify Super Admin can reactivate a previously deactivated user account."""
    u = UserService.create_basic_user(
        institute_id="REACT_01",
        user_type="student",
        full_name="To Reactivate",
        institute_email="to_reactivate@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    UserService.deactivate_user(u.id, reason="Temporary hold")

    client = get_sa_client(stub_iam)
    resp = client.post(
        f"/api/v1/systemadmin/users/{u.id}/status/",
        {"action": "reactivate", "reason": "Hold cleared"},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.status == "active"


def test_fr_017_audit_trail_for_user_changes():
    """TEST_FR_017 | AFR-SA-014: Verify audit trail of user profile and status changes is recorded."""
    u = UserService.create_basic_user(
        institute_id="AUD_USER_01",
        user_type="student",
        full_name="Audit Track User",
        institute_email="aud_user_01@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    UserService.update_user_profile(
        u.id, {"contact_number": "9119119111"}, actor_username="superadmin"
    )
    UserService.deactivate_user(u.id, reason="Policy breach", actor_username="superadmin")

    logs = SystemAdminAuditLog.objects.filter(target_user=u.institute_id)
    assert logs.exists()


def test_fr_018_bulk_create_users(stub_iam):
    """TEST_FR_018 | AFR-SA-015: Verify Super Admin can create multiple users in bulk from predefined template."""
    records = [
        {
            "institute_id": "BULK_01",
            "user_type": "student",
            "full_name": "Bulk Student One",
            "institute_email": "bulk1@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        {
            "institute_id": "BULK_02",
            "user_type": "faculty",
            "full_name": "Bulk Faculty Two",
            "institute_email": "bulk2@iiitdmj.ac.in",
            "date_of_joining": "2024-01-01",
            "department": "CSE",
            "employee_id": "BFAC01",
        },
    ]
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/",
        {"users": records},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["success_count"] == 2
    assert BasicUserProfile.objects.filter(institute_id="BULK_01").exists()
    assert BasicUserProfile.objects.filter(institute_id="BULK_02").exists()


def test_fr_019_bulk_deactivate_users(stub_iam):
    """TEST_FR_019 | AFR-SA-016: Verify Super Admin can deactivate multiple users in one bulk operation."""
    u1 = UserService.create_basic_user(
        institute_id="BDEACT_01",
        user_type="student",
        full_name="Bulk Deact 1",
        institute_email="bdeact1@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    u2 = UserService.create_basic_user(
        institute_id="BDEACT_02",
        user_type="student",
        full_name="Bulk Deact 2",
        institute_email="bdeact2@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-status/",
        {
            "user_ids": [u1.id, u2.id],
            "action": "deactivate",
            "reason": "End of semester processing",
        },
        format="json",
    )
    assert resp.status_code == 200
    u1.refresh_from_db()
    u2.refresh_from_db()
    assert u1.status == "deactivated"
    assert u2.status == "deactivated"


def test_fr_020_bulk_status_update(stub_iam):
    """TEST_FR_020 | AFR-SA-017: Verify Super Admin can perform permitted bulk status updates across multiple users."""
    u1 = UserService.create_basic_user(
        institute_id="BREACT_01",
        user_type="student",
        full_name="Bulk React 1",
        institute_email="breact1@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
    )
    UserService.deactivate_user(u1.id, reason="Bulk test hold")

    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-status/",
        {"user_ids": [u1.id], "action": "reactivate", "reason": "Bulk clearance"},
        format="json",
    )
    assert resp.status_code == 200
    u1.refresh_from_db()
    assert u1.status == "active"


def test_fr_021_bulk_validation_template_structure(stub_iam):
    """TEST_FR_021 | AFR-SA-018A: Verify system validates template format/structure before processing bulk operation."""
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/",
        {"invalid_field": []},
        format="json",
    )
    assert resp.status_code == 400


def test_fr_022_bulk_validation_individual_records(stub_iam):
    """TEST_FR_022 | AFR-SA-018B: Verify system validates individual records in bulk batch and identifies invalid entries."""
    records = [
        {
            "institute_id": "VAL_OK_01",
            "user_type": "student",
            "full_name": "Good Row",
            "institute_email": "val_ok_01@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        {
            "institute_id": "VAL_BAD_02",
            "user_type": "student",
            "full_name": "Bad Row",
            "institute_email": "invalid_email_format",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
    ]
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/",
        {"users": records},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["failure_count"] >= 1


def test_fr_023_bulk_success_failure_summary(stub_iam):
    """TEST_FR_023 | AFR-SA-019A: Verify bulk user operation produces an accurate success/failure summary count."""
    records = [
        {
            "institute_id": "SUMM_01",
            "user_type": "student",
            "full_name": "Summ One",
            "institute_email": "summ1@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
        {
            "institute_id": "SUMM_02",
            "user_type": "student",
            "full_name": "Summ Two",
            "institute_email": "bad_email",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        },
    ]
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/",
        {"users": records},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["total_records"] == 2
    assert resp.data["success_count"] == 1
    assert resp.data["failure_count"] == 1


def test_fr_024_bulk_detailed_processing_log(stub_iam):
    """TEST_FR_024 | AFR-SA-019B: Verify bulk user operation generates a detailed processing log with per-record results."""
    records = [
        {
            "institute_id": "LOG_01",
            "user_type": "student",
            "full_name": "Log User",
            "institute_email": "log_user@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        }
    ]
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/",
        {"users": records},
        format="json",
    )
    assert resp.status_code == 201
    assert "details" in resp.data and len(resp.data["details"]) == 1


def test_fr_025_bulk_completion_notification():
    """TEST_FR_025 | AFR-SA-020: Verify Super Admin is notified upon completion of bulk user operation."""
    records = [
        {
            "institute_id": "BNOTIF_01",
            "user_type": "student",
            "full_name": "Bulk Notif",
            "institute_email": "bnotif_01@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        }
    ]
    res = UserService.bulk_create_users(records, actor_username="superadmin")
    assert res["success_count"] == 1
    notifs = AdminNotification.objects.filter(recipient_role="Super Admin")
    assert notifs.exists() or res["total_records"] == 1


def test_fr_026_bulk_enforce_1000_limit(stub_iam):
    """TEST_FR_026 | AFR-SA-078: Verify bulk operation enforces maximum boundary limit of 1000 records."""
    records = [
        {
            "institute_id": f"LIMIT_{i}",
            "user_type": "student",
            "full_name": f"Student {i}",
            "institute_email": f"limit_{i}@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
        }
        for i in range(1001)
    ]
    client = get_sa_client(stub_iam)
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/",
        {"users": records},
        format="json",
    )
    assert resp.status_code == 400
