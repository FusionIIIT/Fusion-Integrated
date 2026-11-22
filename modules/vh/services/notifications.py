# System-generated notifications and audit dispatch for VHMS.
from datetime import date

from modules.vh.models.alerts import BookingNotificationLog
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem


def notify_booking_submission(booking: Booking) -> BookingNotificationLog:
    # CFR-VH-014, AFR-VH-076, UC-VH-023: Records booking submission notification event.
    visitor = booking.visitors.first()
    vis_name = visitor.name if visitor else "Guest"
    return BookingNotificationLog.objects.create(
        booking=booking,
        event_type="booking_submitted",
        recipient_email=visitor.email if visitor and visitor.email else "indenter@iiitdmj.ac.in",
        recipient_role="Indenter",
        subject=f"Booking Requisition Received: {booking.booking_reference}",
        body=(
            f"Your requisition for {vis_name} from {booking.arrival_date} "
            f"to {booking.departure_date} is Pending review."
        ),
    )


def notify_booking_decision(booking: Booking) -> BookingNotificationLog:
    # CFR-VH-014, AFR-VH-077, UC-VH-023: Communicates final booking decision to Indenter.
    visitor = booking.visitors.first()
    vis_name = visitor.name if visitor else "Guest"
    decision = booking.status.capitalize()
    reason_text = f" Reason: {booking.rejection_reason}" if booking.rejection_reason else ""
    return BookingNotificationLog.objects.create(
        booking=booking,
        event_type="booking_decision",
        recipient_email=visitor.email if visitor and visitor.email else "indenter@iiitdmj.ac.in",
        recipient_role="Indenter",
        subject=f"Visitors Hostel Booking {decision}: {booking.booking_reference}",
        body=f"Booking {booking.booking_reference} for {vis_name}: {decision}.{reason_text}",
    )


def notify_cancellation_update(booking: Booking) -> BookingNotificationLog:
    # CFR-VH-014, AFR-VH-078, UC-VH-023: Records cancellation or modification update event.
    return BookingNotificationLog.objects.create(
        booking=booking,
        event_type="cancellation_update",
        recipient_email="indenter@iiitdmj.ac.in",
        recipient_role="Indenter",
        subject=f"Booking Cancellation Update: {booking.booking_reference}",
        body=(
            f"Booking {booking.booking_reference} cancellation status: {booking.status}. "
            f"Charge: {booking.cancellation_charge_percentage}%."
        ),
    )


def notify_inventory_threshold(item: InventoryItem) -> BookingNotificationLog:
    # CFR-VH-014, AFR-VH-080: Low inventory stock alert.
    return BookingNotificationLog.objects.create(
        booking=None,
        event_type="inventory_threshold_alert",
        recipient_email="caretaker.vh@iiitdmj.ac.in",
        recipient_role="Caretaker",
        subject=f"Low Stock Alert: {item.item_name}",
        body=(
            f"Stock for '{item.item_name}' ({item.current_quantity} {item.unit}) "
            f"is below minimum threshold of {item.minimum_threshold}."
        ),
    )


def dispatch_scheduled_stay_reminders() -> int:
    # AFR-VH-079, UC-VH-024: Dispatches stay check-in and check-out reminders.
    today = date.today()
    arrivals = Booking.objects.filter(
        arrival_date=today, status__in=["approved", "approved_offline", "room_allotted"]
    )
    count = 0
    for b in arrivals:
        BookingNotificationLog.objects.create(
            booking=b,
            event_type="checkin_reminder",
            recipient_email="guest@iiitdmj.ac.in",
            recipient_role="Visitor",
            subject=f"Reminder: Check-in scheduled today for Booking {b.booking_reference}",
            body=(f"Stay at Visitors Hostel commences today ({today}). Caretaker desk is ready."),
        )
        count += 1
    departures = Booking.objects.filter(departure_date=today, status="checked_in")
    for b in departures:
        BookingNotificationLog.objects.create(
            booking=b,
            event_type="checkout_reminder",
            recipient_email="guest@iiitdmj.ac.in",
            recipient_role="Visitor",
            subject=f"Reminder: Check-out scheduled today for Booking {b.booking_reference}",
            body=(f"Stay at VH concludes today ({today}). Settle bills at Caretaker desk."),
        )
        count += 1
    return count
