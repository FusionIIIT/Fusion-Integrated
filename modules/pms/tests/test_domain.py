"""Pure Python domain tests for PMS.

Requires NO database and NO Django ORM.
Maps to:
- CFR-PMS-005, CFR-PMS-006, CFR-PMS-007, CFR-PMS-008, CFR-PMS-009, CFR-PMS-011, CFR-PMS-012, CFR-PMS-015, CFR-PMS-016, CFR-PMS-018, CFR-PMS-020
- BR-PMS-014, BR-PMS-015, BR-PMS-016, BR-PMS-026, BR-PMS-027, BR-PMS-029, BR-PMS-030, BR-PMS-046, BR-PMS-048, BR-PMS-051, BR-PMS-056, BR-PMS-067, BR-PMS-068, BR-PMS-069, BR-PMS-070, BR-PMS-074, BR-PMS-092, BR-PMS-094, BR-PMS-095, BR-PMS-128
- BW-PMS-01 through BW-PMS-16, CW-PMS-01 through CW-PMS-05
"""

from decimal import Decimal

import pytest

from modules.pms.domain.entities import (
    MAX_DOCUMENT_SIZE_BYTES,
    MIN_JUSTIFICATION_LENGTH,
    check_budget_escalation,
    check_director_conflict,
    validate_appeal_outcome,
    validate_appeal_submission,
    validate_budget_components,
    validate_coinventor_shares,
    validate_document,
    validate_filing_preconditions,
    validate_patentability_opinion,
    validate_review_decision,
)
from modules.pms.domain.errors import (
    ConflictOfInterestError,
    IncompleteInventorsError,
    InsufficientJustificationError,
    InvalidDocumentError,
    InvalidTransitionError,
    PreconditionNotMetError,
    WithdrawalNotAllowedError,
)
from modules.pms.domain.state_machine import (
    TERMINAL_STATES,
    WITHDRAWAL_ELIGIBLE_STATES,
    PatentApplicationStatus,
    get_transitions,
    validate_transition,
)

# --- 1. State Machine & Transitions (CFR-PMS-028, BW-PMS-01..16, CW-PMS-01..05) ---


def test_initial_review_path_transitions_valid():
    """BW-PMS-01: Draft -> Submitted -> Under Review -> Approved."""
    t1 = validate_transition(
        PatentApplicationStatus.DRAFT, PatentApplicationStatus.SUBMITTED, actor_role="Applicant"
    )
    assert t1.to_status == PatentApplicationStatus.SUBMITTED
    assert t1.permission == "pms.application.create"

    t2 = validate_transition(
        PatentApplicationStatus.SUBMITTED,
        PatentApplicationStatus.UNDER_REVIEW,
        actor_role="PCC_ADMIN",
    )
    assert t2.to_status == PatentApplicationStatus.UNDER_REVIEW
    assert t2.permission == "pms.application.assign_director"

    t3 = validate_transition(
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.APPROVED,
        actor_role="Director",
    )
    assert t3.to_status == PatentApplicationStatus.APPROVED
    assert t3.permission == "pms.application.review"


def test_revision_and_reapproval_path():
    """BW-PMS-02: Under Review -> Needs Revision -> Resubmitted -> Under Review -> Approved."""
    validate_transition(
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.NEEDS_REVISION,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.NEEDS_REVISION,
        PatentApplicationStatus.RESUBMITTED,
        actor_role="Applicant",
    )
    validate_transition(
        PatentApplicationStatus.RESUBMITTED,
        PatentApplicationStatus.UNDER_REVIEW,
        actor_role="PCC_ADMIN",
    )


def test_appeal_workflow_transitions():
    """BW-PMS-03, 04, 05: Rejection and Appeal disposition."""
    validate_transition(
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.REJECTED,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.REJECTED,
        PatentApplicationStatus.APPEAL_SUBMITTED,
        actor_role="Applicant",
    )
    validate_transition(
        PatentApplicationStatus.APPEAL_SUBMITTED,
        PatentApplicationStatus.REMANDED_FOR_AMENDMENT,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.APPEAL_SUBMITTED,
        PatentApplicationStatus.REJECTION_UPHELD,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.APPEAL_SUBMITTED,
        PatentApplicationStatus.DECISION_MODIFIED,
        actor_role="Director",
    )


def test_attorney_assignment_workflow():
    """BW-PMS-06, 07: Attorney assignment offer, accept, decline."""
    validate_transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        actor_role="PCC_ADMIN",
    )
    validate_transition(
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        PatentApplicationStatus.PENDING_REVIEW,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.PENDING_REVIEW,
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        actor_role="PCC_ADMIN",
    )


def test_budget_transitions():
    """BW-PMS-08, 09, 10: Budget approval, rejection, and escalation."""
    validate_transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.BUDGET_APPROVED,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.BUDGET_REJECTED,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.APPROVED, PatentApplicationStatus.ESCALATED, actor_role="Director"
    )
    validate_transition(
        PatentApplicationStatus.ESCALATED,
        PatentApplicationStatus.ESCALATION_TRACKED,
        actor_role="PCC_ADMIN",
    )


def test_office_action_transitions():
    """BW-PMS-12, 13: Office action and response workflow."""
    validate_transition(
        PatentApplicationStatus.FILED,
        PatentApplicationStatus.OFFICE_ACTION_RECORDED,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.OFFICE_ACTION_RECORDED,
        PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL,
        PatentApplicationStatus.APPLICANT_APPROVED,
        actor_role="Applicant",
    )
    validate_transition(
        PatentApplicationStatus.APPLICANT_APPROVED,
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        PatentApplicationStatus.FILED,
        actor_role="Attorney",
    )


def test_maintenance_renewal_transitions():
    """BW-PMS-14, 15: Post-grant maintenance decision cycle."""
    validate_transition(
        PatentApplicationStatus.GRANTED,
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        PatentApplicationStatus.RENEWAL_APPROVED,
        actor_role="Director",
    )
    validate_transition(
        PatentApplicationStatus.RENEWAL_APPROVED,
        PatentApplicationStatus.RENEWED,
        actor_role="Attorney",
    )
    validate_transition(
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        PatentApplicationStatus.DO_NOT_RENEW,
        actor_role="Director",
    )


def test_terminal_states_have_no_outgoing_transitions():
    """Terminal states must not permit any further forward transitions."""
    for term in TERMINAL_STATES:
        outgoing = get_transitions(term)
        assert outgoing == [], (
            f"Terminal state '{term.value}' has illegal outgoing transitions: {outgoing}"
        )


def test_illegal_status_transition_raises_domain_error():
    """Direct transition from Draft to Filed or Approved must fail."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(PatentApplicationStatus.DRAFT, PatentApplicationStatus.FILED)

    with pytest.raises(InvalidTransitionError):
        validate_transition(PatentApplicationStatus.DRAFT, PatentApplicationStatus.APPROVED)

    with pytest.raises(InvalidTransitionError):
        validate_transition(PatentApplicationStatus.SUBMITTED, PatentApplicationStatus.GRANTED)


def test_unauthorized_role_for_valid_transition_fails():
    """An Applicant cannot approve an application."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            PatentApplicationStatus.UNDER_REVIEW,
            PatentApplicationStatus.APPROVED,
            actor_role="Applicant",
        )


# --- 2. Withdrawal Rules (BR-PMS-067, 068, 069, 070, CW-PMS-05) ---


@pytest.mark.parametrize("state", list(WITHDRAWAL_ELIGIBLE_STATES))
def test_pre_filing_states_eligible_for_withdrawal(state):
    """BW-PMS-16, CW-PMS-05: All pre-filing states can transition to Withdrawn when requirements met."""
    t = validate_transition(
        state,
        PatentApplicationStatus.WITHDRAWN,
        actor_role="Applicant",
        reason="Strategic decision",
        has_coinventor_consent=True,
    )
    assert t.to_status == PatentApplicationStatus.WITHDRAWN


def test_post_filing_withdrawal_prohibited():
    """BR-PMS-067: Withdrawal is prohibited once application has reached Filed or Granted status."""
    for post_state in (
        PatentApplicationStatus.FILED,
        PatentApplicationStatus.OFFICE_ACTION_RECORDED,
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        PatentApplicationStatus.GRANTED,
        PatentApplicationStatus.RENEWED,
    ):
        with pytest.raises(WithdrawalNotAllowedError):
            validate_transition(
                post_state,
                PatentApplicationStatus.WITHDRAWN,
                actor_role="Applicant",
                reason="Valid reason",
                has_coinventor_consent=True,
            )


def test_withdrawal_requires_reason():
    """BR-PMS-069: A withdrawal request must include an Applicant-provided reason."""
    with pytest.raises(WithdrawalNotAllowedError, match="reason is required"):
        validate_transition(
            PatentApplicationStatus.SUBMITTED,
            PatentApplicationStatus.WITHDRAWN,
            actor_role="Applicant",
            reason="",
            has_coinventor_consent=True,
        )


def test_withdrawal_requires_coinventor_consent():
    """BR-PMS-070: All co-inventors must consent to withdrawal."""
    with pytest.raises(WithdrawalNotAllowedError, match="co-inventors must consent"):
        validate_transition(
            PatentApplicationStatus.SUBMITTED,
            PatentApplicationStatus.WITHDRAWN,
            actor_role="Applicant",
            reason="Testing withdrawal",
            has_coinventor_consent=False,
        )


# --- 3. Document Validations (BR-PMS-014, 015, 016) ---


def test_document_format_validation():
    """BR-PMS-014: Only PDF files are accepted."""
    validate_document("specification.pdf", 1024, is_malware_clean=True)

    with pytest.raises(InvalidDocumentError, match="Unsupported document format"):
        validate_document("specification.docx", 1024, is_malware_clean=True)

    with pytest.raises(InvalidDocumentError, match="Unsupported document format"):
        validate_document("drawings.png", 1024, is_malware_clean=True)


def test_document_size_limit():
    """BR-PMS-015: An application document must be under 50 MB."""
    validate_document("valid.pdf", MAX_DOCUMENT_SIZE_BYTES - 1, is_malware_clean=True)

    with pytest.raises(InvalidDocumentError, match="exceeds the 50 MB limit"):
        validate_document("large.pdf", MAX_DOCUMENT_SIZE_BYTES + 1, is_malware_clean=True)


def test_document_malware_validation():
    """BR-PMS-016: A submitted document must pass malware validation."""
    with pytest.raises(InvalidDocumentError, match="failed security / malware validation"):
        validate_document("infected.pdf", 1024, is_malware_clean=False)


# --- 4. Review Decisions & Justifications (BR-PMS-029, 030) ---


def test_valid_review_decisions():
    """BR-PMS-029, 030: Approve, Reject, or Needs Revision with >= 50 chars justification."""
    justification_50 = "A" * MIN_JUSTIFICATION_LENGTH
    validate_review_decision("Approve", justification_50)
    validate_review_decision("Reject", justification_50)
    validate_review_decision("Needs Revision", justification_50)


def test_invalid_review_decision_choice():
    """BR-PMS-029: Review decision must be exactly one of the 3 choices."""
    with pytest.raises(PreconditionNotMetError, match="Invalid review decision"):
        validate_review_decision("Pending", "A" * 50)


def test_review_justification_under_50_chars_fails():
    """BR-PMS-030: Every Director review decision must include justification of at least 50 characters."""
    with pytest.raises(InsufficientJustificationError, match="at least 50 characters"):
        validate_review_decision("Approve", "Too short justification.")


# --- 5. Conflict of Interest (BR-PMS-026, 027) ---


def test_director_conflict_of_interest():
    """BR-PMS-026, 027: A Director must not review an application in which they are an inventor or co-inventor."""
    # Non-conflicted case passes
    check_director_conflict(
        director_user_id=101, applicant_user_id=201, coinventor_user_ids=[202, 203]
    )

    # Director is primary applicant
    with pytest.raises(
        ConflictOfInterestError, match="cannot review an application as primary inventor"
    ):
        check_director_conflict(
            director_user_id=101, applicant_user_id=101, coinventor_user_ids=[202]
        )

    # Director is co-inventor
    with pytest.raises(
        ConflictOfInterestError, match="cannot review an application as co-inventor"
    ):
        check_director_conflict(
            director_user_id=101, applicant_user_id=201, coinventor_user_ids=[101, 203]
        )


# --- 6. Co-Inventor Ownership (BR-PMS-074) ---


def test_coinventor_shares_must_sum_to_100():
    """BR-PMS-074: Inventor ownership percentages must sum to 100%."""
    validate_coinventor_shares([Decimal("60.00"), Decimal("40.00")])
    validate_coinventor_shares([Decimal("100.00")])
    validate_coinventor_shares([Decimal("33.33"), Decimal("33.33"), Decimal("33.34")])

    with pytest.raises(IncompleteInventorsError, match="must equal 100.00%"):
        validate_coinventor_shares([Decimal("50.00"), Decimal("40.00")])

    with pytest.raises(IncompleteInventorsError, match="must equal 100.00%"):
        validate_coinventor_shares([Decimal("60.00"), Decimal("50.00")])


# --- 7. Budget Components and Escalation (BR-PMS-048..051) ---


def test_budget_components_and_escalation():
    """BR-PMS-048, 049, 050, 051: Filing + Attorney + Admin costs; escalation when threshold exceeded."""
    total = validate_budget_components(Decimal("10000.00"), Decimal("20000.00"), Decimal("5000.00"))
    assert total == Decimal("35000.00")
    assert not check_budget_escalation(total, threshold=Decimal("100000.00"))

    # Above threshold
    high_total = validate_budget_components(
        Decimal("50000.00"), Decimal("60000.00"), Decimal("10000.00")
    )
    assert high_total == Decimal("120000.00")
    assert check_budget_escalation(high_total, threshold=Decimal("100000.00"))


# --- 8. External Filing Preconditions (BR-PMS-020, 056, 128) ---


def test_external_filing_preconditions():
    """BR-PMS-020, 056, 128: Preconditions for external patent filing."""
    # Valid domestic filing
    validate_filing_preconditions(
        status="budget_approved",
        budget_status="approved",
        all_agreements_complete=True,
        is_international=False,
    )

    # Budget not approved
    with pytest.raises(PreconditionNotMetError, match="Budget must be approved"):
        validate_filing_preconditions(
            status="budget_approved",
            budget_status="pending_approval",
            all_agreements_complete=True,
        )

    # Agreements incomplete
    with pytest.raises(PreconditionNotMetError, match="agreements and consents must be complete"):
        validate_filing_preconditions(
            status="budget_approved",
            budget_status="approved",
            all_agreements_complete=False,
        )

    # International filing without justification
    with pytest.raises(
        PreconditionNotMetError, match="International filings require additional justification"
    ):
        validate_filing_preconditions(
            status="budget_approved",
            budget_status="approved",
            all_agreements_complete=True,
            is_international=True,
            international_justification="",
        )


# --- 9. Appeal Validations (BR-PMS-092, 094, 095) ---


def test_appeal_submission_and_outcomes():
    """BR-PMS-092, 094, 095: Appeal constraints."""
    validate_appeal_submission(
        status="rejected", grounds="Prior art distinguishable", justification="Details..."
    )

    with pytest.raises(
        PreconditionNotMetError, match="only be filed for applications in 'rejected' status"
    ):
        validate_appeal_submission(status="under_review", grounds="G", justification="J")

    with pytest.raises(PreconditionNotMetError, match="grounds are required"):
        validate_appeal_submission(status="rejected", grounds="", justification="J")

    validate_appeal_outcome("Uphold Rejection", "Rejection upheld after re-examination.")
    validate_appeal_outcome("Remand for Amendment", "Remanded back for claims revision.")
    validate_appeal_outcome("Modify Decision", "Decision modified to Approved.")

    with pytest.raises(PreconditionNotMetError, match="Invalid appeal outcome"):
        validate_appeal_outcome("Invalid Outcome", "Details...")


# --- 10. Patentability Opinion (BR-PMS-046) ---


def test_patentability_opinion_validation():
    """BR-PMS-046: Exactly one recommendation: File Patent, Do Not File, or Needs Amendment."""
    validate_patentability_opinion("File Patent", "Novelty and non-obviousness established.")
    validate_patentability_opinion("Do Not File", "Anticipated by prior publication.")
    validate_patentability_opinion("Needs Amendment", "Claims 1-3 need narrowing.")

    with pytest.raises(PreconditionNotMetError, match="Invalid recommendation"):
        validate_patentability_opinion("Maybe File", "Details...")
