from datetime import date, timedelta
from decimal import Decimal
import pytest

from modules.pms.domain.business_rules import (
    calculate_annuity_grace_period,
    calculate_statutory_fer_deadline,
    verify_appeal_eligibility,
    verify_budget_sanction,
)
from modules.pms.domain.state_machine import (
    IllegalTransitionError,
    PatentStateMachine,
)
from modules.pms.domain.validation import (
    ValidationError,
    validate_application_data,
    validate_coinventor_shares,
    validate_document_size,
    validate_no_conflict_of_interest,
)
from modules.pms.models.application import ApplicationStatus


def test_state_machine_valid_transitions():
    # Draft -> Submitted by applicant
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "SUBMIT", ["applicant"])
    assert nxt == ApplicationStatus.SUBMITTED

    # Submitted -> Under Review by coordinator
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["pms_coordinator"])
    assert nxt == ApplicationStatus.UNDER_REVIEW

    # Under Review -> Approved by Director
    nxt = PatentStateMachine.get_next_state(ApplicationStatus.UNDER_REVIEW, "APPROVE", ["director"])
    assert nxt == ApplicationStatus.APPROVED


def test_state_machine_illegal_transition():
    # Directly Granting from Draft is illegal
    with pytest.raises(IllegalTransitionError):
        PatentStateMachine.get_next_state(ApplicationStatus.DRAFT, "GRANT", ["applicant"])

    # Unauthorized role
    with pytest.raises(IllegalTransitionError):
        PatentStateMachine.get_next_state(ApplicationStatus.SUBMITTED, "ASSIGN_DIRECTOR", ["student"])


def test_validation_rules():
    # Empty title
    with pytest.raises(ValidationError):
        validate_application_data({"title": "", "abstract": "abc", "claims": "xyz"})

    # Non-100% shares
    with pytest.raises(ValidationError):
        validate_coinventor_shares([
            {"user_id": 1, "contribution_percentage": 50},
            {"user_id": 2, "contribution_percentage": 40},
        ])

    # Valid 100% shares
    validate_coinventor_shares([
        {"user_id": 1, "contribution_percentage": 60},
        {"user_id": 2, "contribution_percentage": 40},
    ])

    # Document size exceeding 50 MB (BR-PMS-015)
    with pytest.raises(ValidationError):
        validate_document_size(60 * 1024 * 1024)

    # Conflict of interest (BR-PMS-025)
    with pytest.raises(ValidationError):
        validate_no_conflict_of_interest(applicant_id=10, reviewer_id=10, co_inventor_ids=[20, 30])


def test_business_rules():
    today = date.today()
    deadline = calculate_statutory_fer_deadline(today)
    assert (deadline - today).days == 180

    grace = calculate_annuity_grace_period(today)
    assert (grace - today).days == 180

    # Appeal within 30 days
    verify_appeal_eligibility(today, today + timedelta(days=20))
    with pytest.raises(ValidationError):
        verify_appeal_eligibility(today, today + timedelta(days=35))

    # Budget sanction
    assert verify_budget_sanction(Decimal("50000.00"), Decimal("50000.00")) is True
    assert verify_budget_sanction(Decimal("60000.00"), Decimal("50000.00")) is False
