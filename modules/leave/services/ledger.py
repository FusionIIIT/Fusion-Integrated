from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from modules.leave.models import LeaveBalance, LeaveCategory


@transaction.atomic
def ensure_balance(user_id: int, year: int, category: str, default_credited: Decimal = Decimal("0.0")) -> LeaveBalance:
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        year=year,
        category=category,
        defaults={"credited": default_credited, "availed": Decimal("0.0")},
    )
    return balance


@transaction.atomic
def credit_annual_entitlements(user_id: int, year: int, is_faculty: bool = True) -> dict[str, Decimal]:
    """
    BR-EL-002..006: Annual entitlement crediting.
    """
    credits = {
        LeaveCategory.CL: Decimal("8.0"),
        LeaveCategory.RH: Decimal("2.0"),
        LeaveCategory.SCL: Decimal("15.0"),
        LeaveCategory.COL: Decimal("20.0"),
    }
    if is_faculty:
        credits[LeaveCategory.VL] = Decimal("60.0")
    else:
        # Carry-forward non-faculty EL from previous year, capped at 300
        prev_el = LeaveBalance.objects.filter(
            user_id=user_id,
            year=year - 1,
            category=LeaveCategory.EL,
        ).first()
        carried = Decimal(str(prev_el.available_balance)) if prev_el else Decimal("0.0")
        new_credit = min(Decimal("300.0"), carried + Decimal("30.0"))
        credits[LeaveCategory.EL] = new_credit

    results = {}
    for cat, amount in credits.items():
        bal = ensure_balance(user_id, year, cat, default_credited=amount)
        if bal.credited < amount:
            bal.credited = amount
            bal.save(update_fields=["credited"])
        results[cat] = bal.available_balance

    return results


@transaction.atomic
def debit_balance(user_id: int, year: int, category: str, days: Decimal) -> LeaveBalance:
    """
    Deducts leave days from available balance upon final approval.
    """
    balance = ensure_balance(user_id, year, category)
    if Decimal(str(balance.available_balance)) < days:
        raise ValidationError({
            "balance": _(f"Insufficient {category} balance. Available: {balance.available_balance}, Requested: {days}")
        })
    balance.availed += days
    balance.save(update_fields=["availed"])
    return balance


@transaction.atomic
def refund_balance(user_id: int, year: int, category: str, days: Decimal) -> LeaveBalance:
    """
    Restores leave days upon cancellation or resumption adjustment.
    """
    balance = ensure_balance(user_id, year, category)
    balance.availed = max(Decimal("0.0"), balance.availed - days)
    balance.save(update_fields=["availed"])
    return balance


@transaction.atomic
def convert_vl_to_el(user_id: int, year: int) -> tuple[Decimal, Decimal]:
    """
    BR-EL-007, BR-EL-008: VL-to-EL year-end conversion.
    Converts unused VL at 2 VL : 1 EL into the faculty member's EL account, capped at 300.
    """
    vl_bal = LeaveBalance.objects.filter(
        user_id=user_id,
        year=year,
        category=LeaveCategory.VL,
    ).first()

    unavailed_vl = Decimal(str(vl_bal.available_balance)) if vl_bal else Decimal("0.0")
    converted_el = (unavailed_vl / Decimal("2.0")).quantize(Decimal("0.5"))

    next_el = ensure_balance(user_id, year + 1, LeaveCategory.EL)
    prev_el = LeaveBalance.objects.filter(
        user_id=user_id,
        year=year,
        category=LeaveCategory.EL,
    ).first()
    prev_el_avail = Decimal(str(prev_el.available_balance)) if prev_el else Decimal("0.0")

    total_el = min(Decimal("300.0"), prev_el_avail + converted_el)
    next_el.credited = total_el
    next_el.save(update_fields=["credited"])

    return unavailed_vl, converted_el
