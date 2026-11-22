"""Domain validation functions for Other Academic Procedures business rules."""
from __future__ import annotations

import datetime
from decimal import Decimal

from modules.oap.domain.exceptions import IneligibleRequestError, OAPDomainError


def validate_leave_dates(start_date: datetime.date, end_date: datetime.date):
    if end_date < start_date:
        raise OAPDomainError("End date cannot be prior to start date.")


def validate_medical_certificate(
    leave_type: str, duration_days: int, document_url: str | None
):
    if leave_type == "MEDICAL" and duration_days > 3 and not document_url:
        msg = "Medical leave exceeding 3 days strictly requires an attached medical certificate."
        raise OAPDomainError(msg)


def validate_branch_change_eligibility(
    cpi: Decimal,
    credits_completed: int,
    has_backlogs: bool,
    min_cpi: Decimal = Decimal("8.00"),
    min_credits: int = 36,
):
    if has_backlogs:
        raise IneligibleRequestError(
            "Students with active academic backlogs are ineligible for branch change."
        )
    if cpi < min_cpi:
        raise IneligibleRequestError(
            f"Minimum CPI required is {min_cpi}. Student CPI is {cpi}."
        )
    if credits_completed < min_credits:
        raise IneligibleRequestError(
            f"Minimum {min_credits} credits required. Student completed {credits_completed}."
        )
