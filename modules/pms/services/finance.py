from datetime import date
from decimal import Decimal
from django.db import transaction

from modules.pms.models.finance import PatentFinancialTransaction, PaymentStatus
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def record_transaction(
    app_id: int,
    user_id: int,
    transaction_type: str,
    amount: Decimal,
    reference_no: str,
    roles: list[str],
    description: str = "",
    effective_date: date | None = None,
) -> PatentFinancialTransaction:
    """Record an append-only expense transaction in the financial ledger (§2.7)."""
    app = get_application_scoped(app_id, user_id, roles)

    return PatentFinancialTransaction.objects.create(
        application=app,
        transaction_type=transaction_type,
        amount=amount,
        reference_no=reference_no,
        recorded_by_user_id=user_id,
        effective_date=effective_date or date.today(),
        description=description,
        payment_status=PaymentStatus.RECORDED,
    )


@transaction.atomic
def record_reversal(
    transaction_id: int,
    user_id: int,
    reason: str,
    roles: list[str],
) -> PatentFinancialTransaction:
    """Record an append-only reversing transaction for a previous ledger entry."""
    original = PatentFinancialTransaction.objects.get(pk=transaction_id)
    app = get_application_scoped(original.application_id, user_id, roles)

    original.payment_status = PaymentStatus.REVERSED
    original.save(update_fields=["payment_status", "updated_at"])

    return PatentFinancialTransaction.objects.create(
        application=app,
        transaction_type=original.transaction_type,
        amount=-original.amount,
        reference_no=f"REV-{original.reference_no}",
        recorded_by_user_id=user_id,
        effective_date=date.today(),
        description=f"Reversal of #{original.id}: {reason}",
        reversal_of_transaction_id=original.id,
        payment_status=PaymentStatus.RECONCILED,
    )
