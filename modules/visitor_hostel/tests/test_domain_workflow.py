import unittest
from modules.visitor_hostel.domain.workflow import get_next_booking_state
from modules.visitor_hostel.domain.constants import BookingStatus, BookingEvent
from modules.visitor_hostel.domain.errors import InvalidBookingStateError

class TestWorkflowStateMachine(unittest.TestCase):
    def test_valid_transitions(self):
        self.assertEqual(get_next_booking_state(BookingStatus.DRAFT, BookingEvent.SUBMIT), BookingStatus.PENDING)
        self.assertEqual(get_next_booking_state(BookingStatus.PENDING, BookingEvent.CARETAKER_REJECT), BookingStatus.REJECTED)
        self.assertEqual(get_next_booking_state(BookingStatus.PENDING, BookingEvent.CARETAKER_FORWARD), BookingStatus.FORWARDED)
        self.assertEqual(get_next_booking_state(BookingStatus.FORWARDED, BookingEvent.INCHARGE_APPROVE), BookingStatus.APPROVED)
        self.assertEqual(get_next_booking_state(BookingStatus.FORWARDED, BookingEvent.INCHARGE_REJECT), BookingStatus.REJECTED)
        self.assertEqual(get_next_booking_state(BookingStatus.APPROVED, BookingEvent.ALLOT_ROOM), BookingStatus.ROOM_ALLOTTED)
        self.assertEqual(get_next_booking_state(BookingStatus.ROOM_ALLOTTED, BookingEvent.CHECK_IN), BookingStatus.CHECKED_IN)
        self.assertEqual(get_next_booking_state(BookingStatus.CHECKED_IN, BookingEvent.CHECK_OUT), BookingStatus.CHECKED_OUT)
        self.assertEqual(get_next_booking_state(BookingStatus.PENDING, BookingEvent.REQUEST_CANCEL), BookingStatus.CANCELLATION_REQUESTED)
        self.assertEqual(get_next_booking_state(BookingStatus.CANCELLATION_REQUESTED, BookingEvent.CONFIRM_CANCEL), BookingStatus.CANCELLED)
    
    def test_invalid_transitions(self):
        with self.assertRaises(InvalidBookingStateError):
            get_next_booking_state(BookingStatus.DRAFT, BookingEvent.ALLOT_ROOM)
        
        with self.assertRaises(InvalidBookingStateError):
            get_next_booking_state(BookingStatus.REJECTED, BookingEvent.CHECK_IN)
