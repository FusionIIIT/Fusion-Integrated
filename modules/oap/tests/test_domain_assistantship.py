import pytest

from modules.oap.domain import assistantship as a
from modules.oap.domain.eligibility import is_pg
from modules.oap.domain.errors import InvalidTransition


# --- is_pg -----------------------------------------------------------------
@pytest.mark.parametrize("programme", ["M.Tech", "PhD", "mdes"])
def test_is_pg_true(programme):
    assert is_pg(programme) is True


@pytest.mark.parametrize("programme", ["B.Tech", "", None])
def test_is_pg_false(programme):
    assert is_pg(programme) is False


# --- submit (row 1) --------------------------------------------------------
def test_submit_with_both_roles_resolved():
    assert a.submit(a.NO_CLAIM, True, True) == a.AWAITING_DUAL


def test_submit_missing_thesis_supervisor_raises():
    with pytest.raises(InvalidTransition):
        a.submit(a.NO_CLAIM, False, True)


def test_submit_missing_ta_supervisor_raises():
    with pytest.raises(InvalidTransition):
        a.submit(a.NO_CLAIM, True, False)


def test_submit_from_awaiting_dual_raises():
    with pytest.raises(InvalidTransition):
        a.submit(a.AWAITING_DUAL, True, True)


# --- verify (rows 2-3) -----------------------------------------------------
def test_thesis_then_ta_reaches_department():
    state = a.verify(a.AWAITING_DUAL, set(), a.ROLE_THESIS)
    assert state == a.AWAITING_OTHER
    state = a.verify(state, {a.ROLE_THESIS}, a.ROLE_TA)
    assert state == a.AWAITING_DEPARTMENT


def test_ta_then_thesis_reaches_department():
    state = a.verify(a.AWAITING_DUAL, set(), a.ROLE_TA)
    assert state == a.AWAITING_OTHER
    state = a.verify(state, {a.ROLE_TA}, a.ROLE_THESIS)
    assert state == a.AWAITING_DEPARTMENT


@pytest.mark.parametrize("role", a.ROLES)
def test_one_verification_alone_is_not_enough(role):
    state = a.verify(a.AWAITING_DUAL, set(), role)
    assert state == a.AWAITING_OTHER
    assert state != a.AWAITING_DEPARTMENT


@pytest.mark.parametrize("role", a.ROLES)
def test_same_role_verifying_twice_raises(role):
    with pytest.raises(InvalidTransition):
        a.verify(a.AWAITING_OTHER, {role}, role)


def test_unknown_role_raises_value_error():
    with pytest.raises(ValueError):
        a.verify(a.AWAITING_DUAL, set(), "dean")


@pytest.mark.parametrize("state", [a.AWAITING_DEPARTMENT, a.AWAITING_HOD])
def test_verify_after_both_complete_raises(state):
    with pytest.raises(InvalidTransition):
        a.verify(state, set(), a.ROLE_THESIS)


@pytest.mark.parametrize("state", [a.AWAITING_DEPARTMENT, a.AWAITING_HOD])
def test_verify_from_later_states_with_one_role_raises(state):
    with pytest.raises(InvalidTransition):
        a.verify(state, {a.ROLE_THESIS}, a.ROLE_TA)


# --- forward / approve / reject / process_stipend --------------------------
@pytest.mark.parametrize("state", [a.AWAITING_DUAL, a.AWAITING_OTHER])
def test_forward_before_both_verifications_raises(state):
    with pytest.raises(InvalidTransition):
        a.transition(state, "forward")


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_hod_cannot_act_before_forwarding(action):
    with pytest.raises(InvalidTransition):
        a.transition(a.AWAITING_DEPARTMENT, action)


@pytest.mark.parametrize("state", [a.AWAITING_HOD, a.REJECTED])
def test_process_stipend_before_approval_raises(state):
    with pytest.raises(InvalidTransition):
        a.transition(state, "process_stipend")


# --- full paths ------------------------------------------------------------
def _run_to_hod():
    state = a.submit(a.NO_CLAIM, True, True)
    state = a.verify(state, set(), a.ROLE_THESIS)
    state = a.verify(state, {a.ROLE_THESIS}, a.ROLE_TA)
    return a.transition(state, "forward")


def test_full_approved_path():
    state = _run_to_hod()
    assert state == a.AWAITING_HOD
    state = a.transition(state, "approve")
    assert state == a.APPROVED
    state = a.transition(state, "process_stipend")
    assert state == a.STIPEND_PROCESSED


def test_rejected_path():
    state = a.transition(_run_to_hod(), "reject")
    assert state == a.REJECTED


# --- terminal states -------------------------------------------------------
@pytest.mark.parametrize("state", sorted(a.TERMINAL_STATES))
def test_terminal_states_accept_no_action(state):
    for action in a.ACTION_PERMISSION:
        if action == "submit":
            with pytest.raises(InvalidTransition):
                a.submit(state, True, True)
        elif action == "verify":
            for role in a.ROLES:
                with pytest.raises(InvalidTransition):
                    a.verify(state, set(), role)
        else:
            with pytest.raises(InvalidTransition):
                a.transition(state, action)


def test_state_choices_exclude_start_state():
    assert a.START_STATE not in [v for v, _ in a.STATE_CHOICES]
    assert len(a.STATE_CHOICES) == 7
