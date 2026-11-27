"""Balance query selectors for Employee Leave Management."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.leave.models import LeaveBalance


def get_user_balances(
    user_id: int | None,
    year: int | None = None,
) -> QuerySet[LeaveBalance]:
    """Return leave balances belonging strictly to user_id (EL-UC-012).

    Never exposes another employee's balance records.
    """
    if user_id is None:
        return LeaveBalance.objects.none()

    qs = (
        LeaveBalance.objects.filter(user_id=user_id)
        .select_related("leave_type")
        .order_by("leave_type__code", "-year")
    )
    if year is not None:
        qs = qs.filter(year=year)
    return qs
