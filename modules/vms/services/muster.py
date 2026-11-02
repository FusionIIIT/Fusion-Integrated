"""Emergency muster and accountability (VMS-CFR-018, UC-026/027/032).

# BW-VMS-19 (admin trigger) and BW-VMS-20 (security trigger) are the same
# service; only `trigger_role` differs. Roll-call is UC-027, done by Security.

Lifecycle: ``open -> closed`` (domain/muster_state). Each entry moves
``unaccounted -> accounted | evacuated`` once; the first mark wins.
Only one muster is open at a time (BR-130 sibling rule from the lane brief).
"""
from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.vms.domain import muster_state as ms
from modules.vms.models import (
    Alert,
    EmergencyMuster,
    IntegrationSetting,
    MusterEntry,
    Visitor,
)
from modules.vms.selectors import monitor as monitor_sel
from modules.vms.selectors import roster
from modules.vms.services import delivery
from modules.vms.services.common import audit, authz, notify

TOPIC_ALERT = "muster.alert"
TOPIC_REPORT = "muster.report"
TOPIC_STALE = "muster.stale"
STALE_AFTER = timedelta(hours=6)
MAX_BULK = 1000
_LOCK_KEY = 0x564D5301      # arbitrary advisory-lock id for "one open muster"
MARKS = (ms.ACCOUNTED, ms.EVACUATED)
_MARK_EVENT = {ms.ACCOUNTED: ms.MARK_ACCOUNTED, ms.EVACUATED: ms.MARK_EVACUATED}
APPLIED, UNCHANGED, CONFLICT = "applied", "unchanged", "conflict"


def _directory_users(user_ids):
    return directory.get_users(sorted(set(user_ids)))


# --- helpers ---------------------------------------------------------------------------

def _responder_role(actor) -> str:
    """'admin' or 'security': whichever active VMS role the actor holds (BR-130)."""
    from core.api.exceptions import PermissionDeniedError
    try:
        authz.require_role(actor, "admin")
    except PermissionDeniedError:
        authz.require_role(actor, "security")
        return "security"
    return "admin"


def _get_muster(muster_id, *, lock=False) -> EmergencyMuster:
    qs = EmergencyMuster.objects
    if lock:
        qs = qs.select_for_update()
    muster = qs.filter(pk=muster_id).first()
    if muster is None:
        raise NotFoundError("Muster not found.")
    return muster


def _require_open(muster) -> None:
    if muster.status != EmergencyMuster.Status.OPEN:
        raise ConflictError("This muster is closed.", code="muster_closed")


def _remaining(muster) -> int:
    return muster.entries.filter(status=MusterEntry.Status.UNACCOUNTED).count()


def _assembly_instructions() -> str:
    row = IntegrationSetting.objects.filter(key="assembly_instructions").first()
    value = row.value if row else None
    if isinstance(value, dict):
        value = value.get("text") or value.get("instructions") or ""
    return value.strip() if isinstance(value, str) else ""


def _check_status(status) -> str:
    if status not in MARKS:
        raise BadRequestError("status must be 'accounted' or 'evacuated'.",
                              code="invalid_status")
    return status


def _mark(entry: MusterEntry, status: str, *, actor_id, at) -> str:
    """Apply one mark to a locked entry. First mark wins; a different later status is a
    conflict, the same status is a no-op (idempotent)."""
    if entry.status == status:
        return UNCHANGED
    if entry.status != MusterEntry.Status.UNACCOUNTED:
        return CONFLICT
    entry.status = ms.resolve_entry(entry.status, _MARK_EVENT[status])
    entry.marked_by_user_id, entry.marked_at = actor_id, at
    entry.save(update_fields=["status", "marked_by_user_id", "marked_at"])
    return APPLIED


# --- trigger ---------------------------------------------------------------------------

def current() -> EmergencyMuster | None:
    return EmergencyMuster.objects.filter(status=EmergencyMuster.Status.OPEN).first()


def current_for(*, actor) -> EmergencyMuster | None:
    authz.require(actor, "vms.monitor.view")
    _responder_role(actor)
    return current()


def trigger(*, actor, reason: str = "") -> EmergencyMuster:
    """Start a muster: snapshot everyone on site, alert them, notify staff.

    # VMS-BR-130 · BW-VMS-19 / BW-VMS-20 · UC-026 / UC-032
    """
    authz.require(actor, "vms.muster.trigger")
    role = _responder_role(actor)
    reason = (reason or "").strip()[:500]
    instructions = _assembly_instructions()
    with transaction.atomic():
        with connection.cursor() as cur:       # serialises concurrent triggers
            cur.execute("SELECT pg_advisory_xact_lock(%s)", [_LOCK_KEY])
        if current() is not None:
            raise ConflictError("A muster is already open.", code="muster_already_open")
        muster = EmergencyMuster.objects.create(
            triggered_by_user_id=actor.user_id, trigger_role=role,
            summary={"reason": reason})
        rows = list(monitor_sel.with_last_seen(roster.on_site()).values_list(
            "pk", "last_zone_id", "last_seen_at", "visit_request__visitor_id"))
        MusterEntry.objects.bulk_create([
            MusterEntry(muster=muster, visit_pass_id=pk, last_zone_id=zone_id,
                        last_seen_at=seen) for pk, zone_id, seen, _ in rows])
        visitors = Visitor.objects.in_bulk({v for *_, v in rows})
        body = "EMERGENCY: please move to the assembly point now."
        if instructions:
            body += f"\n\nAssembly instructions: {instructions}"
        for visitor in visitors.values():
            notify.enqueue(topic=TOPIC_ALERT, dedupe_key=f"{TOPIC_ALERT}:{muster.pk}:v{visitor.pk}",
                           subject="Emergency: evacuate to the assembly point", body=body,
                           visitor=visitor, channels=("sms", "inapp"))
        Alert.objects.create(
            kind=Alert.Kind.MUSTER, severity=Alert.Severity.CRITICAL,
            ref_type="emergency_muster", ref_id=muster.pk,
            detail={"muster_id": muster.pk, "on_site": len(rows), "trigger_role": role})
        delivery.notify_role_holders(
            topic=TOPIC_ALERT, dedupe_key=f"{TOPIC_ALERT}:{muster.pk}:staff",
            subject="Emergency muster triggered",
            body=(f"A muster was triggered by a {role}. {len(rows)} visitor(s) on site. "
                  f"{reason}").strip())
        audit.record(actor=actor, action="vms.muster.triggered", entity=muster,
                     detail={"trigger_role": role, "on_site": len(rows), "reason": reason})
    return muster


# --- roster and roll-call --------------------------------------------------------------

def roster_entries(*, actor, muster_id, status=None) -> list[dict]:
    """The muster list: name, phone, email, last zone and time, host, status (AFR-132..135)."""
    authz.require(actor, "vms.monitor.view")
    _responder_role(actor)
    muster = _get_muster(muster_id)
    return _entry_rows(muster, status=status)


def _entry_rows(muster, *, status=None) -> list[dict]:
    qs = muster.entries.select_related(
        "visit_pass__visit_request__visitor", "last_zone").order_by("id")
    if status:
        qs = qs.filter(status=status)
    entries = list(qs)
    users = _directory_users(e.visit_pass.visit_request.host_user_id for e in entries)
    out = []
    for e in entries:
        req = e.visit_pass.visit_request
        host = users.get(req.host_user_id)
        out.append({
            "pass_id": e.visit_pass_id, "visitor_name": req.visitor.full_name,
            "visitor_phone": req.visitor.phone, "visitor_email": req.visitor.email,
            "last_zone_id": e.last_zone_id,
            "last_zone_name": e.last_zone.name if e.last_zone else "",
            "last_seen_at": e.last_seen_at, "host_user_id": req.host_user_id,
            "host_name": host.display_name if host else "",
            "status": e.status, "marked_by_user_id": e.marked_by_user_id,
            "marked_at": e.marked_at})
    return out


def roll_call(*, actor, muster_id, pass_id, status) -> dict:
    """Mark one visitor accounted or evacuated. Idempotent. UC-027, AFR-136."""
    authz.require(actor, "vms.muster.rollcall")
    _responder_role(actor)
    _check_status(status)
    with transaction.atomic():
        muster = _get_muster(muster_id, lock=True)
        _require_open(muster)
        entry = muster.entries.select_for_update().filter(visit_pass_id=pass_id).first()
        if entry is None:
            raise NotFoundError("That pass is not on this muster list.")
        outcome = _mark(entry, status, actor_id=actor.user_id, at=timezone.now())
        if outcome == CONFLICT:
            raise ConflictError(f"Already marked {entry.status}.", code="already_marked")
        if outcome == APPLIED:
            audit.record(actor=actor, action="vms.muster.rollcall", entity=entry,
                         detail={"muster_id": muster.pk, "pass_id": pass_id, "status": status})
        return {"pass_id": pass_id, "status": entry.status, "outcome": outcome,
                "remaining": _remaining(muster)}


def bulk_roll_call(*, actor, muster_id, marks: list[dict]) -> dict:
    """Apply many marks in one transaction (gate-side lists). Conflicts are reported."""
    authz.require(actor, "vms.muster.rollcall")
    _responder_role(actor)
    if len(marks) > MAX_BULK:
        raise BadRequestError(f"At most {MAX_BULK} marks per call.", code="too_many")
    for m in marks:
        _check_status(m.get("status"))
    now = timezone.now()
    with transaction.atomic():
        muster = _get_muster(muster_id, lock=True)
        _require_open(muster)
        entries = {e.visit_pass_id: e for e in muster.entries.select_for_update()
                   .filter(visit_pass_id__in=[m["pass_id"] for m in marks]).order_by("id")}
        res = {"applied": [], "unchanged": [], "conflicts": [], "not_found": []}
        for m in marks:
            entry = entries.get(m["pass_id"])
            if entry is None:
                res["not_found"].append(m["pass_id"])
                continue
            outcome = _mark(entry, m["status"], actor_id=actor.user_id, at=now)
            if outcome == CONFLICT:
                res["conflicts"].append({"pass_id": entry.visit_pass_id,
                                         "requested": m["status"], "current": entry.status})
            elif outcome == UNCHANGED:
                res["unchanged"].append(entry.visit_pass_id)
            else:
                res["applied"].append(entry.visit_pass_id)
                audit.record(actor=actor, action="vms.muster.rollcall", entity=entry,
                             detail={"muster_id": muster.pk, "pass_id": entry.visit_pass_id,
                                     "status": m["status"], "bulk": True})
        res["remaining"] = _remaining(muster)
        return res


def reconcile_cached(*, actor, muster_id, entries: list[dict]) -> dict:
    """Merge marks taken from a cached roster while offline (CFR-018, AFR-140/141).

    Marks are applied in ``marked_at`` order using the time the guard made them.
    A mark that disagrees with one already recorded (a live mark, or an earlier cached
    one) never overwrites it: the existing mark wins and the clash is reported.
    """
    authz.require(actor, "vms.muster.rollcall")
    _responder_role(actor)
    if len(entries) > MAX_BULK:
        raise BadRequestError(f"At most {MAX_BULK} marks per call.", code="too_many")
    for e in entries:
        _check_status(e.get("status"))
    now = timezone.now()
    ordered = sorted(entries, key=lambda e: e["marked_at"])
    with transaction.atomic():
        muster = _get_muster(muster_id, lock=True)
        _require_open(muster)
        locked = {e.visit_pass_id: e for e in muster.entries.select_for_update()
                  .filter(visit_pass_id__in=[e["pass_id"] for e in ordered]).order_by("id")}
        res = {"applied": [], "unchanged": [], "conflicts": [], "not_found": []}
        for e in ordered:
            entry = locked.get(e["pass_id"])
            if entry is None:
                res["not_found"].append(e["pass_id"])
                continue
            at = min(max(e["marked_at"], muster.triggered_at), now)
            current_status, current_at = entry.status, entry.marked_at
            outcome = _mark(entry, e["status"], actor_id=actor.user_id, at=at)
            if outcome == CONFLICT:
                res["conflicts"].append({
                    "pass_id": entry.visit_pass_id, "cached_status": e["status"],
                    "cached_marked_at": e["marked_at"], "kept_status": current_status,
                    "kept_marked_at": current_at, "resolution": "existing_mark_kept"})
            elif outcome == UNCHANGED:
                res["unchanged"].append(entry.visit_pass_id)
            else:
                res["applied"].append(entry.visit_pass_id)
        res["remaining"] = _remaining(muster)
        audit.record(actor=actor, action="vms.muster.reconciled", entity=muster,
                     detail={"submitted": len(entries), "applied": len(res["applied"]),
                             "conflicts": len(res["conflicts"]),
                             "not_found": len(res["not_found"])})
        return res


# --- close and report ------------------------------------------------------------------

def _build_summary(muster, rows, *, reason, note, forced, closed_at, closed_by) -> dict:
    counts = Counter(r["status"] for r in rows)
    marks = [r["marked_at"] for r in rows if r["marked_at"]]
    per_zone: dict = {}
    for r in rows:
        z = per_zone.setdefault(r["last_zone_id"], {
            "zone_id": r["last_zone_id"], "zone_name": r["last_zone_name"],
            "total": 0, "accounted": 0, "evacuated": 0, "unaccounted": 0})
        z["total"] += 1
        z[r["status"]] += 1
    end = closed_at or timezone.now()
    summary = {
        "reason": reason, "note": note, "forced": forced,
        "totals": {"total": len(rows), "accounted": counts[ms.ACCOUNTED],
                   "evacuated": counts[ms.EVACUATED], "unaccounted": counts[ms.UNACCOUNTED]},
        "unaccounted": [
            {k: r[k] for k in ("pass_id", "visitor_name", "visitor_phone", "visitor_email",
                               "last_zone_name", "last_seen_at", "host_user_id", "host_name")}
            for r in rows if r["status"] == ms.UNACCOUNTED],
        "timings": {"triggered_at": muster.triggered_at, "closed_at": closed_at,
                    "duration_seconds": int((end - muster.triggered_at).total_seconds()),
                    "first_mark_at": min(marks) if marks else None,
                    "last_mark_at": max(marks) if marks else None},
        "responder": {"triggered_by_user_id": muster.triggered_by_user_id,
                      "trigger_role": muster.trigger_role, "closed_by_user_id": closed_by,
                      "marks_by_user": dict(Counter(
                          str(r["marked_by_user_id"]) for r in rows if r["marked_by_user_id"]))},
        "per_zone": sorted(per_zone.values(), key=lambda z: (z["zone_name"], z["zone_id"] or 0)),
    }
    return json.loads(json.dumps(summary, cls=DjangoJSONEncoder))   # JSONField-safe


def close(*, actor, muster_id, note: str = "", force: bool = False) -> EmergencyMuster:
    """Finalize the roll-call (UC-027) and store the post-event report (AFR-137).

    Refused while visitors remain unaccounted unless ``force`` with a note.
    """
    authz.require(actor, "vms.muster.trigger")
    _responder_role(actor)
    note = (note or "").strip()
    with transaction.atomic():
        muster = _get_muster(muster_id, lock=True)
        _require_open(muster)
        remaining = _remaining(muster)
        if remaining and not force:
            raise ConflictError(f"{remaining} visitor(s) are still unaccounted for.",
                                code="unaccounted_remain", details=[{"remaining": remaining}])
        if remaining and not note:
            raise BadRequestError("A note is required to close with unaccounted visitors.",
                                  code="note_required")
        now = timezone.now()
        reason = (muster.summary or {}).get("reason", "")
        muster.status = ms.resolve(muster.status, ms.CLOSE)
        muster.closed_at = now
        muster.summary = _build_summary(
            muster, _entry_rows(muster), reason=reason, note=note,
            forced=bool(remaining), closed_at=now, closed_by=actor.user_id)
        muster.save(update_fields=["status", "closed_at", "summary"])
        totals = muster.summary["totals"]
        delivery.notify_role_holders(
            topic=TOPIC_REPORT, dedupe_key=f"{TOPIC_REPORT}:{muster.pk}", roles=("admin",),
            subject="Emergency muster report",
            body=(f"Muster {muster.pk} closed: {totals['accounted']} accounted, "
                  f"{totals['evacuated']} evacuated, {totals['unaccounted']} unaccounted "
                  f"of {totals['total']}."))
        audit.record(actor=actor, action="vms.muster.closed", entity=muster,
                     detail={"forced": bool(remaining), "unaccounted": remaining,
                             "note": note})
    return muster


def counts(muster) -> dict:
    """Entry totals by status for a muster."""
    c = Counter(muster.entries.values_list("status", flat=True))
    return {"total": sum(c.values()), "accounted": c[ms.ACCOUNTED],
            "evacuated": c[ms.EVACUATED], "unaccounted": c[ms.UNACCOUNTED]}


def get(*, actor, muster_id) -> EmergencyMuster:
    authz.require(actor, "vms.monitor.view")
    _responder_role(actor)
    return _get_muster(muster_id)


def report(*, actor, muster_id) -> dict:
    """The post-event summary. An open muster returns a provisional live summary."""
    authz.require(actor, "vms.monitor.view")
    _responder_role(actor)
    muster = _get_muster(muster_id)
    if muster.status == EmergencyMuster.Status.CLOSED:
        summary, provisional = muster.summary, False
    else:
        summary = _build_summary(
            muster, _entry_rows(muster), reason=(muster.summary or {}).get("reason", ""),
            note="", forced=False, closed_at=None, closed_by=None)
        provisional = True
    return {"muster_id": muster.pk, "status": muster.status, "provisional": provisional,
            **summary}


def _safe(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def report_csv(*, actor, muster_id) -> tuple[str, str]:
    """(filename, csv text) of the full muster list; needs vms.report.export."""
    authz.require(actor, "vms.report.export")
    _responder_role(actor)
    muster = _get_muster(muster_id)
    rows = _entry_rows(muster)
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["pass_id", "visitor_name", "visitor_phone", "visitor_email", "last_zone_name",
            "last_seen_at", "host_user_id", "host_name", "status", "marked_by_user_id",
            "marked_at"]
    w.writerow(cols)
    for r in rows:
        w.writerow([_safe(r[c]) for c in cols])
    audit.record(actor=actor, action="vms.muster.exported", entity=muster,
                 detail={"rows": len(rows)})
    return f"muster-{muster.pk}.csv", buf.getvalue()


# --- stale muster job ------------------------------------------------------------------

def stale_check(*, now=None, after: timedelta = STALE_AFTER) -> int:
    """Alert once per muster that has been open longer than `after` (default 6 h)."""
    now = now or timezone.now()
    n = 0
    for muster in EmergencyMuster.objects.filter(
            status=EmergencyMuster.Status.OPEN, triggered_at__lte=now - after):
        if Alert.objects.filter(kind=Alert.Kind.MUSTER, ref_type="emergency_muster_stale",
                                ref_id=muster.pk).exists():
            continue
        Alert.objects.create(
            kind=Alert.Kind.MUSTER, severity=Alert.Severity.HIGH,
            ref_type="emergency_muster_stale", ref_id=muster.pk,
            detail={"muster_id": muster.pk, "open_since": muster.triggered_at.isoformat()})
        delivery.notify_role_holders(
            topic=TOPIC_STALE, dedupe_key=f"{TOPIC_STALE}:{muster.pk}", roles=("admin",),
            subject="Emergency muster still open",
            body=f"Muster {muster.pk} has been open since {muster.triggered_at:%Y-%m-%d %H:%M}.")
        n += 1
    return n
