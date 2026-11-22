# Exhaustive declarative state-machine tests enumerated from the transition tables (Step 5.4).
import pytest

from modules.psm.domain import state_machine as sm
from modules.psm.domain.errors import ActorNotAllowedError, InvalidTransitionError

SPECS = [
    ("indent", sm.INDENT_STATES, sm.INDENT_TRANSITIONS, sm.INDENT_TERMINAL),
    ("transfer", sm.TRANSFER_STATES, sm.TRANSFER_TRANSITIONS, sm.TRANSFER_TERMINAL),
    ("discrepancy", sm.DISCREPANCY_STATES, sm.DISCREPANCY_TRANSITIONS, sm.DISCREPANCY_TERMINAL),
    ("invoice", sm.INVOICE_STATES, sm.INVOICE_TRANSITIONS, sm.INVOICE_TERMINAL),
    ("tender", sm.TENDER_STATES, sm.TENDER_TRANSITIONS, sm.TENDER_TERMINAL),
]


@pytest.mark.parametrize(("entity", "states", "transitions", "terminal"), SPECS)
def test_every_illegal_transition_is_refused(entity, states, transitions, terminal):
    # Enumerated from the declarative table rather than hand-picked (BW-PSM-01..08, BW-PSM-10).
    legal_pairs = {(t.frm, t.to) for t in transitions}
    for frm in states:
        for to in states:
            if (frm, to) in legal_pairs:
                assert sm.is_legal(entity, frm, to) is True
                t = sm.resolve(entity, frm, to)
                assert t.frm == frm and t.to == to
            else:
                assert sm.is_legal(entity, frm, to) is False
                with pytest.raises(InvalidTransitionError):
                    sm.resolve(entity, frm, to)


@pytest.mark.parametrize(("entity", "states", "transitions", "terminal"), SPECS)
def test_terminal_states_have_no_outgoing_transitions(entity, states, transitions, terminal):
    for s in terminal:
        assert [t for t in transitions if t.frm == s] == []


def test_wrong_actor_lane_is_refused():
    with pytest.raises(ActorNotAllowedError):
        sm.resolve("indent", sm.AWAITING_FINAL_APPROVAL, sm.PROCUREMENT_AUTHORIZED, sm.EMPLOYEE)
    with pytest.raises(ActorNotAllowedError):
        sm.resolve("invoice", sm.INV_SUBMITTED, sm.INV_VERIFIED, sm.PS_ADMIN)
