"""Transactional leave balance operations."""

from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction

from modules.elm.models import LeaveBalance, LeaveLedgerEntry


class LeaveBalanceError(ValueError):
    """Raised when a leave balance operation is invalid."""


def _positive_amount(value) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise LeaveBalanceError("Amount must be a valid decimal.") from exc

    if not amount.is_finite() or amount <= 0:
        raise LeaveBalanceError("Amount must be greater than zero.")

    if amount != amount.quantize(Decimal("0.01")):
        raise LeaveBalanceError("Amount may have at most two decimal places.")

    return amount


def _available(balance: LeaveBalance) -> Decimal:
    return (
        balance.opening_balance
        + balance.annual_entitlement
        + balance.accrued
        - balance.used
    )

def _existing_reference(
    *,
    balance: LeaveBalance,
    entry_type: str,
    amount: Decimal,
    reference_key: str,
) -> LeaveLedgerEntry | None:
    """Return a matching prior entry or reject conflicting reference reuse."""
    if not reference_key:
        return None

    existing = LeaveLedgerEntry.objects.filter(
        balance=balance,
        reference_key=reference_key,
    ).first()

    if existing is None:
        return None

    if existing.entry_type != entry_type or existing.amount != amount:
        raise LeaveBalanceError(
            "This reference key was already used for a different transaction."
        )

    return existing
@transaction.atomic
def post_balance_entry(
    *,
    balance_id: int,
    entry_type: str,
    amount,
    reference_key: str = "",
    description: str = "",
    actor_user_id: int | None = None,
) -> LeaveLedgerEntry:
    """Post a credit, debit, or adjustment atomically.

    Positive amounts represent the magnitude of the transaction. Debits
    increase `used`; credits and positive adjustments increase `accrued`.
    Conversions must use `convert_unused_vl_to_el()` below.
    """
    amount = _positive_amount(amount)

    if entry_type not in {"credit", "debit", "adjustment"}:
        raise LeaveBalanceError("Unsupported entry type for this operation.")

    balance = (
        LeaveBalance.objects.select_for_update()
        .filter(pk=balance_id)
        .first()
    )
    if balance is None:
        raise LeaveBalanceError("Leave balance was not found.")
    existing = _existing_reference(
    balance=balance,
    entry_type=entry_type,
    amount=amount,
    reference_key=reference_key,
    )
    if existing is not None:
        return existing
    if entry_type == "debit":
        if _available(balance) < amount:
            raise LeaveBalanceError("Insufficient leave balance.")
        balance.used += amount
    elif entry_type == "credit":
        balance.accrued += amount
    else:
        # Adjustment amounts are positive credits in this initial API.
        balance.accrued += amount

    balance.save(update_fields=["accrued", "used", "updated_at"])

    return LeaveLedgerEntry.objects.create(
        balance=balance,
        entry_type=entry_type,
        amount=amount,
        reference_key=reference_key,
        description=description,
        actor_user_id=actor_user_id,
    )


@transaction.atomic
def convert_vl_balance_to_el(
    *,
    vl_balance_id: int,
    el_balance_id: int,
    reference_key: str,
    actor_user_id: int | None = None,
) -> LeaveLedgerEntry:
    """Convert the available VL balance to EL once per reference key.

    The caller supplies a stable year-end reference, for example
    `vl-to-el:2026:user:123`. Both balances are locked before mutation.
    """
    if not reference_key.strip():
        raise LeaveBalanceError("A conversion reference key is required.")

    vl = (
        LeaveBalance.objects.select_for_update()
        .filter(pk=vl_balance_id, leave_type="VL")
        .first()
    )
    el = (
        LeaveBalance.objects.select_for_update()
        .filter(pk=el_balance_id, leave_type="EL")
        .first()
    )

    if vl is None or el is None:
        raise LeaveBalanceError("Matching VL and EL balances are required.")
    if vl.user_id != el.user_id or vl.leave_year != el.leave_year:
        raise LeaveBalanceError("VL and EL balances must belong to the same user and year.")

    existing = LeaveLedgerEntry.objects.filter(
        balance=el,
        entry_type="conversion",
        reference_key=reference_key,
    ).first()
    if existing:
        return existing

    unused_vl = _available(vl)
    if unused_vl < 0:
        raise LeaveBalanceError("VL balance cannot be negative.")

    amount = (unused_vl / Decimal("2")).quantize(Decimal("0.01"))
    if amount <= 0:
        raise LeaveBalanceError("No unused VL is available for conversion.")

    # Record the VL conversion debit and EL conversion credit together.
    vl.used += unused_vl
    el.accrued += amount
    vl.save(update_fields=["used", "updated_at"])
    el.save(update_fields=["accrued", "updated_at"])

    LeaveLedgerEntry.objects.create(
        balance=vl,
        entry_type="conversion",
        amount=unused_vl,
        reference_key=reference_key,
        description="Unused VL converted to EL (VL side)",
        actor_user_id=actor_user_id,
    )
    try:
        return LeaveLedgerEntry.objects.create(
            balance=el,
            entry_type="conversion",
            amount=amount,
            reference_key=reference_key,
            description="Unused VL converted to EL at 2:1 ratio",
            actor_user_id=actor_user_id,
        )
    except IntegrityError:
        # A concurrent retry must not silently create a second credit.
        # Raising rolls back both balance changes in this transaction.
        raise LeaveBalanceError("This conversion has already been recorded.") from None
