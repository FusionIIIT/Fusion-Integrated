"""
User Scoping for PSM Queries.
Enforces that out-of-scope requests return None/empty sets so API endpoints
return 404 Not Found rather than leaking existence via 403.
"""

from typing import Any
from django.db.models import QuerySet
from modules.psm.models import Indent


def _get_principal_user_id(principal: Any) -> int:
    """Safely extract integer user_id from principal or user object."""
    if principal is None:
        return 0
    if hasattr(principal, "user_id") and principal.user_id is not None:
        return int(principal.user_id)
    if hasattr(principal, "id") and principal.id is not None:
        return int(principal.id)
    if hasattr(principal, "pk") and principal.pk is not None:
        return int(principal.pk)
    return 0


def _is_ps_privileged(principal: Any) -> bool:
    """Check if the principal holds administrative / oversight role for PSM."""
    if principal is None:
        return False
    if getattr(principal, "is_superuser", False):
        return True

    active_role = str(getattr(principal, "active_role", "") or "").upper()
    privileged_roles = {
        "PS_ADMIN",
        "STORE_MANAGER",
        "STORE_OFFICER",
        "PURCHASE_OFFICER",
        "ADMIN",
        "DIRECTOR",
        "DEAN",
    }
    if active_role in privileged_roles:
        return True

    roles = getattr(principal, "roles", ())
    if any(str(r).upper() in privileged_roles for r in roles):
        return True

    if hasattr(principal, "has_permission"):
        if principal.has_permission("psm.indent.manage") or principal.has_permission("psm.indent.view_all"):
            return True

    return False


def get_visible_indents_for_user(principal: Any) -> QuerySet[Indent]:
    """Return indents visible to the user.

    PS_ADMIN / Store Officers see all indents. Standard employees see only their own.
    """
    qs = Indent.objects.all().order_by("-created_at")
    if _is_ps_privileged(principal):
        return qs

    user_id = _get_principal_user_id(principal)
    if not user_id:
        return qs.none()

    return qs.filter(requestor_id=user_id)
