"""Specification-derived leave validation and exact arithmetic.

The spec lists six leave types and requires a balance/eligibility check,
but supplies no numerical allocations or accrual policy. The caller must
provide verified policy outcomes; missing values are a refusal, not a grant.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

LEAVE_TYPES = frozenset(
    {
        "Casual",
        "Restricted",
        "Medical",
        "Earned",
        "Vacation",
        "Sabbatical",
    }
)


class InvalidLeaveRequest(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidatedLeave:
    leave_type: str
    duration: Decimal
    justification: str


def ledger_balance(entries: Iterable[Decimal]) -> Decimal:
    """Sum immutable credits/debits/reversals without float arithmetic."""
    total = Decimal("0")
    for value in entries:
        if not isinstance(value, Decimal) or not value.is_finite():
            raise InvalidLeaveRequest(
                "invalid_entry", "Leave ledger entries must be finite decimals."
            )
        total += value
    return total


def validate_submission(
    leave_type: str,
    duration: Decimal,
    justification: str,
    *,
    available_balance: Decimal | None,
    is_eligible: bool | None,
) -> ValidatedLeave:
    if leave_type not in LEAVE_TYPES:
        raise InvalidLeaveRequest("unsupported_leave_type", "Choose a supported leave type.")
    if not isinstance(duration, Decimal) or not duration.is_finite() or duration <= 0:
        raise InvalidLeaveRequest("invalid_duration", "Enter a positive finite leave duration.")
    if not isinstance(justification, str) or not justification.strip():
        raise InvalidLeaveRequest("missing_justification", "Explain the reason for your leave.")
    if available_balance is None or is_eligible is None:
        raise InvalidLeaveRequest(
            "policy_unavailable", "Leave balance or eligibility policy is not configured."
        )
    if not isinstance(available_balance, Decimal) or not available_balance.is_finite():
        raise InvalidLeaveRequest("invalid_balance", "The leave balance cannot be verified.")
    if is_eligible is not True:
        raise InvalidLeaveRequest(
            "ineligible", "This leave type is not available under your policy."
        )
    if available_balance < duration:
        raise InvalidLeaveRequest(
            "insufficient_balance", "There is not enough leave balance available."
        )
    return ValidatedLeave(leave_type, duration, justification.strip())
