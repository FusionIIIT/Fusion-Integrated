"""The workflow table, checked as a graph and against the specification."""
import pytest

from modules.leave.domain.state_machine import (
    TERMINAL,
    TRANSITIONS,
    Actor,
    Event,
    IllegalTransition,
    State,
    is_terminal,
    permitted,
    resolve,
)


class TestGraph:
    """Properties that must hold however the table is edited."""

    def test_every_state_can_be_reached(self):
        targets = {t.target for t in TRANSITIONS} | {State.DRAFT}
        assert set(State) - targets == set()

    def test_no_state_traps_a_request(self):
        sources = {t.source for t in TRANSITIONS}
        stuck = {s for s in State if s not in sources and s not in TERMINAL}
        assert stuck == set()

    def test_terminal_states_have_no_exit(self):
        assert {t.source for t in TRANSITIONS} & TERMINAL == set()

    def test_every_row_cites_its_workflow_and_use_case(self):
        assert all(t.workflow and t.use_case for t in TRANSITIONS)


class TestRefusals:
    """An illegal move is refused by the table, not by a service remembering."""

    def test_an_unknown_move_is_refused(self):
        with pytest.raises(IllegalTransition):
            resolve(State.AWAITING_UNIT_HEAD, Event.SANCTION)

    def test_an_approved_request_cannot_be_withdrawn(self):
        with pytest.raises(IllegalTransition):
            resolve(State.APPROVED_NOT_STARTED, Event.WITHDRAW)

    def test_a_closed_request_accepts_nothing(self):
        for event in Event:
            assert permitted(State.CLOSED, event) == ()

    def test_an_ambiguous_move_demands_a_target(self):
        with pytest.raises(IllegalTransition):
            resolve(State.DRAFT, Event.SUBMIT)

    def test_naming_the_target_resolves_it(self):
        t = resolve(State.DRAFT, Event.SUBMIT, State.AWAITING_UNIT_HEAD)
        assert t.target is State.AWAITING_UNIT_HEAD

    def test_an_unreachable_target_is_refused(self):
        with pytest.raises(IllegalTransition):
            resolve(State.DRAFT, Event.SUBMIT, State.CLOSED)


class TestSpecifiedPaths:
    """Named paths from the workflow documents."""

    def test_unit_head_is_final_for_casual_leave(self):
        # BR-EL-016, BW-EL-03 row 1.
        t = resolve(State.AWAITING_UNIT_HEAD, Event.UNIT_HEAD_APPROVE)
        assert t.target is State.APPROVED_NOT_STARTED

    def test_higher_sanction_leave_passes_through_the_hierarchy(self):
        # BW-EL-03: unit head recommends, establishment routes, authority sanctions.
        a = resolve(State.AWAITING_UNIT_HEAD, Event.UNIT_HEAD_RECOMMEND, State.AWAITING_ESTABLISHMENT)
        b = resolve(a.target, Event.ROUTE)
        c = resolve(b.target, Event.SANCTION)
        assert c.target is State.APPROVED_NOT_STARTED

    def test_the_establishment_step_can_be_skipped(self):
        # BW-EL-03 row 6: no establishment step where none is configured.
        t = resolve(State.AWAITING_UNIT_HEAD, Event.UNIT_HEAD_RECOMMEND, State.AWAITING_FINAL_SANCTION)
        assert t.target is State.AWAITING_FINAL_SANCTION

    def test_the_director_sanctions_their_own_leave(self):
        # BR-EL-020, and it is the sanctioning authority that acts.
        t = resolve(State.AWAITING_SELF_SANCTION, Event.SANCTION)
        assert t.actor is Actor.SANCTIONING_AUTHORITY

    def test_a_refused_cancellation_leaves_the_leave_approved(self):
        # BW-EL-06: the leave stands.
        t = resolve(State.CANCELLATION_FINAL, Event.CANCELLATION_REFUSE)
        assert t.target is State.APPROVED_NOT_STARTED

    def test_a_refused_extension_leaves_the_leave_running(self):
        # BW-EL-08 row 9: original unchanged.
        t = resolve(State.EXTENSION_AWAITING_FINAL, Event.EXTENSION_REFUSE)
        assert t.target is State.ONGOING

    def test_resumption_may_be_queried_without_closing(self):
        # BW-EL-09: verification can bounce back for more information.
        t = resolve(State.AWAITING_RESUMPTION_VERIFICATION, Event.RESUMPTION_QUERY)
        assert t.target is State.AWAITING_RESUMPTION_VERIFICATION
        assert not is_terminal(t.target)

    def test_only_the_establishment_closes_a_leave(self):
        t = resolve(State.AWAITING_RESUMPTION_VERIFICATION, Event.VERIFY_RESUMPTION)
        assert t.actor is Actor.ESTABLISHMENT
        assert is_terminal(t.target)


class TestDerivedTransitions:
    """The two rows the specification omits, marked as derived."""

    def test_the_declined_extension_can_be_renominated(self):
        t = resolve(State.EXTENSION_APPLICANT_ACTION_REQUIRED, Event.RENOMINATE)
        assert t.target is State.EXTENSION_AWAITING_SUBSTITUTE
        assert "derived" in t.workflow

    def test_abandoning_an_extension_leaves_the_leave_running(self):
        t = resolve(State.EXTENSION_APPLICANT_ACTION_REQUIRED, Event.WITHDRAW)
        assert t.target is State.ONGOING

    def test_derived_rows_are_labelled_so_they_can_be_found(self):
        derived = [t for t in TRANSITIONS if "derived" in t.workflow]
        assert len(derived) == 2
