from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from modules.patents.domain import (
    deadlines,
    filing,
    policy,
    validation,
)
from modules.patents.domain import (
    state_machine as sm,
)

ALL_STATES = [
    sm.DRAFT, sm.SUBMITTED, sm.UNDER_REVIEW, sm.NEEDS_REVISION, sm.REJECTED,
    sm.RESUBMITTED, sm.EXPIRED, sm.APPEAL_SUBMITTED, sm.REMANDED,
    sm.REJECTION_UPHELD, sm.DECISION_MODIFIED, sm.APPROVED,
    sm.ASSIGNMENT_OFFERED, sm.ATTORNEY_ASSIGNED, sm.PENDING_REVIEW,
    sm.ASSESSMENT_IN_PROGRESS, sm.FILED, sm.GRANTED, sm.MAINTENANCE_PENDING,
    sm.RENEWED, sm.LAPSED, sm.WITHDRAWN,
]


def test_transition_table_declarative_consistency():
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm in ALL_STATES:
        for to in ALL_STATES:
            assert sm.is_legal(frm, to) is ((frm, to) in declared)


def test_terminal_states_have_no_exits():
    for s in sm.TERMINAL:
        assert sm.allowed_targets(s) == []


def test_illegal_transition_raises():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.DRAFT, sm.GRANTED)

    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.FILED, sm.WITHDRAWN)


def test_actor_not_allowed_raises():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.DRAFT, sm.SUBMITTED, actor_kind=sm.DIRECTOR)

    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.UNDER_REVIEW, sm.APPROVED, actor_kind=sm.APPLICANT)


def test_attorney_decline_and_reassignment():
    t_decline = sm.resolve(sm.ASSIGNMENT_OFFERED, sm.PENDING_REVIEW, actor_kind=sm.ATTORNEY)
    assert "assignment_declined" in t_decline.guards

    t_reassign = sm.resolve(sm.PENDING_REVIEW, sm.ASSIGNMENT_OFFERED, actor_kind=sm.PCC_ADMIN)
    assert "approved_panel" in t_reassign.guards
    assert "no_coi" in t_reassign.guards


def test_attorney_accept_and_assessment():
    t_accept = sm.resolve(sm.ASSIGNMENT_OFFERED, sm.ATTORNEY_ASSIGNED, actor_kind=sm.ATTORNEY)
    assert "assignment_accepted" in t_accept.guards

    t_start = sm.resolve(sm.ATTORNEY_ASSIGNED, sm.ASSESSMENT_IN_PROGRESS, actor_kind=sm.ATTORNEY)
    assert t_start.to == sm.ASSESSMENT_IN_PROGRESS


def test_appeal_modified_decision_aligns_to_decision_modified():
    t = sm.resolve(sm.APPEAL_SUBMITTED, sm.DECISION_MODIFIED, actor_kind=sm.DIRECTOR)
    assert "decision_modified" in t.guards
    assert t.to == sm.DECISION_MODIFIED
    assert sm.DECISION_MODIFIED in sm.TERMINAL


def test_revision_and_resubmission_from_needs_revision_and_rejected():
    t_rev = sm.resolve(sm.NEEDS_REVISION, sm.RESUBMITTED, actor_kind=sm.APPLICANT)
    assert "within_revision_deadline" in t_rev.guards
    assert "addresses_feedback" in t_rev.guards

    t_rej_rev = sm.resolve(sm.REJECTED, sm.RESUBMITTED, actor_kind=sm.APPLICANT)
    assert "within_revision_deadline" in t_rej_rev.guards
    assert "addresses_feedback" in t_rej_rev.guards


def test_revision_expiration():
    t_rev_exp = sm.resolve(sm.NEEDS_REVISION, sm.EXPIRED, actor_kind=sm.SYSTEM)
    assert "revision_deadline_expired" in t_rev_exp.guards

    t_rej_exp = sm.resolve(sm.REJECTED, sm.EXPIRED, actor_kind=sm.SYSTEM)
    assert "revision_deadline_expired" in t_rej_exp.guards


def test_withdrawal_transitions():
    for state in (
        sm.DRAFT, sm.SUBMITTED, sm.UNDER_REVIEW, sm.NEEDS_REVISION,
        sm.APPROVED, sm.ATTORNEY_ASSIGNED, sm.PENDING_REVIEW,
        sm.ASSESSMENT_IN_PROGRESS,
    ):
        t = sm.resolve(state, sm.WITHDRAWN, actor_kind=sm.APPLICANT)
        assert "has_reason" in t.guards
        assert "withdrawal_eligible" in t.guards


def test_application_field_completeness():
    validation.validate_application_fields(
        title="Solar Cell", abstract="Novel cell", description="Detailed desc", claims="Claim 1",
    )

    with pytest.raises(validation.IncompleteApplicationError):
        validation.validate_application_fields("", "abstract", "desc", "claims")

    with pytest.raises(validation.IncompleteApplicationError):
        validation.validate_application_fields("title", "  ", "desc", "claims")


def test_document_format_and_size():
    validation.validate_document("pdf", 1024)
    validation.validate_document(".PDF", 52_428_800)

    with pytest.raises(validation.DocumentFormatError):
        validation.validate_document("docx", 1024)

    with pytest.raises(validation.DocumentSizeError):
        validation.validate_document("pdf", 0)

    with pytest.raises(validation.DocumentSizeError):
        validation.validate_document("pdf", 52_428_801)


def test_ownership_shares_sum():
    validation.validate_ownership_shares([100])
    validation.validate_ownership_shares([Decimal("60.50"), Decimal("39.50")])
    validation.validate_ownership_shares([25, 25, 50])

    with pytest.raises(validation.InvalidSharePercentageError):
        validation.validate_ownership_shares([])

    with pytest.raises(validation.InvalidSharePercentageError):
        validation.validate_ownership_shares([50, 40])

    with pytest.raises(validation.InvalidSharePercentageError):
        validation.validate_ownership_shares([0, 100])

    with pytest.raises(validation.InvalidSharePercentageError):
        validation.validate_ownership_shares([110, -10])


def test_review_justification_minimum_length():
    valid_text = (
        "This application meets all technical novelty criteria required by institute guidelines."
    )
    assert len(valid_text) >= 50
    validation.validate_justification(valid_text)

    with pytest.raises(validation.InvalidJustificationError):
        validation.validate_justification("Looks good to me.")


def test_conflict_of_interest():
    validation.validate_coi(applicant_user_id=101, reviewer_user_id=202)

    with pytest.raises(validation.ConflictOfInterestError):
        validation.validate_coi(applicant_user_id=101, reviewer_user_id=101)


def test_patentability_recommendations():
    for rec in ("File Patent", "Do Not File", "Needs Amendment"):
        validation.validate_patentability_recommendation(rec)

    with pytest.raises(validation.InvalidOpinionRecommendationError):
        validation.validate_patentability_recommendation("Accept")


def test_appeal_outcomes():
    for outcome in ("Uphold Rejection", "Remand for Amendment", "Modify Decision"):
        validation.validate_appeal_outcome(outcome)

    with pytest.raises(validation.InvalidAppealOutcomeError):
        validation.validate_appeal_outcome("Overturn")


def test_revision_expiration_logic():
    base = datetime(2026, 1, 1, 10, 0, 0)
    within_limit = base + timedelta(days=59)
    at_limit = base + timedelta(days=60)
    past_limit = base + timedelta(days=61)

    assert not deadlines.is_revision_expired(base, within_limit, limit_days=60)
    assert deadlines.is_revision_expired(base, at_limit, limit_days=60)
    assert deadlines.is_revision_expired(base, past_limit, limit_days=60)


def test_review_overdue_logic():
    base = datetime(2026, 1, 1, 10, 0, 0)
    assert not deadlines.is_review_overdue(base, base + timedelta(days=14), limit_days=15)
    assert deadlines.is_review_overdue(base, base + timedelta(days=15), limit_days=15)


def test_alert_intervals():
    today = date(2026, 6, 1)
    assert deadlines.match_alert_interval(date(2026, 7, 1), today) == 30
    assert deadlines.match_alert_interval(date(2026, 6, 16), today) == 15
    assert deadlines.match_alert_interval(date(2026, 6, 6), today) == 5
    assert deadlines.match_alert_interval(date(2026, 6, 10), today) is None


def test_filing_clearance():
    cleared = filing.evaluate_filing_clearance(
        has_inventor_agreements=True,
        has_budget_approval=True,
        has_format_compliance=True,
    )
    assert cleared.cleared is True
    assert "cleared" in cleared.message.lower()

    blocked = filing.evaluate_filing_clearance(
        has_inventor_agreements=False,
        has_budget_approval=True,
        has_format_compliance=False,
    )
    assert blocked.cleared is False
    assert len(blocked.reasons) == 2
    assert "Inventor agreements" in blocked.message
    assert "format standards" in blocked.message


def test_policy_spec_withdrawal_default_and_configured():
    # BR-PMS-068: Default policy is unconfigured / empty tuple, allowing no withdrawals
    default_pol = policy.PolicySpec()
    assert default_pol.withdrawal_eligible_states == ()
    assert default_pol.is_withdrawal_permitted("draft") is False
    assert default_pol.is_withdrawal_permitted("submitted") is False

    # Configured policy allows explicitly declared statuses
    pol = policy.PolicySpec(
        cost_escalation_threshold=Decimal("100000.00"),
        withdrawal_eligible_states=("draft", "submitted"),
    )
    assert pol.is_withdrawal_permitted("draft") is True
    assert pol.is_withdrawal_permitted("submitted") is True
    assert pol.is_withdrawal_permitted("approved") is False

    assert pol.is_cost_escalation_triggered(Decimal("50000.00")) is False
    assert pol.is_cost_escalation_triggered(Decimal("100000.00")) is False
    assert pol.is_cost_escalation_triggered(Decimal("100000.01")) is True
