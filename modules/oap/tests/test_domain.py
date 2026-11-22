"""Unit tests for OAP domain logic and validators."""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from modules.oap.domain.exceptions import IneligibleRequestError, OAPDomainError
from modules.oap.domain.validators import (
    validate_branch_change_eligibility,
    validate_leave_dates,
    validate_medical_certificate,
)


def test_validate_leave_dates():
    start = datetime.date(2026, 12, 1)
    end = datetime.date(2026, 12, 5)
    validate_leave_dates(start, end)

    with pytest.raises(OAPDomainError, match="End date cannot be prior to start date"):
        validate_leave_dates(end, start)


def test_validate_medical_certificate():
    validate_medical_certificate("CASUAL", 5, None)
    validate_medical_certificate("MEDICAL", 2, None)
    validate_medical_certificate("MEDICAL", 5, "http://evidence.test/cert.pdf")

    with pytest.raises(OAPDomainError, match="strictly requires an attached medical certificate"):
        validate_medical_certificate("MEDICAL", 4, None)


def test_validate_branch_change_eligibility():
    validate_branch_change_eligibility(
        cpi=Decimal("8.50"), credits_completed=40, has_backlogs=False
    )

    with pytest.raises(IneligibleRequestError, match="backlogs are ineligible"):
        validate_branch_change_eligibility(
            cpi=Decimal("8.50"), credits_completed=40, has_backlogs=True
        )

    with pytest.raises(IneligibleRequestError, match="Minimum CPI required"):
        validate_branch_change_eligibility(
            cpi=Decimal("7.80"), credits_completed=40, has_backlogs=False
        )

    with pytest.raises(IneligibleRequestError, match="credits required"):
        validate_branch_change_eligibility(
            cpi=Decimal("8.50"), credits_completed=32, has_backlogs=False
        )
