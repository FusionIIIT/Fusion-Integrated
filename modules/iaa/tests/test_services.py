import datetime as dt
from decimal import Decimal

import pytest

from modules.iaa import services
from modules.iaa.models import (
    Anomaly, AuditObservation, RequestStatus, TaStatus,
)

D = dt.date

CREATOR_ID = 101
APPROVER_ID = 201
FINANCE_ID = 301
AUDITOR_ID = 401


# ---- Expense / Voucher lifecycle ------------------------------------------

@pytest.fixture
def draft_expense(db):
    return services.create_draft_expense(
        CREATOR_ID, request_type="Travel", amount=Decimal("5000"),
        department="CSE", description="Conference travel")


def test_create_draft_expense_starts_as_draft(draft_expense):
    assert draft_expense.status == RequestStatus.DRAFT
    assert draft_expense.creator_id == CREATOR_ID


def test_submit_expense_moves_to_submitted(draft_expense):
    req = services.submit_expense(draft_expense.id, CREATOR_ID)
    assert req.status == RequestStatus.SUBMITTED


def test_finance_review_validates_within_budget(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    req = services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    assert req.status == RequestStatus.FINANCE_VALIDATED


def test_finance_review_over_budget_raises_anomaly_not_validated(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    req = services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("100"))
    assert req.status == RequestStatus.SUBMITTED  # unchanged — anomaly raised instead
    assert Anomaly.objects.filter(expense_request=req, category="BUDGET_INSUFFICIENT").exists()


def test_finance_review_query_moves_to_query_raised(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    req = services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=False, query_text="Need a receipt")
    assert req.status == RequestStatus.QUERY_RAISED
    assert req.query_text == "Need a receipt"


def test_respond_query_returns_to_submitted(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=False, query_text="Need a receipt")
    req = services.respond_query_expense(draft_expense.id, CREATOR_ID, "Attached.")
    assert req.status == RequestStatus.SUBMITTED


def test_decide_expense_blocks_self_approval(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    with pytest.raises(ValueError):
        services.decide_expense(draft_expense.id, CREATOR_ID, approved=True, remarks="ok")


def test_decide_expense_requires_remarks(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    with pytest.raises(ValueError):
        services.decide_expense(draft_expense.id, APPROVER_ID, approved=True, remarks="")


def test_decide_expense_single_level_approves_outright(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    req = services.decide_expense(draft_expense.id, APPROVER_ID, approved=True, remarks="ok")
    assert req.status == RequestStatus.APPROVED
    assert req.approval_level == 1


def test_decide_expense_rejection_is_terminal(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    req = services.decide_expense(draft_expense.id, APPROVER_ID, approved=False, remarks="no")
    assert req.status == RequestStatus.REJECTED


def test_decide_expense_multi_level_stays_pending_until_final_level(draft_expense):
    draft_expense.approval_levels_required = 2
    draft_expense.save()
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    req = services.decide_expense(draft_expense.id, APPROVER_ID, approved=True, remarks="L1 ok")
    assert req.status == RequestStatus.APPROVAL_PENDING
    req = services.decide_expense(draft_expense.id, 999, approved=True, remarks="L2 ok")
    assert req.status == RequestStatus.APPROVED


def test_process_record_requires_approved_status(draft_expense):
    with pytest.raises(ValueError):
        services.process_record_expense(draft_expense.id, FINANCE_ID)


def test_process_record_marks_recorded_from_approved(draft_expense):
    services.submit_expense(draft_expense.id, CREATOR_ID)
    services.finance_review_expense(
        draft_expense.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    services.decide_expense(draft_expense.id, APPROVER_ID, approved=True, remarks="ok")
    req = services.process_record_expense(draft_expense.id, FINANCE_ID)
    assert req.status == RequestStatus.RECORDED


def test_escalate_overdue_expense_sets_escalated(draft_expense):
    req = services.escalate_overdue_expense(draft_expense.id, next_authority_id=APPROVER_ID)
    assert req.status == RequestStatus.ESCALATED
    assert req.current_approver_id == APPROVER_ID


# ---- TA Claim lifecycle -----------------------------------------------------

@pytest.fixture
def ta_claim(db):
    return services.submit_ta_claim(
        CREATOR_ID, trip_start=D(2026, 3, 1), trip_end=D(2026, 3, 3),
        purpose="Conference", claimed_amount=Decimal("3000"))


def test_submit_ta_claim_not_high_value_below_threshold(ta_claim):
    assert ta_claim.is_high_value is False
    assert ta_claim.status == TaStatus.SUBMITTED


def test_submit_ta_claim_flags_high_value_at_threshold(db):
    claim = services.submit_ta_claim(
        CREATOR_ID, trip_start=D(2026, 3, 1), trip_end=D(2026, 3, 3),
        purpose="Conference", claimed_amount=Decimal("25000"))
    assert claim.is_high_value is True


def test_verify_ta_claim_low_value_goes_straight_to_verified(ta_claim):
    claim = services.verify_ta_claim(
        ta_claim.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    assert claim.status == TaStatus.VERIFIED


def test_verify_ta_claim_high_value_routes_to_approval_pending(db):
    claim = services.submit_ta_claim(
        CREATOR_ID, trip_start=D(2026, 3, 1), trip_end=D(2026, 3, 3),
        purpose="Conference", claimed_amount=Decimal("30000"))
    claim = services.verify_ta_claim(
        claim.id, FINANCE_ID, approved=True, available_budget=Decimal("50000"))
    assert claim.status == TaStatus.APPROVAL_PENDING


def test_decide_ta_claim_blocks_self_approval(ta_claim):
    services.verify_ta_claim(
        ta_claim.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    with pytest.raises(ValueError):
        services.decide_ta_claim(ta_claim.id, CREATOR_ID, approved=True, remarks="ok")


def test_process_record_ta_claim_requires_verified_or_approved(ta_claim):
    with pytest.raises(ValueError):
        services.process_record_ta_claim(ta_claim.id, FINANCE_ID)
    services.verify_ta_claim(
        ta_claim.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    claim = services.process_record_ta_claim(ta_claim.id, FINANCE_ID)
    assert claim.status == TaStatus.RECORDED


# ---- Anomalies ---------------------------------------------------------------

def test_flag_and_resolve_anomaly(db):
    anomaly = services.flag_anomaly(FINANCE_ID, category="DUPLICATE_CLAIM",
                                    description="Looks duplicated")
    resolved = services.resolve_or_escalate_anomaly(
        anomaly.id, FINANCE_ID, escalate=False, notes="Confirmed not a duplicate")
    assert resolved.status == "RESOLVED"


def test_escalate_anomaly(db):
    anomaly = services.flag_anomaly(FINANCE_ID, category="BUDGET_INSUFFICIENT")
    escalated = services.resolve_or_escalate_anomaly(anomaly.id, FINANCE_ID, escalate=True)
    assert escalated.status == "ESCALATED"


# ---- Audit observations ------------------------------------------------------

def test_audit_observation_lifecycle_requires_responded_before_close(db):
    obs = services.raise_audit_observation(AUDITOR_ID, "Missing supporting bill")
    assert obs.status == "OPEN"
    with pytest.raises(ValueError):
        services.review_close_audit_observation(obs.id, AUDITOR_ID, satisfactory=True)
    obs = services.respond_audit_observation(obs.id, CREATOR_ID, "Bill attached now.")
    assert obs.status == "RESPONDED"
    obs = services.review_close_audit_observation(obs.id, AUDITOR_ID, satisfactory=True)
    assert obs.status == "CLOSED"


def test_audit_observation_reopens_when_response_unsatisfactory(db):
    obs = services.raise_audit_observation(AUDITOR_ID, "Missing supporting bill")
    services.respond_audit_observation(obs.id, CREATOR_ID, "Partial response.")
    obs = services.review_close_audit_observation(obs.id, AUDITOR_ID, satisfactory=False)
    assert obs.status == "OPEN"
    assert not AuditObservation.objects.filter(pk=obs.id, status="CLOSED").exists()


def test_verify_ta_claim_query_raised_path(ta_claim):
    claim = services.verify_ta_claim(ta_claim.id, FINANCE_ID, approved=False,
                                     query_text="Attach boarding pass")
    assert claim.status == TaStatus.QUERY_RAISED
    assert claim.query_text == "Attach boarding pass"


def test_verify_ta_claim_over_budget_raises_anomaly_not_verified(ta_claim):
    claim = services.verify_ta_claim(
        ta_claim.id, FINANCE_ID, approved=True, available_budget=Decimal("100"))
    assert claim.status == TaStatus.SUBMITTED  # unchanged — anomaly raised instead
    assert Anomaly.objects.filter(ta_claim=claim, category="BUDGET_INSUFFICIENT").exists()


def test_decide_ta_claim_single_level_approves_outright(ta_claim):
    services.verify_ta_claim(
        ta_claim.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    claim = services.decide_ta_claim(ta_claim.id, APPROVER_ID, approved=True, remarks="ok")
    assert claim.status == TaStatus.APPROVED
    assert claim.approval_level == 1


def test_decide_ta_claim_rejection_is_terminal(ta_claim):
    services.verify_ta_claim(
        ta_claim.id, FINANCE_ID, approved=True, available_budget=Decimal("10000"))
    claim = services.decide_ta_claim(ta_claim.id, APPROVER_ID, approved=False, remarks="no")
    assert claim.status == TaStatus.REJECTED
