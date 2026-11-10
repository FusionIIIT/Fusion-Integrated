"""On-site roster reads (VMS-CFR-015, BR-105). Single-query, indexed on
`vms_log_pass_created_idx`.

A visitor is on site while the latest *presence* event of their pass is a
check-in or an allowed zone move. Presence events are check_in, zone_allowed,
check_out and auto_check_out; denials, overrides and ``terminated`` markers
never change presence. A terminated pass is deliberately still listed until
physical exit is recorded (BW-VMS-16/18 "On-site Pending Exit").
"""
from __future__ import annotations

from django.db.models import OuterRef, Subquery

from modules.vms.models import VisitLog, VisitPass

E = VisitLog.Event
ON_SITE_EVENTS = (E.CHECK_IN, E.ZONE_ALLOWED)
PRESENCE_EVENTS = (E.CHECK_IN, E.ZONE_ALLOWED, E.CHECK_OUT, E.AUTO_CHECK_OUT)


def _latest_presence(field: str):
    return Subquery(
        VisitLog.objects.filter(visit_pass=OuterRef("pk"), event__in=PRESENCE_EVENTS)
        .order_by("-created_at", "-id").values(field)[:1])


def on_site(*, zone=None):
    """Passes whose visitor is on site now. `zone` (id or Zone) limits to the
    zone of the latest presence event."""
    qs = (VisitPass.objects.select_related("visit_request__visitor")
          .annotate(last_event=_latest_presence("event"),
                    last_zone_id=_latest_presence("zone_id"))
          .filter(last_event__in=ON_SITE_EVENTS))
    if zone is not None:
        qs = qs.filter(last_zone_id=getattr(zone, "pk", zone))
    return qs.order_by("-id")


def open_check_in(pass_) -> VisitLog | None:
    """The check-in log still awaiting a check-out for this pass, else None."""
    last = (VisitLog.objects.filter(visit_pass=pass_, event__in=PRESENCE_EVENTS)
            .order_by("-created_at", "-id").first())
    if last is None or last.event not in ON_SITE_EVENTS:
        return None
    return (VisitLog.objects.filter(visit_pass=pass_, event=E.CHECK_IN)
            .order_by("-created_at", "-id").first()) or last


def visit_history(visitor):
    """Every gate log of every pass issued to `visitor`, newest first."""
    return (VisitLog.objects.filter(visit_pass__visit_request__visitor=visitor)
            .select_related("visit_pass", "zone", "gate").order_by("-created_at", "-id"))
