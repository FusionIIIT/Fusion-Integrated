"""Reporting services for Visitors Hostel (VH) module.

Implements UC-VH-017, UC-VH-018, CFR-VH-015, CFR-VH-016.
"""
from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Sum
from django.utils import timezone

from modules.vh.models import (
    Bill,
    Booking,
    BookingStatus,
    InventoryItem,
    InventoryReplenishment,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    VHAlert,
    VisitorCategory,
)


def get_incharge_reports() -> dict:
    """Generate supervisory reports for VH In-Charge (UC-VH-017, CFR-VH-015)."""
    # 1. Booking Summary
    status_counts = dict(
        Booking.objects.values("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    total_bookings = Booking.objects.count()

    # 2. Category-wise Occupancy
    category_summary = []
    for cat in VisitorCategory.objects.all():
        b_count = Booking.objects.filter(visitor_category=cat).count()
        rooms_count = (
            Booking.objects.filter(visitor_category=cat).aggregate(
                total_rooms=Sum("number_of_rooms")
            )["total_rooms"]
            or 0
        )
        category_summary.append({
            "category_code": cat.code,
            "category_name": cat.name,
            "bookings_count": b_count,
            "total_rooms_booked": rooms_count,
        })

    # 3. Revenue & Billing Summaries
    bill_aggregates = Bill.objects.aggregate(
        total_room_charges=Sum("room_charges"),
        total_meal_charges=Sum("meal_charges"),
        total_cancellation_charges=Sum("cancellation_charges"),
        total_billed=Sum("total_amount"),
    )
    total_settled = (
        Bill.objects.filter(is_settled=True).aggregate(s=Sum("total_amount"))["s"]
        or Decimal("0.00")
    )
    total_billed = bill_aggregates["total_billed"] or Decimal("0.00")
    total_pending = total_billed - total_settled

    revenue_summary = {
        "room_charges": str(bill_aggregates["total_room_charges"] or Decimal("0.00")),
        "meal_charges": str(bill_aggregates["total_meal_charges"] or Decimal("0.00")),
        "cancellation_charges": str(
            bill_aggregates["total_cancellation_charges"] or Decimal("0.00")
        ),
        "total_revenue": str(total_billed),
        "total_settled": str(total_settled),
        "total_pending_settlement": str(total_pending),
    }

    # 4. Inventory Usage & Replenishment
    items_count = InventoryItem.objects.count()
    low_stock_items = [i.name for i in InventoryItem.objects.all() if i.is_below_threshold]
    rep_approved = InventoryReplenishment.objects.filter(
        status=ReplenishmentStatus.APPROVED
    ).count()
    rep_pending = InventoryReplenishment.objects.filter(
        status=ReplenishmentStatus.PENDING
    ).count()

    inventory_usage = {
        "total_inventory_items": items_count,
        "items_below_threshold": low_stock_items,
        "replenishments_approved": rep_approved,
        "replenishments_pending": rep_pending,
    }

    return {
        "booking_summary": {
            "total_bookings": total_bookings,
            "by_status": status_counts,
        },
        "category_occupancy": category_summary,
        "revenue_summary": revenue_summary,
        "inventory_usage": inventory_usage,
    }


def get_caretaker_reports() -> dict:
    """Generate operational reports and logs for Caretaker (UC-VH-018, CFR-VH-016)."""
    today = timezone.localdate()
    next_week = today + timedelta(days=7)

    # 1. Daily Occupancy Information
    occupied_rooms_count = Room.objects.filter(status=RoomStatus.OCCUPIED).count()
    available_rooms_count = Room.objects.filter(status=RoomStatus.AVAILABLE).count()
    maintenance_rooms_count = Room.objects.filter(status=RoomStatus.MAINTENANCE).count()
    currently_checked_in = Booking.objects.filter(status=BookingStatus.CHECKED_IN).count()

    daily_occupancy = {
        "date": str(today),
        "checked_in_guests": currently_checked_in,
        "occupied_rooms": occupied_rooms_count,
        "available_rooms": available_rooms_count,
        "maintenance_rooms": maintenance_rooms_count,
    }

    # 2. Upcoming Schedule (Arrivals / Departures)
    upcoming_arrivals = [
        {
            "id": b.id,
            "booking_reference": b.booking_reference,
            "visitor_name": b.visitor_name,
            "check_in_date": str(b.check_in_date),
            "status": b.status,
            "number_of_rooms": b.number_of_rooms,
        }
        for b in Booking.objects.filter(
            check_in_date__gte=today,
            check_in_date__lte=next_week,
            status__in=[BookingStatus.APPROVED, BookingStatus.ROOM_ALLOTTED],
        ).order_by("check_in_date")
    ]

    upcoming_departures = [
        {
            "id": b.id,
            "booking_reference": b.booking_reference,
            "visitor_name": b.visitor_name,
            "check_out_date": str(b.check_out_date),
            "status": b.status,
        }
        for b in Booking.objects.filter(
            check_out_date__gte=today,
            check_out_date__lte=next_week,
            status=BookingStatus.CHECKED_IN,
        ).order_by("check_out_date")
    ]

    # 3. Pending Actions
    pending_review = Booking.objects.filter(status=BookingStatus.PENDING).values(
        "id", "booking_reference", "visitor_name", "check_in_date"
    )
    pending_cancellation_confirmations = Booking.objects.filter(
        status=BookingStatus.CANCELLATION_REQUESTED
    ).values(
        "id",
        "booking_reference",
        "visitor_name",
        "calculated_cancellation_charge",
    )

    # 4. No-Show and Overstay Logs
    no_shows = [
        {
            "booking_id": a.booking_id,
            "booking_reference": a.booking.booking_reference,
            "visitor_name": a.booking.visitor_name,
            "room_number": a.room.room_number,
            "expected_check_in": str(a.booking.check_in_date),
        }
        for a in RoomAllotment.objects.filter(is_no_show=True).select_related("booking", "room")
    ]

    overstays = [
        {
            "booking_id": a.booking_id,
            "booking_reference": a.booking.booking_reference,
            "visitor_name": a.booking.visitor_name,
            "room_number": a.room.room_number,
            "expected_check_out": str(a.booking.check_out_date),
        }
        for a in RoomAllotment.objects.filter(is_overstay=True).select_related("booking", "room")
    ]

    unresolved_alerts = [
        {
            "id": alt.id,
            "alert_type": alt.alert_type,
            "message": alt.message,
            "created_at": alt.created_at.isoformat(),
        }
        for alt in VHAlert.objects.filter(is_resolved=False).order_by("-created_at")[:20]
    ]

    return {
        "daily_occupancy": daily_occupancy,
        "upcoming_arrivals": upcoming_arrivals,
        "upcoming_departures": upcoming_departures,
        "pending_actions": {
            "pending_review_count": len(pending_review),
            "pending_cancellation_confirmations_count": len(pending_cancellation_confirmations),
            "pending_cancellations": list(pending_cancellation_confirmations),
        },
        "no_show_logs": no_shows,
        "overstay_logs": overstays,
        "unresolved_alerts": unresolved_alerts,
    }

