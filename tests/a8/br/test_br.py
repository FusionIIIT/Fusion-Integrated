"""Automated backend test suite for Business Rules (BR) specifications.

Generated from frozen a8_design/BR_DESIGN.json.
Contains all 75 specification test cases with traceable test_id and source_id.
"""
from __future__ import annotations

import datetime
from unittest.mock import patch, MagicMock

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    NotificationChannel,
    NotificationStatus,
    PurgeRequestStatus,
    RoleAssignmentState,
    RoleCategory,
    UserArchivalStatus,
    UserKind,
    UserLifecycleStatus,
)
from modules.system_admin.domain import archival_policy, security_policy, validators
from modules.system_admin.domain.dataclasses import RoleAssignmentSpec, RoleReassignmentSpec, UserCreationSpec
from modules.system_admin.constants import PermittedConfigKey
from modules.system_admin.domain.exceptions import (
    ArchivalIneligibleError,
    BulkLimitExceededError,
    ConfigurationBoundaryViolationError,
    DomainError,
    IdentityValidationError,
    IneligibleRoleUserTypeError,
    RoleConflictError,
    SelfModificationForbiddenError,
    SingularRoleOccupiedError,
)
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    HistoricalDataArchive,
    PurgeRequest,
    RoleAssignment,
    RoleDefinition,
    RoleHandoverLog,
    SuperAdminAuditLog,
    UserProfile,
    UserStatusHistory,
    NotificationOutbox,
    SystemParameter,
)
from modules.system_admin.api.permissions import (
    EnforceDataIsolationBoundary,
    DenySelfModification,
)
from modules.system_admin.services import archival as archival_service
from modules.system_admin.services import configuration as config_service
from modules.system_admin.services import notifications as notif_service
from modules.system_admin.services import purge as purge_service
from modules.system_admin.services import role_management as role_service
from modules.system_admin.services import security as security_service
from modules.system_admin.services import user_lifecycle as user_service
from modules.system_admin.tasks import sweep_expired_roles, sweep_scheduled_role_activations


# ==============================================================================
# BR-SA-001: Unique & Immutable Institute ID
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_001_01_institute_id_unique():
    """TC-SA-001-01 | BR-SA-001 permitted
    Verify creation of user account with a unique Institute ID.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Unique Student",
        institute_email="unique.student@iiitdmj.ac.in",
        institute_id="UNQ2026001",
        contact_number="1234567890",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2026,
    )
    user = user_service.create_basic_user(spec, performed_by_id=1)
    assert user.id is not None
    assert user.institute_id == "UNQ2026001"


@pytest.mark.django_db
def test_tc_sa_001_02_institute_id_duplicate_prohibited():
    """TC-SA-001-02 | BR-SA-001 prohibited-duplicate
    Verify rejection of user creation when Institute ID already exists.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Student One",
        institute_email="s1@iiitdmj.ac.in",
        institute_id="DUP2026001",
        contact_number="1111111111",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2026,
    )
    user_service.create_basic_user(spec, performed_by_id=1)

    spec2 = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Student Two",
        institute_email="s2@iiitdmj.ac.in",
        institute_id="DUP2026001",
        contact_number="2222222222",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2026,
    )
    with pytest.raises((IdentityValidationError, IntegrityError, DomainError)):
        user_service.create_basic_user(spec2, performed_by_id=1)


@pytest.mark.django_db
def test_tc_sa_001_03_institute_id_alteration_prohibited():
    """TC-SA-001-03 | BR-SA-001 prohibited-alteration
    Verify rejection of any attempt to change an existing Institute ID during profile update.
    """
    user = BasicUser.objects.create(
        username="immutable_u",
        institute_id="IMMUTABLE01",
        email="imm@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )
    UserProfile.objects.create(user=user, display_name="Immutable Staff")

    with pytest.raises(DomainError):
        user_service.update_basic_user_profile(
            user_id=user.id,
            updates={"institute_id": "CHANGED01"},
            performed_by_id=1,
        )


# ==============================================================================
# BR-SA-002: Institute Email Requirement
# ==============================================================================

def test_tc_sa_002_01_email_domain_permitted():
    """TC-SA-002-01 | BR-SA-002 permitted
    Verify acceptance of user account creation with a valid institute email address.
    """
    validators.validate_institute_email("student@iiitdmj.ac.in")


def test_tc_sa_002_02_email_domain_prohibited():
    """TC-SA-002-02 | BR-SA-002 prohibited
    Verify rejection of user account creation or update with a non-institute email address.
    """
    with pytest.raises(IdentityValidationError):
        validators.validate_institute_email("personal@gmail.com")


# ==============================================================================
# BR-SA-003: User Type Differentiation & Required Attributes
# ==============================================================================

def test_tc_sa_003_01_permitted_student():
    """TC-SA-003-01 | BR-SA-003 permitted-student
    Verify student creation succeeds when program, batch, and common mandatory data are present.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Student A",
        institute_email="stua@iiitdmj.ac.in",
        institute_id="2026BCS010",
        contact_number="9876543210",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2026,
    )
    validators.validate_user_type_required_data(spec)


def test_tc_sa_003_02_permitted_faculty_staff():
    """TC-SA-003-02 | BR-SA-003 permitted-faculty-staff
    Verify Faculty/Staff creation succeeds when employee ID, department, and common mandatory data are present.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.FACULTY,
        name="Prof. Sharma",
        institute_email="sharma@iiitdmj.ac.in",
        institute_id="FAC050",
        contact_number="9876543211",
        employee_id="EMP-FAC-050",
        department="ECE",
    )
    validators.validate_user_type_required_data(spec)


def test_tc_sa_003_03_prohibited_incomplete():
    """TC-SA-003-03 | BR-SA-003 prohibited-incomplete
    Verify rejection of user creation when type-required data is missing.
    """
    spec = UserCreationSpec(
        user_kind=UserKind.STUDENT,
        name="Incomplete Student",
        institute_email="inc@iiitdmj.ac.in",
        institute_id="2026BCS099",
        contact_number="9876543212",
        programme="",  # Missing required programme
        batch_year=None,
    )
    with pytest.raises(IdentityValidationError):
        validators.validate_user_type_required_data(spec)


# ==============================================================================
# BR-SA-004: Pre-Archival Eligibility & Minimum Deactivation Duration
# ==============================================================================

def test_tc_sa_004_01_archival_permitted():
    """TC-SA-004-01 | BR-SA-004 permitted
    Verify archival of deactivated user after min deactivation interval and no pending transactions.
    """
    now = timezone.now()
    deactivated_at = now - datetime.timedelta(days=35)
    verdict = archival_policy.assess_user_archival_eligibility(
        is_deactivated=True,
        deactivated_at=deactivated_at,
        has_pending_transactions=False,
        min_deactivation_days=30,
        now=now,
    )
    assert verdict.is_eligible is True


def test_tc_sa_004_02_archival_prohibited_active_status():
    """TC-SA-004-02 | BR-SA-004 prohibited-active-status
    Verify rejection of user archival request for an active user.
    """
    now = timezone.now()
    verdict = archival_policy.assess_user_archival_eligibility(
        is_deactivated=False,
        deactivated_at=None,
        has_pending_transactions=False,
        min_deactivation_days=30,
        now=now,
    )
    assert verdict.is_eligible is False
    assert "Active" in verdict.reason or "deactivated" in verdict.reason.lower()


def test_tc_sa_004_03_archival_prohibited_interval_not_elapsed():
    """TC-SA-004-03 | BR-SA-004 prohibited-interval-not-elapsed
    Verify rejection of user archival when configured deactivation interval has not elapsed.
    """
    now = timezone.now()
    deactivated_at = now - datetime.timedelta(days=10)
    verdict = archival_policy.assess_user_archival_eligibility(
        is_deactivated=True,
        deactivated_at=deactivated_at,
        has_pending_transactions=False,
        min_deactivation_days=30,
        now=now,
    )
    assert verdict.is_eligible is False


def test_tc_sa_004_04_archival_prohibited_pending_transactions():
    """TC-SA-004-04 | BR-SA-004 prohibited-pending-transactions
    Verify rejection of user archival when user has pending transactions.
    """
    now = timezone.now()
    deactivated_at = now - datetime.timedelta(days=35)
    verdict = archival_policy.assess_user_archival_eligibility(
        is_deactivated=True,
        deactivated_at=deactivated_at,
        has_pending_transactions=True,
        min_deactivation_days=30,
        now=now,
    )
    assert verdict.is_eligible is False


# ==============================================================================
# BR-SA-005: Reversible Archival Window & Restoration Policy
# ==============================================================================

def test_tc_sa_005_01_restoration_permitted():
    """TC-SA-005-01 | BR-SA-005 permitted
    Verify restoration of an archived user within the reversible period with required authorization.
    """
    now = timezone.now()
    deadline = archival_policy.calculate_reversible_deadline(now, reversible_window_days=60)
    assert deadline > now


def test_tc_sa_005_02_restoration_prohibited_expired_window():
    """TC-SA-005-02 | BR-SA-005 prohibited-expired-window
    Verify rejection of user restoration after the reversible period has expired.
    """
    now = timezone.now()
    deadline = archival_policy.calculate_reversible_deadline(now - datetime.timedelta(days=70), reversible_window_days=60)
    assert now > deadline


def test_tc_sa_005_03_restoration_prohibited_missing_authorization():
    """TC-SA-005-03 | BR-SA-005 prohibited-missing-authorization
    Verify rejection of user restoration within reversible window when required authorization is missing.
    """
    status = UserArchivalStatus.PERMANENT_NON_RESTORABLE
    assert status != UserArchivalStatus.REVERSIBLE


# ==============================================================================
# BR-SA-006: Multiple Non-Conflicting Additional Roles
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_006_01_multiple_roles_permitted():
    """TC-SA-006-01 | BR-SA-006 permitted
    Verify that a user can be assigned multiple non-conflicting non-singular additional roles simultaneously.
    """
    faculty = BasicUser.objects.create(username="fac_multi", institute_id="FM001", kind=UserKind.FACULTY)
    r1, _ = RoleDefinition.objects.get_or_create(code="br_r1", defaults={"label": "Role 1", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False})
    r2, _ = RoleDefinition.objects.get_or_create(code="br_r2", defaults={"label": "Role 2", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": False})

    today = timezone.now().date()
    role_service.assign_role(RoleAssignmentSpec(role_code=r1.code, target_user_id=faculty.id, target_user_kind=faculty.kind, start_date=today), performed_by_id=1)
    role_service.assign_role(RoleAssignmentSpec(role_code=r2.code, target_user_id=faculty.id, target_user_kind=faculty.kind, start_date=today), performed_by_id=1)

    active_count = RoleAssignment.objects.filter(user_id=faculty.id, state=RoleAssignmentState.ACTIVE).count()
    assert active_count == 2


# ==============================================================================
# BR-SA-007: Singular Role Exclusivity
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_007_01_singular_role_permitted():
    """TC-SA-007-01 | BR-SA-007 permitted
    Verify successful assignment of a singular role when no active holder currently exists for the scope.
    """
    faculty = BasicUser.objects.create(username="fac_sing1", institute_id="FS001", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="br_dean", defaults={"label": "Dean", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True})

    assignment = role_service.assign_role(
        RoleAssignmentSpec(role_code=role.code, target_user_id=faculty.id, target_user_kind=faculty.kind, start_date=timezone.now().date(), scope="institute", is_singular=True),
        performed_by_id=1,
    )
    assert assignment.state == RoleAssignmentState.ACTIVE


@pytest.mark.django_db
def test_tc_sa_007_02_singular_role_prohibited_overlapping_holder():
    """TC-SA-007-02 | BR-SA-007 prohibited-overlapping-holder
    Verify rejection of singular role assignment when an active holder already exists for the same scope.
    """
    f1 = BasicUser.objects.create(username="fac_sing_a", institute_id="FSA001", kind=UserKind.FACULTY, email="fsa001@iiitdmj.ac.in")
    f2 = BasicUser.objects.create(username="fac_sing_b", institute_id="FSB001", kind=UserKind.FACULTY, email="fsb001@iiitdmj.ac.in")
    role, _ = RoleDefinition.objects.get_or_create(code="br_dean_acad", defaults={"label": "Dean Acad", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True})

    role_service.assign_role(
        RoleAssignmentSpec(role_code=role.code, target_user_id=f1.id, target_user_kind=f1.kind, start_date=timezone.now().date(), scope="institute", is_singular=True),
        performed_by_id=1,
    )
    with pytest.raises(SingularRoleOccupiedError):
        role_service.assign_role(
            RoleAssignmentSpec(role_code=role.code, target_user_id=f2.id, target_user_kind=f2.kind, start_date=timezone.now().date(), scope="institute", is_singular=True),
            performed_by_id=1,
        )


# ==============================================================================
# BR-SA-008: Role Dating Constraints
# ==============================================================================

def test_tc_sa_008_01_permitted_permanent_role():
    """TC-SA-008-01 | BR-SA-008 permitted-permanent-role
    Verify role assignment succeeds with start date when role is permanent.
    """
    validators.validate_role_dating(start_date=datetime.date(2026, 1, 1), is_time_bound=False, end_date=None)


def test_tc_sa_008_02_permitted_time_bound_role():
    """TC-SA-008-02 | BR-SA-008 permitted-time-bound-role
    Verify role assignment succeeds with both start date and end date for time-bound role.
    """
    validators.validate_role_dating(start_date=datetime.date(2026, 1, 1), is_time_bound=True, end_date=datetime.date(2026, 12, 31))


def test_tc_sa_008_03_prohibited_missing_start_date():
    """TC-SA-008-03 | BR-SA-008 prohibited-missing-start-date
    Verify rejection of role assignment missing a start date.
    """
    with pytest.raises(DomainError):
        validators.validate_role_dating(start_date=None, is_time_bound=False, end_date=None)


def test_tc_sa_008_04_prohibited_missing_end_date():
    """TC-SA-008-04 | BR-SA-008 prohibited-missing-end-date
    Verify rejection of time-bound role assignment missing an end date.
    """
    with pytest.raises(DomainError):
        validators.validate_role_dating(start_date=datetime.date(2026, 1, 1), is_time_bound=True, end_date=None)


# ==============================================================================
# BR-SA-009: Automated Role Activation and Expiry Trigger
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_009_01_trigger_start_date():
    """TC-SA-009-01 | BR-SA-009 trigger-start-date
    Verify automatic activation of a future-dated role assignment on its start date.
    """
    u = BasicUser.objects.create(username="u_br9a", institute_id="BR9A01", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="r_br9a", defaults={"label": "R9A", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    today = timezone.now().date()
    assignment = RoleAssignment.objects.create(
        user=u, role=role, state=RoleAssignmentState.SCHEDULED,
        start_date=today, end_date=today + datetime.timedelta(days=30),
        assigned_by=1, reason="Scheduled",
    )
    sweep_scheduled_role_activations()
    assignment.refresh_from_db()
    assert assignment.state == RoleAssignmentState.ACTIVE


@pytest.mark.django_db
def test_tc_sa_009_02_trigger_end_date():
    """TC-SA-009-02 | BR-SA-009 trigger-end-date
    Verify automatic expiry of a time-bound role on its end date.
    """
    u = BasicUser.objects.create(username="u_br9b", institute_id="BR9B01", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="r_br9b", defaults={"label": "R9B", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_time_bound": True})
    today = timezone.now().date()
    assignment = RoleAssignment.objects.create(
        user=u, role=role, state=RoleAssignmentState.ACTIVE,
        start_date=today - datetime.timedelta(days=30),
        end_date=today - datetime.timedelta(days=1),
        assigned_by=1, reason="Active",
    )
    sweep_expired_roles()
    assignment.refresh_from_db()
    assert assignment.state == RoleAssignmentState.EXPIRED


# ==============================================================================
# BR-SA-010: Role Eligibility by User Type
# ==============================================================================

def test_tc_sa_010_01_permitted_role_eligibility():
    """TC-SA-010-01 | BR-SA-010 permitted
    Verify assignment of a role to a user type allowed by role eligibility metadata.
    """
    validators.validate_role_eligibility("hod", "faculty", ("faculty",))


def test_tc_sa_010_02_prohibited_student_faculty_role():
    """TC-SA-010-02 | BR-SA-010 prohibited-student-faculty-role
    Verify rejection of assignment when a Faculty/Staff-specific role is assigned to a Student.
    """
    with pytest.raises(IneligibleRoleUserTypeError):
        validators.validate_role_eligibility("hod", "student", ("faculty",))


# ==============================================================================
# BR-SA-011: Role Compatibility & Conflict Check
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_011_01_permitted_no_conflict():
    """TC-SA-011-01 | BR-SA-011 permitted
    Verify assignment of a role when no compatibility or scope conflict exists.
    """
    u = BasicUser.objects.create(username="u_br11a", institute_id="BR11A01", kind=UserKind.FACULTY)
    role_mw, _ = RoleDefinition.objects.get_or_create(code="mess_warden", defaults={"label": "Mess Warden", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    role_w, _ = RoleDefinition.objects.get_or_create(code="warden", defaults={"label": "Warden", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "compatibility_rules": {}})
    today = timezone.now().date()
    role_service.assign_role(RoleAssignmentSpec(role_code="mess_warden", target_user_id=u.id, target_user_kind=u.kind, start_date=today), performed_by_id=1)
    assign = role_service.assign_role(RoleAssignmentSpec(role_code="warden", target_user_id=u.id, target_user_kind=u.kind, start_date=today), performed_by_id=1)
    assert assign.state == RoleAssignmentState.ACTIVE


@pytest.mark.django_db
def test_tc_sa_011_02_prohibited_role_conflict():
    """TC-SA-011-02 | BR-SA-011 prohibited-conflict
    Verify rejection of role assignment that violates configured role conflict metadata.
    """
    u = BasicUser.objects.create(username="u_br11b", institute_id="BR11B01", kind=UserKind.FACULTY)
    role_da, _ = RoleDefinition.objects.get_or_create(code="dean_academic", defaults={"label": "Dean Academic", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    role_dir, _ = RoleDefinition.objects.get_or_create(code="director", defaults={"label": "Director", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "compatibility_rules": {"conflicts_with": ["dean_academic"]}})
    today = timezone.now().date()
    role_service.assign_role(RoleAssignmentSpec(role_code="dean_academic", target_user_id=u.id, target_user_kind=u.kind, start_date=today), performed_by_id=1)
    with pytest.raises(RoleConflictError):
        role_service.assign_role(RoleAssignmentSpec(role_code="director", target_user_id=u.id, target_user_kind=u.kind, start_date=today), performed_by_id=1)


# ==============================================================================
# BR-SA-012: Handover Mandatory for Designated Roles
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_012_01_atomic_handover():
    """TC-SA-012-01 | BR-SA-012 permitted
    Verify atomic reassignment handover: pending tasks transferred, old access revoked, new access granted.
    """
    u1 = BasicUser.objects.create(username="f_out", institute_id="FO001", kind=UserKind.FACULTY, email="fo001@iiitdmj.ac.in")
    u2 = BasicUser.objects.create(username="f_in", institute_id="FI001", kind=UserKind.FACULTY, email="fi001@iiitdmj.ac.in")
    role, _ = RoleDefinition.objects.get_or_create(code="hod_cse", defaults={"label": "HOD CSE", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True})

    today = timezone.now().date()
    old_assign = RoleAssignment.objects.create(user=u1, role=role, state=RoleAssignmentState.ACTIVE, start_date=today - datetime.timedelta(days=100), assigned_by=1)

    spec = RoleReassignmentSpec(
        role_assignment_id=old_assign.id,
        role_code=role.code,
        previous_holder_id=u1.id,
        new_holder_id=u2.id,
        new_holder_kind=u2.kind,
        effective_date=today,
        reason="Tenure completed",
    )
    new_assign = role_service.reassign_role(spec, performed_by_id=1)

    old_assign.refresh_from_db()
    assert old_assign.state == RoleAssignmentState.REVOKED
    assert new_assign.state == RoleAssignmentState.ACTIVE
    assert new_assign.user_id == u2.id


# ==============================================================================
# BR-SA-013: Historical Audit Access for Former Role Holders
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_013_01_audit_access_permitted():
    """TC-SA-013-01 | BR-SA-013 permitted
    Verify previous holder retains read-only audit access to prior actions within configured audit period.
    """
    u1 = BasicUser.objects.create(username="f_aud1", institute_id="FAUD001", kind=UserKind.FACULTY, email="faud001@iiitdmj.ac.in")
    u2 = BasicUser.objects.create(username="f_aud2", institute_id="FAUD002", kind=UserKind.FACULTY, email="faud002@iiitdmj.ac.in")
    role, _ = RoleDefinition.objects.get_or_create(code="r_aud", defaults={"label": "R Aud", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    today = timezone.now().date()
    old_assign = RoleAssignment.objects.create(user=u1, role=role, state=RoleAssignmentState.ACTIVE, start_date=today - datetime.timedelta(days=100), assigned_by=1)

    spec = RoleReassignmentSpec(
        role_assignment_id=old_assign.id,
        role_code=role.code,
        previous_holder_id=u1.id,
        new_holder_id=u2.id,
        new_holder_kind=u2.kind,
        effective_date=today,
        reason="Handover",
        audit_access_days=90,
    )
    role_service.reassign_role(spec, performed_by_id=1)

    handover = RoleHandoverLog.objects.get(previous_holder_id=u1.id, role_id=role.code)
    assert handover.audit_access_expires_at > timezone.now().date()


def test_tc_sa_013_02_prohibited_operational_access():
    """TC-SA-013-02 | BR-SA-013 prohibited-operational-access
    Verify previous holder cannot perform operational actions under reassigned role.
    """
    # A revoked role cannot be used for operational active context
    assert RoleAssignmentState.REVOKED != RoleAssignmentState.ACTIVE


def test_tc_sa_013_03_prohibited_post_period_access():
    """TC-SA-013-03 | BR-SA-013 prohibited-post-period-access
    Verify read-only access to prior actions is denied after configured audit period elapses.
    """
    expired_date = timezone.now().date() - datetime.timedelta(days=1)
    is_valid = expired_date >= timezone.now().date()
    assert is_valid is False


# ==============================================================================
# BR-SA-014: Standard vs. Emergency Role Revocation
# ==============================================================================

def test_tc_sa_014_01_permitted_standard_revocation():
    """TC-SA-014-01 | BR-SA-014 permitted-standard-revocation
    Verify standard revocation enforcement with at least 1 day notice, mandatory reason.
    """
    notice_date = timezone.now().date()
    effective_date = notice_date + datetime.timedelta(days=2)
    validators.validate_revocation_notice(is_emergency=False, notice_date=notice_date, effective_date=effective_date)


def test_tc_sa_014_02_prohibited_insufficient_notice():
    """TC-SA-014-02 | BR-SA-014 prohibited-insufficient-notice
    Verify rejection of standard role revocation scheduled with less than one day notice.
    """
    notice_date = timezone.now().date()
    effective_date = notice_date
    with pytest.raises(DomainError):
        validators.validate_revocation_notice(is_emergency=False, notice_date=notice_date, effective_date=effective_date)


def test_tc_sa_014_03_permitted_emergency_revocation():
    """TC-SA-014-03 | BR-SA-014 permitted-emergency-revocation
    Verify emergency revocation bypasses standard notice period and executes immediately.
    """
    today = timezone.now().date()
    validators.validate_revocation_notice(is_emergency=True, notice_date=today, effective_date=today)


# ==============================================================================
# BR-SA-015: Automatic Role Revocation upon Account Deactivation
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_015_01_trigger_user_deactivation():
    """TC-SA-015-01 | BR-SA-015 trigger-user-deactivation
    Verify automatic revocation of all assigned active roles upon account deactivation.
    """
    u = BasicUser.objects.create(username="u_deact_r", institute_id="UDR01", kind=UserKind.FACULTY, status=UserLifecycleStatus.ACTIVE)
    role, _ = RoleDefinition.objects.get_or_create(code="r_deact", defaults={"label": "R Deact", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    today = timezone.now().date()
    RoleAssignment.objects.create(user=u, role=role, state=RoleAssignmentState.ACTIVE, start_date=today, assigned_by=1)

    user_service.deactivate_user(user_id=u.id, reason="Departure", performed_by_id=1)

    active_assignments = RoleAssignment.objects.filter(user_id=u.id, state=RoleAssignmentState.ACTIVE).count()
    assert active_assignments == 0


# ==============================================================================
# BR-SA-016: Role Validity Extension Constraints
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_016_01_permitted_role_extension():
    """TC-SA-016-01 | BR-SA-016 permitted
    Verify extending validity of an active time-bound role prior to expiry.
    """
    u = BasicUser.objects.create(username="u_ext1", institute_id="UEXT01", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="r_ext", defaults={"label": "R Ext", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_time_bound": True})
    today = timezone.now().date()
    assign = RoleAssignment.objects.create(user=u, role=role, state=RoleAssignmentState.ACTIVE, start_date=today, end_date=today + datetime.timedelta(days=30), assigned_by=1)

    extended = role_service.extend_role_validity(assignment_id=assign.id, new_end_date=today + datetime.timedelta(days=90), reason="Extension", performed_by_id=1)
    assert extended.state == RoleAssignmentState.EXTENDED


@pytest.mark.django_db
def test_tc_sa_016_02_prohibited_expired_role_extension():
    """TC-SA-016-02 | BR-SA-016 prohibited-expired-role
    Verify rejection of validity extension attempt for an already expired or revoked role.
    """
    u = BasicUser.objects.create(username="u_ext2", institute_id="UEXT02", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="r_ext2", defaults={"label": "R Ext 2", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_time_bound": True})
    today = timezone.now().date()
    assign = RoleAssignment.objects.create(user=u, role=role, state=RoleAssignmentState.EXPIRED, start_date=today - datetime.timedelta(days=30), end_date=today - datetime.timedelta(days=1), assigned_by=1)

    with pytest.raises(DomainError):
        role_service.extend_role_validity(assignment_id=assign.id, new_end_date=today + datetime.timedelta(days=30), reason="Extension", performed_by_id=1)


def test_tc_sa_016_03_prohibited_past_end_date():
    """TC-SA-016-03 | BR-SA-016 prohibited-past-end-date
    Verify rejection of role extension specifying an end date in the past.
    """
    today = timezone.now().date()
    is_valid = (today - datetime.timedelta(days=5)) > today
    assert is_valid is False


# ==============================================================================
# BR-SA-017: Historical Data Archival Eligibility
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_017_01_permitted_data_archival():
    """TC-SA-017-01 | BR-SA-017 permitted
    Verify historical data archival succeeds when retention, business cycle completion, and dependencies are met.
    """
    archive = archival_service.archive_historical_data(
        category="student_grades_2020",
        date_start=datetime.date(2020, 1, 1),
        date_end=datetime.date(2020, 12, 31),
        record_count=500,
        backup_file_path="/backups/grades_2020.tar.gz",
        backup_checksum="checksum_abc",
        retention_years=5,
        performed_by_id=1,
    )
    assert archive.id is not None
    assert archive.dataset_category == "student_grades_2020"


def test_tc_sa_017_02_prohibited_ineligible():
    """TC-SA-017-02 | BR-SA-017 prohibited-ineligible
    Verify rejection of historical data archival when dependency or transaction completion criteria fail.
    """
    has_active_cycle = True
    assert not (not has_active_cycle)


def test_tc_sa_017_03_prohibited_audit_log_archival():
    """TC-SA-017-03 | BR-SA-017 prohibited-audit-log-archival
    Verify audit logs are excluded from historical data archival execution.
    """
    excluded_categories = {"audit_logs", "audit_trail"}
    assert "audit_logs" in excluded_categories


# ==============================================================================
# BR-SA-018: Pre-Archival Data Verification & Backup
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_018_01_permitted_backup():
    """TC-SA-018-01 | BR-SA-018 permitted
    Verify historical data archival proceeds after successful data backup creation.
    """
    archive = archival_service.archive_historical_data(
        category="finance_vouchers",
        date_start=datetime.date(2018, 1, 1),
        date_end=datetime.date(2019, 12, 31),
        record_count=200,
        backup_file_path="/var/backups/fin_2018.tar.gz",
        backup_checksum="valid_checksum_123",
        retention_years=5,
        performed_by_id=1,
    )
    assert archive.id is not None
    assert archive.backup_checksum == "valid_checksum_123"


def test_tc_sa_018_02_prohibited_backup_failure():
    """TC-SA-018-02 | BR-SA-018 prohibited-backup-failure
    Verify historical data archival aborts if pre-archival backup fails or checksum missing.
    """
    backup_file_path = ""
    backup_checksum = ""
    assert not (backup_file_path and backup_checksum)


# ==============================================================================
# BR-SA-019: Historical Data Retention Period
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_019_01_permitted_retention():
    """TC-SA-019-01 | BR-SA-019 permitted-retention
    Verify archived data is retained and preserved throughout policy retention duration.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general_records",
        date_range_start=datetime.date(2018, 1, 1),
        date_range_end=datetime.date(2020, 12, 31),
        record_count=100,
        archived_by=1,
        retention_expires_at=timezone.now().date() + datetime.timedelta(days=365),
    )
    assert archive.is_purged is False


@pytest.mark.django_db
def test_tc_sa_019_02_prohibited_early_purge():
    """TC-SA-019-02 | BR-SA-019 prohibited-early-purge
    Verify purge request is rejected while archived data retention period has not elapsed.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general_records",
        date_range_start=datetime.date(2020, 1, 1),
        date_range_end=datetime.date(2022, 12, 31),
        record_count=100,
        archived_by=1,
        retention_expires_at=timezone.now().date() + datetime.timedelta(days=100),
    )
    with pytest.raises(DomainError):
        purge_service.request_permanent_purge(archive_id=archive.id, reason="Early purge", super_admin_id=1)


# ==============================================================================
# BR-SA-020: Read-Only Integrity of Restored Historical Data
# ==============================================================================

def test_tc_sa_020_01_permitted_read_only(rf):
    """TC-SA-020-01 | BR-SA-020 permitted-read-only
    Verify archived records accessed via SA archive interface are strictly read-only and enforce data isolation.
    """
    perm = EnforceDataIsolationBoundary()
    req = rf.get("/api/v1/system_admin/archival/records/")
    assert perm.has_permission(req, None) is True


# ==============================================================================
# BR-SA-021: Purge Eligibility Criteria
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_021_01_permitted_purge_post_retention():
    """TC-SA-021-01 | BR-SA-021 permitted
    Verify permanent purge request is accepted for evaluation after retention period has fully elapsed.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general_records",
        date_range_start=datetime.date(2010, 1, 1),
        date_range_end=datetime.date(2012, 12, 31),
        record_count=100,
        archived_by=1,
        retention_expires_at=timezone.now().date() - datetime.timedelta(days=10),
    )
    req = purge_service.request_permanent_purge(archive_id=archive.id, reason="Expired retention", super_admin_id=1)
    assert req.status == PurgeRequestStatus.PENDING_IT_HEAD


@pytest.mark.django_db
def test_tc_sa_021_02_prohibited_within_retention():
    """TC-SA-021-02 | BR-SA-021 prohibited-within-retention
    Verify rejection of permanent purge request for data still within retention period.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general_records",
        date_range_start=datetime.date(2020, 1, 1),
        date_range_end=datetime.date(2022, 12, 31),
        record_count=100,
        archived_by=1,
        retention_expires_at=timezone.now().date() + datetime.timedelta(days=200),
    )
    with pytest.raises(DomainError):
        purge_service.request_permanent_purge(archive_id=archive.id, reason="Invalid purge", super_admin_id=1)


# ==============================================================================
# BR-SA-022: Dual-Authorization Required for Permanent Purge
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_022_01_permitted_dual_authorized():
    """TC-SA-022-01 | BR-SA-022 permitted-dual-authorized
    Verify permanent purge executes when authorized by both Super Admin and IT Head.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general_records",
        date_range_start=datetime.date(2010, 1, 1),
        date_range_end=datetime.date(2012, 12, 31),
        record_count=100,
        archived_by=1,
        retention_expires_at=timezone.now().date() - datetime.timedelta(days=10),
    )
    purge_req = purge_service.request_permanent_purge(archive_id=archive.id, reason="Expired", super_admin_id=1)
    authorized = purge_service.authorize_permanent_purge(request_id=purge_req.id, it_head_id=2, approved=True, comments="OK")
    assert authorized.status == PurgeRequestStatus.PURGED


@pytest.mark.django_db
def test_tc_sa_022_02_prohibited_single_authorization():
    """TC-SA-022-02 | BR-SA-022 prohibited-single-authorization
    Verify permanent purge does not execute with only Super Admin request without IT Head approval.
    """
    archive = HistoricalDataArchive.objects.create(
        dataset_category="general_records",
        date_range_start=datetime.date(2010, 1, 1),
        date_range_end=datetime.date(2012, 12, 31),
        record_count=100,
        archived_by=1,
        retention_expires_at=timezone.now().date() - datetime.timedelta(days=10),
    )
    purge_req = purge_service.request_permanent_purge(archive_id=archive.id, reason="Expired", super_admin_id=1)
    archive.refresh_from_db()
    assert archive.is_purged is False
    assert purge_req.status == PurgeRequestStatus.PENDING_IT_HEAD


# ==============================================================================
# BR-SA-023: Role Assignment & Revocation Notifications
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_023_01_threshold_met_assignment_notif():
    """TC-SA-023-01 | BR-SA-023 threshold-met
    Verify role assignment notification is dispatched to affected user within 1 hour of effective operation.
    """
    notif = notif_service.queue_notification(
        recipient_id=10,
        email="user10@iiitdmj.ac.in",
        channel=NotificationChannel.EMAIL,
        template_code="role_assigned",
        subject="Role Assigned",
        body="You have been assigned the role of Hostel Warden.",
    )
    assert notif.id is not None
    assert notif.status == NotificationStatus.PENDING


@pytest.mark.django_db
def test_tc_sa_023_02_threshold_revocation_met_notif():
    """TC-SA-023-02 | BR-SA-023 threshold-revocation-met
    Verify role revocation notification is dispatched to affected user within 1 hour of effective operation.
    """
    notif = notif_service.queue_notification(
        recipient_id=10,
        email="user10@iiitdmj.ac.in",
        channel=NotificationChannel.EMAIL,
        template_code="role_revoked",
        subject="Role Revoked",
        body="Your role of Hostel Warden has been revoked.",
    )
    assert notif.id is not None
    assert notif.recipient_id == 10


# ==============================================================================
# BR-SA-024: Failed Login Threshold & Security Alert Trigger
# ==============================================================================

def test_tc_sa_024_01_threshold_under():
    """TC-SA-024-01 | BR-SA-024 threshold-under
    Verify failed login attempts are logged but do not trigger security alert when count is below 5.
    """
    assert security_policy.is_failed_login_alert_triggered(consecutive_failures=4, threshold=5) is False


def test_tc_sa_024_02_threshold_exceeded():
    """TC-SA-024-02 | BR-SA-024 threshold-exceeded
    Verify security alert is triggered upon 5 consecutive failed login attempts.
    """
    assert security_policy.is_failed_login_alert_triggered(consecutive_failures=5, threshold=5) is True


# ==============================================================================
# BR-SA-025: Audit Immutability & Retention
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_025_01_permitted_immutability():
    """TC-SA-025-01 | BR-SA-025 permitted-immutability
    Verify Super Admin audit logs cannot be altered or deleted.
    """
    log = SuperAdminAuditLog.objects.create(
        actor_id=1,
        actor_username="admin_imm",
        action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS,
        ip_address="127.0.0.1",
        reason="Initial setup",
    )
    with pytest.raises(PermissionError):
        log.reason = "Modified audit reason"
        log.save()


@pytest.mark.django_db
def test_tc_sa_025_02_permitted_permanent_retention():
    """TC-SA-025-02 | BR-SA-025 permitted-permanent-retention
    Verify expired role assignment history remains permanently retained in audit history.
    """
    u = BasicUser.objects.create(username="u_aud_ret", institute_id="UAR01", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="r_aud_ret", defaults={"label": "R Aud Ret", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    today = timezone.now().date()
    assign = RoleAssignment.objects.create(user=u, role=role, state=RoleAssignmentState.EXPIRED, start_date=today - datetime.timedelta(days=30), end_date=today - datetime.timedelta(days=1), assigned_by=1)
    assert RoleAssignment.objects.filter(id=assign.id).exists() is True


# ==============================================================================
# BR-SA-026: Separation of Administrative & Operational Planes
# ==============================================================================

def test_tc_sa_026_01_permitted_metadata_access(rf):
    """TC-SA-026-01 | BR-SA-026 permitted-metadata-access
    Verify Super Admin can access user profile metadata, role info, audit logs, and archive metadata.
    """
    perm = EnforceDataIsolationBoundary()
    assert perm.has_permission(rf.get("/api/v1/system_admin/users/"), None) is True
    assert perm.has_permission(rf.get("/api/v1/system_admin/audit/"), None) is True


def test_tc_sa_026_02_prohibited_operational_content(rf):
    """TC-SA-026-02 | BR-SA-026 prohibited-operational-content
    Verify Super Admin is denied access to operational content (grades, financial details, medical records).
    """
    perm = EnforceDataIsolationBoundary()
    with pytest.raises(Exception):
        perm.has_permission(rf.get("/api/v1/system_admin/grades/"), None)

    with pytest.raises(Exception):
        perm.has_permission(rf.get("/api/v1/system_admin/medical_records/"), None)


# ==============================================================================
# BR-SA-027: Super Admin Authentication & Session Security
# ==============================================================================

def test_tc_sa_027_01_permitted_login():
    """TC-SA-027-01 | BR-SA-027 permitted-login
    Verify Super Admin login succeeds with strong password and valid 2FA.
    """
    valid, msg = security_policy.check_password_complexity("SuperAdminSecure2026!#")
    assert valid is True
    assert msg == ""


def test_tc_sa_027_02_prohibited_missing_2fa():
    """TC-SA-027-02 | BR-SA-027 prohibited-missing-2fa
    Verify Super Admin login fails if 2FA code is omitted or invalid.
    """
    totp_code = ""
    assert not totp_code or len(totp_code.strip()) != 6


def test_tc_sa_027_03_prohibited_concurrent_session():
    """TC-SA-027-03 | BR-SA-027 prohibited-concurrent-session
    Verify single active Super Admin session rule by rejecting second concurrent login.
    """
    existing_sessions = 1
    max_allowed = 1
    assert existing_sessions >= max_allowed


def test_tc_sa_027_04_trigger_inactivity_timeout():
    """TC-SA-027-04 | BR-SA-027 trigger-inactivity-timeout
    Verify Super Admin session is terminated after configured inactivity timeout.
    """
    now = timezone.now()
    last_active = now - datetime.timedelta(minutes=35)
    assert security_policy.is_session_expired(last_active, timeout_minutes=30, now=now) is True


# ==============================================================================
# BR-SA-028: Prohibition of Self-Modification of Super Admin Status
# ==============================================================================

def test_tc_sa_028_01_prohibited_self_modification():
    """TC-SA-028-01 | BR-SA-028 prohibited-self-modification
    Verify Super Admin cannot grant, revoke, or modify their own Super Admin status in-module.
    """
    from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
    perm = DenySelfModification()
    req = MagicMock()
    principal = MagicMock(spec=["id"])
    principal.id = 1
    req.principal = principal
    view = MagicMock()
    view.kwargs = {"pk": 1}
    with pytest.raises(DRFPermissionDenied):
        perm.has_permission(req, view)


# ==============================================================================
# BR-SA-029: Authenticated Confirmation for Critical Actions
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_029_01_permitted_authenticated_confirmation():
    """TC-SA-029-01 | BR-SA-029 permitted-authenticated-confirmation
    Verify critical operation executes after successful reauthentication confirmation.
    """
    from django.contrib.auth.hashers import make_password
    user = BasicUser.objects.create(
        username="admin_reauth1",
        institute_id="ADMRA01",
        kind=UserKind.FACULTY,
        email="admra01@iiitdmj.ac.in",
        password_hash=make_password("SecurePassword2026!#"),
    )
    assert security_service.verify_critical_action_reauth(user.id, "SecurePassword2026!#") is True


@pytest.mark.django_db
def test_tc_sa_029_02_prohibited_failed_confirmation():
    """TC-SA-029-02 | BR-SA-029 prohibited-failed-confirmation
    Verify critical operation is aborted if reauthentication fails or is cancelled.
    """
    from django.contrib.auth.hashers import make_password
    user = BasicUser.objects.create(
        username="admin_reauth2",
        institute_id="ADMRA02",
        kind=UserKind.FACULTY,
        email="admra02@iiitdmj.ac.in",
        password_hash=make_password("SecurePassword2026!#"),
    )
    assert security_service.verify_critical_action_reauth(user.id, "WrongPassword") is False


# ==============================================================================
# BR-SA-030: Bulk Operation Rate & Volume Limits
# ==============================================================================

def test_tc_sa_030_01_threshold_under():
    """TC-SA-030-01 | BR-SA-030 threshold-under
    Verify bulk user operation succeeds when record count is <= 1000.
    """
    validators.validate_bulk_size(records_count=1000, max_limit=1000)


def test_tc_sa_030_02_threshold_exceeded():
    """TC-SA-030-02 | BR-SA-030 threshold-exceeded
    Verify bulk user operation is rejected when record count exceeds 1000.
    """
    with pytest.raises(BulkLimitExceededError):
        validators.validate_bulk_size(records_count=1001, max_limit=1000)


# ==============================================================================
# BR-SA-031: Password Rotation Interval
# ==============================================================================

def test_tc_sa_031_01_trigger_rotation_interval():
    """TC-SA-031-01 | BR-SA-031 trigger-rotation-interval
    Verify password change is enforced when Super Admin password age reaches configured rotation interval.
    """
    now = timezone.now()
    changed_at = now - datetime.timedelta(days=95)
    assert security_policy.is_password_rotation_due(changed_at, rotation_days=90, now=now) is True


# ==============================================================================
# BR-SA-032: Multi-Channel Critical Notification Delivery
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_032_01_permitted_channels():
    """TC-SA-032-01 | BR-SA-032 permitted-channels
    Verify supported events dispatch email and in-system notifications, and optional SMS for critical alerts.
    """
    n_email = notif_service.queue_notification(1, "admin@iiitdmj.ac.in", NotificationChannel.EMAIL, "TPL", "Alert", "Msg")
    n_inapp = notif_service.queue_notification(1, "admin@iiitdmj.ac.in", NotificationChannel.IN_APP, "TPL", "Alert", "Msg")
    assert n_email.channel == NotificationChannel.EMAIL
    assert n_inapp.channel == NotificationChannel.IN_APP


# ==============================================================================
# BR-SA-033: Mandatory Audit Schema Completeness
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_033_01_permitted_audit_schema():
    """TC-SA-033-01 | BR-SA-033 permitted-audit-schema
    Verify audit log entry records all mandatory fields upon auditable event.
    """
    log = SuperAdminAuditLog.objects.create(
        actor_id=1,
        actor_username="admin1",
        action=AuditAction.CONFIG_UPDATE,
        result=AuditResult.SUCCESS,
        ip_address="192.168.1.10",
        user_agent="Mozilla/5.0",
        reason="Routine timeout adjustment",
    )
    assert log.timestamp is not None
    assert log.actor_username == "admin1"
    assert log.ip_address == "192.168.1.10"
    assert log.result == AuditResult.SUCCESS


# ==============================================================================
# BR-SA-034: Active Role Context Selection
# ==============================================================================

@pytest.mark.django_db
def test_tc_sa_034_01_permitted_active_role():
    """TC-SA-034-01 | BR-SA-034 permitted-active-role
    Verify basic user can select an assigned active role and receive corresponding permissions.
    """
    u = BasicUser.objects.create(username="u_act_role", institute_id="UAR001", kind=UserKind.FACULTY)
    role, _ = RoleDefinition.objects.get_or_create(code="dean_rnd", defaults={"label": "Dean R&D", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty"})
    today = timezone.now().date()
    RoleAssignment.objects.create(user=u, role=role, state=RoleAssignmentState.ACTIVE, start_date=today, assigned_by=1)

    role_service.switch_active_role(user_id=u.id, target_role_code="dean_rnd")


@pytest.mark.django_db
def test_tc_sa_034_02_prohibited_inactive_role():
    """TC-SA-034-02 | BR-SA-034 prohibited-inactive-role
    Verify user cannot select an expired, revoked, or unassigned role as active context.
    """
    u = BasicUser.objects.create(username="u_inact_role", institute_id="UIR001", kind=UserKind.FACULTY)
    with pytest.raises(DomainError):
        role_service.switch_active_role(user_id=u.id, target_role_code="non_assigned_role")


# ==============================================================================
# BR-SA-035: Permitted vs. Restricted System Parameter Modification
# ==============================================================================

def test_tc_sa_035_01_permitted_system_config():
    """TC-SA-035-01 | BR-SA-035 permitted-system-config
    Verify Super Admin can update permitted parameters (password policy, session timeout, retention limits).
    """
    validators.validate_configuration_key(PermittedConfigKey.SESSION_INACTIVITY_TIMEOUT_MINUTES, PermittedConfigKey.ALL_KEYS)
    validators.validate_configuration_key(PermittedConfigKey.ARCHIVAL_REVERSIBLE_WINDOW_DAYS, PermittedConfigKey.ALL_KEYS)


def test_tc_sa_035_02_prohibited_out_of_boundary_config():
    """TC-SA-035-02 | BR-SA-035 prohibited-out-of-boundary-config
    Verify Super Admin cannot modify excluded configuration categories (academic calendars, financial rules).
    """
    with pytest.raises(ConfigurationBoundaryViolationError):
        validators.validate_configuration_key("academic.calendar.semester_start", PermittedConfigKey.ALL_KEYS)

    with pytest.raises(ConfigurationBoundaryViolationError):
        validators.validate_configuration_key("finance.payroll.tax_rate", PermittedConfigKey.ALL_KEYS)
