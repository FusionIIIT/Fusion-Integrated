"""Pure-Python tests for Graduate Seminar Scheduling State Machine (BW-OAP-09)."""
import pytest
from modules.department.domain.state_machine import (
    SeminarStatus,
    SeminarEvent,
    can_transition,
    get_next_status,
)


def test_transition_submit():
    allowed, msg, rule = can_transition(
        SeminarStatus.NO_SUBMITTED_REQUEST.value,
        SeminarEvent.SUBMIT.value,
    )
    assert allowed is True
    assert rule is not None
    assert rule.to_status == SeminarStatus.AWAITING_SCHEDULING
    assert rule.permission == "department.seminar.request"
    assert get_next_status(SeminarStatus.NO_SUBMITTED_REQUEST.value, SeminarEvent.SUBMIT.value) == "AWAITING_SCHEDULING"


def test_transition_schedule():
    allowed, msg, rule = can_transition(
        SeminarStatus.AWAITING_SCHEDULING.value,
        SeminarEvent.SCHEDULE.value,
    )
    assert allowed is True
    assert rule is not None
    assert rule.to_status == SeminarStatus.SCHEDULED
    assert rule.permission == "department.seminar.schedule"
    assert get_next_status(SeminarStatus.AWAITING_SCHEDULING.value, SeminarEvent.SCHEDULE.value) == "SCHEDULED"


def test_transition_reject():
    allowed, msg, rule = can_transition(
        SeminarStatus.AWAITING_SCHEDULING.value,
        SeminarEvent.REJECT.value,
    )
    assert allowed is True
    assert rule is not None
    assert rule.to_status == SeminarStatus.REJECTED
    assert get_next_status(SeminarStatus.AWAITING_SCHEDULING.value, SeminarEvent.REJECT.value) == "REJECTED"


def test_transition_cancel():
    allowed, msg, rule = can_transition(
        SeminarStatus.AWAITING_SCHEDULING.value,
        SeminarEvent.CANCEL.value,
    )
    assert allowed is True
    assert rule is not None
    assert rule.to_status == SeminarStatus.CANCELLED
    assert get_next_status(SeminarStatus.AWAITING_SCHEDULING.value, SeminarEvent.CANCEL.value) == "CANCELLED"


def test_illegal_transitions():
    # Cannot schedule already scheduled seminar
    allowed, msg, rule = can_transition(
        SeminarStatus.SCHEDULED.value,
        SeminarEvent.SCHEDULE.value,
    )
    assert allowed is False
    assert rule is None
    with pytest.raises(ValueError):
        get_next_status(SeminarStatus.SCHEDULED.value, SeminarEvent.SCHEDULE.value)

    # Cannot cancel a scheduled seminar
    allowed, _, _ = can_transition(
        SeminarStatus.SCHEDULED.value,
        SeminarEvent.CANCEL.value,
    )
    assert allowed is False

    # Cannot schedule a rejected request
    allowed, _, _ = can_transition(
        SeminarStatus.REJECTED.value,
        SeminarEvent.SCHEDULE.value,
    )
    assert allowed is False
