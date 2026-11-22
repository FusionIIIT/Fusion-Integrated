from datetime import date, timedelta
from decimal import Decimal

from modules.pms.domain.validation import ValidationError


def calculate_statutory_fer_deadline(issue_date: date) -> date:
    """Calculate Indian Patent Office statutory FER response deadline (6 months from issue date)."""
    # 180 days approximate statutory period (Section 21, Patents Rules)
    return issue_date + timedelta(days=180)


def calculate_annuity_grace_period(due_date: date) -> date:
    """Calculate patent maintenance renewal grace period (6 months with surcharge)."""
    return due_date + timedelta(days=180)


def verify_appeal_eligibility(rejection_date: date, appeal_date: date) -> None:
    """Verify that an appeal against institutional rejection is filed within 30 days (BR-PMS-038)."""
    max_deadline = rejection_date + timedelta(days=30)
    if appeal_date > max_deadline:
        raise ValidationError(
            f"Appeal window has expired. Appeals must be filed within 30 days of rejection "
            f"(deadline was {max_deadline}, attempted on {appeal_date})."
        )


def verify_budget_sanction(requested_amount: Decimal, approved_amount: Decimal) -> bool:
    """Check whether approved budget covers the requested filing and attorney costs (BR-PMS-041)."""
    return approved_amount >= requested_amount
