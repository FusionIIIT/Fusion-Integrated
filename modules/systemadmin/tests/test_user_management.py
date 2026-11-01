"""Tests for User Management Service and Business Rules."""
import pytest
from datetime import date
from django.utils import timezone

from modules.systemadmin.models.user_mgmt import BasicUserProfile, UserStatusHistory
from modules.systemadmin.models.audit import SystemAdminAuditLog
from modules.systemadmin.services.user_service import UserService, UserManagementError

pytestmark = pytest.mark.django_db


def test_create_valid_student():
    """Verify Student creation with mandatory academic attributes (CFR-SA-001, BR-SA-003)."""
    user = UserService.create_basic_user(
        institute_id="2024CS999",
        user_type="student",
        full_name="Aarav Sharma",
        institute_email="aarav.2024cs999@iiitdmj.ac.in",
        date_of_joining=date(2024, 8, 1),
        department="Computer Science and Engineering",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2024,
        contact_number="+91-9876500001",
        actor_username="test_admin",
    )
    assert user.id is not None
    assert user.institute_id == "2024CS999"
    assert user.status == "active"
    assert user.internal_user_id > 10000

    # Verify audit log was produced
    audit = SystemAdminAuditLog.objects.filter(target_user="2024CS999", action="USER_CREATE").first()
    assert audit is not None
    assert audit.result == "SUCCESS"


def test_create_valid_faculty():
    """Verify Faculty creation with employee_id and department (CFR-SA-001, BR-SA-003)."""
    user = UserService.create_basic_user(
        institute_id="FAC099",
        user_type="faculty",
        full_name="Dr. Vikram Sen",
        institute_email="vikram@iiitdmj.ac.in",
        date_of_joining=date(2021, 6, 15),
        department="Mechanical Engineering",
        employee_id="EMP-ME-099",
        actor_username="test_admin",
    )
    assert user.id is not None
    assert user.user_type == "faculty"
    assert user.employee_id == "EMP-ME-099"


def test_enforce_institute_id_uniqueness():
    """Verify duplicate institute_id is strictly rejected (BR-SA-001)."""
    UserService.create_basic_user(
        institute_id="2024CS101",
        user_type="student",
        full_name="Student One",
        institute_email="s1@iiitdmj.ac.in",
        date_of_joining=date(2024, 8, 1),
        department="CSE",
        programme="B.Tech",
        batch_year=2024,
    )
    with pytest.raises(UserManagementError) as exc_info:
        UserService.create_basic_user(
            institute_id="2024CS101",
            user_type="student",
            full_name="Student Duplicate",
            institute_email="sdup@iiitdmj.ac.in",
            date_of_joining=date(2024, 8, 1),
            department="CSE",
            programme="B.Tech",
            batch_year=2024,
        )
    assert "already exists" in str(exc_info.value)
    assert exc_info.value.code == "duplicate_institute_id"


def test_enforce_institute_email_format():
    """Verify email must belong to @*iiitdmj.ac.in domain (BR-SA-002)."""
    with pytest.raises(UserManagementError) as exc_info:
        UserService.create_basic_user(
            institute_id="2024CS102",
            user_type="student",
            full_name="Student Invalid Email",
            institute_email="student@gmail.com",
            date_of_joining=date(2024, 8, 1),
            department="CSE",
            programme="B.Tech",
            batch_year=2024,
        )
    assert "Must end with '@iiitdmj.ac.in'" in str(exc_info.value) or exc_info.value.code == "invalid_institute_email"


def test_enforce_student_required_data():
    """Verify missing programme or batch_year for student is rejected (BR-SA-003)."""
    with pytest.raises(UserManagementError) as exc_info:
        UserService.create_basic_user(
            institute_id="2024CS103",
            user_type="student",
            full_name="Student No Programme",
            institute_email="noprog@iiitdmj.ac.in",
            date_of_joining=date(2024, 8, 1),
            department="CSE",
            programme="",
            batch_year=2024,
        )
    assert "Missing required fields" in str(exc_info.value) or "programme" in str(exc_info.value)


def test_update_user_immutable_fields():
    """Verify institute_id and institute_email cannot be modified (BR-SA-001)."""
    user = UserService.create_basic_user(
        institute_id="STF005",
        user_type="staff",
        full_name="Ramesh Chandra",
        institute_email="ramesh@iiitdmj.ac.in",
        date_of_joining=date(2022, 1, 1),
        department="Administration",
        employee_id="EMP-STF-005",
    )

    with pytest.raises(UserManagementError) as exc_info:
        UserService.update_user_profile(
            user_id=user.id,
            updates={"institute_id": "NEW_ID"},
            actor_username="test_admin",
        )
    assert "immutable" in str(exc_info.value)

    # Valid profile update
    updated = UserService.update_user_profile(
        user_id=user.id,
        updates={"contact_number": "+91-9999988888"},
        actor_username="test_admin",
    )
    assert updated.contact_number == "+91-9999988888"


def test_deactivation_and_reactivation_cycle():
    """Verify deactivation and reactivation state transitions and status history (CFR-SA-003, CFR-SA-004)."""
    user = UserService.create_basic_user(
        institute_id="STF006",
        user_type="staff",
        full_name="Suresh Kumar",
        institute_email="suresh@iiitdmj.ac.in",
        date_of_joining=date(2022, 1, 1),
        department="Finance",
        employee_id="EMP-STF-006",
    )
    assert user.status == "active"

    # Deactivate
    deactivated = UserService.deactivate_user(
        user_id=user.id,
        reason="Extended medical leave",
        actor_username="test_admin",
    )
    assert deactivated.status == "deactivated"
    assert deactivated.deactivation_reason == "Extended medical leave"
    assert deactivated.deactivated_at is not None

    # Verify history
    history = UserStatusHistory.objects.filter(user=user).first()
    assert history.from_status == "active"
    assert history.to_status == "deactivated"
    assert history.reason == "Extended medical leave"

    # Reactivate
    reactivated = UserService.reactivate_user(
        user_id=user.id,
        reason="Returned from medical leave",
        actor_username="test_admin",
    )
    assert reactivated.status == "active"
    assert reactivated.deactivated_at is None


def test_bulk_create_users_within_limit():
    """Verify bulk user creation processes records accurately within limit (BR-SA-030)."""
    records = [
        {
            "institute_id": f"2024CSB{i:03d}",
            "user_type": "student",
            "full_name": f"Bulk Student {i}",
            "institute_email": f"bulk{i}@iiitdmj.ac.in",
            "date_of_joining": "2024-08-01",
            "department": "Computer Science and Engineering",
            "programme": "B.Tech",
            "batch_year": 2024,
        }
        for i in range(1, 6)
    ]
    summary = UserService.bulk_create_users(
        user_records=records,
        actor_username="test_admin",
    )
    assert summary["total_records"] == 5
    assert summary["success_count"] == 5
    assert summary["failure_count"] == 0
    assert BasicUserProfile.objects.filter(institute_id__startswith="2024CSB").count() == 5


def test_bulk_create_users_exceeds_limit():
    """Verify bulk operation hard cap of 1000 records (BR-SA-030)."""
    records = [{"dummy": i} for i in range(1001)]
    with pytest.raises(UserManagementError) as exc_info:
        UserService.bulk_create_users(
            user_records=records,
            actor_username="test_admin",
        )
    assert "exceeds maximum allowable limit" in str(exc_info.value)
