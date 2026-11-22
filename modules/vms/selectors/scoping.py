"""VMS Role Scoping and Visibility.
Ensures rows a user may not see return 404s by scoping querysets at retrieval.
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.vms.models.access import GateAlert
from modules.vms.models.visits import Visit


def get_visible_visits_for_principal(principal: Any) -> QuerySet[Visit]:
    """Returns Visit QuerySet scoped by the user's evaluated role."""
    base_qs = Visit.objects.select_related("visitor")

    # If principal is an admin or security manager, they see all visits
    if getattr(principal, "is_admin", False) or getattr(principal, "is_superuser", False):
        return base_qs

    perms = getattr(principal, "permissions", set())
    if "vms.security.admin" in perms:
        return base_qs

    # Security guard sees approved, on_site, and completed visits for gate processing
    if "vms.gate.scan" in perms:
        return base_qs.filter(status__in=["approved", "on_site", "completed", "requested"])

    # Normal faculty/staff/student sees only visits hosted by them
    user_id = getattr(principal, "user_id", None) or getattr(principal, "id", None)
    if user_id:
        return base_qs.filter(host_user_id=user_id)

    return base_qs.none()


def get_visible_alerts_for_principal(principal: Any) -> QuerySet[GateAlert]:
    """Returns GateAlert QuerySet scoped by role."""
    perms = getattr(principal, "permissions", set())
    if (
        getattr(principal, "is_superuser", False)
        or "vms.security.admin" in perms
        or "vms.gate.scan" in perms
    ):
        return GateAlert.objects.all().order_by("-created_at")
    return GateAlert.objects.none()
