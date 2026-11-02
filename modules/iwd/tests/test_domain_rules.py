"""Tests for IWD domain rules (pure Python, no DB required)."""
import pytest
from datetime import date, timedelta

from modules.iwd.domain.rules import (
    IWDDomainError,
    Priority,
    RequestStatus,
    WorkCategory,
    WorkRequestDraft,
    can_transition,
    compute_priority_score,
    requires_budget_allocation,
    requires_director_approval,
    validate_transition,
    validate_work_request,
)


class TestWorkRequestValidation:
    def _valid_draft(self, **kwargs):
        defaults = dict(
            title="Fix AC in Room 101",
            description="The air conditioning unit in room 101 is not cooling properly.",
            location="Academic Block A, Room 101",
            category=WorkCategory.ELECTRICAL,
            priority=Priority.MEDIUM,
            requester_username="faculty_abc",
        )
        defaults.update(kwargs)
        return WorkRequestDraft(**defaults)

    def test_valid_draft_has_no_errors(self):
        draft = self._valid_draft()
        assert validate_work_request(draft) == []

    def test_short_title_fails(self):
        draft = self._valid_draft(title="Fix")
        errors = validate_work_request(draft)
        assert any("Title" in e for e in errors)

    def test_short_description_fails(self):
        draft = self._valid_draft(description="Short")
        errors = validate_work_request(draft)
        assert any("Description" in e for e in errors)

    def test_empty_location_fails(self):
        draft = self._valid_draft(location="")
        errors = validate_work_request(draft)
        assert any("Location" in e for e in errors)

    def test_negative_cost_fails(self):
        draft = self._valid_draft(estimated_cost=-500)
        errors = validate_work_request(draft)
        assert any("cost" in e.lower() for e in errors)

    def test_past_required_by_fails(self):
        draft = self._valid_draft(required_by=date.today() - timedelta(days=1))
        errors = validate_work_request(draft)
        assert any("past" in e.lower() for e in errors)

    def test_future_required_by_passes(self):
        draft = self._valid_draft(required_by=date.today() + timedelta(days=10))
        assert validate_work_request(draft) == []


class TestStatusTransitions:
    def test_draft_to_submitted_allowed(self):
        assert can_transition(RequestStatus.DRAFT, RequestStatus.SUBMITTED)

    def test_draft_to_approved_not_allowed(self):
        assert not can_transition(RequestStatus.DRAFT, RequestStatus.APPROVED)

    def test_submitted_to_under_review_allowed(self):
        assert can_transition(RequestStatus.SUBMITTED, RequestStatus.UNDER_REVIEW)

    def test_submitted_to_rejected_allowed(self):
        assert can_transition(RequestStatus.SUBMITTED, RequestStatus.REJECTED)

    def test_under_review_to_approved_allowed(self):
        assert can_transition(RequestStatus.UNDER_REVIEW, RequestStatus.APPROVED)

    def test_approved_to_in_progress_allowed(self):
        assert can_transition(RequestStatus.APPROVED, RequestStatus.IN_PROGRESS)

    def test_in_progress_to_completed_allowed(self):
        assert can_transition(RequestStatus.IN_PROGRESS, RequestStatus.COMPLETED)

    def test_completed_to_closed_allowed(self):
        assert can_transition(RequestStatus.COMPLETED, RequestStatus.CLOSED)

    def test_closed_has_no_transitions(self):
        for target in RequestStatus:
            assert not can_transition(RequestStatus.CLOSED, target)

    def test_rejected_has_no_transitions(self):
        for target in RequestStatus:
            assert not can_transition(RequestStatus.REJECTED, target)

    def test_validate_transition_raises_on_invalid(self):
        with pytest.raises(IWDDomainError):
            validate_transition(RequestStatus.DRAFT, RequestStatus.COMPLETED)

    def test_validate_transition_passes_on_valid(self):
        validate_transition(RequestStatus.DRAFT, RequestStatus.SUBMITTED)


class TestPriorityAndBudget:
    def test_urgent_gets_high_base_score(self):
        score = compute_priority_score(Priority.URGENT, None)
        assert score == 4

    def test_low_priority_gets_low_score(self):
        score = compute_priority_score(Priority.LOW, None)
        assert score == 1

    def test_due_tomorrow_boosts_score(self):
        score_with_boost = compute_priority_score(Priority.MEDIUM, date.today() + timedelta(days=1))
        score_without = compute_priority_score(Priority.MEDIUM, None)
        assert score_with_boost > score_without

    def test_director_approval_required_above_1_lakh(self):
        assert requires_director_approval(150_000)
        assert not requires_director_approval(50_000)

    def test_new_construction_always_needs_budget(self):
        assert requires_budget_allocation(WorkCategory.NEW_CONSTRUCTION, 1000)

    def test_high_cost_needs_budget(self):
        assert requires_budget_allocation(WorkCategory.REPAIR, 600_000)

    def test_normal_repair_no_budget_needed(self):
        assert not requires_budget_allocation(WorkCategory.REPAIR, 20_000)

