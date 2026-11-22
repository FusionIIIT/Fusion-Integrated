"""BR Test Suite 1: Identity, Email, User Types, and Bulk Limits (BR-SA-001..003, 030)."""

from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models import BasicUserProfile
from modules.systemadmin.services.user_service import UserManagementError, UserService

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


pytestmark = pytest.mark.django_db

# --- BR-SA-001: Institute Identity Uniqueness and Immutability ---


def test_br_001_institute_id_uniqueness_permitted(stub_iam):
    """TEST_BR_001 | BR-SA-001: Verify creation of a basic user with a unique Institute ID is permitted."""
    client = get_sa_client(stub_iam)
    payload = {
        "institute_id": "BR_USER_001",
        "user_type": "student",
        "full_name": "BR Student One",
        "institute_email": "br_user_001@iiitdmj.ac.in",
        "date_of_joining": "2026-08-01",
        "programme": "B.Tech",
        "batch_year": 2026,
        "department": "CSE",
    }
    resp = client.post("/api/v1/systemadmin/users/create/", payload, format="json")
    assert resp.status_code == 201
    assert BasicUserProfile.objects.filter(institute_id="BR_USER_001").exists()


def test_br_002_duplicate_institute_id_prohibited(stub_iam):
    """TEST_BR_002 | BR-SA-001: Verify creation of a user with a duplicate Institute ID is prohibited."""
    UserService.create_basic_user(
        institute_id="BR_USER_DUP",
        user_type="student",
        full_name="Duplicate Original",
        institute_email="br_dup_orig@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
        department="CSE",
    )
    client = get_sa_client(stub_iam)
    payload = {
        "institute_id": "BR_USER_DUP",
        "user_type": "student",
        "full_name": "Duplicate Second",
        "institute_email": "br_dup_second@iiitdmj.ac.in",
        "date_of_joining": "2026-08-01",
        "programme": "B.Tech",
        "batch_year": 2026,
        "department": "CSE",
    }
    resp = client.post("/api/v1/systemadmin/users/create/", payload, format="json")
    assert resp.status_code == 400


def test_br_003_institute_id_immutability_prohibited(stub_iam):
    """TEST_BR_003 | BR-SA-001: Verify Institute ID immutability prohibits modification after user creation."""
    u = UserService.create_basic_user(
        institute_id="BR_IMMUTABLE_01",
        user_type="faculty",
        full_name="Immutable Faculty",
        institute_email="br_immutable@iiitdmj.ac.in",
        date_of_joining=date(2024, 7, 1),
        employee_id="BR_FAC_01",
        department="ECE",
    )
    client = get_sa_client(stub_iam)
    # Attempting to alter institute_id via update API
    resp = client.put(
        f"/api/v1/systemadmin/users/{u.id}/",
        {"institute_id": "BR_MODIFIED_ID", "full_name": "Changed Name"},
        format="json",
    )
    # BR-SA-001: Attempting to alter Institute ID must be explicitly rejected
    assert resp.status_code == 400


# --- BR-SA-002: Institute Email Validation ---


def test_br_004_valid_institute_email_permitted(stub_iam):
    """TEST_BR_004 | BR-SA-002: Verify user creation with a valid institute domain email is permitted."""
    user = UserService.create_basic_user(
        institute_id="BR_EMAIL_OK",
        user_type="staff",
        full_name="Staff Valid Email",
        institute_email="br_staff_valid@iiitdmj.ac.in",
        date_of_joining=date(2025, 1, 1),
        employee_id="STF_BR_01",
        department="Admin",
    )
    assert user.institute_email == "br_staff_valid@iiitdmj.ac.in"


def test_br_005_invalid_email_domain_prohibited(stub_iam):
    """TEST_BR_005 | BR-SA-002: Verify user creation with a non-institute domain email is prohibited."""
    with pytest.raises(UserManagementError):
        UserService.create_basic_user(
            institute_id="BR_EMAIL_BAD",
            user_type="student",
            full_name="Bad Email Student",
            institute_email="bad_user@external-domain.com",
            date_of_joining=date(2026, 8, 1),
            programme="B.Tech",
            batch_year=2026,
            department="ME",
        )


# --- BR-SA-003: User-Type Required Data ---


def test_br_006_complete_student_and_faculty_data_permitted():
    """TEST_BR_006 | BR-SA-003: Verify student creation with required programme/batch and faculty with employee_id are permitted."""
    s = UserService.create_basic_user(
        institute_id="BR_DATA_STUD",
        user_type="student",
        full_name="Complete Student",
        institute_email="br_datastud@iiitdmj.ac.in",
        date_of_joining=date(2026, 8, 1),
        programme="B.Tech",
        batch_year=2026,
        department="CSE",
    )
    assert s.programme == "B.Tech" and s.batch_year == 2026
    f = UserService.create_basic_user(
        institute_id="BR_DATA_FAC",
        user_type="faculty",
        full_name="Complete Faculty",
        institute_email="br_datafac@iiitdmj.ac.in",
        date_of_joining=date(2023, 1, 1),
        employee_id="FAC_COMPLETE_01",
        department="Design",
    )
    assert f.employee_id == "FAC_COMPLETE_01" and f.department == "Design"


def test_br_007_student_missing_program_or_batch_prohibited():
    """TEST_BR_007 | BR-SA-003: Verify student creation missing required programme or batch is prohibited."""
    with pytest.raises(UserManagementError):
        UserService.create_basic_user(
            institute_id="BR_MISS_BATCH",
            user_type="student",
            full_name="Missing Batch",
            institute_email="br_missbatch@iiitdmj.ac.in",
            date_of_joining=date(2026, 8, 1),
            programme="B.Tech",
            batch_year=None,
            department="CSE",
        )


def test_br_008_faculty_missing_employee_id_prohibited():
    """TEST_BR_008 | BR-SA-003: Verify faculty creation missing required employee ID is prohibited."""
    with pytest.raises(UserManagementError):
        UserService.create_basic_user(
            institute_id="BR_MISS_EMPID",
            user_type="faculty",
            full_name="Missing EmpID",
            institute_email="br_missempid@iiitdmj.ac.in",
            date_of_joining=date(2024, 1, 1),
            employee_id="",
            department="CSE",
        )


# --- BR-SA-030: Bulk Operation Limit ---


def test_br_059_bulk_operation_within_limit_permitted(stub_iam):
    """TEST_BR_059 | BR-SA-030: Verify bulk user operation within maximum threshold (<= 1000 records) is permitted."""
    client = get_sa_client(stub_iam)
    users_payload = [
        {
            "institute_id": f"BR_BULK_OK_{i}",
            "user_type": "student",
            "full_name": f"Bulk Student {i}",
            "institute_email": f"br_bulk_ok_{i}@iiitdmj.ac.in",
            "date_of_joining": "2026-08-01",
            "programme": "B.Tech",
            "batch_year": 2026,
            "department": "CSE",
        }
        for i in range(3)
    ]
    resp = client.post(
        "/api/v1/systemadmin/users/bulk-create/", {"users": users_payload}, format="json"
    )
    assert resp.status_code == 201
    assert resp.data["success_count"] == 3


def test_br_060_bulk_operation_exceeding_1000_prohibited():
    """TEST_BR_060 | BR-SA-030: Verify bulk operation exceeding maximum threshold (> 1000 records) is prohibited."""
    oversized = [{"institute_id": f"EXCEED_{i}"} for i in range(1001)]
    with pytest.raises(UserManagementError):
        UserService.bulk_create_users(user_records=oversized, actor_username="superadmin")
