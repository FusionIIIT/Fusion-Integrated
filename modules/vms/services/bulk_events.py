"""Bulk visitor lists and special events (VMS-CFR-009; UC-008, UC-009; BW-VMS-21, CW-VMS-07).

Admin uploads the attendee list even when an external organiser supplies it
(problem statement C-01); the organiser is data, never an actor.

Attendee lifecycle: ``invited`` (staged by the upload) -> ``pass_issued``
(approve_batch) -> ``checked_in`` | ``cancelled``.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    NotFoundError,
)
from modules.vms.models import (
    EventAttendee,
    EventBatch,
    VisitPass,
    VisitRequest,
    Zone,
)
from modules.vms.services import blacklist, passes, registration
from modules.vms.services.common import audit, authz, notify

PERM = "vms.event.manage"
MAX_ROWS = 5000                      # UC-008 bulk limit
CHUNK = 500
MAX_EVENT_DAYS = 31                  # assumption: SRS gives no multi-day cap
REQUIRED_COLUMNS = ("name", "id_doc_type", "id_doc_number")
_ALIASES = {"full_name": "name", "visitor_name": "name", "mobile": "phone"}
_CLOSED = (EventBatch.Status.CANCELLED, EventBatch.Status.CLOSED)


@dataclass
class ImportReport:
    """Row-level outcome of an upload; returned whether or not rows failed."""
    total: int = 0
    accepted: list[int] = field(default_factory=list)       # attendee ids
    rejected: list[dict] = field(default_factory=list)      # {row, reason, code}

    def as_dict(self) -> dict:
        return {"total": self.total, "accepted_count": len(self.accepted),
                "rejected_count": len(self.rejected), "accepted": self.accepted,
                "rejected": self.rejected}


# --- helpers ---------------------------------------------------------------------------

def _admin(actor) -> None:
    authz.require(actor, PERM)
    authz.require_role(actor, "admin")


def _get(event_id: int, *, lock=False) -> EventBatch:
    qs = EventBatch.objects.select_for_update() if lock else EventBatch.objects
    ev = qs.filter(pk=event_id).first()
    if ev is None:
        raise NotFoundError("Event not found.")
    return ev


def _msg(exc) -> str:
    return str(getattr(exc, "message", None) or exc)


def _parse_dt(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = parse_datetime(str(value).strip()) if value else None
    if dt is None:
        raise BadRequestError("Invalid date/time.", code="invalid_datetime")
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _validate_slots(slots, start, end) -> list[dict]:
    out = []
    for s in slots or []:
        try:
            a, b = _parse_dt(s.get("start")), _parse_dt(s.get("end"))
            cap = s.get("capacity")
            cap = None if cap in (None, "") else int(cap)
        except (AttributeError, ValueError, TypeError, BadRequestError):
            raise BadRequestError("Each slot needs start, end and an integer capacity.",
                                  code="invalid_slot") from None
        if not (start <= a < b <= end) or (cap is not None and cap < 1):
            raise BadRequestError("A slot must lie inside the event window.",
                                  code="invalid_slot")
        out.append({"start": a.isoformat(), "end": b.isoformat(), "capacity": cap})
    return out


def _validate_zones(zone_ids, allow_restricted) -> list[Zone]:
    ids = sorted(set(zone_ids or []))
    zones = list(Zone.objects.filter(pk__in=ids, is_active=True))
    if len(zones) != len(ids):
        raise BadRequestError("Unknown or inactive zone.", code="unknown_zone")
    allowed = set(allow_restricted or [])
    bad = [z.pk for z in zones if z.is_restricted and z.pk not in allowed]
    if bad:
        raise BadRequestError(
            "Restricted zones must be listed explicitly in allow_restricted_zones.",
            code="restricted_zone_not_confirmed", details=[{"zones": bad}])
    return zones


def _validate_window(start, end) -> None:
    if end <= start:
        raise BadRequestError("valid_until must follow valid_from.", code="invalid_window")
    if end - start > timedelta(days=MAX_EVENT_DAYS):
        raise BadRequestError(f"An event window may not exceed {MAX_EVENT_DAYS} days.",
                              code="window_too_long")
    if end <= timezone.now():
        raise BadRequestError("The event window is already over.", code="window_in_past")


def event_snapshot(ev: EventBatch) -> dict:
    return {"id": ev.pk, "name": ev.name, "organizer": ev.organizer,
            "valid_from": ev.valid_from, "valid_until": ev.valid_until, "status": ev.status,
            "fast_lane": ev.fast_lane, "walkin_rate_limit": ev.walkin_rate_limit,
            "slots": ev.slots, "zone_ids": sorted(ev.zones.values_list("pk", flat=True))}


# --- events ----------------------------------------------------------------------------

def create_event(*, admin_actor, name, organizer="", valid_from, valid_until, zone_ids=(),
                 slots=(), fast_lane=False, walkin_rate_limit=None,
                 allow_restricted_zones=()) -> EventBatch:
    """UC-009 steps 1-2: define the event, its window, zones, slots and entry controls."""
    _admin(admin_actor)
    name = (name or "").strip()
    if not name:
        raise BadRequestError("An event name is required.", code="name_required")
    valid_from, valid_until = _parse_dt(valid_from), _parse_dt(valid_until)
    _validate_window(valid_from, valid_until)
    if walkin_rate_limit is not None and walkin_rate_limit < 0:
        raise BadRequestError("walkin_rate_limit cannot be negative.",
                              code="invalid_rate_limit")
    zones = _validate_zones(zone_ids, allow_restricted_zones)
    slot_rows = _validate_slots(slots, valid_from, valid_until)
    with transaction.atomic():
        ev = EventBatch.objects.create(
            name=name[:150], organizer=(organizer or "").strip()[:150],
            valid_from=valid_from, valid_until=valid_until, slots=slot_rows,
            fast_lane=bool(fast_lane), walkin_rate_limit=walkin_rate_limit,
            created_by_user_id=admin_actor.user_id)
        ev.zones.set(zones)
        audit.record(actor=admin_actor, action="vms.event.created", entity=ev,
                     detail=event_snapshot(ev))
    return ev


def update_event(*, admin_actor, event_id: int, allow_restricted_zones=(),
                 **changes) -> EventBatch:
    """Edit controls any time; window, zones and slots only before passes exist."""
    _admin(admin_actor)
    with transaction.atomic():
        ev = _get(event_id, lock=True)
        if ev.status in _CLOSED:
            raise ConflictError("A closed or cancelled event cannot be changed.",
                                code="event_closed")
        structural = {"valid_from", "valid_until", "zone_ids", "slots"} & set(changes)
        if structural and VisitPass.objects.filter(event=ev).exists():
            raise ConflictError("Window, zones and slots are fixed once passes are issued.",
                                code="passes_issued")
        rate = changes.get("walkin_rate_limit", ev.walkin_rate_limit)
        if rate is not None and rate < 0:
            raise BadRequestError("walkin_rate_limit cannot be negative.",
                                  code="invalid_rate_limit")
        start = _parse_dt(changes.get("valid_from", ev.valid_from))
        end = _parse_dt(changes.get("valid_until", ev.valid_until))
        if {"valid_from", "valid_until"} & set(changes):
            _validate_window(start, end)
        if "slots" in changes or {"valid_from", "valid_until"} & set(changes):
            ev.slots = _validate_slots(changes.get("slots", ev.slots), start, end)
        ev.valid_from, ev.valid_until = start, end
        for key in ("name", "organizer", "fast_lane", "walkin_rate_limit"):
            if key in changes:
                setattr(ev, key, changes[key])
        ev.save()
        if "zone_ids" in changes:
            ev.zones.set(_validate_zones(changes["zone_ids"], allow_restricted_zones))
        audit.record(actor=admin_actor, action="vms.event.updated", entity=ev,
                     detail={"changed": sorted(changes), **event_snapshot(ev)})
    return ev


# --- attendee upload (UC-008 steps 1-2) ------------------------------------------------

def parse_csv(raw: bytes | str) -> list[dict]:
    """CSV text -> dict rows (header names lower-cased, aliases folded).

    XLSX is not supported: the repo carries no spreadsheet dependency.
    """
    try:
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
        reader = csv.DictReader(io.StringIO(text))
        header = [_ALIASES.get((h or "").strip().lower(), (h or "").strip().lower())
                  for h in (reader.fieldnames or [])]
        reader.fieldnames = header
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise BadRequestError("The list is missing required columns: "
                                  + ", ".join(missing) + ".", code="missing_columns")
        return [{k: (v or "").strip() for k, v in r.items() if k} for r in reader]
    except (csv.Error, UnicodeDecodeError) as exc:
        raise BadRequestError("The list could not be parsed as CSV.",
                              code="unparseable_list") from exc


def _slot_for(ev: EventBatch, row: dict, load: dict):
    """(slot_start, slot_end) from the row, else the first slot with room left."""
    a, b = row.get("slot_start"), row.get("slot_end")
    if a or b:
        try:
            sa, sb = _parse_dt(a), _parse_dt(b)
        except BadRequestError:
            raise BadRequestError("slot_start/slot_end are not valid date-times.",
                                  code="invalid_slot") from None
        if not (ev.valid_from <= sa < sb <= ev.valid_until):
            raise BadRequestError("The slot lies outside the event window.",
                                  code="slot_outside_event")
        return sa, sb
    for s in ev.slots or []:
        key = s["start"]
        if s.get("capacity") is None or load.get(key, 0) < s["capacity"]:
            load[key] = load.get(key, 0) + 1
            return _parse_dt(s["start"]), _parse_dt(s["end"])
    if ev.slots:
        raise BadRequestError("All slots are full.", code="slots_full")
    return None, None


def _validate_row(ev, row, load) -> dict:
    name = row.get("name", "")
    if not name:
        raise BadRequestError("name is required.", code="missing_name")
    phone, email = row.get("phone", ""), row.get("email", "")
    if not phone and not email:
        raise BadRequestError("A phone number or an email is required.",
                              code="missing_contact")
    if phone:   # reuse the registration validator (BR-037) with neutral event context
        registration.validate_fields({
            "full_name": name, "phone": phone, "id_doc_type": row.get("id_doc_type"),
            "id_doc_number": row.get("id_doc_number"), "host_user_id": 1, "purpose": "event",
            "scheduled_start": ev.valid_from, "scheduled_end": ev.valid_until})
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            raise BadRequestError("The email address is not valid.",
                                  code="invalid_email") from None
    registration.validate_id_document(row.get("id_doc_type", ""), row.get("id_doc_number", ""))
    sa, sb = _slot_for(ev, row, load)
    return {"name": name[:150], "phone": phone[:20], "email": email, "slot_start": sa,
            "slot_end": sb, "id_doc_type": row["id_doc_type"],
            "id_doc_number": row["id_doc_number"].strip().upper()}


def upload_attendees(*, admin_actor, event_id: int, file=None, rows=None) -> ImportReport:
    """Validate every row, screen the blacklist, stage the accepted ones as
    ``invited`` attendees and return the per-row report (no pass for rejected rows).

    A list that cannot be parsed or exceeds MAX_ROWS is rejected as a whole; otherwise
    valid rows go in even when others fail (UC-008 alternative flow).
    """
    _admin(admin_actor)
    ev = _get(event_id)
    if ev.status in _CLOSED:
        raise ConflictError("This event no longer accepts attendees.", code="event_closed")
    if rows is None:
        if file is None:
            raise BadRequestError("A list file is required.", code="file_required")
        rows = parse_csv(file.read() if hasattr(file, "read") else file)
    if len(rows) > MAX_ROWS:
        raise BadRequestError(f"A list may hold at most {MAX_ROWS} rows.", code="too_many_rows")
    if not rows:
        raise BadRequestError("The list has no rows.", code="empty_list")

    report = ImportReport(total=len(rows))
    existing = EventAttendee.objects.filter(batch=ev).exclude(
        status=EventAttendee.Status.CANCELLED)
    seen = set(existing.values_list("id_doc_number", flat=True))
    load = {s["start"]: existing.filter(slot_start=_parse_dt(s["start"])).count()
            for s in ev.slots or []}
    staged: list[dict] = []
    for idx, raw_row in enumerate(rows, start=2):     # row 1 is the header
        row = {_ALIASES.get(k, k): v for k, v in raw_row.items()}
        try:
            clean = _validate_row(ev, row, load)
            doc = clean["id_doc_number"]
            if doc in seen:
                raise ConflictError("Duplicate identity document in this event.",
                                    code="duplicate")
            hit = blacklist.check(checkpoint="pre_registration", name=clean["name"],
                                  id_doc_number=doc, phone=clean["phone"],
                                  email=clean["email"])
            if hit is not None:
                registration.record_blacklist_hit(actor=admin_actor, hit=hit,
                                                  visitor_label=clean["name"])
                raise BadRequestError("Visitor is not permitted entry.", code="blacklisted")
        except DomainError as exc:
            report.rejected.append({"row": idx, "code": getattr(exc, "code", "invalid"),
                                    "reason": _msg(exc)})
            continue
        seen.add(doc)
        staged.append(clean)

    for i in range(0, len(staged), CHUNK):
        with transaction.atomic():
            made = EventAttendee.objects.bulk_create(
                [EventAttendee(batch=ev, **c) for c in staged[i:i + CHUNK]])
        report.accepted.extend(a.pk for a in made)
    audit.record(actor=admin_actor, action="vms.event.attendees_uploaded", entity=ev, detail={
        "total": report.total, "accepted": len(report.accepted),
        "rejected": len(report.rejected)})
    return report


# --- bulk approval (UC-008 steps 3-5) --------------------------------------------------

def _approve_one(admin_actor, ev, att, now) -> VisitPass:
    with transaction.atomic():
        att = EventAttendee.objects.select_for_update().get(pk=att.pk)
        if att.visit_pass_id or att.status != EventAttendee.Status.INVITED:
            raise ConflictError("Already processed.", code="already_issued")
        hit = blacklist.check(checkpoint="pre_registration", name=att.name,
                              id_doc_number=att.id_doc_number, phone=att.phone,
                              email=att.email)
        if hit is not None:
            raise BadRequestError("Visitor is not permitted entry.", code="blacklisted")
        visitor = registration.resolve_visitor(session_visitor=None, update_existing=False, data={
            "full_name": att.name, "phone": att.phone, "email": att.email,
            "id_doc_type": att.id_doc_type, "id_doc_number": att.id_doc_number})
        vr = VisitRequest.objects.create(
            visitor=visitor, host_user_id=admin_actor.user_id,
            purpose=f"Event: {ev.name}"[:255], scheduled_start=ev.valid_from,
            scheduled_end=ev.valid_until, status=VisitRequest.Status.APPROVED,
            source=VisitRequest.Source.BULK, event=ev, decided_at=now)
        zones = list(ev.zones.all())
        vr.requested_zones.set(zones)
        vp = passes.issue_pass(request=vr, pass_type=VisitPass.PassType.PRE_REGISTERED,
                               issued_by=admin_actor, valid_from=ev.valid_from,
                               valid_until=ev.valid_until, zones=zones)
        # AFR-159: validity is the event window; BR-193's per-visit cap lists UC-005/010/034
        # only, so restore the window issue_pass capped.
        vp.valid_until = ev.valid_until
        vp.fast_lane = ev.fast_lane
        vp.save(update_fields=["valid_until", "fast_lane"])
        att.visit_pass = vp
        att.status = EventAttendee.Status.PASS_ISSUED
        att.save(update_fields=["visit_pass", "status"])
        notify.enqueue(topic="pass.issued", dedupe_key=f"pass.issued:{vp.pk}:{visitor.pk}",
                       subject=f"Your pass for {ev.name}",
                       body="Your event pass is ready. Present its QR code at the gate.",
                       visitor=visitor)
    return vp


def approve_batch(*, admin_actor, event_id: int, attendee_ids=None) -> dict:
    """Approve staged attendees and issue one event pass each (resumable: attendees that
    already hold a pass are skipped). One failure never blocks the rest."""
    _admin(admin_actor)
    now = timezone.now()
    with transaction.atomic():
        ev = _get(event_id, lock=True)
        if ev.status in _CLOSED:
            raise ConflictError("This event is closed.", code="event_closed")
        if ev.valid_until <= now:
            raise ConflictError("The event window is over.", code="window_over")
        if ev.status == EventBatch.Status.DRAFT:
            ev.status = EventBatch.Status.ACTIVE
            ev.save(update_fields=["status"])
    qs = EventAttendee.objects.filter(batch=ev).order_by("pk")
    if attendee_ids is not None:
        qs = qs.filter(pk__in=list(attendee_ids))
    issued, skipped, failed = [], 0, []
    for att in qs:
        if att.visit_pass_id or att.status != EventAttendee.Status.INVITED:
            skipped += 1
            continue
        try:
            issued.append(_approve_one(admin_actor, ev, att, now).pk)
        except DomainError as exc:
            failed.append({"attendee_id": att.pk, "code": getattr(exc, "code", "error"),
                           "reason": _msg(exc)})
    audit.record(actor=admin_actor, action="vms.event.batch_approved", entity=ev, detail={
        "issued": len(issued), "skipped": skipped, "failed": len(failed)})
    return {"issued": len(issued), "pass_ids": issued, "skipped": skipped, "failed": failed}


# --- revoke / cancel -------------------------------------------------------------------

def revoke_attendee(*, admin_actor, event_id: int, attendee_id: int,
                    reason: str) -> EventAttendee:
    """Remove an attendee; an issued pass is terminated (reason mandatory)."""
    _admin(admin_actor)
    reason = (reason or "").strip()
    if not reason:
        raise BadRequestError("A reason is required.", code="reason_required")
    with transaction.atomic():
        att = (EventAttendee.objects.select_for_update()
               .filter(pk=attendee_id, batch_id=event_id).first())
        if att is None:
            raise NotFoundError("Attendee not found.")
        if att.status == EventAttendee.Status.CANCELLED:
            raise ConflictError("Attendee already removed.", code="already_cancelled")
        if att.visit_pass_id and att.visit_pass.is_active:
            passes.terminate_pass(actor=admin_actor, pass_id=att.visit_pass_id, reason=reason)
        att.status = EventAttendee.Status.CANCELLED
        att.save(update_fields=["status"])
        audit.record(actor=admin_actor, action="vms.event.attendee_revoked", entity=att,
                     detail={"event_id": event_id, "reason": reason,
                             "pass_id": att.visit_pass_id})
    return att


def cancel_event(*, admin_actor, event_id: int, reason: str) -> dict:
    """Cancel the event and terminate every active event pass."""
    _admin(admin_actor)
    reason = (reason or "").strip()
    if not reason:
        raise BadRequestError("A reason is required.", code="reason_required")
    with transaction.atomic():
        ev = _get(event_id, lock=True)
        if ev.status == EventBatch.Status.CANCELLED:
            raise ConflictError("The event is already cancelled.", code="already_cancelled")
        terminated = 0
        for vp in VisitPass.objects.filter(event=ev, is_active=True):
            passes.terminate_pass(actor=admin_actor, pass_id=vp.pk,
                                  reason=f"Event cancelled: {reason}")
            terminated += 1
        EventAttendee.objects.filter(batch=ev).update(status=EventAttendee.Status.CANCELLED)
        ev.status = EventBatch.Status.CANCELLED
        ev.save(update_fields=["status"])
        audit.record(actor=admin_actor, action="vms.event.cancelled", entity=ev,
                     detail={"reason": reason, "passes_terminated": terminated})
    return {"event_id": ev.pk, "status": ev.status, "passes_terminated": terminated}


# --- event walk-in lane (AFR-163) ------------------------------------------------------

def walkin_allowance(event_id: int, now=None) -> dict:
    """Read-only: how many more event walk-ins the overflow lane accepts this hour.

    Lane D's ``walkin.register`` may call this when a registration carries an event id.
    ``limit`` None means the lane is uncapped. Counts walk-in requests tied to the event.
    """
    now = now or timezone.now()
    ev = _get(event_id)
    used = VisitRequest.objects.filter(
        event=ev, source=VisitRequest.Source.WALK_IN,
        created_at__gte=now - timedelta(hours=1)).count()
    active = (ev.status == EventBatch.Status.ACTIVE and ev.valid_from <= now <= ev.valid_until)
    limit = ev.walkin_rate_limit
    remaining = None if limit is None else max(limit - used, 0)
    return {"event_id": ev.pk, "limit": limit, "used": used, "remaining": remaining,
            "event_active": active,
            "allowed": active and (remaining is None or remaining > 0)}
