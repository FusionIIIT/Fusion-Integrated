"""Read side of live monitoring (VMS-CFR-017, UC-022).

Selectors here never import another lane's selector. The on-site queryset is
built by the service (lane D's `roster.on_site`) and handed in, already
annotated with ``last_zone_id`` / ``last_event``.
"""
from __future__ import annotations

from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from modules.vms.models import (
    Alert,
    Gate,
    RoleAssignment,
    VisitLog,
    VisitPass,
    Zone,
    ZoneElevation,
)

E = VisitLog.Event
_PRESENCE = (E.CHECK_IN, E.ZONE_ALLOWED, E.CHECK_OUT, E.AUTO_CHECK_OUT)
_ZONE_EVENTS = (E.ZONE_ALLOWED, E.ZONE_DENIED)
MOVEMENT_EVENTS = (E.CHECK_IN, E.ZONE_ALLOWED, E.ZONE_DENIED, E.CHECK_OUT, E.AUTO_CHECK_OUT)


class Scope:
    """What a role holder may see. ``all`` means campus-wide."""

    def __init__(self, *, all_=False, zone_ids=(), gate_ids=()):
        self.all = all_
        self.zone_ids = frozenset(zone_ids)
        self.gate_ids = frozenset(gate_ids)

    def __bool__(self) -> bool:
        return self.all or bool(self.zone_ids or self.gate_ids)

    def allows_zone(self, zone_id) -> bool:
        return self.all or zone_id in self.zone_ids


def scope_for(user_id: int, at=None) -> Scope:
    """Zones/gates covered by the user's active admin/security assignments."""
    at = at or timezone.now()
    rows = list(RoleAssignment.objects.filter(
        user_id=user_id, revoked_at__isnull=True, starts_at__lte=at, ends_at__gt=at)
        .values_list("scope_type", "scope_id"))
    if any(t == RoleAssignment.ScopeType.CAMPUS for t, _ in rows):
        return Scope(all_=True)
    zones = {i for t, i in rows if t == RoleAssignment.ScopeType.ZONE}
    gates = {i for t, i in rows if t == RoleAssignment.ScopeType.GATE}
    if zones or gates:
        for gid, zid in Gate.objects.filter(Q(pk__in=gates) | Q(zone_id__in=zones)).values_list(
                "pk", "zone_id"):
            gates.add(gid)
            zones.add(zid)
    return Scope(zone_ids=zones, gate_ids=gates)


def _latest(event_types, field):
    return Subquery(
        VisitLog.objects.filter(visit_pass=OuterRef("pk"), event__in=event_types)
        .order_by("-created_at", "-id").values(field)[:1])


def with_last_seen(qs):
    """Annotate ``last_seen_at``: time of the latest presence event."""
    return qs.annotate(last_seen_at=_latest(_PRESENCE, "created_at"))


def onsite_rows(qs) -> list[dict]:
    """One query: the facts the dashboard and list need, no model instances."""
    out = []
    rows = with_last_seen(qs).values_list(
        "pk", "last_zone_id", "last_seen_at", "valid_until", "terminated_at",
        "visit_request__host_user_id", "visit_request__visitor__full_name",
        "visit_request__visitor__phone", "visit_request__visitor__email")
    for pk, zone_id, seen, until, term, host, name, phone, email in rows:
        out.append({"pass_id": pk, "zone_id": zone_id, "last_seen_at": seen,
                    "valid_until": until, "terminated": term is not None,
                    "host_user_id": host, "visitor_name": name,
                    "visitor_phone": phone, "visitor_email": email})
    return out


def zone_names(zone_ids) -> dict[int, dict]:
    ids = {z for z in zone_ids if z is not None}
    if not ids:
        return {}
    return {z.pk: {"name": z.name, "is_restricted": z.is_restricted}
            for z in Zone.objects.filter(pk__in=ids)}


def _alert_scope_q(scope: Scope):
    return (Q(detail__zone_id__in=sorted(scope.zone_ids))
            | Q(detail__gate_id__in=sorted(scope.gate_ids)))


def open_alert_counts(scope: Scope) -> dict[str, int]:
    qs = Alert.objects.filter(status=Alert.Status.OPEN)
    if not scope.all:
        qs = qs.filter(_alert_scope_q(scope))
    counts: dict[str, int] = {}
    for kind in qs.values_list("kind", flat=True):
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def recent_denials(scope: Scope, limit: int = 10) -> list[dict]:
    qs = VisitLog.objects.filter(event__in=(E.DENIED, E.ZONE_DENIED))
    if not scope.all:
        qs = qs.filter(Q(zone_id__in=scope.zone_ids) | Q(gate_id__in=scope.gate_ids))
    rows = qs.order_by("-created_at", "-id").values_list(
        "pk", "visit_pass_id", "event", "zone_id", "gate_id", "reason", "created_at")[:limit]
    return [{"visit_log_id": a, "pass_id": b, "event": c, "zone_id": d, "gate_id": e,
             "reason": r, "at": t} for a, b, c, d, e, r, t in rows]


def movements(scope: Scope, *, pass_id=None, zone_id=None, since=None, limit=500):
    """Zone and presence events, oldest first, limited to the caller's scope."""
    qs = VisitLog.objects.filter(event__in=MOVEMENT_EVENTS)
    if pass_id is not None:
        qs = qs.filter(visit_pass_id=pass_id)
    if zone_id is not None:
        qs = qs.filter(zone_id=zone_id)
    if since is not None:
        qs = qs.filter(created_at__gte=since)
    if not scope.all:
        qs = qs.filter(zone_id__in=scope.zone_ids)
    return list(qs.select_related("zone").order_by("created_at", "id")[:limit])


def out_of_bounds(onsite_qs, scope: Scope) -> list[dict]:
    """On-site passes whose latest zone event is a denial, or an allowed move into a
    restricted zone the pass has no permission for (CFR-017 geofence)."""
    qs = onsite_qs.annotate(zone_ev=_latest(_ZONE_EVENTS, "event"),
                            zone_ev_zone=_latest(_ZONE_EVENTS, "zone_id"),
                            zone_ev_at=_latest(_ZONE_EVENTS, "created_at"),
                            zone_ev_reason=_latest(_ZONE_EVENTS, "reason")
                            ).filter(zone_ev__isnull=False)
    rows = list(qs.values_list(
        "pk", "zone_ev", "zone_ev_zone", "zone_ev_at", "zone_ev_reason",
        "visit_request__visitor__full_name", "visit_request__host_user_id"))
    if not scope.all:
        rows = [r for r in rows if r[2] in scope.zone_ids]
    if not rows:
        return []
    zones = zone_names(r[2] for r in rows)
    pass_ids = [r[0] for r in rows]
    permitted = set(VisitPass.allowed_zones.through.objects.filter(
        visitpass_id__in=pass_ids,
        zone_id__in=[z for z, v in zones.items() if v["is_restricted"]]
    ).values_list("visitpass_id", "zone_id"))
    now = timezone.now()
    permitted |= set(ZoneElevation.objects.filter(
        visit_pass_id__in=pass_ids, revoked_at__isnull=True,
        starts_at__lte=now, ends_at__gt=now).values_list("visit_pass_id", "zone_id"))
    out = []
    for pk, ev, zone_id, at, reason, name, host in rows:
        info = zones.get(zone_id, {})
        if ev == E.ZONE_DENIED:
            why = "zone_denied"
        elif (info.get("is_restricted") and (pk, zone_id) not in permitted
              and reason != "vip_override"):
            why = "restricted_without_permission"
        else:
            continue
        out.append({"pass_id": pk, "visitor_name": name, "host_user_id": host,
                    "zone_id": zone_id, "zone_name": info.get("name", ""),
                    "since": at, "reason": why, "detail": reason})
    out.sort(key=lambda r: r["since"], reverse=True)
    return out
