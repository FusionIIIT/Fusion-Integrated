"""Additional database-free workflow tests of explicit state machine paths.

Does not cover persistence, reopen services, escalation jobs, or full STTs.
"""

import pytest

from modules.complaints.domain import state_machine as sm


def test_bw_cms_01_progression_from_submitted_to_resolved():
    """BW-CMS-01: handler starts work, then resolves with outcome details."""
    step1 = sm.resolve(sm.SUBMITTED, "start", sm.HANDLER)
    assert step1.target == sm.IN_PROGRESS
    step2 = sm.resolve(step1.target, "resolve", sm.HANDLER, guards=frozenset({"resolution_details"}))
    assert step2.target == sm.RESOLVED


def test_bw_cms_04_progression_from_submitted_to_rejected():
    """BW-CMS-04: started work may reach a rejected outcome with reason."""
    step1 = sm.resolve(sm.SUBMITTED, "start", sm.HANDLER)
    step2 = sm.resolve(step1.target, "reject", sm.HANDLER, guards=frozenset({"rejection_reason"}))
    assert step2.target == sm.REJECTED


@pytest.mark.parametrize(
    ("event", "actor", "guard"),
    [
        ("verify_user", sm.COMPLAINANT, "user_verification_required"),
        ("verify_supervisor", sm.SUPERVISOR, "supervisor_verification_required"),
    ],
)
def test_bw_cms_02_03_intake_to_verified_closure(event, actor, guard):
    """BW-CMS-02/03: intake, resolution, authorized closure verification."""
    working = sm.resolve(sm.SUBMITTED, "start", sm.HANDLER)
    resolved = sm.resolve(working.target, "resolve", sm.HANDLER, guards=frozenset({"resolution_details"}))
    closed = sm.resolve(resolved.target, event, actor, guards=frozenset({guard}))
    assert (working.target, resolved.target, closed.target) == (sm.IN_PROGRESS, sm.RESOLVED, sm.CLOSED)


@pytest.mark.parametrize("source", [sm.SUBMITTED, sm.IN_PROGRESS, sm.RESOLVED, sm.REJECTED, sm.CLOSED])
def test_cw_cms_01_transition_listing_filters_by_source(source):
    """CW-CMS-01: state machine lists only transitions originating at a given state."""
    assert all(t.source == source for t in sm.transitions_for(source))


@pytest.mark.parametrize(
    ("source", "actor"),
    [
        (sm.SUBMITTED, sm.HANDLER),
        (sm.RESOLVED, sm.COMPLAINANT),
        (sm.RESOLVED, sm.SUPERVISOR),
    ],
)
def test_cw_cms_01_transition_listing_filters_by_actor(source, actor):
    """CW-CMS-01: transition options are filtered by participant role."""
    assert all(t.source == source and t.actor == actor for t in sm.transitions_for(source, actor))
