import pytest

from modules.phc.domain.appointments import TRANSITIONS, AppointmentStatus, validate_transition


def test_appointment_state_machine_has_terminal_states():
    for status in (
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.REJECTED,
        AppointmentStatus.NO_SHOW,
    ):
        assert TRANSITIONS[status] == set()


def test_appointment_status_changes_follow_the_declared_table():
    validate_transition("pending", "confirmed")
    with pytest.raises(ValueError):
        validate_transition("completed", "confirmed")


@pytest.mark.parametrize("status", list(AppointmentStatus))
def test_each_transition_table_entry_is_accepted(status):
    for target in TRANSITIONS[status]:
        validate_transition(status, target)
