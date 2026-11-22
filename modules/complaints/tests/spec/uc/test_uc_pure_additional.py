"""Additional database-free checks for specified actor-triggered CMS flows."""

import pytest

from modules.complaints.domain import state_machine as sm


@pytest.mark.parametrize(
    ("source", "event", "guard", "target"),
    [
        (sm.SUBMITTED, "resolve", "resolution_details", sm.RESOLVED),
        (sm.IN_PROGRESS, "resolve", "resolution_details", sm.RESOLVED),
        (sm.SUBMITTED, "reject", "rejection_reason", sm.REJECTED),
        (sm.IN_PROGRESS, "reject", "rejection_reason", sm.REJECTED),
    ],
)
def test_uc_cms_006_handler_outcomes(source, event, guard, target):
    """UC-CMS-006: handler may resolve/reject with required outcome details."""
    transition = sm.resolve(source, event, sm.HANDLER, guards=frozenset({guard}))
    assert transition.source == source
    assert transition.target == target
    assert transition.actor == sm.HANDLER


@pytest.mark.parametrize(
    ("event", "actor", "guard"),
    [
        ("verify_user", sm.COMPLAINANT, "user_verification_required"),
        ("verify_supervisor", sm.SUPERVISOR, "supervisor_verification_required"),
    ],
)
def test_uc_cms_007_019_verified_closure(event, actor, guard):
    """UC-CMS-007/019: correct verification actor can close resolved complaint."""
    transition = sm.resolve(sm.RESOLVED, event, actor, guards=frozenset({guard}))
    assert transition.target == sm.CLOSED


@pytest.mark.parametrize(
    ("event", "actor", "guard"),
    [
        ("verify_user", sm.HANDLER, "user_verification_required"),
        ("verify_user", sm.SUPERVISOR, "user_verification_required"),
        ("verify_supervisor", sm.COMPLAINANT, "supervisor_verification_required"),
        ("verify_supervisor", sm.HANDLER, "supervisor_verification_required"),
    ],
)
def test_uc_cms_007_019_wrong_verifier_refused(event, actor, guard):
    """UC-CMS-007/019: another role cannot impersonate the required verifier."""
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.RESOLVED, event, actor, guards=frozenset({guard}))
