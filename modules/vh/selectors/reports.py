# Reporting selectors for Caretaker and VH In-Charge.
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum

from modules.vh.models.alerts import StayAlert
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem
from modules.vh.models.room import RoomAllotment


def get_daily_occupancy_report(target_date: date | None = None) -> dict:
    # CFR-VH-016: Daily occupancy numbers and allocated rooms.
    day = target_date or date.today()
    active_allotments = RoomAllotment.objects.filter(
        booking__arrival_date__lte=day,
        booking__departure_date__gte=day,
        booking__status__in=["room_allotted", "checked_in"],
    ).select_related("room", "booking")
    total_occupants = sum(a.booking.number_of_occupants for a in active_allotments)
    return {
        "date": day.isoformat(),
        "total_rooms_occupied": active_allotments.count(),
        "total_occupants": total_occupants,
        "rooms": [
            {
                "room_number": a.room.room_number,
                "room_type": a.room.room_type,
                "occupancy_type": a.occupancy_type,
                "booking_reference": a.booking.booking_reference,
            }
            for a in active_allotments
        ],
    }


def get_arrivals_departures_report(target_date: date | None = None) -> dict:
    # CFR-VH-016: Upcoming arrivals and departures.
    day = target_date or date.today()
    arrivals = Booking.objects.filter(
        arrival_date=day, status__in=["approved", "room_allotted", "pending"]
    )
    departures = Booking.objects.filter(departure_date=day, status="checked_in")
    return {
        "date": day.isoformat(),
        "arrivals_count": arrivals.count(),
        "departures_count": departures.count(),
        "arrivals": [
            {
                "id": b.id,
                "booking_reference": b.booking_reference,
                "visitor_category": b.visitor_category,
                "status": b.status,
            }
            for b in arrivals
        ],
        "departures": [
            {
                "id": b.id,
                "booking_reference": b.booking_reference,
                "status": b.status,
            }
            for b in departures
        ],
    }


def get_pending_approvals_report() -> dict:
    # CFR-VH-016: Pending approval lists for operational management.
    pending_caretaker = Booking.objects.filter(status__in=["pending", "pending_offline"]).count()
    forwarded_incharge = Booking.objects.filter(
        status__in=["forwarded", "forwarded_offline"]
    ).count()
    cancellations = Booking.objects.filter(status="cancellation_requested").count()
    return {
        "pending_caretaker_review": pending_caretaker,
        "forwarded_to_incharge": forwarded_incharge,
        "pending_cancellations": cancellations,
    }


def get_stay_exception_logs() -> list[dict]:
    # CFR-VH-016: No-show and overstay logs.
    alerts = StayAlert.objects.all().select_related("booking").order_by("-triggered_at")[:50]
    return [
        {
            "id": a.id,
            "booking_reference": a.booking.booking_reference,
            "alert_type": a.alert_type,
            "status": a.status,
            "details": a.details,
            "triggered_at": a.triggered_at.isoformat(),
        }
        for a in alerts
    ]


def get_booking_summary_report() -> dict:
    # CFR-VH-015: Booking summary metrics for VH In-Charge.
    counts = Booking.objects.values("status").annotate(count=Count("id"))
    total = Booking.objects.count()
    offline_total = Booking.objects.filter(is_offline=True).count()
    return {
        "total_bookings": total,
        "offline_bookings": offline_total,
        "status_distribution": {item["status"]: item["count"] for item in counts},
    }


def get_category_occupancy_report() -> list[dict]:
    # CFR-VH-015: Category-wise occupancy report.
    records = (
        Booking.objects.filter(status__in=["checked_in", "checked_out"])
        .values("visitor_category")
        .annotate(total_stays=Count("id"), total_occupants=Sum("number_of_occupants"))
    )
    return list(records)


def get_revenue_summary_report() -> dict:
    # CFR-VH-015: Revenue and billing summaries based on VHMS billing records.
    total_billed = Bill.objects.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    room_billed = Bill.objects.aggregate(total=Sum("room_rent_total"))["total"] or Decimal("0.00")
    meal_billed = Bill.objects.aggregate(total=Sum("meal_charge_total"))["total"] or Decimal("0.00")
    cancellation_billed = Bill.objects.aggregate(total=Sum("cancellation_charge_total"))[
        "total"
    ] or Decimal("0.00")
    settled = Bill.objects.filter(status="settled").aggregate(total=Sum("total_amount"))[
        "total"
    ] or Decimal("0.00")
    return {
        "total_billed": float(total_billed),
        "room_rent_total": float(room_billed),
        "meal_charge_total": float(meal_billed),
        "cancellation_charge_total": float(cancellation_billed),
        "settled_total": float(settled),
    }


def get_inventory_usage_report() -> list[dict]:
    # CFR-VH-015: Inventory status and usage summary.
    items = InventoryItem.objects.all().order_by("category", "item_name")
    return [
        {
            "id": i.id,
            "item_name": i.item_name,
            "category": i.category,
            "current_quantity": i.current_quantity,
            "minimum_threshold": i.minimum_threshold,
            "unit": i.unit,
            "is_below_threshold": i.current_quantity < i.minimum_threshold,
        }
        for i in items
    ]
