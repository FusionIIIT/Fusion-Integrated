import pytest
from datetime import date
from modules.hm.domain import (
    validate_room_capacity,
    check_capacity_guard,
    validate_stay_dates,
    transition_state,
    ACCOMMODATION_TRANSITIONS,
    LEAVE_TRANSITIONS,
    COMPLAINT_TRANSITIONS,
    GUEST_BOOKING_TRANSITIONS,
    EXTENDED_STAY_TRANSITIONS,
    NOTICE_TRANSITIONS,
)


def test_validate_room_capacity():
    validate_room_capacity(1)
    validate_room_capacity(10)
    with pytest.raises(ValueError, match="Room capacity must be greater than zero"):
        validate_room_capacity(0)
    with pytest.raises(ValueError, match="Room capacity must be greater than zero"):
        validate_room_capacity(-1)


def test_check_capacity_guard():
    # Capacity 2, 0 occupied -> OK
    check_capacity_guard(2, 0)
    # Capacity 2, 1 occupied -> OK
    check_capacity_guard(2, 1)
    # Capacity 2, 2 occupied -> Exceeded
    with pytest.raises(ValueError, match="Room capacity exceeded"):
        check_capacity_guard(2, 2)


def test_validate_stay_dates():
    validate_stay_dates(date(2026, 1, 1), date(2026, 1, 5))
    validate_stay_dates(date(2026, 1, 1), date(2026, 1, 1))
    with pytest.raises(ValueError, match="End date cannot be earlier than start date"):
        validate_stay_dates(date(2026, 1, 5), date(2026, 1, 1))


def test_accommodation_transitions():
    assert transition_state(ACCOMMODATION_TRANSITIONS, "submitted", "allot", "admin") == "allotted"
    assert transition_state(ACCOMMODATION_TRANSITIONS, "submitted", "cancel", "student") == "cancelled"
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(ACCOMMODATION_TRANSITIONS, "allotted", "allot", "admin")


def test_leave_transitions():
    assert transition_state(LEAVE_TRANSITIONS, "submitted", "approve", "caretaker") == "approved"
    assert transition_state(LEAVE_TRANSITIONS, "submitted", "reject", "caretaker") == "rejected"
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(LEAVE_TRANSITIONS, "approved", "approve", "caretaker")


def test_complaint_transitions():
    assert transition_state(COMPLAINT_TRANSITIONS, "submitted", "resolve", "caretaker") == "resolved"
    assert transition_state(COMPLAINT_TRANSITIONS, "submitted", "update", "caretaker") == "updated"
    assert transition_state(COMPLAINT_TRANSITIONS, "submitted", "escalate", "caretaker") == "escalated"
    assert transition_state(COMPLAINT_TRANSITIONS, "escalated", "resolve", "warden") == "resolved"
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(COMPLAINT_TRANSITIONS, "resolved", "update", "caretaker")


def test_guest_booking_transitions():
    assert transition_state(GUEST_BOOKING_TRANSITIONS, "submitted", "approve", "caretaker") == "approved"
    assert transition_state(GUEST_BOOKING_TRANSITIONS, "submitted", "reject", "caretaker") == "rejected"
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(GUEST_BOOKING_TRANSITIONS, "rejected", "approve", "caretaker")


def test_extended_stay_transitions():
    assert transition_state(EXTENDED_STAY_TRANSITIONS, "submitted", "approve", "warden") == "approved"
    assert transition_state(EXTENDED_STAY_TRANSITIONS, "submitted", "reject", "warden") == "rejected"
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(EXTENDED_STAY_TRANSITIONS, "approved", "reject", "warden")


def test_notice_transitions():
    assert transition_state(NOTICE_TRANSITIONS, "draft", "publish", "authority") == "published"
    assert transition_state(NOTICE_TRANSITIONS, "published", "withdraw", "authority") == "withdrawn"
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(NOTICE_TRANSITIONS, "withdrawn", "publish", "authority")
