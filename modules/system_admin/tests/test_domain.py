"""Domain tests: pure Python, zero database, sub-millisecond execution."""
from datetime import UTC, date, datetime, timedelta

import pytest

from modules.system_admin.domain.exceptions import (
    ArchivalReversibilityExpiredError,
    DomainValidationError,
    IneligibleUserTypeError,
    InvalidDateRangeError,
    InvalidEmailDomainError,
    InvalidStateTransitionError,
    ParameterOutOfBoundsError,
    RetentionNotElapsedError,
    SeparationOfDutiesConflictError,
    SingularRoleOccupancyError,
    UserNotEligibleForArchivalError,
)
from modules.system_admin.domain.models import UserIdentity
from modules.system_admin.domain.rules import (
    validate_archival_eligibility,
    validate_institute_email,
    validate_institute_id,
    validate_purge_eligibility,
    validate_restoration_window,
    validate_role_dates,
    validate_singular_role_occupancy,
    validate_sod_conflicts,
    validate_system_parameters,
    validate_user_type_data,
    validate_user_type_role_eligibility,
)
from modules.system_admin.domain.state_machines import (
    transition_purge_state,
    transition_role_state,
    transition_user_state,
)


# ---- BR-SA-001: Institute ID validation ----
def test_institute_id_valid():
    validate_institute_id("2024BCS001")
    validate_institute_id("FAC_CSE_101")


def test_institute_id_blank_or_too_long():
    with pytest.raises(DomainValidationError):
        validate_institute_id("")
    with pytest.raises(DomainValidationError):
        validate_institute_id("   ")
    with pytest.raises(DomainValidationError):
        validate_institute_id("A" * 33)


# ---- BR-SA-002: Institute Email domain validation ----
def test_institute_email_valid():
    validate_institute_email("student@iiitdmj.ac.in")
    validate_institute_email("faculty.cse@iiitdmj.ac.in")


def test_institute_email_invalid():
    with pytest.raises(InvalidEmailDomainError):
        validate_institute_email("user@gmail.com")
    with pytest.raises(InvalidEmailDomainError):
        validate_institute_email("user@yahoo.com")
    with pytest.raises(InvalidEmailDomainError):
        validate_institute_email("")


# ---- BR-SA-003: User type profile constraints ----
def test_student_data_validation():
    valid_student = UserIdentity(
        institute_id="2024BCS001",
        username="ranjith",
        email="ranjith@iiitdmj.ac.in",
        user_type="student",
        discipline="CSE",
        programme="B.Tech",
        batch_year=2024,
    )
    validate_user_type_data(valid_student)

    # Missing discipline & programme
    invalid_student = UserIdentity(
        institute_id="2024BCS002",
        username="john",
        email="john@iiitdmj.ac.in",
        user_type="student",
        discipline="",
        programme="",
        batch_year=2024,
    )
    with pytest.raises(DomainValidationError):
        validate_user_type_data(invalid_student)


def test_faculty_staff_data_validation():
    valid_faculty = UserIdentity(
        institute_id="FAC001",
        username="prof_smith",
        email="smith@iiitdmj.ac.in",
        user_type="faculty",
        department="Computer Science and Engineering",
    )
    validate_user_type_data(valid_faculty)

    invalid_faculty = UserIdentity(
        institute_id="FAC002",
        username="prof_jones",
        email="jones@iiitdmj.ac.in",
        user_type="faculty",
        department="",
    )
    with pytest.raises(DomainValidationError):
        validate_user_type_data(invalid_faculty)


# ---- BR-SA-008: Role duration bounds ----
def test_role_dates_validation():
    today = date(2026, 11, 20)
    # Valid 1 year role
    validate_role_dates(start_date=today, end_date=today + timedelta(days=365))

    # Inverted dates
    with pytest.raises(InvalidDateRangeError):
        validate_role_dates(start_date=today, end_date=today - timedelta(days=1))


# ---- BR-SA-007: Singular role occupancy ----
def test_singular_role_occupancy():
    validate_singular_role_occupancy("dean_academics", is_singular=True, current_active_holders=0)
    validate_singular_role_occupancy("tpo", is_singular=False, current_active_holders=5)

    with pytest.raises(SingularRoleOccupancyError):
        validate_singular_role_occupancy("dean_academics", is_singular=True, current_active_holders=1)


# ---- BR-SA-010: User type role eligibility ----
def test_role_eligibility():
    validate_user_type_role_eligibility("faculty", "dean_academics")
    validate_user_type_role_eligibility("staff", "finance_officer")
    validate_user_type_role_eligibility("student", "student_senator")

    with pytest.raises(IneligibleUserTypeError):
        validate_user_type_role_eligibility("student", "dean_academics")

    with pytest.raises(IneligibleUserTypeError):
        validate_user_type_role_eligibility("faculty", "student_senator")


# ---- BR-SA-011: Separation of Duties (SOD) ----
def test_sod_conflicts():
    validate_sod_conflicts(new_role="dean_academics", active_roles=["tpo"])

    with pytest.raises(SeparationOfDutiesConflictError):
        validate_sod_conflicts(new_role="finance_officer", active_roles=["internal_auditor"])

    with pytest.raises(SeparationOfDutiesConflictError):
        validate_sod_conflicts(new_role="hod_cse", active_roles=["dean_academics"])


# ---- BR-SA-004: Archival eligibility ----
def test_archival_eligibility():
    now = datetime(2026, 11, 20, tzinfo=UTC)
    validate_archival_eligibility(
        status="deactivated",
        deactivation_date=now - timedelta(days=35),
        current_time=now,
    )

    with pytest.raises(UserNotEligibleForArchivalError):
        validate_archival_eligibility(
            status="active",
            deactivation_date=now - timedelta(days=35),
            current_time=now,
        )

    with pytest.raises(UserNotEligibleForArchivalError):
        validate_archival_eligibility(
            status="deactivated",
            deactivation_date=now - timedelta(days=10),
            current_time=now,
            min_interval_days=30,
        )


# ---- BR-SA-005: Restoration window ----
def test_restoration_window():
    now = datetime(2026, 11, 20, tzinfo=UTC)
    archived_at = now - timedelta(days=30)
    validate_restoration_window(
        is_permanent=False,
        archived_at=archived_at,
        window_days=90,
        current_time=now,
    )

    with pytest.raises(ArchivalReversibilityExpiredError):
        old_archive = now - timedelta(days=100)
        validate_restoration_window(
            is_permanent=False,
            archived_at=old_archive,
            window_days=90,
            current_time=now,
        )

    with pytest.raises(ArchivalReversibilityExpiredError):
        validate_restoration_window(
            is_permanent=True,
            archived_at=archived_at,
            window_days=90,
            current_time=now,
        )


# ---- BR-SA-021: Purge eligibility ----
def test_purge_retention():
    now = datetime(2026, 11, 20, tzinfo=UTC)
    old_archive = now - timedelta(days=8 * 365)
    validate_purge_eligibility(
        archived_at=old_archive,
        retention_years=7,
        current_time=now,
    )

    with pytest.raises(RetentionNotElapsedError):
        recent_archive = now - timedelta(days=5 * 365)
        validate_purge_eligibility(
            archived_at=recent_archive,
            retention_years=7,
            current_time=now,
        )


# ---- BR-SA-035: System parameters validation ----
def test_system_parameters_validation():
    valid_params = {
        "bulk_operation_limit": 500,
        "session_timeout_minutes": 30,
        "archival_retention_years": 7,
    }
    validate_system_parameters(valid_params)

    with pytest.raises(ParameterOutOfBoundsError):
        validate_system_parameters({"bulk_operation_limit": 2000})

    with pytest.raises(ParameterOutOfBoundsError):
        validate_system_parameters({"session_timeout_minutes": 2})

    with pytest.raises(ParameterOutOfBoundsError):
        validate_system_parameters({"financial_audit_threshold": 50000})


# ---- State Machine transitions ----
def test_user_lifecycle_state_machine():
    assert transition_user_state("active", "deactivate", "super_admin") == "deactivated"
    assert transition_user_state("deactivated", "reactivate", "super_admin") == "active"
    assert transition_user_state("deactivated", "archive", "super_admin") == "archived"
    assert transition_user_state("archived", "restore", "super_admin") == "active"

    with pytest.raises(InvalidStateTransitionError):
        transition_user_state("active", "restore", "super_admin")


def test_role_state_machine():
    assert transition_role_state("none", "assign_immediate", "super_admin") == "active"
    assert transition_role_state("none", "assign_future", "super_admin") == "scheduled"
    assert transition_role_state("scheduled", "reach_start_date", "system") == "active"
    assert transition_role_state("active", "revoke_standard", "super_admin") == "revoked"
    assert transition_role_state("active", "reach_end_date", "system") == "expired"

    with pytest.raises(InvalidStateTransitionError):
        transition_role_state("expired", "revoke_standard", "super_admin")


def test_purge_state_machine():
    assert transition_purge_state("archived_retention_elapsed", "request_purge", "super_admin") == "pending_it_head"
    assert transition_purge_state("pending_it_head", "approve", "it_head") == "permanently_purged"
    assert transition_purge_state("pending_it_head", "reject", "it_head") == "purge_rejected_retained"

    with pytest.raises(InvalidStateTransitionError):
        transition_purge_state("pending_it_head", "approve", "super_admin")


def test_boundary_rules_branches():
    from modules.system_admin.domain.models import UserIdentity
    from modules.system_admin.domain.rules import (
        validate_restoration_window,
        validate_role_dates,
        validate_system_parameters,
        validate_user_type_data,
    )

    # Student batch year missing
    u_stu = UserIdentity(
        institute_id="2024BCS001",
        username="stu",
        email="stu@iiitdmj.ac.in",
        user_type="student",
        programme="B.Tech",
        discipline="CSE",
        batch_year=None,
    )
    with pytest.raises(DomainValidationError, match="batch year"):
        validate_user_type_data(u_stu)

    # Faculty department missing
    u_fac = UserIdentity(
        institute_id="FAC001",
        username="fac",
        email="fac@iiitdmj.ac.in",
        user_type="faculty",
        department="",
    )
    with pytest.raises(DomainValidationError, match="department"):
        validate_user_type_data(u_fac)

    # Missing start date
    with pytest.raises(InvalidDateRangeError):
        validate_role_dates(start_date=None, end_date=date(2026, 12, 31))

    # Missing end date for time bound role
    with pytest.raises(InvalidDateRangeError):
        validate_role_dates(start_date=date(2026, 1, 1), end_date=None, is_time_bound=True)

    # Restoration window expired
    arch_date = datetime(2020, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ArchivalReversibilityExpiredError):
        validate_restoration_window(is_permanent=False, archived_at=arch_date, window_days=90, current_time=now)

    # Retention years boundary
    with pytest.raises(ParameterOutOfBoundsError):
        validate_system_parameters({"archival_retention_years": 999})
