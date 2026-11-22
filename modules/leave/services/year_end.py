"""Year-end automated batch processing (EL-UC-020, BR-EL-002, BR-EL-007, BR-EL-008)."""
from __future__ import annotations

from decimal import Decimal
from django.db import transaction

from modules.leave.domain.year_end import compute_year_end_transition
from modules.leave.models import LeaveBalance, LeaveLedgerEntry
from modules.leave.selectors.balances import configured_entitlements, get_or_create_balance


@transaction.atomic
def run_year_end_processing(current_year: int) -> int:
    """Execute year-end transitions for all balances of current_year."""
    from modules.directory import contracts as directory

    for employee in directory.get_employees():
        get_or_create_balance(
            employee.user_id, year=current_year,
            is_faculty=employee.kind == "faculty",
        )
    balances = LeaveBalance.objects.select_for_update().filter(
        year=current_year, year_end_processed=False
    )
    next_year = current_year + 1
    processed_count = 0
    annual = configured_entitlements()

    for old_bal in balances:
        res = compute_year_end_transition(
            cl=old_bal.cl_balance,
            rh=old_bal.rh_balance,
            scl=old_bal.scl_balance,
            el=old_bal.el_balance,
            vl=old_bal.vl_balance,
            col=old_bal.col_balance,
            is_faculty=old_bal.is_faculty,
        )

        # Record each lapse/conversion, then clear consumed balances so retries cannot
        # duplicate next year's carry-forward.
        for category, amount in (
            ("CL", res["lapsed_cl"]),
            ("RH", res["lapsed_rh"]),
            ("SCL", res["lapsed_scl"]),
        ):
            if amount <= Decimal("0.0"):
                continue
            LeaveLedgerEntry.objects.create(
                balance=old_bal,
                user_id=old_bal.user_id,
                category=category,
                entry_type="lapse",
                change_amount=-amount,
                balance_after=Decimal("0.0"),
                remarks="Year-end lapse",
            )
        if res["converted_vl_to_el"] > Decimal("0.0"):
            LeaveLedgerEntry.objects.create(
                balance=old_bal,
                user_id=old_bal.user_id,
                category="VL",
                entry_type="conversion",
                change_amount=-old_bal.vl_balance,
                balance_after=Decimal("0.0"),
                remarks=f"Converted {old_bal.vl_balance} VL to {res['converted_vl_to_el']} EL",
            )

        if res["lapsed_vl"] > Decimal("0.0"):
            LeaveLedgerEntry.objects.create(
                balance=old_bal, user_id=old_bal.user_id, category="VL",
                entry_type="lapse", change_amount=-res["lapsed_vl"],
                balance_after=Decimal("0.0"), remarks="Year-end VL lapse",
            )

        old_bal.cl_balance = Decimal("0.0")
        old_bal.rh_balance = Decimal("0.0")
        old_bal.scl_balance = Decimal("0.0")
        old_bal.vl_balance = Decimal("0.0")
        old_bal.el_balance = Decimal("0.0")
        old_bal.col_balance = Decimal("0.0")
        old_bal.year_end_processed = True
        old_bal.save()

        # Create the next year's annual grants once, plus carried EL/COL.
        next_bal, created = LeaveBalance.objects.get_or_create(
            user_id=old_bal.user_id,
            year=next_year,
            defaults={
                "is_faculty": old_bal.is_faculty,
                "cl_balance": annual["CL"],
                "rh_balance": annual["RH"],
                "scl_balance": annual["SCL"],
                "el_balance": res["carried_el"] if old_bal.is_faculty else res["carried_el"] + annual["EL"],
                "vl_balance": annual["VL"] if old_bal.is_faculty else Decimal("0.0"),
                "col_balance": res["carried_col"] + annual["COL"],
            },
        )
        if not created:
            next_bal.el_balance += res["carried_el"]
            next_bal.col_balance += res["carried_col"]
            next_bal.save(update_fields=["el_balance", "col_balance", "updated_at"])

        for category, amount in (
            ("CL", annual["CL"]),
            ("RH", annual["RH"]),
            ("SCL", annual["SCL"]),
            ("EL", res["carried_el"] + (Decimal("0.0") if old_bal.is_faculty else annual["EL"])),
            ("VL", annual["VL"] if old_bal.is_faculty else Decimal("0.0")),
            ("COL", res["carried_col"] + annual["COL"]),
        ):
            if amount > Decimal("0.0"):
                LeaveLedgerEntry.objects.create(
                    balance=next_bal, user_id=old_bal.user_id, category=category,
                    entry_type="credit", change_amount=amount,
                    balance_after=next_bal.get_category_balance(category),
                    remarks=f"Year {next_year} annual grant and carry-forward",
                )

        processed_count += 1

    return processed_count
