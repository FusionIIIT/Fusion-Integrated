"""Every write to a booking (UC-VH-001, 003..009, 020..022).

All status movement goes through `transition`: one locked read, the state
machine, the permission, the duty check, the self-decision check, the audit
row and the notification, in one transaction. A second path into a state is
how rules drift apart, so there is no second path.
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import date, datetime, time

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.visitor_hostel.domain import billing as billing_rules
from modules.visitor_hostel.domain import cancellation as schedule
from modules.visitor_hostel.domain import duty, tariffs
from modules.visitor_hostel.domain import permissions as perms
from modules.visitor_hostel.domain import requisition as req
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import (
    Booking,
    BookingTransition,
    CancellationRequest,
    ModificationRequest,
    Room,
    RoomAllotment,
)
from modules.visitor_hostel.selectors import duty as duty_selectors
from modules.visitor_hostel.selectors import rooms as room_selectors
from modules.visitor_hostel.selectors import tariffs as tariff_selectors
from modules.visitor_hostel.services import authz, notifications

log = logging.getLogger("fusion.visitor_hostel.bookings")

REQUISITION_FIELDS = (
    "visitor_name", "visitor_phone", "visitor_email", "visitor_organization",
    "visitor_address", "purpose", "category", "occupancy", "arrival_date",
    "arrival_time", "departure_date", "departure_time", "rooms_required",
    "occupants", "billing_responsibility", "billing_reference",
)


def _validate(data: dict) -> None:
    try:
        req.validate(
            category=data["category"], occupancy=data["occupancy"],
            billing_responsibility=data["billing_responsibility"],
            arrival_date=data["arrival_date"], departure_date=data["departure_date"],
            rooms_required=data["rooms_required"], occupants=data["occupants"],
            today=timezone.localdate())
    except req.InvalidRequisition as exc:
        raise BadRequestError(str(exc), code=exc.code) from exc


def _audit(booking: Booking, frm: str, to: str, actor, lane: str, reason: str = "") -> None:
    BookingTransition.objects.create(
        booking=booking, from_status=frm, to_status=to,
        actor_user_id=getattr(actor, "user_id", None), actor_lane=lane,
        reason=reason[:300])


def _create(*, actor, data: dict, source: str, indenter_user_id: int | None) -> Booking:
    fields = {k: data[k] for k in REQUISITION_FIELDS if k in data}
    _validate(fields)
    booking = Booking.objects.create(
        **fields, source=source, is_offline=source != req.ONLINE,
        indenter_user_id=indenter_user_id, recorded_by_user_id=actor.user_id,
        status=sm.PENDING,
        caretaker_user_id=duty_selectors.current_holder_id(duty.CARETAKER),
        incharge_user_id=duty_selectors.current_holder_id(duty.INCHARGE))
    _audit(booking, "", sm.PENDING, actor,
           sm.INDENTER if source == req.ONLINE else sm.CARETAKER,
           "offline booking recorded" if booking.is_offline else "submitted")
    notifications.booking_event(booking, "booking.submitted")
    return booking


@transaction.atomic
def submit_online(*, actor, data: dict) -> Booking:
    """UC-VH-001: the Indenter's requisition, Pending on success (AFR-VH-013)."""
    authz.require(actor, perms.BOOKING_CREATE)
    return _create(actor=actor, data=data, source=req.ONLINE,
                   indenter_user_id=actor.user_id)


@transaction.atomic
def record_offline(*, actor, data: dict, source: str,
                   indenter_user_id: int | None = None) -> Booking:
    """UC-VH-005: flagged Offline (BR-VH-005), then the same routing and
    availability checks as any booking (BR-VH-003/004) — it is one table and
    one state machine."""
    authz.require_operator(actor, sm.CARETAKER, perms.OFFLINE_BOOKING_CREATE)
    if source not in req.OFFLINE_SOURCES:
        raise BadRequestError("An offline booking is telephonic or walk_in.",
                              code="invalid_source")
    return _create(actor=actor, data=data, source=source,
                   indenter_user_id=indenter_user_id)


# -- The choke point -----------------------------------------------------------
def _resolve(frm: str, to: str, lane: str) -> sm.Transition:
    try:
        return sm.resolve(frm, to, lane)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A {frm.replace('_', ' ')} booking cannot become {to.replace('_', ' ')}.",
            code="invalid_transition",
            details=[{"from": frm, "to": to,
                      "allowed": sm.allowed_targets(frm, lane)}]) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError("Your role cannot make that change.",
                                    code="actor_not_allowed") from exc


def _guard(name: str, booking: Booking, reason: str) -> None:
    if name == "has_reason" and not reason.strip():
        raise ConflictError("Give a reason; the Indenter is told it.",
                            code="reason_required")
    if name == "cancellation_requested" and not CancellationRequest.objects.filter(
            booking=booking, status="requested").exists():
        raise ConflictError("There is no cancellation request on this booking.",
                            code="no_cancellation_request")


_NOTIFY = {sm.APPROVED: "booking.approved", sm.REJECTED: "booking.rejected"}


@transaction.atomic
def transition(*, booking_id: int, to_status: str, actor, lane: str,
               reason: str = "", scope=None,
               effect: Callable[[Booking], Sequence[str]] | None = None) -> Booking:
    """Move one booking. `scope` makes an out-of-scope id a 404; `effect` runs
    inside the lock and returns any extra fields it changed."""
    qs = scope if scope is not None else Booking.objects.all()
    booking = qs.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")

    needed = sm.permission_for(to_status, lane)
    if needed:
        authz.require(actor, needed)
    t = _resolve(booking.status, to_status, lane)
    authz.require_on_duty(actor, lane)
    authz.refuse_own(actor, booking)
    for g in t.guards:
        _guard(g, booking, reason)

    frm = booking.status
    booking.status = to_status
    touched = ["status", "updated_at"]
    if to_status == sm.REJECTED:
        booking.decision_reason = reason[:300]
        touched.append("decision_reason")
    owner = {sm.CARETAKER: "caretaker_user_id", sm.INCHARGE: "incharge_user_id"}.get(lane)
    if owner and getattr(booking, owner) != actor.user_id:
        setattr(booking, owner, actor.user_id)
        touched.append(owner)
    if effect is not None:
        touched.extend(effect(booking) or ())
    booking.save(update_fields=sorted(set(touched)))

    _audit(booking, frm, to_status, actor, lane, reason)
    topic = _NOTIFY.get(to_status)
    if topic:
        notifications.booking_event(booking, topic, detail=reason)
    log.info("visitor_hostel.booking.moved id=%s %s->%s by=%s", booking.pk, frm,
             to_status, getattr(actor, "user_id", None))
    return booking


# -- UC-VH-003 / UC-VH-004 -----------------------------------------------------
def review(*, booking_id: int, outcome: str, actor, reason: str = "", scope=None) -> Booking:
    targets = {"forward": sm.FORWARDED, "reject": sm.REJECTED}
    if outcome not in targets:
        raise BadRequestError("Outcome must be forward or reject.", code="invalid_outcome")
    return transition(booking_id=booking_id, to_status=targets[outcome], actor=actor,
                      lane=sm.CARETAKER, reason=reason, scope=scope)


def decide(*, booking_id: int, outcome: str, actor, reason: str = "", scope=None) -> Booking:
    targets = {"approve": sm.APPROVED, "reject": sm.REJECTED}
    if outcome not in targets:
        raise BadRequestError("Outcome must be approve or reject.", code="invalid_outcome")
    return transition(booking_id=booking_id, to_status=targets[outcome], actor=actor,
                      lane=sm.INCHARGE, reason=reason, scope=scope)


# -- UC-VH-008: allotment ------------------------------------------------------
def allot_rooms(*, booking_id: int, rooms: Sequence[dict], actor, scope=None) -> Booking:
    """BR-VH-012 is the state machine's: only Approved -> Room Allotted exists."""
    wanted = [(int(r["room_id"]), r["occupancy"]) for r in rooms]
    if len({rid for rid, _ in wanted}) != len(wanted):
        raise BadRequestError("A room is listed twice.", code="duplicate_room")
    for _, occupancy in wanted:
        if occupancy not in tariffs.OCCUPANCIES:
            raise BadRequestError("Occupancy must be single or double.",
                                  code="invalid_occupancy")

    def effect(booking: Booking) -> list[str]:
        if len(wanted) != booking.rooms_required:
            raise ConflictError(
                f"This booking needs {booking.rooms_required} room(s); "
                f"{len(wanted)} were chosen.", code="room_count_mismatch")
        # Locked in id order, so two allotments cannot deadlock on each other.
        locked = {r.pk: r for r in Room.objects.select_for_update()
                  .filter(pk__in=[rid for rid, _ in wanted]).order_by("pk")}
        taken = room_selectors.occupied_room_ids(
            booking.arrival_date, booking.departure_date, exclude_booking_id=booking.pk)
        for rid, _ in wanted:
            room = locked.get(rid)
            if room is None or not room.is_active:
                raise ConflictError(f"Room {rid} does not exist or is out of service.",
                                    code="room_unavailable")
            if rid in taken:
                raise ConflictError(
                    f"Room {room.number} is already allotted for those dates.",
                    code="room_unavailable")
        RoomAllotment.objects.bulk_create([
            RoomAllotment(booking=booking, room_id=rid, occupancy=occ,
                          allotted_by_user_id=actor.user_id) for rid, occ in wanted])
        return []

    return transition(booking_id=booking_id, to_status=sm.ROOM_ALLOTTED, actor=actor,
                      lane=sm.CARETAKER, scope=scope, effect=effect)


# -- UC-VH-009 / UC-VH-021: check-in and check-out -----------------------------
def _recorded_time(at: datetime | None, *, not_before: datetime, what: str) -> datetime:
    """The time the Caretaker states, or now. Never in the future, never before
    the record could have happened."""
    now = timezone.now()
    at = at or now
    if at > now:
        raise BadRequestError(f"The {what} time cannot be in the future.",
                              code="time_in_future")
    if at < not_before:
        raise BadRequestError(f"The {what} time is earlier than this booking allows.",
                              code="time_too_early")
    return at


def check_in(*, booking_id: int, actor, at: datetime | None = None, scope=None) -> Booking:
    def effect(booking: Booking) -> list[str]:
        earliest = timezone.make_aware(datetime.combine(booking.arrival_date, time.min))
        booking.checked_in_at = _recorded_time(
            at, not_before=max(earliest, booking.created_at), what="check-in")
        return ["checked_in_at"]

    return transition(booking_id=booking_id, to_status=sm.CHECKED_IN, actor=actor,
                      lane=sm.CARETAKER, scope=scope, effect=effect)


def check_out(*, booking_id: int, actor, at: datetime | None = None, scope=None) -> Booking:
    def effect(booking: Booking) -> list[str]:
        booking.checked_out_at = _recorded_time(
            at, not_before=booking.checked_in_at, what="check-out")
        return ["checked_out_at"]

    return transition(booking_id=booking_id, to_status=sm.CHECKED_OUT, actor=actor,
                      lane=sm.CARETAKER, scope=scope, effect=effect)


# -- UC-VH-007 / UC-VH-020: cancellation ---------------------------------------
def one_day_rent(booking: Booking):
    """The rooms actually allotted if any, otherwise the rooms requested."""
    occupancies = list(booking.allotments.values_list("occupancy", flat=True)) \
        or [booking.occupancy] * booking.rooms_required
    try:
        return billing_rules.one_day_rent(
            occupancies, category=booking.category, on=booking.arrival_date,
            rates=tariff_selectors.room_rates(booking.category))
    except tariffs.NoApplicableTariff as exc:
        raise ConflictError(
            f"{exc} The charge cannot be worked out until it is.",
            code="tariff_missing") from exc


def _own_booking(scope, booking_id: int, actor) -> Booking:
    booking = scope.select_for_update().filter(pk=booking_id).first()
    if booking is None or booking.indenter_user_id != actor.user_id:
        raise NotFoundError("No such booking.")
    return booking


@transaction.atomic
def request_cancellation(*, booking_id: int, actor, reason: str = "",
                         scope=None) -> CancellationRequest:
    """Records the request and its charge case; the booking is untouched until
    the Caretaker confirms (UC-VH-007 minimal guarantee)."""
    authz.require(actor, perms.CANCELLATION_CREATE)
    booking = _own_booking(scope if scope is not None else Booking.objects.all(),
                           booking_id, actor)
    if booking.status not in sm.PRE_ARRIVAL:
        raise ConflictError("Only a booking that has not yet started can be cancelled.",
                            code="not_pre_arrival")
    if CancellationRequest.objects.filter(booking=booking).exists():
        raise ConflictError("A cancellation has already been requested for this booking.",
                            code="already_requested")

    today = timezone.localdate()
    try:
        case = schedule.case_for(booking.arrival_date, today)
    except schedule.NotBeforeArrival as exc:
        raise ConflictError(str(exc), code="not_pre_arrival") from exc
    rent = one_day_rent(booking) if case.percent else None
    request = CancellationRequest.objects.create(
        booking=booking, requested_by_user_id=actor.user_id, requested_on=today,
        days_before_arrival=schedule.days_before(booking.arrival_date, today),
        charge_case=case.code, charge_percent=case.percent, one_day_rent=rent,
        charge_amount=schedule.charge(case, rent), reason=reason[:300])
    notifications.booking_event(
        booking, "cancellation.requested", key_suffix="requested",
        detail=f"Applicable cancellation charge: Rs {request.charge_amount} "
               f"({case.percent}% of one day's room rent, {case.rule}).")
    return request


def confirm_cancellation(*, booking_id: int, actor, scope=None) -> Booking:
    """UC-VH-020 and BR-VH-011: a non-zero charge becomes the booking's bill."""
    from modules.visitor_hostel.services import billing

    def effect(booking: Booking) -> list[str]:
        request = CancellationRequest.objects.select_for_update().get(booking=booking)
        request.status = "confirmed"
        request.confirmed_by_user_id = actor.user_id
        request.confirmed_at = timezone.now()
        request.save(update_fields=["status", "confirmed_by_user_id", "confirmed_at",
                                    "updated_at"])
        billing.bill_cancellation(booking, request, actor)
        return []

    booking = transition(booking_id=booking_id, to_status=sm.CANCELLED, actor=actor,
                         lane=sm.CARETAKER, scope=scope, effect=effect)
    notifications.booking_event(
        booking, "cancellation.confirmed",
        detail=f"Cancellation charge: Rs {booking.cancellation.charge_amount}.")
    return booking


# -- UC-VH-006 / UC-VH-022: modification ---------------------------------------
def _jsonable(value):
    if isinstance(value, (date, time)):
        return value.isoformat()
    return value


def _parse(field: str, value):
    if value is None:
        return None
    if field.endswith("_date"):
        return date.fromisoformat(value)
    if field.endswith("_time"):
        return time.fromisoformat(value)
    return value


@transaction.atomic
def request_modification(*, booking_id: int, actor, changes: dict, reason: str = "",
                         scope=None) -> ModificationRequest:
    """Recorded only; the booking changes when an outcome is confirmed."""
    authz.require(actor, perms.MODIFICATION_CREATE)
    booking = _own_booking(scope if scope is not None else Booking.objects.all(),
                           booking_id, actor)
    if booking.status not in sm.PRE_ARRIVAL or timezone.localdate() > booking.arrival_date:
        raise ConflictError("A booking can only be modified before arrival.",
                            code="not_pre_arrival")
    unknown = set(changes) - set(req.MODIFIABLE_FIELDS)
    if unknown or not changes:
        raise BadRequestError(
            f"Only {', '.join(req.MODIFIABLE_FIELDS)} can be changed.",
            code="invalid_modification")
    _validate({**{f: getattr(booking, f) for f in REQUISITION_FIELDS}, **changes})
    try:
        with transaction.atomic():
            mod = ModificationRequest.objects.create(
                booking=booking, requested_by_user_id=actor.user_id,
                changes={k: _jsonable(v) for k, v in changes.items()},
                reason=reason[:300])
    except IntegrityError as exc:
        raise ConflictError("A modification is already awaiting confirmation.",
                            code="modification_open") from exc
    notifications.booking_event(booking, "modification.requested",
                                key_suffix=f"mod{mod.pk}")
    return mod


@transaction.atomic
def confirm_modification(*, modification_id: int, actor) -> ModificationRequest:
    """UC-VH-022 (provisional): the confirming authority is unresolved, so this
    needs a code no designation holds until the institute names one."""
    authz.require(actor, perms.MODIFICATION_APPROVE)
    mod = (ModificationRequest.objects.select_for_update()
           .filter(pk=modification_id, status="requested").first())
    if mod is None:
        raise NotFoundError("No open modification request with that id.")
    booking = Booking.objects.select_for_update().get(pk=mod.booking_id)
    authz.refuse_own(actor, booking)
    if booking.status not in (sm.PENDING, sm.FORWARDED, sm.APPROVED):
        raise ConflictError(
            "Rooms are already allotted; cancel and re-book to change this stay.",
            code="modification_after_allotment")

    changes = {k: _parse(k, v) for k, v in mod.changes.items()}
    _validate({**{f: getattr(booking, f) for f in REQUISITION_FIELDS}, **changes})
    mod.previous = {k: _jsonable(getattr(booking, k)) for k in changes}
    for field, value in changes.items():
        setattr(booking, field, value)
    booking.save(update_fields=[*changes, "updated_at"])

    mod.status = "confirmed"
    mod.confirmed_by_user_id = actor.user_id
    mod.confirmed_at = timezone.now()
    mod.save(update_fields=["previous", "status", "confirmed_by_user_id",
                            "confirmed_at", "updated_at"])
    _audit(booking, booking.status, booking.status, actor, sm.SYSTEM,
           f"modification #{mod.pk} confirmed")
    notifications.booking_event(booking, "modification.confirmed",
                                key_suffix=f"mod{mod.pk}")
    return mod
