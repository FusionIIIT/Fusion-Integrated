"""Tests for Role Management Service and Business Rules."""
import pytest
from datetime import date, timedelta
from django.utils import timezone

from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.models.role_mgmt import RoleDefinition, RoleConflict, RoleAssignment
from modules.systemadmin.models.audit import SystemAdminAuditLog
from modules.systemadmin.services.user_service import UserService
from modules.systemadmin.services.role_service import RoleService, RoleManagementError

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_data():
    faculty1 = UserService.create_basic_user(
        institute_id="FAC_T1",
        user_type="faculty",
        full_name="Dr. Anil Kapoor",
        institute_email="anil@iiitdmj.ac.in",
        date_of_joining=date(2020, 1, 1),
        department="Computer Science and Engineering",
        employee_id="EMP-T1",
    )
    faculty2 = UserService.create_basic_user(
        institute_id="FAC_T2",
        user_type="faculty",
        full_name="Dr. Bharti Singh",
        institute_email="bharti@iiitdmj.ac.in",
        date_of_joining=date(2020, 1, 1),
        department="Computer Science and Engineering",
        employee_id="EMP-T2",
    )
    student1 = UserService.create_basic_user(
        institute_id="STU_T1",
        user_type="student",
        full_name="Chetan Bhagat",
        institute_email="chetan@iiitdmj.ac.in",
        date_of_joining=date(2024, 8, 1),
        department="Computer Science and Engineering",
        programme="B.Tech",
        batch_year=2024,
    )
    role_hod = RoleDefinition.objects.create(
        code="TEST_HOD",
        name="Test Head of Department",
        description="HOD test role",
        module_or_dept="Computer Science and Engineering",
        allowed_user_types=["faculty"],
        is_singular=True,
        is_time_bound=True,
        default_validity_days=730,
    )
    role_dean = RoleDefinition.objects.create(
        code="TEST_DEAN",
        name="Test Dean Academic",
        description="Dean test role",
        module_or_dept="Academic Office",
        allowed_user_types=["faculty"],
        is_singular=True,
        is_time_bound=True,
        default_validity_days=730,
    )
    role_senate = RoleDefinition.objects.create(
        code="TEST_SENATE",
        name="Test Student Senate",
        description="Senate member test role",
        module_or_dept="Gymkhana",
        allowed_user_types=["student"],
        is_singular=False,
        is_time_bound=True,
        default_validity_days=365,
    )
    # Define conflict between Dean and HOD
    RoleConflict.objects.create(
        role_a=role_dean,
        role_b=role_hod,
        reason="Separation of administrative & departmental supervisory powers",
    )
    RoleConflict.objects.create(
        role_a=role_hod,
        role_b=role_dean,
        reason="Separation of administrative & departmental supervisory powers",
    )

    return {
        "faculty1": faculty1,
        "faculty2": faculty2,
        "student1": student1,
        "role_hod": role_hod,
        "role_dean": role_dean,
        "role_senate": role_senate,
    }


def test_assign_role_to_eligible_faculty(test_data):
    """Verify role assignment succeeds for eligible active user (CFR-SA-006)."""
    today = date.today()
    assignment = RoleService.assign_role(
        role_code="TEST_HOD",
        user_id=test_data["faculty1"].id,
        start_date=today,
        end_date=today + timedelta(days=730),
        reason="Appointed as Department Head",
        actor_username="superadmin",
    )
    assert assignment.id is not None
    assert assignment.status == "active"
    assert assignment.role.code == "TEST_HOD"
    assert assignment.user.institute_id == "FAC_T1"


def test_reject_ineligible_user_type(test_data):
    """Verify role assignment fails when user_type is not allowed (BR-SA-007)."""
    today = date.today()
    with pytest.raises(RoleManagementError) as exc_info:
        RoleService.assign_role(
            role_code="TEST_HOD",
            user_id=test_data["student1"].id,
            start_date=today,
            end_date=today + timedelta(days=365),
            reason="Illegal assignment",
        )
    assert "not eligible" in str(exc_info.value)
    assert exc_info.value.code == "ineligible_user_type"


def test_reject_conflicting_role_assignment(test_data):
    """Verify Separation of Duties prevents mutually conflicting roles (BR-SA-012)."""
    today = date.today()
    # First assign HOD
    RoleService.assign_role(
        role_code="TEST_HOD",
        user_id=test_data["faculty1"].id,
        start_date=today,
        end_date=today + timedelta(days=730),
        reason="Assigned HOD",
    )
    # Attempt to assign conflicting DEAN role
    with pytest.raises(RoleManagementError) as exc_info:
        RoleService.assign_role(
            role_code="TEST_DEAN",
            user_id=test_data["faculty1"].id,
            start_date=today,
            end_date=today + timedelta(days=730),
            reason="Assigned Dean",
        )
    assert "conflicts with" in str(exc_info.value)
    assert exc_info.value.code == "role_conflict_detected"


def test_reject_singular_role_duplicate_holder(test_data):
    """Verify singular role cannot have two concurrent active holders (BR-SA-010)."""
    today = date.today()
    RoleService.assign_role(
        role_code="TEST_HOD",
        user_id=test_data["faculty1"].id,
        start_date=today,
        end_date=today + timedelta(days=730),
        reason="Holder 1",
    )

    with pytest.raises(RoleManagementError) as exc_info:
        RoleService.assign_role(
            role_code="TEST_HOD",
            user_id=test_data["faculty2"].id,
            start_date=today,
            end_date=today + timedelta(days=730),
            reason="Holder 2",
        )
    assert "Singular role" in str(exc_info.value)
    assert exc_info.value.code == "singular_role_occupied"


def test_reject_super_admin_assignment(test_data):
    """Verify Super Admin status cannot be granted via standard role assignment (BR-SA-028)."""
    today = date.today()
    with pytest.raises(RoleManagementError) as exc_info:
        RoleService.assign_role(
            role_code="super_admin",
            user_id=test_data["faculty1"].id,
            start_date=today,
            end_date=today + timedelta(days=365),
            reason="Self escalate",
        )
    assert "Super Admin status is immutable" in str(exc_info.value)


def test_reassign_role_with_handover_and_audit_access(test_data):
    """Verify role reassignment revokes old holder, grants new holder, and sets previous audit window (BR-SA-013, BW-SA-05)."""
    today = date.today()
    assignment1 = RoleService.assign_role(
        role_code="TEST_HOD",
        user_id=test_data["faculty1"].id,
        start_date=today,
        end_date=today + timedelta(days=730),
        reason="Original HOD",
    )

    new_assignment = RoleService.reassign_role(
        current_assignment_id=assignment1.id,
        new_user_id=test_data["faculty2"].id,
        effective_date=today + timedelta(days=2),
        reason="Handover after completion of term",
        pending_task_disposition="transfer",
        actor_username="superadmin",
    )

    assignment1.refresh_from_db()
    assert assignment1.status == "reassigned"
    assert assignment1.reassigned_to_user_id == test_data["faculty2"].id
    assert assignment1.previous_holder_audit_until is not None

    assert new_assignment.user_id == test_data["faculty2"].id
    assert new_assignment.role.code == "TEST_HOD"


def test_revoke_role_standard_vs_emergency(test_data):
    """Verify standard revocation requires notice; emergency takes effect immediately (BR-SA-014)."""
    today = date.today()
    assignment = RoleService.assign_role(
        role_code="TEST_SENATE",
        user_id=test_data["student1"].id,
        start_date=today,
        end_date=today + timedelta(days=365),
        reason="Senate election",
    )

    # Standard revocation with effective_date=today must fail (requires future notice)
    with pytest.raises(RoleManagementError) as exc_info:
        RoleService.revoke_role(
            assignment_id=assignment.id,
            reason="Standard revocation without notice",
            is_emergency=False,
            effective_date=today,
        )
    assert "requires at least one day's notice" in str(exc_info.value)

    # Emergency revocation succeeds immediately
    revoked = RoleService.revoke_role(
        assignment_id=assignment.id,
        reason="Disciplinary violation",
        is_emergency=True,
        actor_username="superadmin",
    )
    assert revoked.status == "revoked"
    assert revoked.revocation_reason == "Disciplinary violation"


def test_extend_role_validity(test_data):
    """Verify role extension updates validity with approval ref (BR-SA-015, UC-SA-011)."""
    today = date.today()
    assignment = RoleService.assign_role(
        role_code="TEST_SENATE",
        user_id=test_data["student1"].id,
        start_date=today,
        end_date=today + timedelta(days=100),
        reason="Senate election",
    )

    extended = RoleService.extend_role_validity(
        assignment_id=assignment.id,
        new_end_date=today + timedelta(days=200),
        extension_approval_ref="DIR/OFFICE/EXT/2026/01",
        reason="Tenure extended by Senate resolution",
        actor_username="superadmin",
    )
    assert extended.status == "extended"
    assert extended.end_date == today + timedelta(days=200)
    assert "DIR/OFFICE/EXT/2026/01" in extended.extension_reason
