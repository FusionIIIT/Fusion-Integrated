"""Year-end leave lapse, carry-forward, and VL conversion service."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from django.db import transaction

from modules.leave.domain.rules import convert_vl_to_el
from modules.leave.models import LedgerEntry
from modules.leave.selectors.balances import get_user_balance
from modules.leave.selectors.policy import get_active_policy


def run_year_end_processing(
    year: int,
    user_ids: Sequence[int] | None = None,
    faculty_user_ids: Sequence[int] | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Executes year-end leave balance conversion and lapse under EL-UC-020."""
    if user_ids is None:
        user_ids = list(
            LedgerEntry.objects.filter(year=year).values_list("user_id", flat=True).distinct()
        )

    fac_set = set(faculty_user_ids or [])
    policy = get_active_policy()
    ratio = policy.vl_to_el_ratio if policy else Decimal("2.0")

    summary = {"users_processed": 0, "entries_created": 0}

    with transaction.atomic():
        for uid in user_ids:
            summary["users_processed"] += 1

            # 1. Faculty VL conversion to EL under BR-EL-007
            if uid in fac_set:
                vl_balance = get_user_balance(uid, year, "VL")
                if vl_balance > Decimal("0"):
                    el_credit = convert_vl_to_el(vl_balance, ratio)
                    # Deduct remaining VL
                    LedgerEntry.objects.create(
                        user_id=uid,
                        year=year,
                        category="VL",
                        days=-vl_balance,
                        reason="vl_conversion",
                        note=f"Year-end VL conversion for {year}",
                    )
                    # Credit converted EL in next year
                    LedgerEntry.objects.create(
                        user_id=uid,
                        year=year + 1,
                        category="EL",
                        days=el_credit,
                        reason="vl_to_el_conversion",
                        note=f"EL credited from {year} VL conversion",
                    )
                    summary["entries_created"] += 2

            # 2. EL and COL carry forward to next year under BR-EL-005, BR-EL-009
            for cat in ("EL", "COL"):
                bal = get_user_balance(uid, year, cat)
                if bal > Decimal("0"):
                    # Check if already carried forward
                    exists = LedgerEntry.objects.filter(
                        user_id=uid, year=year + 1, category=cat, reason="carry_forward"
                    ).exists()
                    if not exists:
                        LedgerEntry.objects.create(
                            user_id=uid,
                            year=year + 1,
                            category=cat,
                            days=bal,
                            reason="carry_forward",
                            note=f"Carried forward from {year}",
                        )
                        summary["entries_created"] += 1

        if dry_run:
            transaction.set_rollback(True)

    return summary
