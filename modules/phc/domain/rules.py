"""Pure Python domain evaluation rules.

Enforces business rules BR-04, BR-05, BR-06, BR-07, BR-14.
Zero Django / DRF imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .entities import ReimbursementStatus, StockThresholdEvaluation
from .errors import (
    ClaimImmutableError,
    IneligibleClaimantError,
    PrescriptionRequiredError,
    SubmissionWindowExpiredError,
)


@dataclass(frozen=True)
class ClaimantEligibilityResult:
    is_eligible: bool
    reason: str = ""


@dataclass(frozen=True)
class PrescriptionRequirementResult:
    is_eligible: bool
    reason: str = ""


@dataclass(frozen=True)
class SubmissionWindowResult:
    is_eligible: bool
    days_elapsed: int = 0
    reason: str = ""


@dataclass(frozen=True)
class ClaimImmutabilityResult:
    is_editable: bool
    reason: str = ""


def evaluate_claimant_eligibility(user_role: str) -> ClaimantEligibilityResult:
    """PHC-BR-04: Student reimbursement exclusion.
    
    Students are strictly ineligible for PHC medical reimbursements.
    Employees (Faculty, Staff, Compounder, PHC Admin, etc.) are eligible.
    """
    normalized_role = user_role.lower().strip()
    if normalized_role in {"student", "student_role"}:
        return ClaimantEligibilityResult(
            is_eligible=False,
            reason="Students are ineligible for medical reimbursements (PHC-BR-04).",
        )
    return ClaimantEligibilityResult(is_eligible=True)


def evaluate_prescription_requirement(
    prescription_id: Optional[int],
    claimant_user_id: int,
    prescription_patient_user_id: Optional[int],
) -> PrescriptionRequirementResult:
    """PHC-BR-05: Mandatory linked prescription.
    
    Claims must be backed by a recorded prescription issued to the claimant.
    """
    if not prescription_id:
        return PrescriptionRequirementResult(
            is_eligible=False,
            reason="A recorded prescription is strictly required to claim reimbursement (PHC-BR-05).",
        )
    if prescription_patient_user_id is None or prescription_patient_user_id != claimant_user_id:
        return PrescriptionRequirementResult(
            is_eligible=False,
            reason="Prescription does not belong to the submitting claimant (PHC-BR-05).",
        )
    return PrescriptionRequirementResult(is_eligible=True)


def evaluate_submission_window(
    expense_date: date,
    current_date: date,
    window_days: int = 90,
) -> SubmissionWindowResult:
    """PHC-BR-06: 90-day submission window limit.
    
    Claims submitted more than 90 days after expense incurred are rejected.
    """
    days_elapsed = (current_date - expense_date).days
    if days_elapsed > window_days:
        return SubmissionWindowResult(
            is_eligible=False,
            days_elapsed=days_elapsed,
            reason=f"Claim submission window of {window_days} days expired ({days_elapsed} days elapsed) (PHC-BR-06).",
        )
    return SubmissionWindowResult(is_eligible=True, days_elapsed=days_elapsed)


def evaluate_claim_immutability(current_status: ReimbursementStatus) -> ClaimImmutabilityResult:
    """PHC-BR-14: Immutability of submitted / rejected claims.
    
    Submitted claims cannot be modified in-flight. Rejected claims are terminal
    and cannot be resubmitted; a new claim must be submitted.
    """
    if current_status in {
        ReimbursementStatus.PENDING_PHC_REVIEW,
        ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION,
        ReimbursementStatus.PENDING_SANCTION,
        ReimbursementStatus.APPROVED_FOR_PAYMENT,
        ReimbursementStatus.REJECTED,
        ReimbursementStatus.REIMBURSED,
    }:
        return ClaimImmutabilityResult(
            is_editable=False,
            reason=f"Claim in state '{current_status}' is immutable (PHC-BR-14).",
        )
    return ClaimImmutabilityResult(is_editable=True)


def evaluate_stock_threshold(
    current_stock: int,
    reorder_threshold: int,
    item_code: str = "MED",
) -> StockThresholdEvaluation:
    """PHC-BR-07: Low stock alert threshold calculation."""
    return StockThresholdEvaluation(
        item_code=item_code,
        current_stock=current_stock,
        reorder_threshold=reorder_threshold,
    )
