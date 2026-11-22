"""Pure Python domain validation rules for Institute Accounts and Audits."""

from decimal import Decimal


class DomainValidationError(Exception):
    def __init__(self, message: str, code: str = "validation_error"):
        super().__init__(message)
        self.message = message
        self.code = code


def validate_segregation_of_duties(creator_id: int, approver_id: int) -> None:
    """IAA-BR-001: A creator/claimant must not approve the same request or claim."""
    if creator_id == approver_id:
        raise DomainValidationError(
            "Creator or claimant cannot approve their own financial request or claim.",
            code="segregation_of_duties_violation",
        )


def validate_decision_remarks(remarks: str | None) -> None:
    """IAA-BR-005: Every approval or rejection decision must record non-empty remarks."""
    if not remarks or not remarks.strip():
        raise DomainValidationError(
            "Decision remarks are mandatory and cannot be blank.",
            code="remarks_required",
        )


def validate_request_completeness(
    title: str | None,
    description: str | None,
    department: str | None,
    total_amount: Decimal | None,
    items_count: int,
) -> None:
    """IAA-BR-101: Formal submission requires all mandatory fields and at least one item."""
    if not title or not title.strip():
        raise DomainValidationError("Request title is mandatory for formal submission.")
    if not department or not department.strip():
        raise DomainValidationError("Department is mandatory for formal submission.")
    if total_amount is None or total_amount <= Decimal("0"):
        raise DomainValidationError("Total amount must be greater than zero.")
    if items_count < 1:
        raise DomainValidationError(
            "At least one expense line item is required for formal submission."
        )


def validate_travel_completeness(
    purpose: str | None,
    departure_date: str | None,
    arrival_date: str | None,
    claimed_amount: Decimal | None,
    source_location: str | None,
    destination_location: str | None,
) -> None:
    """IAA-BR-101 & IAA-BR-201: Mandatory travel claim fields validation."""
    if not purpose or not purpose.strip():
        raise DomainValidationError("Travel purpose is mandatory.")
    if not departure_date or not arrival_date:
        raise DomainValidationError("Departure and arrival dates are mandatory.")
    if str(arrival_date) < str(departure_date):
        raise DomainValidationError("Arrival date cannot be earlier than departure date.")
    if not source_location or not destination_location:
        raise DomainValidationError("Source and destination locations are mandatory.")
    if claimed_amount is None or claimed_amount <= Decimal("0"):
        raise DomainValidationError("Claimed amount must be greater than zero.")


def is_high_value_ta(claimed_amount: Decimal, threshold: Decimal) -> bool:
    """IAA-BR-202: Determines if travel claim meets configured high-value criteria."""
    return claimed_amount >= threshold


def check_budget_sufficiency(available_budget: Decimal, requested_amount: Decimal) -> bool:
    """IAA-BR-102: Validates budget availability."""
    return available_budget >= requested_amount


def validate_record_not_locked(is_locked: bool) -> None:
    """IAA-BR-104: Block ordinary creator editing when record is locked."""
    if is_locked:
        raise DomainValidationError(
            "This record is locked against direct editing after formal submission.",
            code="record_locked",
        )
