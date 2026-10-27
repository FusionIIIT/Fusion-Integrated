"""All reads. Ownership filtering lives HERE — once per module, not once per
view — which is why a foreign id naturally yields 404 instead of 403."""
from __future__ import annotations

from django.db import models

from modules.leave.models import LeaveApplication, LeaveBalance


def applications_for(actor):
    """Returns applications visible to the actor."""
    base = LeaveApplication.objects.select_related("category")
    if getattr(actor, "has_permission", lambda p: False)("leave_management.application.view"):
        return base

    user_id = getattr(actor, "user_id", None)
    if not user_id:
        return LeaveApplication.objects.none()

    return base.filter(
        models.Q(user_id=user_id) | models.Q(substitute_user_id=user_id)
    )


def balances_for(actor):
    """Returns balances visible to the actor."""
    base = LeaveBalance.objects.select_related("category")
    has_perm = getattr(actor, "has_permission", lambda p: False)
    if has_perm("leave_management.balance.view") or has_perm("leave_management.balance.manage"):
        return base

    user_id = getattr(actor, "user_id", None)
    if not user_id:
        return LeaveBalance.objects.none()

    return base.filter(user_id=user_id)
