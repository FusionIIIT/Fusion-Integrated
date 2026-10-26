"""Services for Leave Balance management."""
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ..models import LeaveBalance, LeavePolicy, OfflineLeaveEntry, YearEndProcessing
from ..selectors.balances import get_or_create_balance, calculate_vl_to_el_conversion
from ..selectors.leave_requests import get_leave_policy
from ..domain.entities import LeaveCategory, EmployeeType


@transaction.atomic
def adjust_balance(
    user_id: int,
    category: str,
    year: int,
    adjustment: Decimal,
    reason: str = "",
) -> LeaveBalance:
    """Adjust a leave balance (admin only)."""
    balance = get_or_create_balance(user_id, category, year)
    balance.closing_balance += adjustment
    balance.credited += adjustment
    balance.save(update_fields=["closing_balance", "credited", "updated_at"])
    return balance


@transaction.atomic
def ensure_user_balances(
    user_id: int,
    employee_type: str,
    year: int,
) -> dict[str, LeaveBalance]:
    """Provision the year's balances from the active policy, once.

    A faculty member's first visit must not fail with "no balance": the
    entitlement is a consequence of the policy, not an administrator chore.
    Existing rows are left untouched, so re-running is safe and an adjustment
    is never overwritten.
    """
    categories = (LeavePolicy.objects
                  .filter(employee_type=employee_type, is_active=True)
                  .values_list("category", flat=True).distinct())
    balances: dict[str, LeaveBalance] = {}
    for category in categories:
        policy = get_leave_policy(category, employee_type, date(year, 1, 1))
        if policy is None:
            continue
        balance, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id, category=category, year=year,
            defaults={
                "opening_balance": policy.annual_entitlement,
                "credited": policy.annual_entitlement,
                "closing_balance": policy.annual_entitlement,
            },
        )
        balances[category] = balance
    return balances


@transaction.atomic
def credit_annual_entitlement(
    user_id: int,
    category: str,
    year: int,
    employee_type: str,
    principal,
) -> LeaveBalance:
    """Credit annual leave entitlement at year start."""
    policy = get_leave_policy(category, employee_type, date(year, 1, 1))
    if not policy:
        raise ValueError(f"No policy for {category} ({employee_type}) in {year}")

    balance = get_or_create_balance(user_id, category, year)
    balance.opening_balance += policy.annual_entitlement
    balance.credited += policy.annual_entitlement
    balance.closing_balance += policy.annual_entitlement
    balance.save(update_fields=["opening_balance", "credited", "closing_balance", "updated_at"])

    return balance


@transaction.atomic
def process_year_end(year: int, principal) -> YearEndProcessing:
    """Run year-end leave processing for all users."""
    yep = YearEndProcessing.objects.create(year=year, status="running", started_at=timezone.now())

    from ..models import LeaveBalance, LeaveRequest
    from ..domain.rules.eligibility import year_end_processing as calc_year_end

    try:
        balances = list(LeaveBalance.objects.filter(year=year))
        # Resolve every employee's kind in one batched directory call rather
        # than guessing from the numeric id.
        from modules.directory import contracts as directory

        kinds = {uid: u.kind
                 for uid, u in directory.get_users([b.user_id for b in balances]).items()}
        processed = 0
        errors = []

        for balance in balances:
            try:
                kind = kinds.get(balance.user_id, "staff")
                employee_type = (EmployeeType.FACULTY if kind == "faculty"
                                 else EmployeeType.NON_FACULTY)
                category = balance.category

                lapsed, carried, el_credited = calc_year_end(
                    category, employee_type, balance
                )

                if lapsed > 0:
                    balance.lapsed += lapsed
                    balance.closing_balance -= lapsed

                if carried > 0:
                    # Create next year's balance with carried forward
                    next_balance = get_or_create_balance(balance.user_id, category, year + 1)
                    next_balance.opening_balance += carried
                    next_balance.credited += carried
                    next_balance.closing_balance += carried
                    next_balance.save(update_fields=["opening_balance", "credited", "closing_balance", "updated_at"])

                if el_credited > 0:
                    # Credit EL from VL conversion
                    el_balance = get_or_create_balance(balance.user_id, LeaveCategory.EL, year + 1)
                    el_balance.credited += Decimal(str(el_credited))
                    el_balance.closing_balance += Decimal(str(el_credited))
                    el_balance.save(update_fields=["credited", "closing_balance", "updated_at"])

                balance.save(update_fields=["lapsed", "closing_balance", "updated_at"])
                processed += 1

            except Exception as e:
                errors.append({"user_id": balance.user_id, "category": balance.category, "error": str(e)})

        yep.status = "completed"
        yep.completed_at = timezone.now()
        yep.processed_users = processed
        yep.errors = errors
        yep.save(update_fields=["status", "completed_at", "processed_users", "errors", "updated_at"])

    except Exception as e:
        yep.status = "failed"
        yep.completed_at = timezone.now()
        yep.errors = [{"error": str(e)}]
        yep.save(update_fields=["status", "completed_at", "errors", "updated_at"])
        raise

    return yep


@transaction.atomic
def record_offline_leave(
    *,
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    total_days: Decimal,
    sanction_order_number: str,
    sanction_order_date: date,
    sanctioning_authority: str,
    remarks: str,
    entered_by: int,
) -> OfflineLeaveEntry:
    """Record offline-sanctioned leave (admin only)."""
    # Also update balance
    balance = get_or_create_balance(user_id, category, start_date.year)
    balance.availed += total_days
    balance.closing_balance -= total_days
    balance.save(update_fields=["availed", "closing_balance", "updated_at"])

    return OfflineLeaveEntry.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        sanction_order_number=sanction_order_number,
        sanction_order_date=sanction_order_date,
        sanctioning_authority=sanctioning_authority,
        remarks=remarks,
        entered_by=entered_by,
    )