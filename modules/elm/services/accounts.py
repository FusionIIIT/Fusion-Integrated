"""Internal, transactional operations for the ELM leave-account ledger.

Callers must authorize the requested business action before posting a ledger
entry. This module is not an API entry point.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import (
    TRANSACTION_TYPE_CHOICES,
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveBalance,
)

TRANSACTION_TYPES = {value for value, _label in TRANSACTION_TYPE_CHOICES}

POSITIVE_TYPES = {
    "annual_grant",
    "restoration",
    "carry_forward_in",
    "vl_conversion_in",
}

NEGATIVE_TYPES = {
    "leave_debit",
    "carry_forward_out",
    "lapse",
    "vl_conversion_out",
    "offline_sanction",
}


def _amount(value: Decimal | int | str) -> Decimal:
    """Validate a finite, nonzero amount with at most two decimal places."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as err:
        raise ConflictError(
            "Transaction amount must be a valid decimal.",
            code="invalid_amount",
        ) from err

    if not amount.is_finite() or amount == 0:
        raise ConflictError(
            "Transaction amount must be finite and nonzero.",
            code="invalid_amount",
        )

    try:
        if amount != amount.quantize(Decimal("0.01")):
            raise ConflictError(
                "Transaction amounts support at most two decimal places.",
                code="invalid_amount",
            )
    except InvalidOperation as err:
        raise ConflictError(
            "Transaction amount is outside the supported range.",
            code="invalid_amount",
        ) from err

    return amount


@transaction.atomic
def post_transaction(
    *,
    balance_id: int,
    delta: Decimal | int | str,
    transaction_type: str,
    effective_date: date,
    actor_user_id: int | None = None,
    application_id: int | None = None,
    reference: str = "",
    note: str = "",
) -> LeaveAccountTransaction:
    """Append a validated ledger entry without rewriting account history.

    Positive amounts increase the available balance; negative amounts
    decrease it. The balance row is locked so concurrent postings through
    this service cannot both spend the same available balance.
    """
    amount = _amount(delta)

    if transaction_type not in TRANSACTION_TYPES:
        raise ConflictError(
            f"Unknown transaction type: {transaction_type!r}.",
            code="invalid_transaction_type",
        )

    if transaction_type in POSITIVE_TYPES and amount < 0:
        raise ConflictError(
            f"{transaction_type} must increase the balance.",
            code="invalid_transaction_sign",
        )

    if transaction_type in NEGATIVE_TYPES and amount > 0:
        raise ConflictError(
            f"{transaction_type} must decrease the balance.",
            code="invalid_transaction_sign",
        )

    if not isinstance(effective_date, date):
        raise ConflictError(
            "A valid effective date is required.",
            code="invalid_effective_date",
        )

    clean_reference = (reference or "").strip()
    clean_note = (note or "").strip()

    if transaction_type == "manual_adjustment" and not clean_note:
        raise ConflictError(
            "Manual adjustments require an explanatory note.",
            code="note_required",
        )

    if transaction_type == "offline_sanction" and not clean_reference:
        raise ConflictError(
            "Offline sanctions require a sanction reference.",
            code="reference_required",
        )

    if transaction_type == "leave_debit" and application_id is None:
        raise ConflictError(
            "A leave debit must reference an approved leave application.",
            code="application_required",
        )

    # Lock the application before the balance to keep the lock order stable
    # for callers that post transactions against an application.
    application = None
    if application_id is not None:
        application = LeaveApplication.objects.select_for_update().filter(pk=application_id).first()
        if application is None:
            raise NotFoundError("Leave application not found.")

    balance = LeaveBalance.objects.select_for_update().filter(pk=balance_id).first()
    if balance is None:
        raise NotFoundError("Leave balance not found.")

    if application is not None and (
        application.user_id != balance.user_id or application.category != balance.category
    ):
        raise ConflictError(
            "Application employee and category must match the leave account.",
            code="application_account_mismatch",
        )

    if transaction_type == "leave_debit" and application.status != "approved":
        raise ConflictError(
            "Only an approved application can receive a leave debit.",
            code="application_not_approved",
        )

    available = balance.current_balance
    resulting_balance = available + amount

    if resulting_balance < 0:
        raise ConflictError(
            "Transaction would make the leave balance negative.",
            code="insufficient_balance",
        )

    return LeaveAccountTransaction.objects.create(
        balance=balance,
        application=application,
        delta=amount,
        transaction_type=transaction_type,
        effective_date=effective_date,
        actor_user_id=actor_user_id,
        reference=clean_reference,
        note=clean_note,
    )
