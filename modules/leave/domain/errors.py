"""Leave domain errors — no Django imports."""
from typing import Optional


class LeaveDomainError(Exception):
    """Base exception for leave domain errors."""
    def __init__(self, message: str, code: str = "leave_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class InsufficientBalanceError(LeaveDomainError):
    def __init__(self, category: str, available: float, requested: float):
        super().__init__(
            f"Insufficient {category} balance: {available} available, {requested} requested",
            "insufficient_balance",
        )


class OverlappingLeaveError(LeaveDomainError):
    def __init__(self):
        super().__init__(
            "Leave request overlaps with existing pending or approved leave",
            "overlapping_leave",
        )


class InvalidTransitionError(LeaveDomainError):
    def __init__(self, from_status: str, to_status: str, category: str):
        super().__init__(
            f"Invalid transition from {from_status} to {to_status} for {category}",
            "invalid_transition",
        )


class SubstituteRequiredError(LeaveDomainError):
    def __init__(self):
        super().__init__(
            "Substitute nomination is required for this leave category",
            "substitute_required",
        )


class SubstituteNotEligibleError(LeaveDomainError):
    def __init__(self, reason: str):
        super().__init__(
            f"Substitute not eligible: {reason}",
            "substitute_not_eligible",
        )


class SubstituteConsentRequiredError(LeaveDomainError):
    def __init__(self):
        super().__init__(
            "Substitute consent is required before approval can proceed",
            "substitute_consent_required",
        )


class MedicalCertificateRequiredError(LeaveDomainError):
    def __init__(self):
        super().__init__(
            "Medical certificate is required for this leave category",
            "medical_certificate_required",
        )


class LeavePolicyNotFoundError(LeaveDomainError):
    def __init__(self, category: str, employee_type: str):
        super().__init__(
            f"No leave policy found for {category} ({employee_type})",
            "policy_not_found",
        )


class HolidayCalendarNotFoundError(LeaveDomainError):
    def __init__(self, date_str: str):
        super().__init__(
            f"No holiday calendar entry for {date_str}",
            "holiday_not_found",
        )


class YearEndProcessingError(LeaveDomainError):
    def __init__(self, message: str):
        super().__init__(message, "year_end_processing_error")