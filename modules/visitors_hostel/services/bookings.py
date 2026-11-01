"""Booking workflows. State, permission, scope, and audit are checked together."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.visitors_hostel.domain import rules, state_machine as sm
from modules.visitors_hostel.models import (
    Booking, BookingChangeRequest, BookingTransition, OperationalRoleAssignment,
    Room, RoomAllocation, StayRecord, Tariff)
from modules.visitors_hostel.services import notifications


def _user_id(actor):
    return getattr(actor, "user_id", None)


def _require(actor, permission):
    if actor is None or not actor.has_permission(permission):
        raise PermissionDeniedError("Your role cannot perform this action.",
                                    code="permission_denied")


def _record(booking, target, actor, role, reason=""):
    try:
        sm.resolve(booking.status, target, role)
    except (sm.InvalidTransition, sm.ActorNotAllowed) as exc:
        raise ConflictError(str(exc), code="invalid_transition") from exc
    old = booking.status
    booking.status = target
    booking.save(update_fields=["status", "updated_at"])
    BookingTransition.objects.create(
        booking=booking, from_status=old, to_status=target,
        actor_user_id=_user_id(actor), actor_role=role, reason=reason)


def _role_user(role):
    return OperationalRoleAssignment.objects.filter(
        role=role, ends_at__isnull=True).values_list("user_id", flat=True).first()


def _available_rooms(*, arrival, departure, occupancy, room_kind):
    conflicts = RoomAllocation.objects.filter(
        arrival_date__lt=departure, departure_date__gt=arrival,
        booking__status__in=[sm.APPROVED, sm.ROOM_ALLOTTED, sm.CHECKED_IN])
    return Room.objects.filter(
        active=True, status="available", occupancy=occupancy,
        room_type__room_kind=room_kind,
        room_type__is_active=True, building__is_active=True,
    ).exclude(pk__in=conflicts.values("room_id"))


def _assert_availability(*, arrival, departure, occupancy, room_kind, count):
    available = _available_rooms(arrival=arrival, departure=departure,
                                 occupancy=occupancy, room_kind=room_kind).count()
    if available < count:
        raise ConflictError("There are not enough rooms available for those dates.",
                            code="insufficient_availability",
                            details=[{"requested": count, "available": available}])


def _booking_number():
    prefix = "VH" + timezone.localdate().strftime("%Y%m%d")
    last = Booking.objects.filter(booking_number__startswith=prefix).order_by(
        "-booking_number").values_list("booking_number", flat=True).first()
    seq = int(last[-4:]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


@transaction.atomic
def create_booking(*, actor, data, source="online"):
    role = "indenter" if source == "online" else "caretaker"
    permission = ("visitor_hostel.booking.create" if source == "online"
                  else "visitor_hostel.booking.record_offline")
    _require(actor, permission)
    if source not in {"online", "offline"}:
        raise ConflictError("Booking source must be online or offline.",
                            code="invalid_source")
    try:
        rules.validate_booking(
            category=data["visitor_category"],
            billing_responsibility=data["billing_responsibility"],
            arrival_date=data["arrival_date"], departure_date=data["departure_date"],
            rooms=int(data["room_count"]), occupants=int(data["occupant_count"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise ConflictError(str(exc) or "Required booking fields are missing.",
                            code="invalid_booking") from exc
    _assert_availability(
        arrival=data["arrival_date"], departure=data["departure_date"],
        occupancy=data["requested_occupancy"],
        room_kind=data["requested_room_kind"], count=int(data["room_count"]))
    booking = Booking.objects.create(
        booking_number=_booking_number(), source=source, status=sm.PENDING,
        indenter_user_id=_user_id(actor) if source == "online" else None,
        created_by_user_id=_user_id(actor), **data)
    BookingTransition.objects.create(
        booking=booking, from_status="", to_status=sm.PENDING,
        actor_user_id=_user_id(actor), actor_role=role)
    if booking.indenter_user_id:
        notifications.enqueue(
            topic="booking.submitted", dedupe_key=f"booking:{booking.pk}:submitted",
            subject=f"Visitors Hostel booking {booking.booking_number} submitted",
            body="Your Visitors Hostel booking request has been submitted.",
            user_id=booking.indenter_user_id, payload={"booking_id": booking.pk})
    return booking


@transaction.atomic
def review_booking(*, booking_id, actor, outcome, note=""):
    _require(actor, "visitor_hostel.booking.review")
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    if outcome not in {"forward", "reject"}:
        raise ConflictError("Outcome must be forward or reject.", code="invalid_outcome")
    target = sm.FORWARDED if outcome == "forward" else sm.REJECTED
    booking.decision_note = note
    _record(booking, target, actor, sm.CARETAKER, note)
    if target == sm.FORWARDED:
        recipient = _role_user("vh_in_charge")
        if recipient:
            notifications.enqueue(
                topic="booking.submitted",
                dedupe_key=f"booking:{booking.pk}:forwarded",
                subject=f"Booking {booking.booking_number} awaits a decision",
                body="A Visitors Hostel booking was forwarded for your decision.",
                user_id=recipient, payload={"booking_id": booking.pk})
    if target == sm.REJECTED and booking.indenter_user_id:
        notifications.enqueue(
            topic="booking.decided", dedupe_key=f"booking:{booking.pk}:rejected",
            subject=f"Booking {booking.booking_number} was rejected",
            body=note or "The booking request was rejected.",
            user_id=booking.indenter_user_id)
    return booking


@transaction.atomic
def decide_booking(*, booking_id, actor, decision, note=""):
    _require(actor, "visitor_hostel.booking.decide")
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    if decision not in {"approve", "reject"}:
        raise ConflictError("Decision must be approve or reject.", code="invalid_decision")
    target = sm.APPROVED if decision == "approve" else sm.REJECTED
    booking.decision_note = note
    _record(booking, target, actor, sm.IN_CHARGE, note)
    if booking.indenter_user_id:
        notifications.enqueue(
            topic="booking.decided", dedupe_key=f"booking:{booking.pk}:{target}",
            subject=f"Booking {booking.booking_number}: {target.title()}",
            body=note or f"Your booking request was {target}.",
            user_id=booking.indenter_user_id)
    return booking


def _one_day_rent(booking):
    tariff = Tariff.objects.filter(
        occupancy=booking.requested_occupancy,
        visitor_category=booking.visitor_category,
        effective_from__lte=booking.arrival_date, active=True,
    ).order_by("-effective_from").first()
    if tariff is None:
        raise ConflictError("No applicable tariff is configured.", code="tariff_missing")
    return tariff.daily_rate * booking.room_count


@transaction.atomic
def request_cancellation(*, booking_id, actor, requested_on=None):
    booking = Booking.objects.select_for_update().filter(
        pk=booking_id, indenter_user_id=_user_id(actor)).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    _require(actor, "visitor_hostel.booking.cancel_self")
    requested_on = requested_on or timezone.localdate()
    if requested_on > booking.arrival_date:
        raise ConflictError("Cancellation requests must be made before arrival.",
                            code="cancellation_after_arrival")
    charge = rules.cancellation_charge(
        arrival_date=booking.arrival_date, cancellation_date=requested_on,
        one_day_room_rent=_one_day_rent(booking))
    booking.cancellation_charge = charge
    booking.cancellation_requested_at = timezone.now()
    booking.save(update_fields=["cancellation_charge", "cancellation_requested_at",
                                "updated_at"])
    _record(booking, sm.CANCELLATION_REQUESTED, actor, sm.INDENTER)
    recipient = _role_user("caretaker")
    if recipient:
        notifications.enqueue(
            topic="booking.cancelled",
            dedupe_key=f"booking:{booking.pk}:cancellation-requested",
            subject=f"Cancellation requested: {booking.booking_number}",
            body="An Indenter requested cancellation of a Visitors Hostel booking.",
            user_id=recipient, payload={"booking_id": booking.pk})
    return booking


@transaction.atomic
def request_modification(*, booking_id, actor, requested_changes):
    booking = Booking.objects.select_for_update().filter(
        pk=booking_id, indenter_user_id=_user_id(actor)).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    _require(actor, "visitor_hostel.booking.modify_self")
    if timezone.localdate() >= booking.arrival_date:
        raise ConflictError("Modification requests must be made before arrival.",
                            code="modification_after_arrival")
    allowed = {"visitor_name", "visitor_email", "visitor_phone", "purpose",
               "arrival_date", "departure_date", "room_count", "occupant_count",
               "requested_occupancy", "requested_room_kind", "billing_responsibility"}
    if not requested_changes or set(requested_changes) - allowed:
        raise ConflictError("Modification contains unsupported fields.",
                            code="invalid_modification")
    request = BookingChangeRequest.objects.create(
        booking=booking, requested_by_user_id=_user_id(actor),
        requested_changes=requested_changes)
    recipient = _role_user("caretaker")
    if recipient:
        notifications.enqueue(
            topic="booking.modified",
            dedupe_key=f"booking:{booking.pk}:modification:{request.pk}",
            subject=f"Modification requested: {booking.booking_number}",
            body="An Indenter requested a booking modification for review.",
            user_id=recipient, payload={"booking_id": booking.pk,
                                        "change_request_id": request.pk})
    return request


@transaction.atomic
def confirm_cancellation(*, booking_id, actor, confirm, note=""):
    _require(actor, "visitor_hostel.booking.review")
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    if not confirm:
        raise ConflictError("Cancellation request was not confirmed.",
                            code="cancellation_not_confirmed")
    booking.cancellation_confirmed_at = timezone.now()
    booking.decision_note = note
    booking.save(update_fields=["cancellation_confirmed_at", "decision_note", "updated_at"])
    _record(booking, sm.CANCELLED, actor, sm.CARETAKER, note)
    if booking.indenter_user_id:
        notifications.enqueue(
            topic="booking.cancelled",
            dedupe_key=f"booking:{booking.pk}:cancelled",
            subject=f"Booking {booking.booking_number} cancelled",
            body="The cancellation request was confirmed.",
            user_id=booking.indenter_user_id,
            payload={"booking_id": booking.pk,
                     "cancellation_charge": str(booking.cancellation_charge)})
    return booking


@transaction.atomic
def allot_rooms(*, booking_id, actor, room_ids):
    _require(actor, "visitor_hostel.room.manage")
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    if len(room_ids) != booking.room_count:
        raise ConflictError("The number of allotted rooms must match the booking.",
                            code="room_count_mismatch")
    rooms = list(_available_rooms(
        arrival=booking.arrival_date, departure=booking.departure_date,
        occupancy=booking.requested_occupancy,
        room_kind=booking.requested_room_kind).filter(pk__in=room_ids))
    if len(rooms) != len(set(room_ids)):
        raise ConflictError("One or more selected rooms are unavailable.",
                            code="room_unavailable")
    tariffs = {}
    for tariff in Tariff.objects.filter(
            occupancy=booking.requested_occupancy,
            visitor_category=booking.visitor_category,
            effective_from__lte=booking.arrival_date, active=True).order_by("-effective_from"):
        tariffs.setdefault(tariff.occupancy, tariff.daily_rate)
    if not tariffs:
        raise ConflictError("No applicable tariff is configured.", code="tariff_missing")
    rate = tariffs[booking.requested_occupancy]
    allocations = [RoomAllocation.objects.create(
        booking=booking, room=room, arrival_date=booking.arrival_date,
        departure_date=booking.departure_date, occupancy=booking.requested_occupancy,
        tariff_daily_snapshot=rate) for room in rooms]
    _record(booking, sm.ROOM_ALLOTTED, actor, sm.CARETAKER)
    for allocation in allocations:
        StayRecord.objects.create(allocation=allocation)
    return allocations


@transaction.atomic
def record_check_in(*, booking_id, actor):
    _require(actor, "visitor_hostel.stay.manage")
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    allocations = list(booking.allocations.select_related("stay"))
    if not allocations or any(a.stay.checked_in_at for a in allocations):
        raise ConflictError("Booking has no allotment or is already checked in.",
                            code="invalid_check_in")
    now = timezone.now()
    for allocation in allocations:
        allocation.stay.checked_in_at = now
        allocation.stay.checked_in_by_user_id = _user_id(actor)
        allocation.stay.save(update_fields=["checked_in_at", "checked_in_by_user_id"])
    _record(booking, sm.CHECKED_IN, actor, sm.CARETAKER)
    return booking


@transaction.atomic
def record_check_out(*, booking_id, actor, bill_verified=False):
    _require(actor, "visitor_hostel.stay.manage")
    booking = Booking.objects.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    allocations = list(booking.allocations.select_related("stay"))
    if not allocations or any(not a.stay.checked_in_at or a.stay.checked_out_at
                              for a in allocations):
        raise ConflictError("Booking is not in a check-out eligible state.",
                            code="invalid_check_out")
    now = timezone.now()
    for allocation in allocations:
        allocation.stay.checked_out_at = now
        allocation.stay.checked_out_by_user_id = _user_id(actor)
        allocation.stay.bill_verified = bool(bill_verified)
        allocation.stay.bill_verified_at = now if bill_verified else None
        allocation.stay.save(update_fields=["checked_out_at", "checked_out_by_user_id",
                                            "bill_verified", "bill_verified_at"])
    _record(booking, sm.CHECKED_OUT, actor, sm.CARETAKER)
    return booking
