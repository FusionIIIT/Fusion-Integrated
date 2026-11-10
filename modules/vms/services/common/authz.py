"""Authorization helpers: IAM permissions, time-bound VMS roles, implicit host.

BR-181 roles are time-bound, BR-182 a reassignment takes effect at once (every
check reads the table), BR-184 hierarchy Super Admin > Admin > Security,
BR-185 faculty/staff are hosts without an assignment.
"""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.vms.models import Gate, RoleAssignment

HOST_KINDS = frozenset({"faculty", "staff"})   # BR-185
#: A role also satisfies every role below it (BR-184).
_SATISFIES = {
    RoleAssignment.Role.ADMIN: {"admin", "security"},
    RoleAssignment.Role.SECURITY: {"security"},
}


def require(actor, *perm_codes: str) -> None:
    """IAM permission check for services; every code is required."""
    if actor is None or not all(actor.has_permission(c) for c in perm_codes):
        raise PermissionDeniedError()


def is_host(actor) -> bool:
    """Faculty/staff are hosts implicitly (BR-185)."""
    if actor is None:
        return False
    return (getattr(actor, "kind", "") in HOST_KINDS
            or bool(HOST_KINDS & set(getattr(actor, "roles", ()) or ())))


def active_assignments(user_id, at=None):
    at = at or timezone.now()
    return RoleAssignment.objects.filter(
        user_id=user_id, revoked_at__isnull=True, starts_at__lte=at, ends_at__gt=at)


def require_role(actor, role, *, zone_id=None, gate_id=None, at=None) -> RoleAssignment:
    """Return the active assignment that grants `role`, or raise PermissionDenied.

    With no zone/gate any active assignment of the role qualifies. With a
    target, the assignment must be campus-wide or scoped to that zone, that
    gate, or (for a gate) the gate's zone.
    """
    role = getattr(role, "value", role)
    if actor is None or getattr(actor, "user_id", None) is None:
        raise PermissionDeniedError()
    roles = [r for r, ok in _SATISFIES.items() if role in ok]
    qs = active_assignments(actor.user_id, at).filter(role__in=roles)
    if zone_id is not None or gate_id is not None:
        scope = Q(scope_type=RoleAssignment.ScopeType.CAMPUS)
        zone_ids = set()
        if zone_id is not None:
            zone_ids.add(zone_id)
        if gate_id is not None:
            scope |= Q(scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate_id)
            gate_zone = (Gate.objects.filter(pk=gate_id)
                         .values_list("zone_id", flat=True).first())
            if gate_zone is not None:
                zone_ids.add(gate_zone)
        if zone_ids:
            scope |= Q(scope_type=RoleAssignment.ScopeType.ZONE, scope_id__in=zone_ids)
        qs = qs.filter(scope)
    assignment = qs.order_by("-ends_at").first()
    if assignment is None:
        raise PermissionDeniedError()
    return assignment
