"""Leave balance modification services."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError
from modules.elm.domain.constants import LeaveCategory, TransactionType
from modules.elm.models import LeaveAccount, LeaveBalanceTransaction
from modules.elm.selectors.config import get_active_policy_config


@transaction.atomic
def ensure_leave_accounts_for_user(user_id: int, year: int, user_kind: str) -> None:
    """Ensure baseline leave accounts exist for a user in a year."""
    cfg = get_active_policy_config()

    # Determine default entitlements
    defaults_map = {
        LeaveCategory.CL.value: cfg.cl_annual_entitlement,
        LeaveCategory.RH.value: cfg.rh_annual_entitlement,
        LeaveCategory.SCL.value: cfg.scl_annual_limit,
        LeaveCategory.COL.value: cfg.col_annual_entitlement,
    }

    if user_kind == "faculty":
        defaults_map[LeaveCategory.VL.value] = cfg.faculty_vl_annual_entitlement
        # Faculty may also have EL from previous conversion, default 0
        defaults_map[LeaveCategory.EL.value] = Decimal("0.00")
    else:
        # Non-faculty receives 30 EL
        defaults_map[LeaveCategory.EL.value] = cfg.non_faculty_el_annual_credit

    for cat, credited in defaults_map.items():
        account, created = LeaveAccount.objects.get_or_create(
            user_id=user_id,
            year=year,
            category=cat,
            defaults={
                "credited": credited,
                "carried_forward": Decimal("0.00"),
                "availed": Decimal("0.00"),
                "balance": credited,
            },
        )
        if created and credited > Decimal("0.00"):
            LeaveBalanceTransaction.objects.create(
                user_id=user_id,
                leave_account=account,
                year=year,
                category=cat,
                transaction_type=TransactionType.ANNUAL_CREDIT.value,
                amount=credited,
                balance_after=credited,
                remarks="Initial annual leave credit",
            )


@transaction.atomic
def debit_leave_balance(
    user_id: int,
    year: int,
    category: str,
    amount: Decimal,
    *,
    reference_id: str = "",
    remarks: str = "",
    performed_by_user_id: int | None = None,
    transaction_type: str = TransactionType.DEBIT_AVAIL.value,
) -> LeaveAccount:
    """Debit days from a user's leave account upon approval."""
    acc = LeaveAccount.objects.select_for_update().filter(
        user_id=user_id, year=year, category=category
    ).first()

    if not acc:
        raise BadRequestError(
            f"No leave account found for user {user_id}, category {category}, year {year}."
        )

    if acc.balance < amount:
        raise BadRequestError(
            f"Insufficient balance in {category} account. Available: {acc.balance}, "
            f"Debit: {amount}."
        )

    acc.availed += amount
    acc.balance -= amount
    acc.save(update_fields=["availed", "balance", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        leave_account=acc,
        year=year,
        category=category,
        transaction_type=transaction_type,
        amount=-amount,
        balance_after=acc.balance,
        reference_id=reference_id,
        remarks=remarks,
        performed_by_user_id=performed_by_user_id,
    )
    return acc


@transaction.atomic
def credit_leave_balance(
    user_id: int,
    year: int,
    category: str,
    amount: Decimal,
    *,
    transaction_type: str = TransactionType.RESTORE_CANCELLATION.value,
    reference_id: str = "",
    remarks: str = "",
    performed_by_user_id: int | None = None,
) -> LeaveAccount:
    """Credit days back into an account (e.g. cancellation restore or early resumption)."""
    acc = LeaveAccount.objects.select_for_update().filter(
        user_id=user_id, year=year, category=category
    ).first()

    if not acc:
        raise BadRequestError(
            f"No leave account found for user {user_id}, category {category}, year {year}."
        )

    if transaction_type == TransactionType.RESTORE_CANCELLATION.value:
        acc.availed = max(Decimal("0.00"), acc.availed - amount)
    acc.balance += amount
    acc.save(update_fields=["availed", "balance", "updated_at"])

    LeaveBalanceTransaction.objects.create(
        user_id=user_id,
        leave_account=acc,
        year=year,
        category=category,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=acc.balance,
        reference_id=reference_id,
        remarks=remarks,
        performed_by_user_id=performed_by_user_id,
    )
    return acc
