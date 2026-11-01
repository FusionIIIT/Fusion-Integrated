"""Unit tests for Super Admin domain policies."""
from datetime import UTC, date, datetime, timedelta

import pytest

from modules.superadmin.domain import policy
from modules.superadmin.domain.policy import DomainValidationError


def test_email_validation() -> None:
    policy.validate_institute_email("24bcs170@iiitdmj.ac.in")
    with pytest.raises(DomainValidationError):
        policy.validate_institute_email("user@gmail.com")


def test_archival_and_reversibility() -> None:
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    deactivated = now - timedelta(days=35)
    policy.validate_archival_eligibility("DEACTIVATED", deactivated, now=now, min_days=30)

    window = policy.calculate_reversible_window(now, window_days=90)
    policy.validate_archived_user_restoration("ARCHIVED_REVERSIBLE", window, now=now)

    with pytest.raises(DomainValidationError):
        policy.validate_archived_user_restoration("ARCHIVED_PERMANENT", window, now=now)


def test_role_rules() -> None:
    policy.validate_role_dating(date(2026, 8, 1), date(2026, 12, 31))
    with pytest.raises(DomainValidationError):
        policy.validate_role_dating(date(2026, 8, 1), date(2026, 7, 1))

    policy.validate_singular_role_occupancy("DEAN_ACADEMICS", "INSTITUTE", [])
    with pytest.raises(DomainValidationError):
        policy.validate_singular_role_occupancy("DEAN_ACADEMICS", "INSTITUTE", ["INSTITUTE"])

    with pytest.raises(DomainValidationError):
        policy.validate_role_revocation("")
