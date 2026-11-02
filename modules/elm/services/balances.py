"""Write services for leave balances and ledger transactions."""
from __future__ import annotations

from decimal import Decimal
from django.db import transaction

from modules.elm.domain.errors import InsufficientBalanceError
from modules.elm.models.balances import LeaveAccountTransaction, LeaveBalance
from modules.elm.selectors.balances import get_user_balance_for_category


DEFAULT_ANNUAL_ENTITLEMENTS: dict[str, Decimal] = {
    "CL": Decimal("8.00"),
    "RH": Decimal("2.00"),
    "SCL": Decimal("15.00"),
    "EL": Decimal("30.00"),
    "VL": Decimal("60.00"),
    "COL": Decimal("20.00"),
}


def seed_default_balances(user_id: int, year: int) -> list[LeaveBalance]:
    """Ensure baseline annual entitlements exist for a user in the given year."""
    balances = []
    with transaction.atomic():
        for cat, entitlement in DEFAULT_ANNUAL_ENTITLEMENTS.items():
            bal, created = LeaveBalance.objects.get_or_create(
                user_id=user_id,
                year=year,
                category=cat,
                defaults={
                    "credited_balance": entitlement,
                    "carried_forward": Decimal("0.00"),
                    "availed_balance": Decimal("0.00"),
                },
            )
            if created:
                LeaveAccountTransaction.objects.create(
                    user_id=user_id,
                    year=year,
                    category=cat,
                    transaction_type="credit",
                    days=entitlement,
                    remarks=f"Initial annual credit for {year}",
                )
            balances.append(bal)
    return balances


def deduct_balance(
    *,
    user_id: int,
    year: int,
    category: str,
    days: float,
    reason: str = "",
) -> LeaveBalance:
    """Atomically deduct availed leave days from a user's category balance."""
    dec_days = Decimal(str(days))
    with transaction.atomic():
        # Select for update to lock the row and avoid concurrent balance exhaustion
        try:
            bal = (
                LeaveBalance.objects.select_for_update()
                .get(user_id=user_id, year=year, category=category)
            )
        except LeaveBalance.DoesNotExist:
            # Seed on demand if record was not pre-populated
            seed_default_balances(user_id, year)
            bal = (
                LeaveBalance.objects.select_for_update()
                .get(user_id=user_id, year=year, category=category)
            )

        if bal.available_balance < dec_days:
            raise InsufficientBalanceError(
                f"Insufficient {category} balance: required {dec_days}, available {bal.available_balance}."
            )

        bal.availed_balance += dec_days
        bal.save(update_fields=["availed_balance", "updated_at"])

        LeaveAccountTransaction.objects.create(
            user_id=user_id,
            year=year,
            category=category,
            transaction_type="deduction",
            days=dec_days,
            remarks=reason or "Leave availed deduction",
        )
        return bal


def refund_balance(
    *,
    user_id: int,
    year: int,
    category: str,
    days: float,
    reason: str = "",
) -> LeaveBalance:
    """Atomically refund leave days upon cancellation or withdrawal of approved leave."""
    dec_days = Decimal(str(days))
    with transaction.atomic():
        bal = (
            LeaveBalance.objects.select_for_update()
            .get(user_id=user_id, year=year, category=category)
        )
        bal.availed_balance = max(Decimal("0.00"), bal.availed_balance - dec_days)
        bal.save(update_fields=["availed_balance", "updated_at"])

        LeaveAccountTransaction.objects.create(
            user_id=user_id,
            year=year,
            category=category,
            transaction_type="refund",
            days=dec_days,
            remarks=reason or "Leave cancellation refund",
        )
        return bal
