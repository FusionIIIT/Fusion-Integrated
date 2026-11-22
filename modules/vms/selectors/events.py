"""Event reads: lists, attendance, throughput, fast-lane manifest (VMS-AFR-160..162).

Read-only; used by the events API and by lane H's event reports.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from django.db.models import OuterRef, Subquery
from django.utils import timezone

from modules.vms.models import EventAttendee, EventBatch, VisitLog, VisitPass

E = VisitLog.Event
_PRESENCE = (E.CHECK_IN, E.CHECK_OUT, E.AUTO_CHECK_OUT)


def events(*, status: str | None = None):
    qs = EventBatch.objects.order_by("-valid_from", "-pk")
    return qs.filter(status=status) if status else qs


def attendees(event_id: int, *, status: str | None = None):
    qs = EventAttendee.objects.filter(batch_id=event_id).order_by("pk")
    return qs.filter(status=status) if status else qs


def attendance(event: EventBatch, now=None) -> dict:
    """invited / passes issued / checked in / no-show / currently inside (AFR-161)."""
    now = now or timezone.now()
    live = EventAttendee.objects.filter(batch=event).exclude(
        status=EventAttendee.Status.CANCELLED)
    invited = live.count()
    issued_ids = set(live.filter(visit_pass__isnull=False).values_list("visit_pass_id", flat=True))
    arrived = set(VisitLog.objects.filter(
        visit_pass_id__in=issued_ids, event=E.CHECK_IN).values_list("visit_pass_id", flat=True))
    last = (VisitLog.objects.filter(visit_pass_id=OuterRef("pk"), event__in=_PRESENCE)
            .order_by("-created_at", "-pk").values("event")[:1])
    inside = (VisitPass.objects.filter(pk__in=issued_ids).annotate(last_event=Subquery(last))
              .filter(last_event=E.CHECK_IN).count())
    not_arrived = len(issued_ids) - len(arrived)
    return {
        "event_id": event.pk, "invited": invited, "passes_issued": len(issued_ids),
        "checked_in": len(arrived), "current_inside": inside,
        "not_arrived": not_arrived,
        # a no-show can only be declared once the event window has closed
        "no_show": not_arrived if now > event.valid_until else 0,
        "cancelled": EventAttendee.objects.filter(
            batch=event, status=EventAttendee.Status.CANCELLED).count(),
    }


def throughput(event: EventBatch, bucket_minutes: int = 5) -> list[dict]:
    """Entries and exits per bucket, ordered by time (AFR-162)."""
    size = max(int(bucket_minutes), 1) * 60
    ins, outs = Counter(), Counter()
    rows = VisitLog.objects.filter(
        visit_pass__event=event, event__in=_PRESENCE).values_list("event", "created_at")
    for ev, at in rows.iterator():
        key = int(at.timestamp()) // size * size
        (ins if ev == E.CHECK_IN else outs)[key] += 1
    return [{"bucket_start": datetime.fromtimestamp(k, tz=UTC),
             "check_ins": ins[k], "check_outs": outs[k]}
            for k in sorted(set(ins) | set(outs))]


def fast_lane_manifest(event: EventBatch, now=None) -> list[dict]:
    """Active fast-lane passes for scanner caching. Carries QR tokens: callers must hold
    `vms.gate.sync`. The gate still validates every scan (UC-018)."""
    now = now or timezone.now()
    slots = {a.visit_pass_id: (a.slot_start, a.slot_end)
             for a in EventAttendee.objects.filter(batch=event, visit_pass__isnull=False)}
    passes = VisitPass.objects.filter(event=event, fast_lane=True, is_active=True,
                                      valid_until__gt=now).order_by("pk")
    return [{"pass_id": p.pk, "qr_token": p.qr_token, "valid_from": p.valid_from,
             "valid_until": p.valid_until, "slot_start": slots.get(p.pk, (None, None))[0],
             "slot_end": slots.get(p.pk, (None, None))[1]} for p in passes]
