"""The listed reports, and only those (UC-VH-017, UC-VH-018). Read-only."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum

from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import (
    Bill,
    Booking,
    InventoryAdjustment,
    InventoryItem,
    RoomAllotment,
    StayAlert,
)
from modules.visitor_hostel.selectors.rooms import HOLDING

ZERO = Decimal("0.00")


# -- VH In-Charge (UC-VH-017) --------------------------------------------------
def booking_summary(start: date, end: date) -> dict:
    """AFR-VH-082. Bookings whose stay starts in the range, online vs offline."""
    qs = Booking.objects.filter(arrival_date__gte=start, arrival_date__lte=end)
    by_status = dict(qs.values_list("status").annotate(n=Count("id")))
    return {
        "from": start, "to": end,
        "total": sum(by_status.values()),
        "online": qs.filter(is_offline=False).count(),
        "offline": qs.filter(is_offline=True).count(),
        "by_status": {s: by_status.get(s, 0) for s in sm.ALL_STATES},
    }


def category_occupancy(start: date, end: date) -> dict:
    """AFR-VH-083. Room-days used per visitor category, counted inside the range."""
    days = defaultdict(int)
    bookings = defaultdict(set)
    rows = (RoomAllotment.objects
            .filter(booking__status__in=(*HOLDING, sm.CHECKED_OUT),
                    booking__arrival_date__lte=end,
                    booking__departure_date__gte=start)
            .values_list("booking_id", "booking__category",
                         "booking__arrival_date", "booking__departure_date"))
    for booking_id, category, arrival, departure in rows:
        lo, hi = max(arrival, start), min(departure, end + timedelta(days=1))
        days[category] += max(1, (hi - lo).days)
        bookings[category].add(booking_id)
    return {"from": start, "to": end,
            "categories": [{"category": c, "room_days": days.get(c, 0),
                            "bookings": len(bookings.get(c, ()))}
                           for c in ("A", "B", "C", "D")]}


def revenue_summary(start: date, end: date) -> dict:
    """AFR-VH-084. From VHMS bills only — not an accounting ledger (B-02)."""
    qs = Bill.objects.filter(generated_at__date__gte=start,
                             generated_at__date__lte=end)
    sums = qs.aggregate(room=Sum("room_amount"), meal=Sum("meal_amount"),
                        cancellation=Sum("cancellation_amount"), billed=Sum("total"),
                        settled=Sum("total", filter=Q(status="settled")))
    by_resp = (qs.values("billing_responsibility")
               .annotate(n=Count("id"), billed=Sum("total"))
               .order_by("billing_responsibility"))
    total = sums["billed"] or ZERO
    settled = sums["settled"] or ZERO
    return {
        "from": start, "to": end, "bills": qs.count(),
        "room": sums["room"] or ZERO, "meal": sums["meal"] or ZERO,
        "cancellation": sums["cancellation"] or ZERO,
        "total": total, "settled": settled, "outstanding": total - settled,
        "by_billing_responsibility": [
            {"billing_responsibility": r["billing_responsibility"],
             "bills": r["n"], "total": r["billed"] or ZERO} for r in by_resp],
    }


def inventory_usage(start: date, end: date) -> dict:
    """AFR-VH-085. Issued (negative) and received (positive) per item."""
    agg = (InventoryAdjustment.objects
           .filter(at__date__gte=start, at__date__lte=end)
           .values("item_id")
           .annotate(used=Sum("delta", filter=Q(delta__lt=0)),
                     received=Sum("delta", filter=Q(delta__gt=0))))
    by_item = {r["item_id"]: r for r in agg}
    items = []
    for item in InventoryItem.objects.order_by("name"):
        r = by_item.get(item.pk, {})
        items.append({"item_id": item.pk, "name": item.name, "kind": item.kind,
                      "unit": item.unit, "used": -(r.get("used") or 0),
                      "received": r.get("received") or 0,
                      "current_quantity": item.quantity,
                      "min_threshold": item.min_threshold})
    return {"from": start, "to": end, "items": items}


# -- Caretaker (UC-VH-018) -----------------------------------------------------
def daily_occupancy(day: date) -> dict:
    """AFR-VH-086. Which rooms hold a guest on `day`."""
    rows = (RoomAllotment.objects
            .select_related("room", "booking")
            .filter(booking__status__in=HOLDING, booking__arrival_date__lte=day)
            .filter(Q(booking__departure_date__gt=day)
                    | Q(booking__departure_date=day, booking__arrival_date=day)
                    | Q(booking__status=sm.CHECKED_IN))
            .order_by("room__number"))
    return {"date": day, "occupied": len(rows), "rooms": [
        {"room": a.room.number, "room_type": a.room.room_type,
         "occupancy": a.occupancy, "booking_id": a.booking_id,
         "visitor_name": a.booking.visitor_name, "status": a.booking.status,
         "departure_date": a.booking.departure_date} for a in rows]}


def arrivals_and_departures(start: date, days: int = 7) -> dict:
    """AFR-VH-087."""
    end = start + timedelta(days=days)
    arriving = (Booking.objects
                .filter(status__in=(sm.APPROVED, sm.ROOM_ALLOTTED),
                        arrival_date__gte=start, arrival_date__lt=end)
                .order_by("arrival_date", "arrival_time"))
    departing = (Booking.objects
                 .filter(status=sm.CHECKED_IN, departure_date__lt=end)
                 .order_by("departure_date", "departure_time"))

    def row(b):
        return {"booking_id": b.pk, "visitor_name": b.visitor_name,
                "status": b.status, "arrival_date": b.arrival_date,
                "arrival_time": b.arrival_time, "departure_date": b.departure_date,
                "departure_time": b.departure_time, "rooms_required": b.rooms_required}

    return {"from": start, "to": end, "arrivals": [row(b) for b in arriving],
            "departures": [row(b) for b in departing]}


def pending_approvals() -> dict:
    """AFR-VH-088. Awaiting the Caretaker, and awaiting the VH In-Charge."""
    qs = (Booking.objects.filter(status__in=(sm.PENDING, sm.FORWARDED))
          .order_by("arrival_date"))
    return {"bookings": [
        {"booking_id": b.pk, "status": b.status, "is_offline": b.is_offline,
         "visitor_name": b.visitor_name, "arrival_date": b.arrival_date,
         "category": b.category, "rooms_required": b.rooms_required,
         "created_at": b.created_at} for b in qs]}


def no_show_overstay_log(start: date, end: date) -> dict:
    """AFR-VH-089."""
    qs = (StayAlert.objects.select_related("booking")
          .filter(raised_at__date__gte=start, raised_at__date__lte=end)
          .order_by("-raised_at"))
    return {"from": start, "to": end, "alerts": [
        {"id": a.pk, "kind": a.kind, "booking_id": a.booking_id,
         "visitor_name": a.booking.visitor_name, "expected_at": a.expected_at,
         "raised_at": a.raised_at, "booking_status": a.booking.status}
        for a in qs]}
