"""Additional database-free CMS business-rule checks.

These test the exposed pure domain functions, not persistence or HTTP.
"""

import pytest

from modules.complaints.domain import state_machine as sm
from modules.complaints.domain.submission import InvalidSubmission, validate_submission


@pytest.mark.parametrize("blank", ["", "  ", "\t", "\n"])
def test_br_cms_002_blank_category_refused(blank):
    """BR-CMS-002: missing complaint category is unacceptable."""
    with pytest.raises(InvalidSubmission, match="category"):
        validate_submission(category=blank, description="Damaged desk")


@pytest.mark.parametrize("blank", ["", "  ", "\t", "\n"])
def test_br_cms_002_blank_description_refused(blank):
    """BR-CMS-002: missing complaint description is unacceptable."""
    with pytest.raises(InvalidSubmission, match="description"):
        validate_submission(category="Facilities", description=blank)


@pytest.mark.parametrize(
    ("source", "event", "guard"),
    [
        (sm.SUBMITTED, "resolve", "resolution_details"),
        (sm.IN_PROGRESS, "resolve", "resolution_details"),
        (sm.SUBMITTED, "reject", "rejection_reason"),
        (sm.IN_PROGRESS, "reject", "rejection_reason"),
    ],
)
def test_br_cms_013_014_outcome_detail_required(source, event, guard):
    """BR-CMS-013/014: the appropriate outcome detail is required."""
    with pytest.raises(sm.GuardFailed):
        sm.resolve(source, event, sm.HANDLER)
    assert sm.resolve(source, event, sm.HANDLER, guards=frozenset({guard})).target in {
        sm.RESOLVED, sm.REJECTED
    }


@pytest.mark.parametrize(
    ("event", "actor", "guard"),
    [
        ("verify_user", sm.COMPLAINANT, "user_verification_required"),
        ("verify_supervisor", sm.SUPERVISOR, "supervisor_verification_required"),
    ],
)
def test_br_cms_016_verification_requires_configured_guard(event, actor, guard):
    """BR-CMS-016: applicable closure verification requires its guard."""
    with pytest.raises(sm.GuardFailed):
        sm.resolve(sm.RESOLVED, event, actor)
    assert sm.resolve(sm.RESOLVED, event, actor, guards=frozenset({guard})).target == sm.CLOSED
