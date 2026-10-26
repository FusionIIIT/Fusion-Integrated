"""Event-triggered year-end leave processing services (EL-UC-020 / CFR-EL-028)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from modules.elm.domain.constants import LeaveCategory, TransactionType
from modules.elm.domain.year_end import (
    YearEndAccountInput,
    calculate_year_end_outcome,
)
from modules.elm.models import (
    LeaveAccount,
    LeaveBalanceTransaction,
    YearEndRun,
)
from modules.elm.selectors.config import get_active_policy_config


@transaction.atomic
def execute_year_end_processing(
    year: int,
    executed_by_user_id: int | None = None,
) -> YearEndRun:
    """Execute year-end leave-account outcomes across all accounts (EL-UC-020, CFR-EL-028).

    Enforces:
    - BR-EL-002: CL lapse
    - BR-EL-003: RH lapse
    - BR-EL-004: SCL lapse
    - BR-EL-005: EL carry forward
    - BR-EL-007: Faculty VL-to-EL conversion at 2:1 including fractions, and VL lapse
    - BR-EL-008: Converted EL credited to EL balance and usable
    - BR-EL-009: COL carry forward
    """
    cfg = get_active_policy_config()
    next_year = year + 1

    accounts = LeaveAccount.objects.filter(year=year).order_by("user_id", "category")

    accounts_processed = 0
    cl_lapsed_count = 0
    rh_lapsed_count = 0
    scl_lapsed_count = 0
    vl_converted_count = 0
    total_el_credited_from_vl = Decimal("0.00")
    el_cf_count = 0
    col_cf_count = 0
    exceptions = []

    # Map user_id -> converted EL from VL
    user_vl_to_el_map: dict[int, Decimal] = {}

    for acc in accounts:
        try:
            accounts_processed += 1
            cat = acc.category
            bal = acc.balance

            # We treat faculty VL conversion specifically
            inp = YearEndAccountInput(
                user_id=acc.user_id,
                category=cat,
                balance=bal,
                is_faculty=(cat == LeaveCategory.VL.value),
            )
            outcome = calculate_year_end_outcome(inp)

            if cat == LeaveCategory.CL.value:
                if outcome.lapsed_amount > Decimal("0.00"):
                    acc.balance = Decimal("0.00")
                    acc.save(update_fields=["balance", "updated_at"])
                    cl_lapsed_count += 1
                    LeaveBalanceTransaction.objects.create(
                        user_id=acc.user_id,
                        leave_account=acc,
                        year=year,
                        category=cat,
                        transaction_type=TransactionType.YEAR_END_LAPSE.value,
                        amount=-outcome.lapsed_amount,
                        balance_after=Decimal("0.00"),
                        remarks=f"Year-end CL lapse for {year}",
                        performed_by_user_id=executed_by_user_id,
                    )

            elif cat == LeaveCategory.RH.value:
                if outcome.lapsed_amount > Decimal("0.00"):
                    acc.balance = Decimal("0.00")
                    acc.save(update_fields=["balance", "updated_at"])
                    rh_lapsed_count += 1
                    LeaveBalanceTransaction.objects.create(
                        user_id=acc.user_id,
                        leave_account=acc,
                        year=year,
                        category=cat,
                        transaction_type=TransactionType.YEAR_END_LAPSE.value,
                        amount=-outcome.lapsed_amount,
                        balance_after=Decimal("0.00"),
                        remarks=f"Year-end RH lapse for {year}",
                        performed_by_user_id=executed_by_user_id,
                    )

            elif cat == LeaveCategory.SCL.value:
                if outcome.lapsed_amount > Decimal("0.00"):
                    acc.balance = Decimal("0.00")
                    acc.save(update_fields=["balance", "updated_at"])
                    scl_lapsed_count += 1
                    LeaveBalanceTransaction.objects.create(
                        user_id=acc.user_id,
                        leave_account=acc,
                        year=year,
                        category=cat,
                        transaction_type=TransactionType.YEAR_END_LAPSE.value,
                        amount=-outcome.lapsed_amount,
                        balance_after=Decimal("0.00"),
                        remarks=f"Year-end SCL lapse for {year}",
                        performed_by_user_id=executed_by_user_id,
                    )

            elif cat == LeaveCategory.VL.value:
                if outcome.lapsed_amount > Decimal("0.00"):
                    acc.balance = Decimal("0.00")
                    acc.save(update_fields=["balance", "updated_at"])
                    vl_converted_count += 1
                    converted_el = outcome.converted_to_el_amount
                    total_el_credited_from_vl += converted_el
                    user_vl_to_el_map[acc.user_id] = converted_el

                    LeaveBalanceTransaction.objects.create(
                        user_id=acc.user_id,
                        leave_account=acc,
                        year=year,
                        category=cat,
                        transaction_type=TransactionType.VL_CONVERSION_LAPSE.value,
                        amount=-outcome.lapsed_amount,
                        balance_after=Decimal("0.00"),
                        remarks=f"Year-end VL conversion to EL for {year}",
                        performed_by_user_id=executed_by_user_id,
                    )

            elif cat == LeaveCategory.EL.value:
                cf = outcome.carried_forward_amount
                if cf > Decimal("0.00"):
                    el_cf_count += 1
                    # Ensure next year account has this carry forward
                    next_acc, _ = LeaveAccount.objects.get_or_create(
                        user_id=acc.user_id,
                        year=next_year,
                        category=LeaveCategory.EL.value,
                        defaults={
                            "credited": cfg.non_faculty_el_annual_credit,
                            "carried_forward": cf,
                            "availed": Decimal("0.00"),
                            "balance": cfg.non_faculty_el_annual_credit + cf,
                        },
                    )
                    if not _:
                        next_acc.carried_forward += cf
                        next_acc.balance += cf
                        next_acc.save(update_fields=["carried_forward", "balance", "updated_at"])

                    LeaveBalanceTransaction.objects.create(
                        user_id=acc.user_id,
                        leave_account=next_acc,
                        year=next_year,
                        category=LeaveCategory.EL.value,
                        transaction_type=TransactionType.CARRY_FORWARD.value,
                        amount=cf,
                        balance_after=next_acc.balance,
                        remarks=f"Carried forward EL from {year}",
                        performed_by_user_id=executed_by_user_id,
                    )

            elif cat == LeaveCategory.COL.value:
                cf = outcome.carried_forward_amount
                if cf > Decimal("0.00"):
                    col_cf_count += 1
                    next_acc, _ = LeaveAccount.objects.get_or_create(
                        user_id=acc.user_id,
                        year=next_year,
                        category=LeaveCategory.COL.value,
                        defaults={
                            "credited": cfg.col_annual_entitlement,
                            "carried_forward": cf,
                            "availed": Decimal("0.00"),
                            "balance": cfg.col_annual_entitlement + cf,
                        },
                    )
                    if not _:
                        next_acc.carried_forward += cf
                        next_acc.balance += cf
                        next_acc.save(update_fields=["carried_forward", "balance", "updated_at"])

                    LeaveBalanceTransaction.objects.create(
                        user_id=acc.user_id,
                        leave_account=next_acc,
                        year=next_year,
                        category=LeaveCategory.COL.value,
                        transaction_type=TransactionType.CARRY_FORWARD.value,
                        amount=cf,
                        balance_after=next_acc.balance,
                        remarks=f"Carried forward COL from {year}",
                        performed_by_user_id=executed_by_user_id,
                    )

        except Exception as exc:  # noqa: BLE001
            exceptions.append({
                "user_id": acc.user_id,
                "category": acc.category,
                "error": str(exc),
            })

    # Now apply converted EL from VL to next year's EL account (BR-EL-008)
    for uid, converted_el in user_vl_to_el_map.items():
        if converted_el > Decimal("0.00"):
            next_el_acc, _ = LeaveAccount.objects.get_or_create(
                user_id=uid,
                year=next_year,
                category=LeaveCategory.EL.value,
                defaults={
                    "credited": Decimal("0.00"),
                    "carried_forward": converted_el,
                    "availed": Decimal("0.00"),
                    "balance": converted_el,
                },
            )
            if not _:
                next_el_acc.balance += converted_el
                next_el_acc.carried_forward += converted_el
                next_el_acc.save(update_fields=["balance", "carried_forward", "updated_at"])

            LeaveBalanceTransaction.objects.create(
                user_id=uid,
                leave_account=next_el_acc,
                year=next_year,
                category=LeaveCategory.EL.value,
                transaction_type=TransactionType.VL_CONVERSION_CREDIT.value,
                amount=converted_el,
                balance_after=next_el_acc.balance,
                remarks=f"Credited converted EL from {year} VL (2:1 ratio)",
                performed_by_user_id=executed_by_user_id,
            )

    return YearEndRun.objects.create(
        year=year,
        accounts_processed=accounts_processed,
        cl_lapsed_count=cl_lapsed_count,
        rh_lapsed_count=rh_lapsed_count,
        scl_lapsed_count=scl_lapsed_count,
        vl_converted_count=vl_converted_count,
        total_el_credited_from_vl=total_el_credited_from_vl,
        el_carried_forward_count=el_cf_count,
        col_carried_forward_count=col_cf_count,
        exceptions=exceptions,
        executed_by_user_id=executed_by_user_id,
    )
