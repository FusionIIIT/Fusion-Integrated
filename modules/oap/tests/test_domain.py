import itertools

import pytest

from modules.oap.domain import assistantship as asd
from modules.oap.domain import no_dues as nd
from modules.oap.domain import state_machines as sm
from modules.oap.domain.errors import IllegalTransition

ROLES = ["hod", "academic_admin", "supervisor", "dept_admin", "student", "nobody"]
EVENTS = ["approve", "reject", "verify", "forward", "process_stipend", "schedule"]


def _illegal(machine, states):
    legal = set(sm.MACHINES[machine])
    for state, event, role in itertools.product(states, EVENTS, ROLES):
        if (state, event, role) not in legal:
            yield state, event, role


@pytest.mark.parametrize(
    "machine,states",
    [
        ("leave", [sm.LEAVE_SUBMITTED, sm.LEAVE_APPROVED, sm.LEAVE_REJECTED]),
        ("bonafide", [sm.BONAFIDE_SUBMITTED, sm.BONAFIDE_APPROVED, sm.BONAFIDE_REJECTED]),
        (
            "claim",
            [
                sm.CLAIM_AWAITING_DUAL,
                sm.CLAIM_AWAITING_OTHER,
                sm.CLAIM_AWAITING_DEPT_REVIEW,
                sm.CLAIM_AWAITING_HOD,
                sm.CLAIM_APPROVED,
                sm.CLAIM_REJECTED,
                sm.CLAIM_STIPEND_PROCESSED,
            ],
        ),
        ("seminar", [sm.SEMINAR_AWAITING, sm.SEMINAR_SCHEDULED]),
    ],
)
def test_every_illegal_transition_is_refused(machine, states):
    for state, event, role in _illegal(machine, states):
        with pytest.raises(IllegalTransition):
            sm.next_state(machine, state, event, role)


def test_claim_path_follows_the_specified_order():
    s = sm.CLAIM_AWAITING_DUAL
    s = sm.next_state("claim", s, "verify", "supervisor")
    s = sm.next_state("claim", s, "verify", "supervisor")
    s = sm.next_state("claim", s, "forward", "dept_admin")
    s = sm.next_state("claim", s, "approve", "hod")
    s = sm.next_state("claim", s, "process_stipend", "academic_admin")
    assert s == sm.CLAIM_STIPEND_PROCESSED


def test_no_dues_status_is_derived_from_seven_results():
    clear = dict.fromkeys(nd.DOMAINS, nd.CLEAR)
    assert nd.derive_status({}, finalized=False) == nd.IN_PROGRESS
    assert nd.derive_status(clear, finalized=False) == nd.ALL_CLEAR
    assert (
        nd.derive_status({**clear, "lab": nd.OUTSTANDING}, finalized=False) == nd.DUES_OUTSTANDING
    )
    assert nd.derive_status(clear, finalized=True) == nd.FINALIZED
    assert not nd.may_finalize({**clear, "mess": nd.PENDING}, finalized=False)


def test_both_supervisor_roles_are_required():
    assert asd.pending_roles([]) == (asd.THESIS, asd.TA)
    assert asd.pending_roles([asd.THESIS]) == (asd.TA,)
    assert asd.both_recorded([asd.THESIS, asd.TA])
    assert not asd.both_recorded([asd.TA])
