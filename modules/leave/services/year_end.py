"""Year-end processing service.

Implements EL-UC-020, EVT-01, BR-EL-002, BR-EL-003, BR-EL-004, BR-EL-005, BR-EL-007, BR-EL-008, BR-EL-009.
"""


from django.db import transaction

from modules.directory.contracts import get_employees
from modules.leave.domain.constants import LeaveCategory, LedgerTransactionType
from modules.leave.domain.year_end import compute_year_end_adjustments
from modules.leave.models.ledger import LeaveLedgerEntry
from modules.leave.selectors.balances import get_user_balances
from modules.leave.selectors.policy import get_current_policy


def execute_year_end_processing(year: int, dry_run: bool = False) -> dict:
    """Executes year-end lapse, conversion, and new-year credit processing (idempotent)."""
    policy = get_current_policy()
    employees = get_employees()

    results = {
        "year": year,
        "employees_processed": 0,
        "adjustments_made": 0,
        "dry_run": dry_run,
        "details": [],
    }

    # Ensure idempotency by checking if year-end has already been run for this year
    ref_marker = f"YEAR_END_{year}"

    with transaction.atomic():
        for emp in employees:
            uid = emp.user_id
            kind = emp.kind

            # Check if this user was already processed for this year
            already_done = LeaveLedgerEntry.objects.filter(
                user_id=uid,
                reference_id__startswith=ref_marker,
            ).exists()
            if already_done:
                continue

            balances = get_user_balances(uid)
            adjustments = compute_year_end_adjustments(
                employee_kind=kind,
                current_balances=balances,
                vl_to_el_ratio=policy.vl_to_el_ratio,
                max_el_carry_forward=policy.max_el_carry_forward,
            )

            # Also credit new year entitlements
            new_year_credits = [
                (
                    LeaveCategory.CL.value,
                    policy.cl_entitlement,
                    "Annual Casual Leave credit (BR-EL-002)",
                ),
                (
                    LeaveCategory.RH.value,
                    policy.rh_entitlement,
                    "Annual Restricted Holiday credit (BR-EL-003)",
                ),
                (
                    LeaveCategory.SCL.value,
                    policy.scl_entitlement,
                    "Annual Special Casual Leave credit (BR-EL-004)",
                ),
                (
                    LeaveCategory.COL.value,
                    policy.col_entitlement,
                    "Annual Commuted Leave credit (BR-EL-009)",
                ),
            ]
            if kind == "faculty":
                new_year_credits.append(
                    (
                        LeaveCategory.VL.value,
                        policy.faculty_vl_entitlement,
                        "Annual Vacation Leave credit (BR-EL-006)",
                    )
                )
            else:
                new_year_credits.append(
                    (
                        LeaveCategory.EL.value,
                        policy.nonfaculty_el_credit,
                        "Annual Earned Leave credit (BR-EL-005)",
                    )
                )

            emp_summary = {
                "user_id": uid,
                "name": emp.display_name,
                "adjustments": len(adjustments),
                "credits": len(new_year_credits),
            }

            if not dry_run:
                # Post adjustments
                for adj in adjustments:
                    LeaveLedgerEntry.objects.create(
                        user_id=uid,
                        category=adj.category,
                        delta_days=adj.delta_days,
                        transaction_type=adj.transaction_type.value,
                        reason=adj.reason,
                        reference_id=f"{ref_marker}_ADJ",
                    )

                # Post new year credits
                for cat, days, reason in new_year_credits:
                    LeaveLedgerEntry.objects.create(
                        user_id=uid,
                        category=cat,
                        delta_days=days,
                        transaction_type=LedgerTransactionType.CREDIT.value,
                        reason=reason,
                        reference_id=f"{ref_marker}_CREDIT",
                    )

            results["employees_processed"] += 1
            results["adjustments_made"] += len(adjustments) + len(new_year_credits)
            results["details"].append(emp_summary)

        if dry_run:
            transaction.set_rollback(True)

    return results
