import pytest

from modules.complaints.domain import state_machine as sm
from modules.complaints.domain.submission import InvalidSubmission, validate_submission


def test_submission_trims_required_values():
    assert validate_submission(category="  Facilities ", description="  Broken tap  ") == (
        "Facilities",
        "Broken tap",
    )


@pytest.mark.parametrize("field", ["category", "description"])
def test_submission_requires_category_and_description(field):
    values = {"category": "Facilities", "description": "Broken tap"}
    values[field] = "   "
    with pytest.raises(InvalidSubmission):
        validate_submission(**values)


def test_handler_can_resolve_submitted_complaint_with_details():
    move = sm.resolve(sm.SUBMITTED, "resolve", sm.HANDLER, guards=frozenset({"resolution_details"}))
    assert move.target == sm.RESOLVED


def test_handler_can_reject_submitted_complaint_with_reason():
    move = sm.resolve(sm.SUBMITTED, "reject", sm.HANDLER, guards=frozenset({"rejection_reason"}))
    assert move.target == sm.REJECTED


def test_transition_requires_the_specified_guard():
    with pytest.raises(sm.GuardFailed):
        sm.resolve(sm.SUBMITTED, "resolve", sm.HANDLER)


def test_only_complainant_can_use_user_verification_transition():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(
            sm.RESOLVED, "verify_user", sm.HANDLER, guards=frozenset({"user_verification_required"})
        )


def test_assignment_starts_work_and_resolve_uses_in_progress_state():
    assert sm.resolve(sm.SUBMITTED, "start", sm.HANDLER).target == sm.IN_PROGRESS
    assert (
        sm.resolve(
            sm.IN_PROGRESS, "resolve", sm.HANDLER, guards=frozenset({"resolution_details"})
        ).target
        == sm.RESOLVED
    )
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.CLOSED, "reopen", sm.SUPERVISOR)
