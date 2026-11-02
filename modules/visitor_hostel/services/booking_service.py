from django.db import transaction
from datetime import date
from typing import Dict, Any, Optional
import uuid
from modules.visitor_hostel.models import BookingDetail, VisitorDetail
from modules.visitor_hostel.domain.constants import BookingStatus, BookingEvent, BillingResponsibility
from modules.visitor_hostel.domain.workflow import get_next_booking_state
from modules.visitor_hostel.domain.errors import InvalidBookingStateError

@transaction.atomic
def create_booking(indenter: str, visitor_data: Dict[str, Any], booking_from: date, booking_to: date, category: str = 'B', billing_responsibility: str = 'Visitor', purpose: str = '', is_offline: bool = False, offline_contact: Optional[str] = None) -> BookingDetail:
    if booking_to < booking_from:
        raise ValueError("Booking to date must be greater than or equal to from date")
    
    visitor_detail = VisitorDetail.objects.create(**visitor_data)
    booking_id = 'VH-' + uuid.uuid4().hex[:8].upper()
    status = BookingStatus.PENDING

    return BookingDetail.objects.create(
        booking_id=booking_id,
        indenter=indenter,
        visitor=visitor_detail,
        booking_from=booking_from,
        booking_to=booking_to,
        category=category,
        billing_responsibility=billing_responsibility,
        purpose=purpose,
        is_offline=is_offline,
        offline_contact_person=offline_contact,
        status=status
    )

@transaction.atomic
def caretaker_forward_booking(booking_id: str, actor: str) -> BookingDetail:
    booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    if not get_next_booking_state(booking.status, BookingEvent.CARETAKER_FORWARD):
        raise InvalidBookingStateError("Invalid state transition")
    booking.status = BookingStatus.FORWARDED
    booking.save()
    return booking

@transaction.atomic
def caretaker_reject_booking(booking_id: str, actor: str, reason: str) -> BookingDetail:
    booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    booking.status = BookingStatus.REJECTED
    booking.rejection_reason = reason
    booking.save()
    return booking

@transaction.atomic
def incharge_approve_booking(booking_id: str, actor: str) -> BookingDetail:
    booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    if not get_next_booking_state(booking.status, BookingEvent.INCHARGE_APPROVE):
        raise InvalidBookingStateError("Invalid state transition")
    booking.status = BookingStatus.APPROVED
    booking.save()
    return booking

@transaction.atomic
def incharge_reject_booking(booking_id: str, actor: str, reason: str) -> BookingDetail:
    booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    booking.status = BookingStatus.REJECTED
    booking.rejection_reason = reason
    booking.save()
    return booking

@transaction.atomic
def request_cancellation(booking_id: str, actor: str, reason: str) -> BookingDetail:
    booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    if not get_next_booking_state(booking.status, BookingEvent.REQUEST_CANCEL):
        raise InvalidBookingStateError("Invalid state transition")
    booking.status = BookingStatus.CANCELLATION_REQUESTED
    booking.cancellation_reason = reason
    booking.save()
    return booking

@transaction.atomic
def confirm_cancellation(booking_id: str, actor: str) -> BookingDetail:
    booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    if not get_next_booking_state(booking.status, BookingEvent.CONFIRM_CANCEL):
        raise InvalidBookingStateError("Invalid state transition")
    booking.status = BookingStatus.CANCELLED
    booking.save()
    return booking
