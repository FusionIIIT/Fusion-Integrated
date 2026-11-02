"""Emergency muster: trigger, roll-call, finalise.

VMS-BR-045  a roster entry that runs more than the grace minutes (default
            15) past the muster deadline is EVICTED at finalisation —
            the one rule the eviction clock implements.
"""
from __future__ import annotations

from django.utils import timezone

from modules.vms.models import Muster, MusterEntry, Pass, Visit, Visitor
from modules.vms.services import policies
from modules.vms.services.alerts import open_alert
from modules.vms.services.errors import MusterStateError, NotFoundError


def trigger_muster(*, actor, reason: str = "",
                   muster_type: str = "EMERGENCY") -> Muster:
    """Freeze the on-site roster the moment the muster starts.

    The snapshot is what the offline roll-call works from when connectivity
    drops (VMS-CFR-018); the entries are the live roll-call rows.
    """
    now = timezone.now()
    muster = Muster.objects.create(
        muster_type=muster_type, reason=reason,
        triggered_by_user_id=getattr(actor, "user_id", 0) or 0,
        started_at=now)

    snapshot = []
    for visit in Visit.objects.filter(status="ON_SITE").order_by("id"):
        active = (Pass.objects
                  .filter(visit_id=visit.id, status="ACTIVE")
                  .order_by("-id")
                  .first())
        zone = active.permitted_zones[0] if active and active.permitted_zones \
            else ""
        MusterEntry.objects.create(
            muster=muster, visit_id=visit.id, visitor_id=visit.visitor_id,
            host_user_id=visit.host_user_id, last_seen_zone=zone,
            last_seen_at=visit.checked_in_at)
        visitor = Visitor.objects.filter(pk=visit.visitor_id).first()
        snapshot.append({
            "visit_id": visit.id,
            "visitor_id": visit.visitor_id,
            "name": visitor.full_name if visitor else "",
            "phone": visitor.phone if visitor else "",
            "email": visitor.email if visitor else "",
            "host_user_id": visit.host_user_id,
            "last_seen_zone": zone,
            "last_seen_at": visit.checked_in_at.isoformat()
            if visit.checked_in_at else None,
        })
    muster.roster_snapshot = snapshot
    muster.save(update_fields=["roster_snapshot", "updated_at"])
    open_alert(alert_type="EMERGENCY_MUSTER", severity="HIGH",
               message=f"Muster {muster.id} triggered: {reason or 'emergency'}",
               dedupe=False)
    return muster


def _entry(muster: Muster, visit_id: int) -> MusterEntry:
    entry = MusterEntry.objects.filter(muster=muster,
                                       visit_id=visit_id).first()
    if entry is None:
        raise NotFoundError("Visitor is not on this muster roster.",
                            code="not_on_roster")
    return entry


def record_roll_call(*, muster: Muster, visit_id: int, present: bool,
                     actor, at=None, notes: str = "") -> MusterEntry:
    if muster.status != "IN_PROGRESS":
        raise MusterStateError("This muster is already finalised.",
                               code="muster_completed")
    entry = _entry(muster, visit_id)
    at = at or timezone.now()
    extra = int((at - muster.started_at).total_seconds() // 60)
    entry.marked_present = present
    entry.marked_at = at
    entry.marked_by_user_id = getattr(actor, "user_id", None)
    entry.extra_minutes = max(extra, 0)
    entry.status = "ACCOUNTED" if present else "UNACCOUNTED"
    entry.notes = notes
    entry.save(update_fields=["marked_present", "marked_at",
                              "marked_by_user_id", "extra_minutes",
                              "status", "notes", "updated_at"])
    return entry


def finalize_muster(*, muster: Muster, actor=None,
                    at=None) -> Muster:
    """Close the roll-call.

    VMS-BR-045: every entry still unaccounted for when the roster has been
    open longer than the policy grace (default 15 minutes) is EVICTED.
    Accounted-for visitors are never evicted, however late they were found.
    """
    if muster.status != "IN_PROGRESS":
        raise MusterStateError("This muster is already finalised.",
                               code="muster_completed")
    at = at or timezone.now()
    grace = policies.effective().muster_eviction_grace_minutes
    elapsed = int((at - muster.started_at).total_seconds() // 60)

    accounted = evicted = unaccounted = 0
    for entry in muster.entries.all():
        if entry.marked_present:
            entry.status = "ACCOUNTED"
            accounted += 1
        elif elapsed > grace:
            # BR-045: extra time past the grace minute triggers eviction.
            entry.extra_minutes = max(elapsed, entry.extra_minutes)
            entry.status = "EVICTED"
            evicted += 1
        else:
            entry.status = "UNACCOUNTED"
            unaccounted += 1
        entry.save(update_fields=["status", "extra_minutes", "updated_at"])

    muster.status = "COMPLETED"
    muster.completed_at = at
    muster.summary = (f"accounted={accounted} evicted={evicted} "
                      f"unaccounted={unaccounted}")
    muster.save(update_fields=["status", "completed_at", "summary",
                               "updated_at"])
    return muster


def roster(muster: Muster) -> dict:
    return {
        "muster_id": muster.id,
        "status": muster.status,
        "started_at": muster.started_at,
        "completed_at": muster.completed_at,
        "summary": muster.summary,
        "entries": [
            {"visit_id": e.visit_id, "visitor_id": e.visitor_id,
             "host_user_id": e.host_user_id,
             "last_seen_zone": e.last_seen_zone,
             "status": e.status, "marked_present": e.marked_present,
             "extra_minutes": e.extra_minutes}
            for e in muster.entries.order_by("id")
        ],
        "offline_snapshot": muster.roster_snapshot,
    }
