from modules.leave.domain.state_machine import (
    APPLICANT_ACTION_REQUIRED,
    APPROVED,
    AWAITING_FINAL_SANCTION,
    AWAITING_SUBSTITUTE,
    AWAITING_UNIT_HEAD,
    DRAFT,
    REJECTED,
    WITHDRAWN,
)
from modules.leave.models import LeaveRequest, LeaveRequestHistory

STATUSES = [
    DRAFT,
    AWAITING_SUBSTITUTE,
    APPLICANT_ACTION_REQUIRED,
    AWAITING_UNIT_HEAD,
    AWAITING_FINAL_SANCTION,
    APPROVED,
    REJECTED,
    WITHDRAWN,
]


def test_request_status_choices_match_state_machine():
    assert {f[0] for f in LeaveRequest._meta.get_field("status").choices} == set(STATUSES)


def test_status_fields_are_long_enough():
    status_fields = [
        (LeaveRequest, "status"),
        (LeaveRequestHistory, "from_status"),
        (LeaveRequestHistory, "to_status"),
    ]
    for model, field_name in status_fields:
        field = model._meta.get_field(field_name)
        assert field.max_length >= max(len(s) for s in STATUSES)


def test_default_status_is_draft():
    assert LeaveRequest._meta.get_field("status").default == DRAFT
