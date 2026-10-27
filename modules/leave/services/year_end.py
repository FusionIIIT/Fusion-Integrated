"""Year-end automated batch processing (EL-UC-020, BR-EL-002, BR-EL-007, BR-EL-008)."""
from __future__ import annotations

from decimal import Decimal
from django.db import transaction

from modules.leave.domain.year_end import compute_year_end_transition
from modules.leave.models import LeaveBalance, LeaveLedgerEntry
from modules.leave.selectors.balances import configured_entitlements, get_or_create_balance


@transaction.atomic
def run_year_end_processing(current_year: int) -> int:
    """Execute year-end transitions with a ledger trail that reconciles to each balance.

    Carry-forward entries are recorded separately from annual grants and VL-to-EL
    conversions. If next year's balance already exists, only the carried amounts are
    added; annual entitlements are not granted or logged a second time.
    """
    from modules.directory import contracts as directory

    for employee in directory.get_employees():
        get_or_create_balance(employee.user_id, year=current_year, is_faculty=employee.kind == "faculty")
    balances = LeaveBalance.objects.select_for_update().filter(year=current_year, year_end_processed=False)
    next_year = current_year + 1
    processed_count = 0
    annual = configured_entitlements()

    for old_bal in balances:
        source_el = old_bal.el_balance
        res = compute_year_end_transition(
            cl=old_bal.cl_balance, rh=old_bal.rh_balance, scl=old_bal.scl_balance,
            el=old_bal.el_balance, vl=old_bal.vl_balance, col=old_bal.col_balance,
            is_faculty=old_bal.is_faculty,
        )
        for category, amount in (("CL", res["lapsed_cl"]), ("RH", res["lapsed_rh"]), ("SCL", res["lapsed_scl"])):
            if amount > Decimal("0.0"):
                LeaveLedgerEntry.objects.create(
                    balance=old_bal, user_id=old_bal.user_id, category=category,
                    entry_type="lapse", change_amount=-amount, balance_after=Decimal("0.0"),
                    remarks=f"Year {current_year} year-end lapse",
                )
        if res["converted_vl_to_el"] > Decimal("0.0"):
            LeaveLedgerEntry.objects.create(
                balance=old_bal, user_id=old_bal.user_id, category="VL", entry_type="conversion",
                change_amount=-old_bal.vl_balance, balance_after=Decimal("0.0"), reference_id=old_bal.pk,
                remarks=f"Year {current_year} VL converted to {res['converted_vl_to_el']} EL in {next_year}",
            )
        if res["lapsed_vl"] > Decimal("0.0"):
            LeaveLedgerEntry.objects.create(
                balance=old_bal, user_id=old_bal.user_id, category="VL", entry_type="lapse",
                change_amount=-res["lapsed_vl"], balance_after=Decimal("0.0"), remarks=f"Year {current_year} VL lapse",
            )
        for category, amount in (("EL", old_bal.el_balance), ("COL", old_bal.col_balance)):
            if amount > Decimal("0.0"):
                LeaveLedgerEntry.objects.create(
                    balance=old_bal, user_id=old_bal.user_id, category=category,
                    entry_type="carry_forward", change_amount=-amount, balance_after=Decimal("0.0"),
                    reference_id=old_bal.pk, remarks=f"Carry-forward from {current_year} to {next_year}",
                )

        old_bal.cl_balance = Decimal("0.0")
        old_bal.rh_balance = Decimal("0.0")
        old_bal.scl_balance = Decimal("0.0")
        old_bal.vl_balance = Decimal("0.0")
        old_bal.el_balance = Decimal("0.0")
        old_bal.col_balance = Decimal("0.0")
        old_bal.year_end_processed = True
        old_bal.save()

        next_bal, created = LeaveBalance.objects.get_or_create(
            user_id=old_bal.user_id, year=next_year,
            defaults={
                "is_faculty": old_bal.is_faculty,
                "cl_balance": annual["CL"], "rh_balance": annual["RH"], "scl_balance": annual["SCL"],
                "el_balance": res["carried_el"] if old_bal.is_faculty else res["carried_el"] + annual["EL"],
                "vl_balance": annual["VL"] if old_bal.is_faculty else Decimal("0.0"),
                "col_balance": res["carried_col"] + annual["COL"],
            },
        )
        if created:
            pre_el = Decimal("0.0") if old_bal.is_faculty else annual["EL"]
        else:
            pre_el = next_bal.el_balance
        pre_col = annual["COL"] if created else next_bal.col_balance
        if not created:
            next_bal.el_balance += res["carried_el"]
            next_bal.col_balance += res["carried_col"]
            next_bal.save(update_fields=["el_balance", "col_balance", "updated_at"])

        if created:
            for category, amount in (
                ("CL", annual["CL"]), ("RH", annual["RH"]), ("SCL", annual["SCL"]),
                ("EL", Decimal("0.0") if old_bal.is_faculty else annual["EL"]),
                ("VL", annual["VL"] if old_bal.is_faculty else Decimal("0.0")), ("COL", annual["COL"]),
            ):
                if amount > Decimal("0.0"):
                    LeaveLedgerEntry.objects.create(
                        balance=next_bal, user_id=old_bal.user_id, category=category,
                        entry_type="credit", change_amount=amount, balance_after=amount,
                        remarks=f"Year {next_year} annual entitlement",
                    )

        running_el = pre_el
        for amount, entry_type, label in (
            (source_el, "carry_forward", f"EL carry-forward from {current_year}"),
            (res["converted_vl_to_el"], "conversion", f"VL-to-EL conversion from {current_year}"),
        ):
            if amount <= Decimal("0.0"):
                continue
            running_el += amount
            LeaveLedgerEntry.objects.create(
                balance=next_bal, user_id=old_bal.user_id, category="EL", entry_type=entry_type,
                change_amount=amount, balance_after=running_el, reference_id=old_bal.pk, remarks=label,
            )
        if res["carried_col"] > Decimal("0.0"):
            running_col = pre_col
            LeaveLedgerEntry.objects.create(
                balance=next_bal, user_id=old_bal.user_id, category="COL", entry_type="carry_forward",
                change_amount=res["carried_col"], balance_after=running_col + res["carried_col"],
                reference_id=old_bal.pk, remarks=f"COL carry-forward from {current_year}",
            )
        processed_count += 1
    return processed_count
