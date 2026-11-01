"""Pure Python domain errors for PHC.

Must never import Django, DRF or Celery (enforced by import-linter).
"""


class PhcDomainError(Exception):
    """Base error for all PHC domain rule violations."""


class IneligibleClaimantError(PhcDomainError):
    """PHC-BR-04 / AFR-PHC-013: Only institute employees may submit reimbursement claims."""


class PrescriptionRequiredError(PhcDomainError):
    """PHC-BR-05 / AFR-PHC-014: Claim must be linked to a valid prescription for the claimant."""


class SubmissionWindowExpiredError(PhcDomainError):
    """PHC-BR-06 / AFR-PHC-015: Claim must be submitted within the configured submission window."""


class InvalidStateTransitionError(PhcDomainError):
    """PHC-BR-08 / CW-PHC-01 / CW-PHC-02: Workflow step does not match required state progression."""


class ClaimImmutableError(PhcDomainError):
    """PHC-BR-14 / AFR-PHC-038: Submitted/rejected claims cannot be modified or reopened in-place."""


class UnauthorizedRecordAccessError(PhcDomainError):
    """PHC-BR-02 / AFR-PHC-012: Patient may access only their own medical records."""


class InsufficientStockError(PhcDomainError):
    """Stock deduction cannot exceed current available stock."""


class RequisitionNotApprovedError(PhcDomainError):
    """PHC-BR-10: Procurement requisition must be approved before fulfillment."""
