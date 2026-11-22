"""Selected explicit CMS state transitions (not exhaustive STT coverage)."""
import pytest
from modules.complaints.domain import state_machine as sm


def test_bw_cms_01_intake_to_resolved():
    """BW-CMS-01: handler can resolve with recorded resolution details guard."""
    step = sm.resolve(sm.SUBMITTED, "resolve", sm.HANDLER, guards=frozenset({"resolution_details"}))
    assert step.target == sm.RESOLVED


def test_bw_cms_02_user_verified_closure():
    """BW-CMS-02: complainant may verify resolved complaint for closure."""
    step = sm.resolve(sm.RESOLVED, "verify_user", sm.COMPLAINANT, guards=frozenset({"user_verification_required"}))
    assert step.target == sm.CLOSED


def test_bw_cms_03_supervisor_verified_closure():
    """BW-CMS-03: supervisor may verify resolved complaint for closure."""
    step = sm.resolve(sm.RESOLVED, "verify_supervisor", sm.SUPERVISOR, guards=frozenset({"supervisor_verification_required"}))
    assert step.target == sm.CLOSED


def test_bw_cms_04_intake_to_rejection():
    """BW-CMS-04: handler rejection requires reason guard."""
    step = sm.resolve(sm.SUBMITTED, "reject", sm.HANDLER, guards=frozenset({"rejection_reason"}))
    assert step.target == sm.REJECTED


@pytest.mark.parametrize("event,guard", [("resolve", "resolution_details"), ("reject", "rejection_reason")])
def test_cw_cms_01_outcome_guard_required(event, guard):
    """CW-CMS-01: a required outcome detail guard cannot be omitted."""
    with pytest.raises(sm.GuardFailed):
        sm.resolve(sm.SUBMITTED, event, sm.HANDLER)


def test_cw_cms_01_verification_actor_enforced():
    """CW-CMS-01: handler may not perform user closure verification."""
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.RESOLVED, "verify_user", sm.HANDLER,
                   guards=frozenset({"user_verification_required"}))
