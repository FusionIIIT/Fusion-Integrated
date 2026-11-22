# Booking lifecycle services and state transitions for VHMS.
import uuid
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.vh.domain.cancellation import (
    compute_cancellation_percentage,
)
from modules.vh.domain.rules import (
    validate_billing_responsibility,
    validate_stay_dates,
    validate_visitor_category,
)
from modules.vh.domain.state_machine import (
    TERMINAL_STATES,
    InvalidStateTransitionError,
    can_cancel_booking,
    can_modify_booking,
    transition,
)
from modules.vh.models.booking import Booking
from modules.vh.models.visitor import VisitorDetail
from modules.vh.services.notifications import notify_booking_decision, notify_booking_submission


def generate_booking_reference() -> str:
    # Generates unique reference code for a booking.
    return f"VH-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"


@transaction.atomic
def create_online_booking(data: dict, principal) -> Booking:
    # CFR-VH-002: Creates standardized online booking requisition in Pending state.
    indenter_id = getattr(principal, "user_id", None)
    if indenter_id is None:
        raise PermissionDeniedError("Valid indenter identity is required to submit a booking.")

    billing_resp = validate_billing_responsibility(data.get("billing_responsibility", "visitor"))
    category = validate_visitor_category(data.get("visitor_category", "A"))
    arrival = data.get("arrival_date")
    departure = data.get("departure_date")
    if not arrival or not departure:
        raise BadRequestError("Arrival and departure dates are required.")
    if isinstance(arrival, str):
        arrival = date.fromisoformat(arrival)
    if isinstance(departure, str):
        departure = date.fromisoformat(departure)
    try:
        validate_stay_dates(arrival, departure)
    except ValueError as err:
        raise BadRequestError(str(err)) from None

    num_rooms = int(data.get("number_of_rooms", 1))
    num_occupants = int(data.get("number_of_occupants", 1))
    if num_rooms < 1 or num_occupants < 1:
        raise BadRequestError("Number of rooms and occupants must be at least 1.")

    ref = generate_booking_reference()
    booking = Booking.objects.create(
        booking_reference=ref,
        indenter_id=indenter_id,
        is_offline=False,
        booking_source="online",
        status="pending",
        visitor_category=category,
        visit_purpose=data.get("visit_purpose", "").strip(),
        arrival_date=arrival,
        departure_date=departure,
        number_of_rooms=num_rooms,
        number_of_occupants=num_occupants,
        billing_responsibility=billing_resp,
    )

    visitors = data.get("visitors", [])
    if visitors:
        for v in visitors:
            VisitorDetail.objects.create(
                booking=booking,
                name=v.get("name", "Guest").strip(),
                email=v.get("email", "").strip(),
                phone=v.get("phone", "").strip(),
                organization=v.get("organization", "").strip(),
                designation=v.get("designation", "").strip(),
                gender=v.get("gender", "").strip(),
            )
    else:
        VisitorDetail.objects.create(
            booking=booking,
            name=data.get("visitor_name", "Primary Guest").strip(),
            email=data.get("visitor_email", "").strip(),
            phone=data.get("visitor_phone", "").strip(),
        )

    notify_booking_submission(booking)
    return booking


@transaction.atomic
def create_offline_booking(data: dict, principal) -> Booking:
    # CFR-VH-004: Caretaker records telephonic or walk-in booking flagged as offline.
    source = data.get("booking_source", "walk_in").strip().lower()
    if source not in {"telephonic", "walk_in"}:
        raise BadRequestError("Offline booking source must be telephonic or walk_in.")

    billing_resp = validate_billing_responsibility(data.get("billing_responsibility", "visitor"))
    category = validate_visitor_category(data.get("visitor_category", "A"))
    arrival = data.get("arrival_date")
    departure = data.get("departure_date")
    if not arrival or not departure:
        raise BadRequestError("Arrival and departure dates are required.")
    if isinstance(arrival, str):
        arrival = date.fromisoformat(arrival)
    if isinstance(departure, str):
        departure = date.fromisoformat(departure)
    try:
        validate_stay_dates(arrival, departure)
    except ValueError as err:
        raise BadRequestError(str(err)) from None

    indenter_id = data.get("indenter_id") or getattr(principal, "user_id", 0)

    booking = Booking.objects.create(
        booking_reference=generate_booking_reference(),
        indenter_id=indenter_id,
        is_offline=True,
        booking_source=source,
        status="pending_offline",
        visitor_category=category,
        visit_purpose=data.get("visit_purpose", "Offline booking").strip(),
        arrival_date=arrival,
        departure_date=departure,
        number_of_rooms=int(data.get("number_of_rooms", 1)),
        number_of_occupants=int(data.get("number_of_occupants", 1)),
        billing_responsibility=billing_resp,
    )

    VisitorDetail.objects.create(
        booking=booking,
        name=data.get("visitor_name", "Walk-in Guest").strip(),
        email=data.get("visitor_email", "").strip(),
        phone=data.get("visitor_phone", "").strip(),
    )
    return booking


@transaction.atomic
def transition_booking_state(
    booking_id: int, event: str, actor_role: str, principal, reason: str = ""
) -> Booking:
    # Transactional choke point for all booking state progressions.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} does not exist.") from None

    if booking.status in TERMINAL_STATES:
        raise ConflictError(f"Booking is in terminal state '{booking.status}' and cannot advance.")

    try:
        next_state = transition(booking.status, event, actor_role)
    except InvalidStateTransitionError as err:
        raise ConflictError(str(err)) from None

    booking.status = next_state
    if "reject" in event:
        booking.rejection_reason = reason.strip()
    if "cancellation" in event:
        if event == "request_cancellation":
            booking.cancellation_reason = reason.strip()
            booking.cancellation_requested_at = timezone.now()
        elif event == "confirm_cancellation":
            booking.cancellation_confirmed_at = timezone.now()

    booking.save()

    if next_state in {"approved", "approved_offline", "rejected", "rejected_offline"}:
        notify_booking_decision(booking)

    return booking


def caretaker_route_booking(booking_id: int, action: str, principal, reason: str = "") -> Booking:
    # UC-VH-003: Caretaker directly rejects or forwards booking to VH In-Charge.
    act = action.strip().lower()
    if act == "reject":
        return transition_booking_state(
            booking_id, "caretaker_reject", "caretaker", principal, reason
        )
    if act == "forward":
        return transition_booking_state(
            booking_id, "caretaker_forward", "caretaker", principal, reason
        )
    raise BadRequestError("Route action must be 'reject' or 'forward'.")


def incharge_decide_booking(booking_id: int, action: str, principal, reason: str = "") -> Booking:
    # UC-VH-004: VH In-Charge approves or rejects forwarded booking.
    act = action.strip().lower()
    if act == "approve":
        return transition_booking_state(
            booking_id, "incharge_approve", "incharge", principal, reason
        )
    if act == "reject":
        return transition_booking_state(
            booking_id, "incharge_reject", "incharge", principal, reason
        )
    raise BadRequestError("Decision action must be 'approve' or 'reject'.")


@transaction.atomic
def request_cancellation(booking_id: int, reason: str, principal) -> Booking:
    # CFR-VH-006, BR-VH-006..009: Indenter requests pre-arrival cancellation.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    user_id = getattr(principal, "user_id", None)
    perms = getattr(principal, "permissions", set())
    if "vh.booking.review" not in perms and booking.indenter_id != user_id:
        raise PermissionDeniedError("You can only request cancellation for your own bookings.")

    if not can_cancel_booking(booking.status):
        raise ConflictError(f"Cannot cancel booking in '{booking.status}' status.")

    today = date.today()
    if booking.arrival_date < today:
        raise ConflictError("Cannot cancel a booking after arrival date has passed.")

    pct = compute_cancellation_percentage(booking.arrival_date, today)
    booking.cancellation_charge_percentage = pct
    booking.cancellation_reason = reason.strip()
    booking.cancellation_requested_at = timezone.now()
    booking.status = "cancellation_requested"
    booking.save()
    return booking


@transaction.atomic
def confirm_cancellation(booking_id: int, principal) -> Booking:
    # UC-VH-020, BR-VH-011: Caretaker confirms cancellation and generates cancellation bill.
    from modules.vh.services.billing import generate_bill

    booking = transition_booking_state(booking_id, "confirm_cancellation", "caretaker", principal)
    generate_bill(booking.id, principal)
    return booking


@transaction.atomic
def request_booking_modification(booking_id: int, updates: dict, principal) -> Booking:
    # CFR-VH-005, UC-VH-006: Indenter requests modification before arrival.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    user_id = getattr(principal, "user_id", None)
    perms = getattr(principal, "permissions", set())
    if "vh.booking.review" not in perms and booking.indenter_id != user_id:
        raise PermissionDeniedError("You can only modify your own bookings.")

    if not can_modify_booking(booking.status):
        raise ConflictError(f"Cannot modify booking in '{booking.status}' status.")

    if "arrival_date" in updates or "departure_date" in updates:
        arr = date.fromisoformat(str(updates.get("arrival_date", booking.arrival_date)))
        dep = date.fromisoformat(str(updates.get("departure_date", booking.departure_date)))
        validate_stay_dates(arr, dep)
        booking.arrival_date = arr
        booking.departure_date = dep

    if "visit_purpose" in updates:
        booking.visit_purpose = str(updates["visit_purpose"]).strip()
    if "visitor_category" in updates:
        booking.visitor_category = validate_visitor_category(updates["visitor_category"])
    if "number_of_rooms" in updates:
        booking.number_of_rooms = int(updates["number_of_rooms"])
    if "number_of_occupants" in updates:
        booking.number_of_occupants = int(updates["number_of_occupants"])
    if "billing_responsibility" in updates:
        booking.billing_responsibility = validate_billing_responsibility(
            updates["billing_responsibility"]
        )

    booking.save()
    return booking
