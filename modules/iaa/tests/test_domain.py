"""Pure unit tests for domain.py — no db, no Django setup needed."""
import pytest

from modules.iaa import domain


def test_segregation_of_duties_blocks_self_approval():
    with pytest.raises(ValueError):
        domain.check_segregation_of_duties(creator_id=1, actor_id=1)


def test_segregation_of_duties_allows_different_actor():
    domain.check_segregation_of_duties(creator_id=1, actor_id=2)


def test_submission_completeness_skipped_for_draft():
    domain.check_submission_completeness({}, ("amount", "department"), is_draft=True)


def test_submission_completeness_enforced_on_formal_submit():
    with pytest.raises(ValueError):
        domain.check_submission_completeness(
            {"amount": 100}, ("amount", "department"), is_draft=False)


def test_submission_completeness_passes_when_all_fields_present():
    domain.check_submission_completeness(
        {"amount": 100, "department": "CS"}, ("amount", "department"), is_draft=False)


def test_budget_available_true_when_within_budget():
    assert domain.check_budget_available(500, 1000) is True


def test_budget_available_false_when_exceeding_budget():
    assert domain.check_budget_available(1500, 1000) is False


def test_more_approval_levels_required_true_when_below_threshold():
    assert domain.more_approval_levels_required(current_level=1, levels_required=2) is True


def test_more_approval_levels_required_false_at_final_level():
    assert domain.more_approval_levels_required(current_level=2, levels_required=2) is False


def test_is_high_value_true_at_or_above_threshold():
    assert domain.is_high_value(25000, 25000) is True
    assert domain.is_high_value(30000, 25000) is True


def test_is_high_value_false_below_threshold():
    assert domain.is_high_value(24999, 25000) is False


def test_require_remarks_rejects_blank_or_missing():
    with pytest.raises(ValueError):
        domain.require_remarks("")
    with pytest.raises(ValueError):
        domain.require_remarks("   ")
    with pytest.raises(ValueError):
        domain.require_remarks(None)


def test_require_remarks_accepts_nonblank_text():
    domain.require_remarks("Looks good, approved.")


def test_can_close_observation_requires_responded_status():
    with pytest.raises(ValueError):
        domain.can_close_observation("OPEN")
    domain.can_close_observation("RESPONDED")
