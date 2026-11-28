"""BW-GYM-01 and BW-GYM-03: every edge allowed for its actor, every other move refused."""
import itertools

import pytest

from modules.gymkhana.domain import state_machine as sm

EVENTS = (sm.CREATE, sm.APPLY, sm.APPROVE)
ACTORS = (sm.STUDENT_ADMIN, sm.CLUB_HEAD, sm.STUDENT)
SOURCES = (sm.NONE, sm.OPEN, sm.CONFIRMED)
LEGAL = {(t.machine, t.frm, t.event): t for t in sm.TRANSITIONS}


def test_bw_gym_03_club_lifecycle():
    assert sm.resolve(sm.CLUB, sm.NONE, sm.CREATE, sm.STUDENT_ADMIN).to == sm.OPEN
    assert sm.resolve(sm.CLUB, sm.OPEN, sm.APPROVE, sm.STUDENT_ADMIN).to == sm.CONFIRMED


def test_bw_gym_01_membership_lifecycle():
    assert sm.resolve(sm.MEMBERSHIP, sm.NONE, sm.APPLY, sm.STUDENT).to == sm.OPEN
    assert sm.resolve(sm.MEMBERSHIP, sm.OPEN, sm.APPROVE, sm.CLUB_HEAD).to == sm.CONFIRMED


@pytest.mark.parametrize("machine,frm,event,actor", [
    combo for combo in itertools.product((sm.CLUB, sm.MEMBERSHIP), SOURCES, EVENTS, ACTORS)
    if (combo[0], combo[1], combo[2]) not in LEGAL
])
def test_every_move_absent_from_the_table_is_refused(machine, frm, event, actor):
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(machine, frm, event, actor)


@pytest.mark.parametrize("transition,actor", [
    (t, a) for t in sm.TRANSITIONS for a in ACTORS if a != t.actor
])
def test_every_legal_edge_refuses_the_wrong_actor(transition, actor):
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(transition.machine, transition.frm, transition.event, actor)


def test_br_gym_004_and_011_confirmed_is_terminal():
    for machine in (sm.CLUB, sm.MEMBERSHIP):
        assert not [t for t in sm.TRANSITIONS if t.machine == machine
                    and t.frm == sm.CONFIRMED]


def test_no_rejection_or_cancellation_edge_exists():
    assert {t.to for t in sm.TRANSITIONS} == {sm.OPEN, sm.CONFIRMED}
