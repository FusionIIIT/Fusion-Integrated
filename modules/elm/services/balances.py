"""Balance management, entitlement credits, and year-end processing.

Directly implements:
- BR-EL-006: CL strictly non-accumulative, zero carry-forward
- BR-EL-007: Non-faculty EL entitlement 30 days/yr, accumulative up to 300 days
- BR-EL-008: Faculty VL 60 days/yr, converts to EL at 2:1 ratio at year-end
- BR-EL-009: COL 20 days/yr, max balance 20 days
- BR-EL-031: RH strictly non-accumulative, max 2 days/yr
"""
from __future__ import annotations

from decimal import Decimal
from django.db import transaction

from modules.elm.domain.leave_policy import (
    CL,
    COL,
    COL_MAX_BALANCE,
    COL_PER_YEAR,
    CL_PER_YEAR,
    EL,
    EL_MAX_ACCUMULATION,
    NON_FACULTY_EL_PER_YEAR,
    RH,
    RH_PER_YEAR,
    SCL,
    SCL_MAX_PER_YEAR,
    VACATION_TO_EL_RATIO,
    VL,
    FACULTY_VL_DAYS,
)
from modules.elm.models import LeaveBalance


def get_or_create_balance(user_id: int, category: str, year: int) -> LeaveBalance:
    """Fetch or initialize a LeaveBalance row for user/category/year."""
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={
            "credited": Decimal("0.0"),
            "used": Decimal("0.0"),
            "carried_forward": Decimal("0.0"),
        },
    )
    return balance


@transaction.atomic
def credit_annual_entitlement(
    user_id: int,
    year: int,
    is_faculty: bool = False,
) -> dict[str, LeaveBalance]:
    """Credit initial annual leave quotas for an employee at start of year."""
    balances = {}

    # CL
    cl_bal = get_or_create_balance(user_id, CL, year)
    cl_bal.credited = Decimal(str(CL_PER_YEAR))
    cl_bal.save()
    balances[CL] = cl_bal

    # RH
    rh_bal = get_or_create_balance(user_id, RH, year)
    rh_bal.credited = Decimal(str(RH_PER_YEAR))
    rh_bal.save()
    balances[RH] = rh_bal

    # SCL quota
    scl_bal = get_or_create_balance(user_id, SCL, year)
    scl_bal.credited = Decimal(str(SCL_MAX_PER_YEAR))
    scl_bal.save()
    balances[SCL] = scl_bal

    if is_faculty:
        # Faculty gets 60 days VL
        vl_bal = get_or_create_balance(user_id, VL, year)
        vl_bal.credited = Decimal(str(FACULTY_VL_DAYS))
        vl_bal.save()
        balances[VL] = vl_bal

        # Faculty starts with 0 new credited EL (EL comes from conversion or prior balance)
        el_bal = get_or_create_balance(user_id, EL, year)
        el_bal.save()
        balances[EL] = el_bal
    else:
        # Non-faculty gets 30 days EL
        el_bal = get_or_create_balance(user_id, EL, year)
        el_bal.credited = Decimal(str(NON_FACULTY_EL_PER_YEAR))
        el_bal.save()
        balances[EL] = el_bal

        # COL: Non-faculty gets 20 days COL
        col_bal = get_or_create_balance(user_id, COL, year)
        col_bal.credited = Decimal(str(COL_PER_YEAR))
        col_bal.save()
        balances[COL] = col_bal

    return balances


@transaction.atomic
def process_year_end_rollover(
    user_id: int,
    from_year: int,
    to_year: int,
    is_faculty: bool = False,
) -> dict[str, LeaveBalance]:
    """Execute year-end rollover and conversion from from_year to to_year.

    Rules applied:
    - CL & RH: Zero carry forward (lapses completely).
    - EL (Non-faculty): Unused balance carries forward, capped at 300.
    - VL (Faculty): Unused VL converts to EL at 2:1 ratio (2 VL = 1 EL).
      Converted EL is added to carry-forward EL, capped at 300.
    - COL (Non-faculty): Carried forward up to COL_MAX_BALANCE (20 days).
    """
    new_balances = credit_annual_entitlement(user_id, to_year, is_faculty=is_faculty)

    # 1. EL Rollover
    old_el = LeaveBalance.objects.filter(user_id=user_id, category=EL, year=from_year).first()
    el_carried = Decimal("0.0")
    if old_el:
        el_available = max(Decimal("0.0"), old_el.credited + old_el.carried_forward - old_el.used)
        el_carried = el_available

    # 2. Faculty VL to EL conversion (BR-EL-008)
    if is_faculty:
        old_vl = LeaveBalance.objects.filter(user_id=user_id, category=VL, year=from_year).first()
        if old_vl:
            vl_unused = max(Decimal("0.0"), old_vl.credited + old_vl.carried_forward - old_vl.used)
            # 2 days of VL convert to 1 day of EL
            el_from_vl = Decimal(str(float(vl_unused) / VACATION_TO_EL_RATIO))
            el_carried += el_from_vl

    # Cap EL at 300 days (BR-EL-007)
    el_carried = min(el_carried, Decimal(str(EL_MAX_ACCUMULATION)))
    el_target = new_balances[EL]
    el_target.carried_forward = el_carried
    el_target.save()
    new_balances[EL] = el_target

    # 3. COL Rollover (Non-faculty)
    if not is_faculty:
        old_col = LeaveBalance.objects.filter(user_id=user_id, category=COL, year=from_year).first()
        if old_col:
            col_available = max(Decimal("0.0"), old_col.credited + old_col.carried_forward - old_col.used)
            col_carried = min(col_available, Decimal(str(COL_MAX_BALANCE)))
            col_target = new_balances[COL]
            col_target.carried_forward = col_carried
            col_target.save()
            new_balances[COL] = col_target

    return new_balances


@transaction.atomic
def deduct_leave_balance(user_id: int, category: str, year: int, days: Decimal) -> LeaveBalance:
    """Deduct days from user balance."""
    bal = get_or_create_balance(user_id, category, year)
    bal.used += days
    bal.save()
    return bal


@transaction.atomic
def refund_leave_balance(user_id: int, category: str, year: int, days: Decimal) -> LeaveBalance:
    """Refund days back to user balance (e.g. upon cancellation or early resumption)."""
    bal = get_or_create_balance(user_id, category, year)
    bal.used = max(Decimal("0.0"), bal.used - days)
    bal.save()
    return bal
