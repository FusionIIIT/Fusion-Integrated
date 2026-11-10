"""Bills, meals and offline settlement (UC-VH-012, UC-VH-013, UC-VH-021).

A bill is written once. Its lines copy the rate they used, so a later tariff
cannot reach back into it (BR-VH-024), and nothing here ever updates an
amount (BR-VH-037): settlement and verification fill their own fields, once.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.visitor_hostel.domain import billing as rules
from modules.visitor_hostel.domain import cancellation as schedule
from modules.visitor_hostel.domain import meals as meal_rules
from modules.visitor_hostel.domain import permissions as perms
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.domain import tariffs
from modules.visitor_hostel.models import (
    Bill,
    BillLine,
    Booking,
    MealBooking,
    StayAlert,
)
from modules.visitor_hostel.selectors import tariffs as tariff_selectors
from modules.visitor_hostel.services import authz

log = logging.getLogger("fusion.visitor_hostel.billing")


def _write(booking: Booking, lines: list[rules.Line], actor) -> Bill:
    t = rules.totals(lines)
    bill = Bill.objects.create(
        booking=booking, billing_responsibility=booking.billing_responsibility,
        billing_reference=booking.billing_reference, room_amount=t.room,
        meal_amount=t.meal, cancellation_amount=t.cancellation, total=t.total,
        generated_by_user_id=actor.user_id)
    BillLine.objects.bulk_create([
        BillLine(bill=bill, kind=ln.kind, description=ln.description[:200],
                 quantity=ln.quantity, unit_rate=ln.unit_rate, amount=ln.amount,
                 tariff_ref=ln.tariff_ref) for ln in lines])
    log.info("visitor_hostel.bill.generated booking=%s total=%s", booking.pk, t.total)
    return bill


def _charge_line(case: schedule.ChargeCase, amount: Decimal) -> rules.Line:
    label = "No-show" if case.code == schedule.NO_SHOW.code else "Cancellation"
    return rules.Line(rules.CANCELLATION,
                      f"{label} charge: {case.percent}% of one day's room rent "
                      f"({case.rule})", 1, amount, amount)


def bill_cancellation(booking: Booking, request, actor) -> Bill | None:
    """BR-VH-011, inside the confirming transaction. Nothing owed, no bill."""
    if request.charge_amount <= 0:
        return None
    case = schedule.CASES[request.charge_case]
    return _write(booking, [_charge_line(case, request.charge_amount)], actor)


def _stay_lines(booking: Booking) -> list[rules.Line]:
    check_in = timezone.localdate(booking.checked_in_at)
    check_out = timezone.localdate(booking.checked_out_at)
    allotments = [(a.room.number, a.occupancy)
                  for a in booking.allotments.select_related("room").order_by("room__number")]
    lines = rules.room_lines(allotments, category=booking.category, check_in=check_in,
                             check_out=check_out,
                             rates=tariff_selectors.room_rates(booking.category))
    qty: dict[tuple[date, str], int] = defaultdict(int)
    for m in booking.meals.all():
        qty[(m.meal_date, meal_rules.priced_item(m.kind, m.item))] += m.quantity
    lines += rules.meal_lines([(d, item, n) for (d, item), n in qty.items()],
                              tariff_selectors.meal_rates())
    return lines


@transaction.atomic
def generate(*, booking_id: int, actor, scope=None) -> Bill:
    """UC-VH-013. After check-out, or for a recorded no-show (BR-VH-009)."""
    qs = scope if scope is not None else Booking.objects.all()
    booking = qs.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    authz.require_operator(actor, sm.CARETAKER, perms.BILL_MANAGE, booking=booking)
    if Bill.objects.filter(booking=booking).exists():
        raise ConflictError("This booking already has a bill, and bills are never "
                            "regenerated.", code="already_billed")

    try:
        if booking.status == sm.CHECKED_OUT:
            lines = _stay_lines(booking)
        elif (booking.status in (sm.APPROVED, sm.ROOM_ALLOTTED)
              and StayAlert.objects.filter(booking=booking,
                                           kind=StayAlert.NO_SHOW).exists()):
            from modules.visitor_hostel.services.bookings import one_day_rent

            amount = schedule.charge(schedule.NO_SHOW, one_day_rent(booking))
            lines = [_charge_line(schedule.NO_SHOW, amount)]
        else:
            raise ConflictError(
                "A bill is generated after check-out, or for a recorded no-show.",
                code="not_billable")
    except tariffs.NoApplicableTariff as exc:
        raise ConflictError(str(exc), code="tariff_missing") from exc
    return _write(booking, lines, actor)


def _locked_bill(bill_id: int, scope) -> Bill:
    qs = scope if scope is not None else Bill.objects.all()
    bill = (qs.select_for_update(of=("self",)).select_related("booking")
            .filter(pk=bill_id).first())
    if bill is None:
        raise NotFoundError("No such bill.")
    return bill


@transaction.atomic
def settle(*, bill_id: int, actor, amount: Decimal, receipt_reference: str = "",
           scope=None) -> Bill:
    """BR-VH-036: offline cash, in full, recorded once."""
    bill = _locked_bill(bill_id, scope)
    authz.require_operator(actor, sm.CARETAKER, perms.BILL_MANAGE, booking=bill.booking)
    if bill.status == "settled":
        raise ConflictError("This bill is already settled.", code="already_settled")
    if rules.money(amount) != bill.total:
        raise ConflictError(
            f"The bill total is Rs {bill.total}; record the settlement for exactly "
            f"that amount.", code="amount_mismatch")
    bill.status = "settled"
    bill.settlement_mode = "cash"
    bill.settled_amount = bill.total
    bill.receipt_reference = receipt_reference[:60]
    bill.settled_by_user_id = actor.user_id
    bill.settled_at = timezone.now()
    bill.save(update_fields=["status", "settlement_mode", "settled_amount",
                             "receipt_reference", "settled_by_user_id", "settled_at"])
    return bill


@transaction.atomic
def record_verification(*, bill_id: int, actor, note: str = "", scope=None) -> Bill:
    """AFR-VH-065: the guest checked the bill at the desk; no visitor login."""
    bill = _locked_bill(bill_id, scope)
    authz.require_operator(actor, sm.CARETAKER, perms.BILL_MANAGE)
    if bill.guest_verified:
        raise ConflictError("Verification is already recorded for this bill.",
                            code="already_verified")
    bill.guest_verified = True
    bill.verification_note = note[:300]
    bill.verified_by_user_id = actor.user_id
    bill.verified_at = timezone.now()
    bill.save(update_fields=["guest_verified", "verification_note",
                             "verified_by_user_id", "verified_at"])
    return bill


@transaction.atomic
def add_meal(*, booking_id: int, actor, meal_date: date, kind: str, item: str = "",
             quantity: int = 1, scope=None) -> MealBooking:
    """UC-VH-012: only for a guest who is staying (BR-VH-025)."""
    qs = scope if scope is not None else Booking.objects.all()
    booking = qs.select_for_update().filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    authz.require_operator(actor, sm.CARETAKER, perms.MEAL_MANAGE)
    if booking.status != sm.CHECKED_IN:
        raise ConflictError("Meals are booked only for a guest who has checked in.",
                            code="guest_not_staying")
    if Bill.objects.filter(booking=booking).exists():
        raise ConflictError("This stay is already billed.", code="already_billed")
    if quantity < 1:
        raise BadRequestError("Quantity must be at least 1.", code="invalid_quantity")
    try:
        meal_rules.priced_item(kind, item)
        meal_rules.within_stay(meal_date, booking.arrival_date, booking.departure_date)
    except meal_rules.InvalidMeal as exc:
        raise BadRequestError(str(exc), code=exc.code) from exc
    return MealBooking.objects.create(
        booking=booking, meal_date=meal_date, kind=kind, item=item,
        quantity=quantity, recorded_by_user_id=actor.user_id)
