"""Which visit requests an actor may see. Wrong owner = not in the queryset = 404."""
from __future__ import annotations

from django.db.models import Q

from modules.vms.models import Gate, RoleAssignment, VisitRequest

from .authz import active_assignments


def requests_as_host(actor):
    return VisitRequest.objects.filter(host_user_id=actor.user_id)


def requests_as_visitor(actor):
    """A visitor session sees the requests it filed or that name it."""
    visitor_id = getattr(actor, "visitor_id", None)
    if visitor_id is not None:
        return VisitRequest.objects.filter(
            Q(visitor_id=visitor_id) | Q(created_by_visitor_id=visitor_id))
    return VisitRequest.objects.none()


def _admin_scope(actor):
    """None = no admin role; True = campus-wide; else a Q limiting by zone."""
    user_id = getattr(actor, "user_id", None)
    if user_id is None:
        return None
    rows = list(active_assignments(user_id).filter(role=RoleAssignment.Role.ADMIN))
    if not rows:
        return None
    zones = set()
    for a in rows:
        if a.scope_type == RoleAssignment.ScopeType.CAMPUS:
            return True
        if a.scope_type == RoleAssignment.ScopeType.ZONE:
            zones.add(a.scope_id)
        else:
            zones.update(Gate.objects.filter(pk=a.scope_id)
                         .values_list("zone_id", flat=True))
    return Q(requested_zones__in=zones)


def visible_requests(actor):
    """Own as host, own as visitor, everything for a campus Admin (zone-scoped
    Admins also see requests touching their zones)."""
    if actor is None:
        return VisitRequest.objects.none()
    admin = _admin_scope(actor)
    if admin is True:
        return VisitRequest.objects.all()
    qs = requests_as_visitor(actor)
    if getattr(actor, "user_id", None) is not None:
        qs = qs | requests_as_host(actor)
    if admin is not None:
        qs = qs | VisitRequest.objects.filter(admin)
    return qs.distinct()
