"""Unit tests for pure Python PMS domain rules and state machine."""

import decimal

import pytest

from modules.pms.domain.constants import (
    ACTOR_APPLICANT,
    ACTOR_ATTORNEY,
    ACTOR_DIRECTOR,
    ACTOR_PCC_ADMIN,
    DOC_MAX_BYTES,
    STATUS_APPROVED,
    STATUS_ASSIGNMENT_OFFERED,
    STATUS_ATTORNEY_ASSIGNED,
    STATUS_DRAFT,
    STATUS_FILED,
    STATUS_NEEDS_REVISION,
    STATUS_RESUBMITTED,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_WITHDRAWN,
)
from modules.pms.domain.exceptions import (
    ActorNotAllowedError,
    ConflictOfInterestError,
    InvalidTransitionError,
    ValidationError,
)
from modules.pms.domain.rules import (
    check_director_conflict_of_interest,
    check_pcc_admin_conflict_of_interest,
    check_pre_filing_prerequisites,
    validate_application_submission_fields,
    validate_director_review_decision,
    validate_document_file,
    validate_inventor_shares,
)
from modules.pms.domain.state_machine import validate_transition


class TestDocumentValidation:
    def test_valid_pdf_accepted(self):
        validate_document_file("claims.pdf", 1024 * 1024, "application/pdf")

    def test_non_pdf_rejected(self):
        with pytest.raises(ValidationError, match="must be PDF"):
            validate_document_file("claims.docx", 1024, "application/vnd.openxmlformats")

    def test_oversized_file_rejected(self):
        with pytest.raises(ValidationError, match="exceeds maximum limit of 50 MB"):
            validate_document_file("large.pdf", DOC_MAX_BYTES + 1, "application/pdf")

    def test_empty_file_rejected(self):
        with pytest.raises(ValidationError, match="must not be empty"):
            validate_document_file("empty.pdf", 0, "application/pdf")


class TestApplicationValidation:
    def test_complete_fields_pass(self):
        validate_application_submission_fields(
            title="Quantum Photonic Processor",
            abstract="Novel processor using polarized photons.",
            description="Detailed embodiment of quantum waveguides...",
            claims="Claim 1: An optical processing unit comprising...",
            domain="Computer Science & Engineering",
        )

    def test_missing_fields_fail(self):
        with pytest.raises(ValidationError, match="Missing required application fields"):
            validate_application_submission_fields(
                title="",
                abstract="Some abstract",
                description="",
                claims="Some claim",
                domain="CSE",
            )


class TestInventorShares:
    def test_exact_hundred_percent_passes(self):
        validate_inventor_shares(
            [
                decimal.Decimal("60.00"),
                decimal.Decimal("40.00"),
            ]
        )

    def test_non_hundred_percent_fails(self):
        with pytest.raises(ValidationError, match=r"must total exactly 100\.00%"):
            validate_inventor_shares(
                [
                    decimal.Decimal("50.00"),
                    decimal.Decimal("40.00"),
                ]
            )

    def test_empty_inventors_fails(self):
        with pytest.raises(ValidationError, match="At least one inventor is required"):
            validate_inventor_shares([])


class TestDirectorReview:
    def test_valid_approval_with_justification(self):
        justification = (
            "The proposed method shows substantial technical merit, "
            "novel architecture, and high institutional patentability value."
        )
        assert len(justification) >= 50
        validate_director_review_decision("approve", justification)

    def test_short_justification_fails(self):
        with pytest.raises(ValidationError, match="requires justification of >= 50 chars"):
            validate_director_review_decision("approve", "Looks good to me.")

    def test_invalid_decision_fails(self):
        with pytest.raises(ValidationError, match="Decision must be one of"):
            validate_director_review_decision("maybe", "A" * 60)


class TestConflictOfInterest:
    def test_director_cannot_review_own_invention(self):
        with pytest.raises(ConflictOfInterestError, match="Conflict of interest"):
            check_director_conflict_of_interest(director_user_id=101, inventor_user_ids=[101, 202])

    def test_director_can_review_independent_application(self):
        check_director_conflict_of_interest(director_user_id=101, inventor_user_ids=[303, 404])

    def test_admin_cannot_review_own_invention(self):
        with pytest.raises(ConflictOfInterestError, match="Conflict of interest"):
            check_pcc_admin_conflict_of_interest(admin_user_id=999, inventor_user_ids=[999, 101])


class TestPreFilingPrerequisites:
    def test_satisfied_prerequisites_pass(self):
        check_pre_filing_prerequisites(
            budget_approved=True,
            inventor_agreements_completed=True,
            patentability_assessed=True,
        )

    def test_missing_agreements_fails(self):
        with pytest.raises(ValidationError, match="Inventor agreements must be completed"):
            check_pre_filing_prerequisites(
                budget_approved=True,
                inventor_agreements_completed=False,
                patentability_assessed=True,
            )


class TestStateMachineTransitions:
    def test_initial_review_path(self):
        # BW-PMS-01: Draft -> Submitted (Applicant) -> Under Review (Admin) -> Approved (Director)
        e1 = validate_transition(STATUS_DRAFT, STATUS_SUBMITTED, ACTOR_APPLICANT)
        assert e1.workflow_id == "BW-PMS-01"

        e2 = validate_transition(STATUS_SUBMITTED, STATUS_UNDER_REVIEW, ACTOR_PCC_ADMIN)
        assert e2.workflow_id == "BW-PMS-01"

        e3 = validate_transition(STATUS_UNDER_REVIEW, STATUS_APPROVED, ACTOR_DIRECTOR)
        assert e3.workflow_id == "BW-PMS-01"

    def test_revision_and_reapproval_path(self):
        # BW-PMS-02: Under Review -> Needs Revision -> Resubmitted -> Under Review
        validate_transition(STATUS_UNDER_REVIEW, STATUS_NEEDS_REVISION, ACTOR_DIRECTOR)
        validate_transition(STATUS_NEEDS_REVISION, STATUS_RESUBMITTED, ACTOR_APPLICANT)
        validate_transition(STATUS_RESUBMITTED, STATUS_UNDER_REVIEW, ACTOR_PCC_ADMIN)

    def test_attorney_assignment_path(self):
        # BW-PMS-06: Approved -> Assignment Offered -> Attorney Assigned
        validate_transition(STATUS_APPROVED, STATUS_ASSIGNMENT_OFFERED, ACTOR_PCC_ADMIN)
        validate_transition(STATUS_ASSIGNMENT_OFFERED, STATUS_ATTORNEY_ASSIGNED, ACTOR_ATTORNEY)

    def test_withdrawal_before_filing_allowed(self):
        # BW-PMS-16: pre-filing withdrawal
        e = validate_transition(STATUS_SUBMITTED, STATUS_WITHDRAWN, ACTOR_APPLICANT)
        assert e.workflow_id == "BW-PMS-16"

    def test_withdrawal_after_filing_forbidden(self):
        with pytest.raises(InvalidTransitionError, match="Cannot withdraw in status 'filed'"):
            validate_transition(STATUS_FILED, STATUS_WITHDRAWN, ACTOR_APPLICANT)

    def test_unauthorized_actor_transition_refused(self):
        with pytest.raises(ActorNotAllowedError):
            validate_transition(STATUS_UNDER_REVIEW, STATUS_APPROVED, ACTOR_APPLICANT)
