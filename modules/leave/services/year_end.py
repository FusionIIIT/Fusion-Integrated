from decimal import Decimal

from django.db import transaction

from modules.leave import contracts
from modules.leave.models import LeavePolicy
from modules.leave.services import accounts


@transaction.atomic
def process_year_end(year: int) -> dict[str, int]:
    employees = {row.user_id: row for row in contracts._active_employees()}
    result = {"employees": len(employees), "transactions": 0}
    policies = list(LeavePolicy.objects.all())
    for employee in employees.values():
        for policy in policies:
            accounts.ensure_annual_credit(
                user_id=employee.user_id, leave_type=policy.leave_type,
                year=year, employee_kind=employee.kind,
            )
            remaining = accounts.balance(employee.user_id, policy.leave_type, year)
            if remaining <= Decimal("0"):
                continue
            if policy.leave_type == "VL" and employee.kind == "faculty":
                accounts.post(
                    user_id=employee.user_id, leave_type="VL", year=year,
                    amount=-remaining, transaction_type="vl_year_end_conversion",
                    source_key=f"year-end:{year}:{employee.user_id}:VL:debit",
                    note="VL converted to EL at 2:1.",
                )
                accounts.post(
                    user_id=employee.user_id, leave_type="EL", year=year + 1,
                    amount=remaining / Decimal("2"),
                    transaction_type="vl_to_el_conversion",
                    source_key=f"year-end:{year}:{employee.user_id}:VL:EL",
                    note="Unused VL conversion at 2 VL : 1 EL.",
                )
                result["transactions"] += 2
            elif policy.carry_forward:
                accounts.post(
                    user_id=employee.user_id, leave_type=policy.leave_type, year=year,
                    amount=-remaining, transaction_type="carry_forward_close",
                    source_key=f"year-end:{year}:{employee.user_id}:{policy.leave_type}:debit",
                )
                accounts.post(
                    user_id=employee.user_id, leave_type=policy.leave_type,
                    year=year + 1, amount=remaining,
                    transaction_type="carry_forward_credit",
                    source_key=f"year-end:{year}:{employee.user_id}:{policy.leave_type}:credit",
                )
                result["transactions"] += 2
            else:
                accounts.post(
                    user_id=employee.user_id, leave_type=policy.leave_type, year=year,
                    amount=-remaining, transaction_type="year_end_lapse",
                    source_key=f"year-end:{year}:{employee.user_id}:{policy.leave_type}:lapse",
                )
                result["transactions"] += 1
    return result
