from django.db.models import Count, Sum
from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.visitors_hostel.models import (
    Bill, Booking, InventoryChange, StayAlert)


def build_report(*, actor, report_type):
    caretaker_reports = {"daily_occupancy", "arrivals_departures",
                         "pending_approvals", "stay_exceptions"}
    in_charge_reports = {"booking_summary", "category_occupancy",
                         "billing_summary", "inventory_usage"}
    permission = ("visitor_hostel.report.view_caretaker"
                  if report_type in caretaker_reports
                  else "visitor_hostel.report.view_in_charge")
    if report_type not in caretaker_reports | in_charge_reports:
        raise BadRequestError("Unsupported Visitors Hostel report type.",
                              code="invalid_report_type")
    if not actor.has_permission(permission):
        raise PermissionDeniedError()
    if report_type == "daily_occupancy":
        today = timezone.localdate()
        return {"type": report_type, "rows": list(Booking.objects.filter(
            status__in=["room_allotted", "checked_in"],
            arrival_date__lte=today, departure_date__gt=today).values(
                "arrival_date", "visitor_category").annotate(bookings=Count("id")))}
    if report_type == "arrivals_departures":
        today = timezone.localdate()
        return {"type": report_type, "arrivals": list(Booking.objects.filter(
            status="approved", arrival_date__gte=today).values(
                "booking_number", "visitor_name", "arrival_date")),
            "departures": list(Booking.objects.filter(status="checked_in",
                departure_date__gte=today).values(
                "booking_number", "visitor_name", "departure_date"))}
    if report_type == "pending_approvals":
        return {"type": report_type, "rows": list(Booking.objects.filter(
            status__in=["pending", "forwarded"]).values(
                "booking_number", "source", "status", "arrival_date", "visitor_name"))}
    if report_type == "stay_exceptions":
        return {"type": report_type, "rows": list(StayAlert.objects.select_related(
            "booking").values("kind", "created_at", "booking__booking_number",
                              "booking__status"))}
    if report_type == "booking_summary":
        rows = Booking.objects.values("status", "source").annotate(total=Count("id"))
        return {"type": report_type, "rows": list(rows)}
    if report_type == "category_occupancy":
        rows = Booking.objects.filter(status__in=["room_allotted", "checked_in",
                                                   "checked_out"]).values(
            "visitor_category").annotate(bookings=Count("id"))
        return {"type": report_type, "rows": list(rows)}
    if report_type == "billing_summary":
        return {"type": report_type, "total": Bill.objects.aggregate(
            total=Sum("total_amount"))["total"] or 0}
    rows = InventoryChange.objects.values("item__name").annotate(
        quantity_changed=Sum("quantity_delta"))
    return {"type": report_type, "rows": list(rows)}
