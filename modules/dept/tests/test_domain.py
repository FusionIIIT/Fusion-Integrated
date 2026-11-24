"""Pure Python domain tests: no database, fast execution."""

import datetime

import pytest

from modules.dept.domain.department import (
    transition_official_change,
    validate_official_change_proposal,
)
from modules.dept.domain.exceptions import (
    AvailabilityError,
    ConflictError,
    InvalidTransitionError,
    ValidationError,
)
from modules.dept.domain.feedback import (
    transition_feedback,
    validate_feedback_submission,
)
from modules.dept.domain.roles import (
    transition_role_assignment,
    validate_role_tenure,
)
from modules.dept.domain.stock import (
    transition_stock_request,
    validate_stock_request_creation,
)
from modules.dept.domain.timetables import (
    TimeSlot,
    check_slot_conflicts,
    do_slots_overlap,
    validate_time_range,
)


# ---- Stock Domain Tests ----
def test_stock_request_validation():
    with pytest.raises(ValidationError):
        validate_stock_request_creation(0, 10)
    with pytest.raises(ValidationError):
        validate_stock_request_creation(-5, 10)
    with pytest.raises(AvailabilityError):
        validate_stock_request_creation(15, 10)
    # Valid
    validate_stock_request_creation(5, 10)


def test_stock_request_transitions():
    assert transition_stock_request("SUBMITTED", "APPROVE", "HOD", 5, 10) == "APPROVED"
    assert transition_stock_request("SUBMITTED", "REJECT", "HOD", 5, 10) == "REJECTED"
    assert transition_stock_request("APPROVED", "ISSUE", "DEPT_ADMIN", 5, 10) == "ISSUED"

    with pytest.raises(AvailabilityError):
        transition_stock_request("APPROVED", "ISSUE", "DEPT_ADMIN", 15, 10)

    with pytest.raises(InvalidTransitionError):
        transition_stock_request("SUBMITTED", "ISSUE", "DEPT_ADMIN", 5, 10)


# ---- Feedback Domain Tests ----
def test_feedback_validation():
    with pytest.raises(ValidationError):
        validate_feedback_submission("", "Details", "ACADEMIC")
    with pytest.raises(ValidationError):
        validate_feedback_submission("Title", "", "ACADEMIC")
    with pytest.raises(ValidationError):
        validate_feedback_submission("Title", "Details", "UNKNOWN_CATEGORY")
    validate_feedback_submission("Title", "Details", "ACADEMIC")


def test_feedback_transitions():
    assert transition_feedback("NEW", "START_REVIEW", "DEPT_ADMIN") == "UNDER_REVIEW"
    assert transition_feedback("NEW", "RESOLVE", "DEPT_ADMIN") == "RESOLVED"
    assert transition_feedback("NEW", "CLOSE", "DEPT_ADMIN") == "CLOSED"
    assert transition_feedback("UNDER_REVIEW", "RESOLVE", "HOD") == "RESOLVED"
    assert transition_feedback("UNDER_REVIEW", "CLOSE", "HOD") == "CLOSED"

    with pytest.raises(InvalidTransitionError):
        transition_feedback("RESOLVED", "START_REVIEW", "DEPT_ADMIN")


# ---- Timetable Domain Tests ----
def test_time_overlap_logic():
    t9 = datetime.time(9, 0)
    t10 = datetime.time(10, 0)
    t10_30 = datetime.time(10, 30)
    t11 = datetime.time(11, 0)

    # 9-10 and 10-11 do not overlap (touching boundary)
    assert do_slots_overlap(t9, t10, t10, t11) is False
    assert do_slots_overlap(t10, t11, t9, t10) is False
    # 9-10:30 and 10-11 overlap
    assert do_slots_overlap(t9, t10_30, t10, t11) is True


def test_timetable_validation_and_conflicts():
    t9 = datetime.time(9, 0)
    t10 = datetime.time(10, 0)
    t9_30 = datetime.time(9, 30)
    t10_30 = datetime.time(10, 30)

    # Start >= end raises ValidationError
    with pytest.raises(ValidationError):
        validate_time_range(t10, t9)
    with pytest.raises(ValidationError):
        validate_time_range(t9, t9)

    existing = [
        TimeSlot(
            entry_id="slot-1",
            day_of_week=0,
            start_time=t9,
            end_time=t10,
            room_or_lab="Room 101",
            instructor_id="prof_x",
        ),
    ]

    # Room conflict
    with pytest.raises(ConflictError):
        check_slot_conflicts(
            TimeSlot(
                day_of_week=0,
                start_time=t9_30,
                end_time=t10_30,
                room_or_lab="Room 101",
                instructor_id="prof_y",
            ),
            existing,
        )

    # Instructor conflict
    with pytest.raises(ConflictError):
        check_slot_conflicts(
            TimeSlot(
                day_of_week=0,
                start_time=t9_30,
                end_time=t10_30,
                room_or_lab="Room 202",
                instructor_id="prof_x",
            ),
            existing,
        )

    # Different day -> no conflict
    check_slot_conflicts(
        TimeSlot(
            day_of_week=1,
            start_time=t9,
            end_time=t10,
            room_or_lab="Room 101",
            instructor_id="prof_x",
        ),
        existing,
    )

    # Same day non-overlapping time -> no conflict
    check_slot_conflicts(
        TimeSlot(
            day_of_week=0,
            start_time=datetime.time(11, 0),
            end_time=datetime.time(12, 0),
            room_or_lab="Room 101",
            instructor_id="prof_x",
        ),
        existing,
    )

    # Same entry_id (updating self) -> no conflict
    check_slot_conflicts(
        TimeSlot(
            entry_id="slot-1",
            day_of_week=0,
            start_time=t9,
            end_time=t10,
            room_or_lab="Room 101",
            instructor_id="prof_x",
        ),
        existing,
    )

    # Different room and different instructor during same time -> no conflict
    check_slot_conflicts(
        TimeSlot(
            entry_id="slot-2",
            day_of_week=0,
            start_time=t9,
            end_time=t10,
            room_or_lab="Room 999",
            instructor_id="prof_different",
        ),
        existing,
    )


# ---- Department Official Changes ----
def test_official_change_validation_and_transitions():
    with pytest.raises(ValidationError):
        validate_official_change_proposal("unsupported_field", "val", "justification")
    with pytest.raises(ValidationError):
        validate_official_change_proposal("name", "", "justification")
    with pytest.raises(ValidationError):
        validate_official_change_proposal("name", "New Name", " ")

    validate_official_change_proposal("name", "New Name", "Authorized upgrade")

    assert transition_official_change("PENDING", "APPROVE", "HOD") == "APPROVED"
    assert transition_official_change("PENDING", "REJECT", "HOD") == "REJECTED"
    with pytest.raises(InvalidTransitionError):
        transition_official_change("APPROVED", "REJECT", "HOD")


# ---- Role Governance ----
def test_role_tenure_validation():
    d1 = datetime.datetime(2026, 8, 1, tzinfo=datetime.UTC)
    d2 = datetime.datetime(2027, 8, 1, tzinfo=datetime.UTC)

    with pytest.raises(ValidationError):
        validate_role_tenure("UNKNOWN_ROLE", d1, d2)
    with pytest.raises(ValidationError):
        validate_role_tenure("HOD", d2, d1)

    validate_role_tenure("HOD", d1, d2)

    assert transition_role_assignment("SCHEDULED", "ACTIVATE", "SYSTEM") == "ACTIVE"
    assert transition_role_assignment("SCHEDULED", "REVOKE", "INSTITUTE_ADMIN") == "REVOKED"
    assert transition_role_assignment("ACTIVE", "EXPIRE", "SYSTEM") == "EXPIRED"
    assert transition_role_assignment("ACTIVE", "REVOKE", "INSTITUTE_ADMIN") == "REVOKED"

    with pytest.raises(InvalidTransitionError):
        transition_role_assignment("ACTIVE", "ACTIVATE", "SYSTEM")
