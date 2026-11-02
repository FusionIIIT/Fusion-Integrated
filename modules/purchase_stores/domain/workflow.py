"""State transitions for purchase indents and their procurement lifecycle."""

from enum import StrEnum
from types import MappingProxyType


class IndentStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    STOCK_RESERVED = "STOCK_RESERVED"
    EXTERNAL_PROCUREMENT_REQUIRED = "EXTERNAL_PROCUREMENT_REQUIRED"
    DEPARTMENT_REVIEWED = "DEPARTMENT_REVIEWED"
    INTERNAL_ISSUE_APPROVED = "INTERNAL_ISSUE_APPROVED"
    DISPATCHED_READY_FOR_RECEIPT = "DISPATCHED_READY_FOR_RECEIPT"
    DEPARTMENT_HEAD_RECOMMENDED = "DEPARTMENT_HEAD_RECOMMENDED"
    AWAITING_FINAL_APPROVAL = "AWAITING_FINAL_APPROVAL"
    PROCUREMENT_AUTHORIZED = "PROCUREMENT_AUTHORIZED"
    PO_ISSUED = "PO_ISSUED"
    DELIVERED = "DELIVERED"
    GRN_ACCEPTED = "GRN_ACCEPTED"
    GRN_PARTIAL = "GRN_PARTIAL"
    RECEIPT_CONFIRMED = "RECEIPT_CONFIRMED"
    DISCREPANCY_IDENTIFIED = "DISCREPANCY_IDENTIFIED"
    DISCREPANCY_CASE_OPEN = "DISCREPANCY_CASE_OPEN"
    REPLACEMENT_AWAITED = "REPLACEMENT_AWAITED"
    REPLACEMENT_CONFIRMED = "REPLACEMENT_CONFIRMED"
    INVOICE_VERIFIED = "INVOICE_VERIFIED"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class InvalidTransition(ValueError):
    """The requested lifecycle transition is not permitted."""


_TRANSITIONS = {
    IndentStatus.DRAFT: {IndentStatus.SUBMITTED, IndentStatus.WITHDRAWN, IndentStatus.CANCELLED},
    IndentStatus.SUBMITTED: {
        IndentStatus.STOCK_RESERVED,
        IndentStatus.EXTERNAL_PROCUREMENT_REQUIRED,
        IndentStatus.WITHDRAWN,
        IndentStatus.CANCELLED,
        IndentStatus.REJECTED,
    },
    IndentStatus.STOCK_RESERVED: {
        IndentStatus.DEPARTMENT_REVIEWED,
        IndentStatus.WITHDRAWN,
        IndentStatus.CANCELLED,
        IndentStatus.REJECTED,
    },
    IndentStatus.EXTERNAL_PROCUREMENT_REQUIRED: {
        IndentStatus.DEPARTMENT_REVIEWED,
        IndentStatus.WITHDRAWN,
        IndentStatus.CANCELLED,
        IndentStatus.REJECTED,
    },
    IndentStatus.DEPARTMENT_REVIEWED: {
        IndentStatus.INTERNAL_ISSUE_APPROVED,
        IndentStatus.DEPARTMENT_HEAD_RECOMMENDED,
        IndentStatus.AWAITING_FINAL_APPROVAL,
        IndentStatus.PROCUREMENT_AUTHORIZED,
        IndentStatus.WITHDRAWN,
        IndentStatus.CANCELLED,
        IndentStatus.REJECTED,
    },
    IndentStatus.INTERNAL_ISSUE_APPROVED: {IndentStatus.DISPATCHED_READY_FOR_RECEIPT},
    IndentStatus.DISPATCHED_READY_FOR_RECEIPT: {
        IndentStatus.GRN_ACCEPTED,
        IndentStatus.GRN_PARTIAL,
        IndentStatus.RECEIPT_CONFIRMED,
        IndentStatus.DISCREPANCY_IDENTIFIED,
    },
    IndentStatus.DEPARTMENT_HEAD_RECOMMENDED: {
        IndentStatus.AWAITING_FINAL_APPROVAL,
        IndentStatus.PROCUREMENT_AUTHORIZED,
        IndentStatus.WITHDRAWN,
        IndentStatus.REJECTED,
    },
    IndentStatus.AWAITING_FINAL_APPROVAL: {
        IndentStatus.PROCUREMENT_AUTHORIZED,
        IndentStatus.REJECTED,
    },
    IndentStatus.PROCUREMENT_AUTHORIZED: {IndentStatus.PO_ISSUED},
    IndentStatus.PO_ISSUED: {IndentStatus.DELIVERED},
    IndentStatus.DELIVERED: {
        IndentStatus.GRN_ACCEPTED,
        IndentStatus.GRN_PARTIAL,
        IndentStatus.DISCREPANCY_IDENTIFIED,
    },
    IndentStatus.GRN_ACCEPTED: {
        IndentStatus.RECEIPT_CONFIRMED,
        IndentStatus.DISCREPANCY_IDENTIFIED,
        IndentStatus.DISCREPANCY_CASE_OPEN,
    },
    IndentStatus.GRN_PARTIAL: {
        IndentStatus.GRN_PARTIAL,
        IndentStatus.RECEIPT_CONFIRMED,
        IndentStatus.DISCREPANCY_IDENTIFIED,
    },
    IndentStatus.DISCREPANCY_IDENTIFIED: {IndentStatus.DISCREPANCY_CASE_OPEN},
    IndentStatus.DISCREPANCY_CASE_OPEN: {
        IndentStatus.REPLACEMENT_AWAITED,
        IndentStatus.RECEIPT_CONFIRMED,
    },
    IndentStatus.REPLACEMENT_AWAITED: {IndentStatus.REPLACEMENT_CONFIRMED},
    IndentStatus.REPLACEMENT_CONFIRMED: {IndentStatus.RECEIPT_CONFIRMED},
    IndentStatus.RECEIPT_CONFIRMED: {
        IndentStatus.INVOICE_VERIFIED,
        IndentStatus.DISCREPANCY_IDENTIFIED,
    },
    IndentStatus.INVOICE_VERIFIED: {IndentStatus.PAID, IndentStatus.PARTIALLY_PAID},
    IndentStatus.PARTIALLY_PAID: {IndentStatus.PAID},
}

ALLOWED_TRANSITIONS = MappingProxyType(
    {status: frozenset(targets) for status, targets in _TRANSITIONS.items()}
)


def validate_transition(
    from_status: str | IndentStatus,
    to_status: str | IndentStatus,
    reason: str = "",
) -> None:
    """Raise :class:`InvalidTransition` unless an explicitly listed edge applies."""
    try:
        source = IndentStatus(from_status)
        target = IndentStatus(to_status)
    except ValueError as exc:
        raise InvalidTransition("Unknown indent status.") from exc
    if target == IndentStatus.REJECTED and not reason.strip():
        raise InvalidTransition("A rejection reason is required.")
    if target not in ALLOWED_TRANSITIONS.get(source, frozenset()):
        raise InvalidTransition(f"Cannot move an indent from {source} to {target}.")
