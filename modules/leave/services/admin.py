from django.db import transaction

from modules.leave.domain import policy
from modules.leave.models import ReportingLine
from modules.leave.services.applications import LeaveError, get_balance


@transaction.atomic
def set_reporting_line(
    user_id: int, unit_head_id: int, establishment_id=None, sanctioning_authority_id=None
) -> ReportingLine:
    """
    Update or create the reporting line for a user.

    Raises LeaveError if unit_head_id is missing.
    """
    if unit_head_id is None:
        raise LeaveError("Unit head ID cannot be empty.")

    reporting_line, _created = ReportingLine.objects.update_or_create(
        user_id=user_id,
        defaults={
            "unit_head_id": unit_head_id,
            "establishment_id": establishment_id,
            "sanctioning_authority_id": sanctioning_authority_id,
        },
    )

    return reporting_line


@transaction.atomic
def ensure_balances(user_id: int, kind: str, year: int) -> list:
    """
    Ensure leave balances exist for all categories eligible for the given kind.

    Returns a list of LeaveBalance objects ordered by category name.
    """
    eligible_categories = []

    for category in policy.CATEGORIES:
        entitlement = policy.entitlement(category, kind)
        if entitlement is not None:
            eligible_categories.append(category)

    balances = []
    for category in eligible_categories:
        balance = get_balance(user_id, kind, category, year)
        balances.append(balance)

    return balances
