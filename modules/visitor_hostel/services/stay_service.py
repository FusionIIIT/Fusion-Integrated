from django.db import transaction
from django.utils import timezone
from datetime import date
from modules.visitor_hostel.models import BookingDetail, RoomDetail, RoomAllotment
from modules.visitor_hostel.domain.constants import BookingStatus, BookingEvent
from modules.visitor_hostel.domain.errors import RoomNotAvailableError, InvalidBookingStateError

@transaction.atomic
def allot_room(booking_id: str, room_number: str, actor: str) -> RoomAllotment:
    try:
        booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    except BookingDetail.DoesNotExist:
        booking = BookingDetail.objects.select_for_update().get(pk=booking_id)
    
    if booking.status != BookingStatus.APPROVED:
        raise InvalidBookingStateError("The booking is not in an approved state.")
        
    try:
        room = RoomDetail.objects.select_for_update().get(room_number=room_number, status='Available', is_operational=True)
    except RoomDetail.DoesNotExist:
        raise RoomNotAvailableError(f"Room {room_number} is not available for allotment.")
        
    allotment = RoomAllotment.objects.create(
        booking=booking,
        room=room,
        allotted_from=booking.booking_from,
        allotted_to=booking.booking_to,
        is_active=True
    )
    
    room.status = 'Occupied'
    room.save()
    
    booking.status = BookingStatus.ROOM_ALLOTTED
    booking.save()
    
    return allotment

@transaction.atomic
def check_in_guest(booking_id: str, actor: str) -> RoomAllotment:
    try:
        booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    except BookingDetail.DoesNotExist:
        booking = BookingDetail.objects.select_for_update().get(pk=booking_id)
        
    if booking.status != BookingStatus.ROOM_ALLOTTED:
        raise InvalidBookingStateError("The booking is not in a room allotted state.")
        
    allotment = RoomAllotment.objects.get(booking=booking, is_active=True)
    allotment.actual_check_in = timezone.now()
    allotment.save()
    
    booking.status = BookingStatus.CHECKED_IN
    booking.save()
    
    return allotment

@transaction.atomic
def check_out_guest(booking_id: str, actor: str) -> RoomAllotment:
    try:
        booking = BookingDetail.objects.select_for_update().get(booking_id=booking_id)
    except BookingDetail.DoesNotExist:
        booking = BookingDetail.objects.select_for_update().get(pk=booking_id)
        
    if booking.status != BookingStatus.CHECKED_IN:
        raise InvalidBookingStateError("The booking is not in a checked-in state.")
        
    allotment = RoomAllotment.objects.get(booking=booking, is_active=True)
    allotment.actual_check_out = timezone.now()
    allotment.is_active = False
    allotment.save()
    
    room = allotment.room
    room.status = 'Available'
    room.save()
    
    booking.status = BookingStatus.CHECKED_OUT
    booking.save()
    
    return allotment
