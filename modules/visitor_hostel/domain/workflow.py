from modules.visitor_hostel.domain.constants import BookingStatus, BookingEvent
from modules.visitor_hostel.domain.errors import InvalidBookingStateError

def get_next_booking_state(current_state: BookingStatus, event: BookingEvent) -> BookingStatus:
    if (current_state, event) == (BookingStatus.DRAFT, BookingEvent.SUBMIT):
        return BookingStatus.PENDING
    elif (current_state, event) == (BookingStatus.PENDING, BookingEvent.CARETAKER_REJECT):
        return BookingStatus.REJECTED
    elif (current_state, event) == (BookingStatus.PENDING, BookingEvent.CARETAKER_FORWARD):
        return BookingStatus.FORWARDED
    elif (current_state, event) == (BookingStatus.FORWARDED, BookingEvent.INCHARGE_APPROVE):
        return BookingStatus.APPROVED
    elif (current_state, event) == (BookingStatus.FORWARDED, BookingEvent.INCHARGE_REJECT):
        return BookingStatus.REJECTED
    elif (current_state, event) == (BookingStatus.APPROVED, BookingEvent.ALLOT_ROOM):
        return BookingStatus.ROOM_ALLOTTED
    elif (current_state, event) == (BookingStatus.ROOM_ALLOTTED, BookingEvent.CHECK_IN):
        return BookingStatus.CHECKED_IN
    elif (current_state, event) == (BookingStatus.CHECKED_IN, BookingEvent.CHECK_OUT):
        return BookingStatus.CHECKED_OUT
    elif (current_state, event) in [(status, BookingEvent.REQUEST_CANCEL) for status in [BookingStatus.PENDING, BookingStatus.FORWARDED, BookingStatus.APPROVED, BookingStatus.ROOM_ALLOTTED]]:
        return BookingStatus.CANCELLATION_REQUESTED
    elif (current_state, event) == (BookingStatus.CANCELLATION_REQUESTED, BookingEvent.CONFIRM_CANCEL):
        return BookingStatus.CANCELLED
    else:
        raise InvalidBookingStateError(f"Cannot transition from {current_state} on {event}")
