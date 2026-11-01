"""Automated Year-End Leave Processing Service (EL-UC-020, EVT-01).

Implements:
- BR-EL-002: Unused Casual Leave lapses.
- BR-EL-003: Unused Restricted Holiday lapses.
- BR-EL-004: Unused Special Casual Leave lapses.
- BR-EL-007: Faculty VL converts to EL at 2 VL : 1 EL.
- BR-EL-008: Converted EL credited to employee's EL account and carries forward.
- BR-EL-005: Staff EL carries forward.
- BR-EL-009: Commuted Leave carries forward.
"""
from decimal import Decimal

from django.db import transaction

from modules.elm.domain.calculations import calculate_vl_to_el_conversion
from modules.elm.models.balances import LeaveAccountTransaction, LeaveBalance


@transaction.atomic
def execute_year_end_processing(current_year: int) -> dict[str, int]:
    """Execute annual boundary processing for all employees."""
    next_year = current_year + 1
    stats = {"lapsed": 0, "converted_vl": 0, "carried_forward": 0}

    balances = LeaveBalance.objects.select_for_update().filter(year=current_year)

    for bal in balances:
        available = bal.available_balance

        # 1. CL, RH, SCL lapse at year-end
        if bal.category in ("CL", "RH", "SCL"):
            if available > 0:
                LeaveAccountTransaction.objects.create(
                    user_id=bal.user_id,
                    year=current_year,
                    category=bal.category,
                    transaction_type="lapse",
                    days=available,
                    description=f"{bal.category} year-end lapse for {current_year}",
                )
                stats["lapsed"] += 1

        # 2. Faculty Vacation Leave (VL) converts to EL at 2:1 (BR-EL-007)
        elif bal.category == "VL":
            if available > 0:
                el_converted = Decimal(str(calculate_vl_to_el_conversion(float(available))))

                # Log VL lapse/conversion transaction
                LeaveAccountTransaction.objects.create(
                    user_id=bal.user_id,
                    year=current_year,
                    category="VL",
                    transaction_type="conversion",
                    days=available,
                    description=f"VL converted to {el_converted} EL at 2:1",
                )

                # Credit converted EL in next year
                el_next, _ = LeaveBalance.objects.get_or_create(
                    user_id=bal.user_id,
                    year=next_year,
                    category="EL",
                    defaults={"credited_balance": Decimal("0.00"), "carried_forward": Decimal("0.00")},
                )
                el_next.carried_forward += el_converted
                el_next.save(update_fields=["carried_forward", "updated_at"])

                LeaveAccountTransaction.objects.create(
                    user_id=bal.user_id,
                    year=next_year,
                    category="EL",
                    transaction_type="credit",
                    days=el_converted,
                    description=f"Converted from {current_year} VL",
                )
                stats["converted_vl"] += 1

        # 3. EL and COL carry forward directly
        elif bal.category in ("EL", "COL"):
            if available > 0:
                next_bal, _ = LeaveBalance.objects.get_or_create(
                    user_id=bal.user_id,
                    year=next_year,
                    category=bal.category,
                    defaults={"credited_balance": Decimal("0.00"), "carried_forward": Decimal("0.00")},
                )
                next_bal.carried_forward += available
                next_bal.save(update_fields=["carried_forward", "updated_at"])

                LeaveAccountTransaction.objects.create(
                    user_id=bal.user_id,
                    year=next_year,
                    category=bal.category,
                    transaction_type="carry_forward",
                    days=available,
                    description=f"{bal.category} carry forward from {current_year}",
                )
                stats["carried_forward"] += 1

    return stats
