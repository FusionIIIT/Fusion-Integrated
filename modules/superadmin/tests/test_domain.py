"""Domain tests: pure Python, zero Django, zero database, sub-millisecond."""

from datetime import UTC, datetime, timedelta

import pytest

from modules.superadmin.domain.exceptions import (
    DualAuthorizationRequiredError,
    PolicyViolationError,
    ReversibilityExpiredError,
    SingularRoleConflictError,
    ValidationDomainError,
)
from modules.superadmin.domain.policy import (
    calculate_reversibility_expiry,
    check_separation_of_duties,
    check_singular_role_conflict,
    is_purge_eligible,
    is_role_singular,
    validate_reversibility_window,
    validate_role_compatibility,
)
from modules.superadmin.domain.validators import (
    validate_institute_email,
    validate_institute_id,
    validate_retention_period_days,
    validate_role_validity_dates,
    validate_user_id,
)


def test_validate_user_id_positive_integers():
    validate_user_id(1)
    validate_user_id(999999)
    with pytest.raises(ValidationDomainError, match="positive integer"):
        validate_user_id(0)
    with pytest.raises(ValidationDomainError, match="positive integer"):
        validate_user_id(-5)


def test_validate_institute_email_domain():
    validate_institute_email("student@iiitdmj.ac.in")
    validate_institute_email("dean.acad@iiitdmj.ac.in")
    with pytest.raises(ValidationDomainError, match="not an authorized institute domain"):
        validate_institute_email("hacker@gmail.com")
    with pytest.raises(ValidationDomainError, match="not an authorized institute domain"):
        validate_institute_email("student@yahoo.co.in")
    with pytest.raises(ValidationDomainError, match="valid email"):
        validate_institute_email("invalid-email-address")


def test_validate_institute_id():
    validate_institute_id("24BCS170")
    validate_institute_id("FAC_CSE_001")
    with pytest.raises(ValidationDomainError, match="cannot be blank"):
        validate_institute_id("")
    with pytest.raises(ValidationDomainError, match="cannot be blank"):
        validate_institute_id("   ")


def test_validate_retention_period():
    validate_retention_period_days(365)
    validate_retention_period_days(1825)
    with pytest.raises(ValidationDomainError, match="at least 365"):
        validate_retention_period_days(364)
    with pytest.raises(ValidationDomainError, match="at least 365"):
        validate_retention_period_days(0)


def test_validate_role_validity_dates():
    now = datetime.now(UTC)
    future = now + timedelta(days=30)
    validate_role_validity_dates(now, future)
    validate_role_validity_dates(now, None)  # indefinite valid_to is allowed
    with pytest.raises(ValidationDomainError, match="strictly after"):
        validate_role_validity_dates(future, now)


def test_singular_roles_check():
    assert is_role_singular("Dean of Academic Affairs") is True
    assert is_role_singular("Head of Department (CSE)") is True
    assert is_role_singular("Faculty Advisor") is False
    assert is_role_singular("Course Instructor") is False


def test_singular_role_conflict_prevention():
    # Attempting to assign singular role when already held by someone else raises error
    with pytest.raises(SingularRoleConflictError, match="already actively held"):
        check_singular_role_conflict(
            "Dean of Academic Affairs", current_holder_user_id=101, new_holder_user_id=102
        )

    # Re-assigning to the same holder is valid (no conflict with self)
    check_singular_role_conflict(
        "Dean of Academic Affairs", current_holder_user_id=101, new_holder_user_id=101
    )

    # Singular role with no current holder is valid
    check_singular_role_conflict(
        "Dean of Academic Affairs", current_holder_user_id=None, new_holder_user_id=102
    )


def test_role_compatibility_rules():
    # Student cannot hold executive or faculty governance roles
    with pytest.raises(PolicyViolationError, match="not eligible for administrative role"):
        validate_role_compatibility("STUDENT", "Dean of Academic Affairs")
    with pytest.raises(PolicyViolationError, match="not eligible for administrative role"):
        validate_role_compatibility("STUDENT", "Head of Department")

    # Faculty can hold Dean and HOD
    validate_role_compatibility("FACULTY", "Dean of Academic Affairs")
    validate_role_compatibility("FACULTY", "Head of Department")

    # Staff can hold staff roles
    validate_role_compatibility("STAFF", "Warden")


def test_calculate_reversibility_expiry():
    archival_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    expiry = calculate_reversibility_expiry(archival_date, window_days=90)
    assert expiry == datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)


def test_validate_reversibility_window():
    now = datetime.now(UTC)
    future_expiry = now + timedelta(days=10)
    past_expiry = now - timedelta(days=1)

    # Active window allows restoration
    validate_reversibility_window(future_expiry, current_time=now)

    # Expired window raises ReversibilityExpiredError
    with pytest.raises(ReversibilityExpiredError, match="expired"):
        validate_reversibility_window(past_expiry, current_time=now)


def test_purge_eligibility():
    now = datetime.now(UTC)
    past_purge_eligible = now - timedelta(days=1)
    future_purge_eligible = now + timedelta(days=10)

    # Eligible when purge_eligible_at <= now
    assert is_purge_eligible(past_purge_eligible, current_time=now) is True

    # Ineligible when purge_eligible_at > now
    assert is_purge_eligible(future_purge_eligible, current_time=now) is False


def test_separation_of_duties_dual_authorization():
    # Requester and authorizer must not be the same user
    with pytest.raises(DualAuthorizationRequiredError, match="distinct second authorizer"):
        check_separation_of_duties(requester_user_id=42, authorizer_user_id=42)

    # Distinct users satisfy separation of duties
    check_separation_of_duties(requester_user_id=42, authorizer_user_id=99)
