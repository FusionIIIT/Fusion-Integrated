"""Event-triggered year-end leave processing (EL-UC-020, BR-EL-003, BR-EL-007)."""

from decimal import Decimal

from django.db import transaction

from modules.leave.domain.rules import calculate_year_end_conversions
from modules.leave.models import LeaveBalance
from modules.leave.services.balances import DEFAULT_ENTITLEMENTS


def execute_year_end_processing(year: int) -> dict:
    """Execute year-end leave category outcomes across all active balances."""
    with transaction.atomic():
        user_ids = list(
            LeaveBalance.objects.filter(year=year).values_list("user_id", flat=True).distinct()
        )

        processed_count = 0
        total_vl_converted = Decimal("0.0")

        for uid in user_ids:
            balances = {
                b.leave_type: b.balance for b in LeaveBalance.objects.filter(user_id=uid, year=year)
            }
            is_faculty = "VL" in balances

            new_balances, vl_to_el = calculate_year_end_conversions(balances, is_faculty=is_faculty)
            total_vl_converted += vl_to_el

            next_year = year + 1

            # Carry forward EL and COL + add new year entitlement
            el_carry = new_balances.get("EL", Decimal("0.0"))
            col_carry = new_balances.get("COL", Decimal("0.0"))

            # Seed next year's balances
            categories = ["CL", "RH", "SCL", "COL"]
            if is_faculty:
                categories.append("VL")
                if el_carry > Decimal("0.0"):
                    categories.append("EL")
            else:
                categories.append("EL")

            for t_code in categories:
                entitlement = DEFAULT_ENTITLEMENTS.get(t_code, Decimal("0.0"))
                if t_code == "EL" and is_faculty:
                    entitlement = Decimal("0.0")
                init_credit = entitlement
                if t_code == "EL":
                    init_credit += el_carry
                elif t_code == "COL":
                    init_credit += col_carry

                LeaveBalance.objects.update_or_create(
                    user_id=uid,
                    year=next_year,
                    leave_type=t_code,
                    defaults={
                        "credited": init_credit,
                        "availed": Decimal("0.0"),
                        "balance": init_credit,
                    },
                )
            processed_count += 1

        return {
            "year": year,
            "next_year": year + 1,
            "employees_processed": processed_count,
            "total_vl_converted_to_el": str(total_vl_converted),
        }
