"""Leave balance management and year-end processing services (BR-EL-002..009)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from modules.elm.models import LeaveBalance


def get_or_create_default_balances(
    user_id: int, year: int = 2026, is_faculty: bool = False
) -> None:
    """Initialize annual entitlements for an employee if not present.

    CL: 8 days/year (all)
    RH: 2 days/year (all)
    SCL: 15 days/year (all)
    EL: 30 days/year (non-faculty / staff)
    VL: 60 days/year (faculty)
    COL: 20 days/year (all eligible)
    """
    defaults = {
        "CL": Decimal("8.0"),
        "RH": Decimal("2.0"),
        "SCL": Decimal("15.0"),
        "COL": Decimal("20.0"),
    }
    if is_faculty:
        defaults["VL"] = Decimal("60.0")
        defaults["EL"] = Decimal("0.0")
    else:
        defaults["EL"] = Decimal("30.0")
        defaults["VL"] = Decimal("0.0")

    for cat, cred in defaults.items():
        LeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=year,
            leave_category=cat,
            defaults={"credited": cred, "used": Decimal("0.0")},
        )


@transaction.atomic
def deduct_balance(user_id: int, category: str, days: Decimal, year: int = 2026) -> LeaveBalance:
    """Deduct approved leave days from balance."""
    bal, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        year=year,
        leave_category=category,
        defaults={"credited": Decimal("0.0"), "used": Decimal("0.0")},
    )
    bal.used += days
    bal.save(update_fields=["used", "updated_at"])
    return bal


@transaction.atomic
def restore_balance(user_id: int, category: str, days: Decimal, year: int = 2026) -> LeaveBalance:
    """Restore balance when approved leave is cancelled or early resumption occurs."""
    bal, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id,
        year=year,
        leave_category=category,
        defaults={"credited": Decimal("0.0"), "used": Decimal("0.0")},
    )
    bal.used = max(Decimal("0.0"), bal.used - days)
    bal.save(update_fields=["used", "updated_at"])
    return bal


@transaction.atomic
def execute_year_end_processing(current_year: int = 2026) -> dict[str, int]:
    """Execute year-end lapse, conversion, and carry-forward (BR-EL-002..008, EL-UC-020).

    - CL, RH, SCL lapse (unused does not carry forward)
    - Faculty VL converts to EL at 2 VL : 1 EL, including fractional conversion
    - EL and COL carry forward to next year
    """
    next_year = current_year + 1
    stats = {"lapsed": 0, "converted_vl": 0, "carried_forward": 0}

    # 1. Process CL, RH, SCL lapse
    lapsed_balances = LeaveBalance.objects.filter(
        year=current_year,
        leave_category__in=["CL", "RH", "SCL"],
    )
    for _b in lapsed_balances:
        # Lapsed: no carry forward
        stats["lapsed"] += 1

    # 2. Process VL to EL conversion (BR-EL-007, BR-EL-008)
    vl_balances = LeaveBalance.objects.filter(year=current_year, leave_category="VL")
    for vl in vl_balances:
        unused_vl = max(Decimal("0.0"), vl.available)
        converted_el = unused_vl / Decimal("2.0")

        # Credit converted EL to next year's EL balance
        el_next, _ = LeaveBalance.objects.get_or_create(
            user_id=vl.user_id,
            year=next_year,
            leave_category="EL",
            defaults={"credited": Decimal("0.0"), "used": Decimal("0.0")},
        )
        el_next.credited += converted_el
        el_next.save()
        stats["converted_vl"] += 1

    # 3. Process EL and COL carry forward (BR-EL-005, BR-EL-009)
    carry_balances = LeaveBalance.objects.filter(
        year=current_year,
        leave_category__in=["EL", "COL"],
    )
    for b in carry_balances:
        unused = max(Decimal("0.0"), b.available)
        next_bal, _ = LeaveBalance.objects.get_or_create(
            user_id=b.user_id,
            year=next_year,
            leave_category=b.leave_category,
            defaults={"credited": Decimal("0.0"), "used": Decimal("0.0")},
        )
        next_bal.credited += unused
        next_bal.save()
        stats["carried_forward"] += 1

    return stats
