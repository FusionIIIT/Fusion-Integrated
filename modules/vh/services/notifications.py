"""Notification and alert services for Visitors Hostel (VH) module.

Implements UC-VH-023, UC-VH-024, UC-VH-025, CFR-VH-014, BR-VH-017, BR-VH-018, BR-VH-041, BR-VH-043.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from modules.vh.models import (
    Booking,
    BookingStatus,
    InventoryItem,
    RoomAllotment,
    VHAlert,
    VHAlertType,
    VHNotificationEventType,
    VHNotificationLog,
    VHMSUserRole,
    VHMSUserRoleType,
)

logger = logging.getLogger("fusion.vh.notifications")


def emit_booking_lifecycle_notification(
    booking: Booking,
    event_type: str,
    subject: str = "",
    body: str = "",
    recipient_email: str = "",
    recipient_user_id: int | None = None,
) -> VHNotificationLog:
    """Record and dispatch system-generated email notification for booking events (UC-VH-023, CFR-VH-014)."""
    email = recipient_email or booking.visitor_email
    user_id = recipient_user_id or booking.indenter_id

    if not subject:
        subject = f"[VHMS] {event_type.replace('_', ' ').title()} - {booking.booking_reference}"
    if not body:
        body = (
            f"Notification for Booking Reference: {booking.booking_reference}\n"
            f"Visitor Name: {booking.visitor_name}\n"
            f"Current Status: {booking.status}\n"
            f"Stay: {booking.check_in_date} to {booking.check_out_date}\n"
        )

    log_entry = VHNotificationLog.objects.create(
        event_type=event_type,
        booking=booking,
        recipient_email=email,
        recipient_user_id=user_id,
        subject=subject,
        body=body,
    )

    # Attempt email delivery without failing caller transaction if email is unconfigured or fails
    if email:
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "vhms@iiitdm.ac.in"),
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning("Failed to send email to %s: %s", email, exc)

    return log_entry


def check_stay_exception_alerts() -> dict[str, int]:
    """Scan stay records for no-shows and overstays (BR-VH-017, BR-VH-018, UC-VH-024).

    Returns summary counts of created alerts: {'no_shows': N, 'overstays': M}.
    """
    today = timezone.localdate()
    now = timezone.now()
    active_caretaker = VHMSUserRole.get_active_caretaker()
    caretaker_user_id = active_caretaker.user_id if active_caretaker else None

    no_shows_count = 0
    overstays_count = 0

    # 1. No-Show: Approved & Allotted bookings where check_in_date is today or in past, but check_in_time is null
    pending_checkins = RoomAllotment.objects.filter(
        booking__status=BookingStatus.ROOM_ALLOTTED,
        booking__check_in_date__lte=today,
        check_in_time__isnull=True,
        is_no_show=False,
    ).select_related("booking", "room")

    for allotment in pending_checkins:
        allotment.is_no_show = True
        allotment.save(update_fields=["is_no_show"])
        VHAlert.objects.create(
            alert_type=VHAlertType.NO_SHOW,
            booking=allotment.booking,
            message=(
                f"Guest {allotment.booking.visitor_name} has not checked in for booking "
                f"{allotment.booking.booking_reference} (expected: {allotment.booking.check_in_date})."
            ),
            recipient_role=VHMSUserRoleType.CARETAKER,
            recipient_user_id=caretaker_user_id,
        )
        no_shows_count += 1

    # 2. Overstay: Bookings with CHECKED_IN status where check_out_date < today and check_out_time is null
    active_stays = RoomAllotment.objects.filter(
        booking__status=BookingStatus.CHECKED_IN,
        booking__check_out_date__lt=today,
        check_out_time__isnull=True,
        is_overstay=False,
    ).select_related("booking", "room")

    for allotment in active_stays:
        allotment.is_overstay = True
        allotment.save(update_fields=["is_overstay"])
        VHAlert.objects.create(
            alert_type=VHAlertType.OVERSTAY,
            booking=allotment.booking,
            message=(
                f"Guest {allotment.booking.visitor_name} (Booking {allotment.booking.booking_reference}) "
                f"has exceeded the approved duration (scheduled checkout: {allotment.booking.check_out_date})."
            ),
            recipient_role=VHMSUserRoleType.CARETAKER,
            recipient_user_id=caretaker_user_id,
        )
        overstays_count += 1

    return {"no_shows": no_shows_count, "overstays": overstays_count}


def check_inventory_threshold_alert(item: InventoryItem) -> VHAlert | None:
    """Generate threshold alert and notification event if item falls below threshold (BR-VH-041, BR-VH-043, UC-VH-025)."""
    if not item.is_below_threshold:
        return None

    active_caretaker = VHMSUserRole.get_active_caretaker()
    caretaker_user_id = active_caretaker.user_id if active_caretaker else None

    # Check if unresolved alert already exists for this item
    alert = VHAlert.objects.filter(
        alert_type=VHAlertType.INVENTORY_THRESHOLD,
        inventory_item=item,
        is_resolved=False,
    ).first()

    if not alert:
        msg = (
            f"Inventory alert: Item '{item.name}' current quantity ({item.current_quantity}) "
            f"is below minimum threshold ({item.minimum_threshold})."
        )
        alert = VHAlert.objects.create(
            alert_type=VHAlertType.INVENTORY_THRESHOLD,
            inventory_item=item,
            message=msg,
            recipient_role=VHMSUserRoleType.CARETAKER,
            recipient_user_id=caretaker_user_id,
        )

        # Trigger corresponding email notification event (BR-VH-043)
        VHNotificationLog.objects.create(
            event_type=VHNotificationEventType.INVENTORY_THRESHOLD,
            recipient_user_id=caretaker_user_id,
            subject=f"[VHMS] Inventory Low Threshold Alert: {item.name}",
            body=msg,
        )

    return alert

