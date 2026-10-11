"""Read paths. Ownership and scope live here, not in views."""
from __future__ import annotations

from modules.elm.models import LeaveApplication, LeaveBalance

#: Statuses that count as "active" for overlap purposes.
ACTIVE_STATUSES = ("submitted", "approved")


def visible_applications(principal):
    """Applications the caller may see: their own, or everything if they hold
    the scoped view permission."""
    if principal.has_permission("elm.application.view"):
        return LeaveApplication.objects.all()
    return LeaveApplication.objects.filter(user_id=principal.user_id)


def balances_for(user_id: int, year: int):
    return (LeaveBalance.objects
            .filter(user_id=user_id, year=year)
            .order_by("category"))
