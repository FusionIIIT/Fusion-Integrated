"""Live visitor monitoring (VMS-CFR-017, VMS-UC-022).

Composes lane D's `roster.on_site` (the single source of "who is inside") with
the monitor selectors. Everything is scoped to the caller's active admin or
security assignments (BR-181): a zone-scoped guard sees only their zones.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.vms.selectors import monitor as sel
from modules.vms.selectors import roster
from modules.vms.services.common import authz

RECENT_DENIALS = 10


def _directory_users(user_ids):
    return directory.get_users(sorted(set(user_ids)))


def _scope(actor) -> sel.Scope:
    authz.require(actor, "vms.monitor.view")
    scope = sel.scope_for(actor.user_id)
    if not scope:
        raise PermissionDeniedError()
    return scope


def _onsite_qs(scope: sel.Scope, zone_id=None):
    if zone_id is not None and not scope.allows_zone(zone_id):
        raise PermissionDeniedError()
    qs = roster.on_site(zone=zone_id)
    if not scope.all:
        qs = qs.filter(last_zone_id__in=sorted(scope.zone_ids))
    return qs


def on_site(*, actor, zone_id=None) -> list[dict]:
    """The live on-site list: who, where, since when, whose guest (UC-022)."""
    scope = _scope(actor)
    rows = sel.onsite_rows(_onsite_qs(scope, zone_id))
    zones = sel.zone_names(r["zone_id"] for r in rows)
    users = _directory_users(r["host_user_id"] for r in rows)
    now = timezone.now()
    for r in rows:
        host = users.get(r["host_user_id"])
        r["zone_name"] = zones.get(r["zone_id"], {}).get("name", "")
        r["host_name"] = host.display_name if host else ""
        r["host_department"] = host.department if host else ""
        r["overstay"] = r["valid_until"] < now
    return rows


def dashboard(*, actor, zone_id=None) -> dict:
    """Counts only (no PII): on-site total, by zone, by host department, open
    alerts, recent denials and overstays (on site past the pass end)."""
    scope = _scope(actor)
    rows = sel.onsite_rows(_onsite_qs(scope, zone_id))
    now = timezone.now()
    zones = sel.zone_names(r["zone_id"] for r in rows)
    users = _directory_users(r["host_user_id"] for r in rows)
    by_zone = Counter(r["zone_id"] for r in rows)
    by_dept = Counter((users[r["host_user_id"]].department if r["host_user_id"] in users
                       else "") or "unknown" for r in rows)
    overstays = sorted((r for r in rows if r["valid_until"] < now),
                       key=lambda r: r["valid_until"])
    alerts = sel.open_alert_counts(scope)
    return {
        "on_site": len(rows),
        "by_zone": [{"zone_id": z, "zone_name": zones.get(z, {}).get("name", ""),
                     "count": n} for z, n in sorted(by_zone.items(), key=lambda kv: -kv[1])],
        "by_department": [{"department": d, "count": n}
                          for d, n in sorted(by_dept.items(), key=lambda kv: -kv[1])],
        "open_alerts": {"total": sum(alerts.values()), "by_kind": alerts},
        "recent_denials": sel.recent_denials(scope, RECENT_DENIALS),
        "overstays": {"count": len(overstays),
                      "passes": [{"pass_id": r["pass_id"], "valid_until": r["valid_until"],
                                  "zone_id": r["zone_id"]} for r in overstays[:20]]},
        "as_of": now,
    }


def movements(*, actor, pass_id=None, zone_id=None, since: datetime | None = None) -> list:
    """Ordered zone/presence events for one pass or one zone."""
    scope = _scope(actor)
    if pass_id is None and zone_id is None:
        raise BadRequestError("pass_id or zone_id is required.", code="filter_required")
    if zone_id is not None and not scope.allows_zone(zone_id):
        raise PermissionDeniedError()
    return sel.movements(scope, pass_id=pass_id, zone_id=zone_id, since=since)


def out_of_bounds(*, actor) -> list[dict]:
    """Geofence list: visitors whose latest zone event is a denial or an unpermitted
    move into a restricted zone (CFR-017)."""
    scope = _scope(actor)
    rows = sel.out_of_bounds(_onsite_qs(scope), scope)
    users = _directory_users(r["host_user_id"] for r in rows)
    for r in rows:
        host = users.get(r["host_user_id"])
        r["host_name"] = host.display_name if host else ""
    return rows
