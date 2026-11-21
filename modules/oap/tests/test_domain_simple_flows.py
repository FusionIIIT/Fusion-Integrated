import pytest

from modules.oap.domain import bonafide, leave, seminar
from modules.oap.domain.errors import InvalidTransition

FLOWS = [leave, bonafide, seminar]


def _flow_id(flow):
    return flow.__name__.rsplit(".", 1)[-1]


# One test case per row of each state transition table.
ROWS = [
    (flow, state, action, to_state)
    for flow in FLOWS
    for (state, action), to_state in flow.TRANSITIONS.items()
]


def test_row_counts_match_spec():
    assert len(leave.TRANSITIONS) == 3
    assert len(bonafide.TRANSITIONS) == 3
    assert len(seminar.TRANSITIONS) == 2


# --- CW-OAP-01 -------------------------------------------------------------
def test_leave_submit():
    assert leave.transition(
        "No submitted leave application", "submit"
    ) == "Submitted – Awaiting HoD Decision"  # noqa: RUF001


def test_leave_approve():
    assert leave.transition(
        "Submitted – Awaiting HoD Decision", "approve"  # noqa: RUF001
    ) == "Approved"


def test_leave_reject():
    assert leave.transition(
        "Submitted – Awaiting HoD Decision", "reject"  # noqa: RUF001
    ) == "Rejected"


# --- CW-OAP-02 -------------------------------------------------------------
def test_bonafide_submit():
    assert bonafide.transition(
        "No submitted bonafide request", "submit"
    ) == "Submitted – Awaiting Academic Administrator"  # noqa: RUF001


def test_bonafide_approve():
    assert bonafide.transition(
        "Submitted – Awaiting Academic Administrator", "approve"  # noqa: RUF001
    ) == "Approved – Certificate Available"  # noqa: RUF001


def test_bonafide_reject():
    assert bonafide.transition(
        "Submitted – Awaiting Academic Administrator", "reject"  # noqa: RUF001
    ) == "Rejected"


# --- BW-OAP-09 -------------------------------------------------------------
def test_seminar_submit():
    assert seminar.transition(
        "No submitted seminar request", "submit"
    ) == "Awaiting Scheduling"


def test_seminar_schedule():
    assert seminar.transition("Awaiting Scheduling", "schedule") == "Scheduled"


# --- table-driven cross-check ---------------------------------------------
@pytest.mark.parametrize(
    "flow,state,action,to_state",
    ROWS,
    ids=[f"{_flow_id(r[0])}-{r[2]}" for r in ROWS],
)
def test_every_row(flow, state, action, to_state):
    assert flow.transition(state, action) == to_state


# --- terminal states -------------------------------------------------------
@pytest.mark.parametrize("flow", FLOWS, ids=_flow_id)
def test_terminal_states_reject_every_action(flow):
    assert flow.TERMINAL_STATES
    for state in flow.TERMINAL_STATES:
        for action in flow.ACTION_PERMISSION:
            with pytest.raises(InvalidTransition):
                flow.transition(state, action)


@pytest.mark.parametrize("flow", FLOWS, ids=_flow_id)
def test_terminal_states_have_no_outgoing_row(flow):
    sources = {state for (state, _action) in flow.TRANSITIONS}
    assert flow.TERMINAL_STATES.isdisjoint(sources)


# --- cannot submit twice ---------------------------------------------------
@pytest.mark.parametrize("flow", FLOWS, ids=_flow_id)
def test_cannot_submit_twice(flow):
    with pytest.raises(InvalidTransition):
        flow.transition(flow.INITIAL_STATE, "submit")


# --- unknown action --------------------------------------------------------
@pytest.mark.parametrize("flow", FLOWS, ids=_flow_id)
def test_unknown_action_raises(flow):
    with pytest.raises(InvalidTransition):
        flow.transition(flow.START_STATE, "no-such-action")
    with pytest.raises(InvalidTransition):
        flow.transition(flow.INITIAL_STATE, "no-such-action")


def test_error_message_names_state_and_action():
    with pytest.raises(InvalidTransition) as exc:
        leave.transition("Approved", "approve")
    assert "Approved" in str(exc.value)
    assert "approve" in str(exc.value)


# --- STATE_CHOICES ---------------------------------------------------------
@pytest.mark.parametrize("flow", FLOWS, ids=_flow_id)
def test_state_choices_exclude_start_state(flow):
    assert flow.START_STATE not in [value for value, _label in flow.STATE_CHOICES]


@pytest.mark.parametrize("flow", FLOWS, ids=_flow_id)
def test_state_choices_cover_all_other_states(flow):
    states = {s for (s, _a) in flow.TRANSITIONS} | set(flow.TRANSITIONS.values())
    states.discard(flow.START_STATE)
    assert {value for value, _label in flow.STATE_CHOICES} == states
    assert all(value == label for value, label in flow.STATE_CHOICES)
