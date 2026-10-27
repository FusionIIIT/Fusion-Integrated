"""Year-end ledger processing, with idempotent postings and policy guards.

Adapted from the private ELM implementation's fail-closed year-end approach.
This service continues to use Fusion's existing LeaveAccountTransaction ledger.
"""

from decimal import Decimal

from django.db import transaction

from modules.leave import contracts
from modules.leave.models import LeaveAccountTransaction, LeavePolicy
from modules.leave.services import accounts

CARRY_FORWARD_TYPES = frozenset({"EL", "COL"})


def _post_once(**kwargs) -> int:
    """Post a transaction once; verify repeat keys still describe the same posting."""
    existed = LeaveAccountTransaction.objects.filter(source_key=kwargs["source_key"]).exists()
    accounts.post(**kwargs)
    return 0 if existed else 1


@transaction.atomic
def process_year_end(year: int) -> dict[str, int]:
    if not isinstance(year, int) or isinstance(year, bool) or year < 1:
        raise ValueError("Year-end processing requires a valid year.")

    employees_from_provider = list(contracts._active_employees())
    employees = {row.user_id: row for row in employees_from_provider}
    if len(employees) != len(employees_from_provider):
        raise ValueError("Duplicate employee identities in year-end directory source.")

    policies = list(LeavePolicy.objects.all())
    if any(p.carry_forward and p.leave_type not in CARRY_FORWARD_TYPES for p in policies):
        raise ValueError("Only EL and COL can be marked eligible for carry-forward.")

    result = {"employees": len(employees), "transactions": 0}
    for employee in employees.values():
        if employee.kind not in {"faculty", "staff"}:
            raise ValueError("Authoritative employee category is not faculty or staff.")

        for policy in policies:
            accounts.ensure_annual_credit(
                user_id=employee.user_id,
                leave_type=policy.leave_type,
                year=year,
                employee_kind=employee.kind,
            )
            remaining = accounts.balance(employee.user_id, policy.leave_type, year)
            if not remaining.is_finite():
                raise ValueError("Year-end account balance is not finite.")
            if remaining <= Decimal("0"):
                continue

            base = f"year-end:{year}:{employee.user_id}:{policy.leave_type}"
            if policy.leave_type == "VL":
                if employee.kind != "faculty":
                    raise ValueError("Only faculty may have a VL balance.")
                result["transactions"] += _post_once(
                    user_id=employee.user_id,
                    leave_type="VL",
                    year=year,
                    amount=-remaining,
                    transaction_type="vl_year_end_conversion",
                    source_key=f"{base}:debit",
                    note="VL converted to EL at 2:1.",
                )
                result["transactions"] += _post_once(
                    user_id=employee.user_id,
                    leave_type="EL",
                    year=year + 1,
                    amount=remaining / Decimal("2"),
                    transaction_type="vl_to_el_conversion",
                    source_key=f"{base}:EL",
                    note="Unused VL conversion at 2 VL : 1 EL.",
                )
            elif policy.leave_type in CARRY_FORWARD_TYPES and policy.carry_forward:
                result["transactions"] += _post_once(
                    user_id=employee.user_id,
                    leave_type=policy.leave_type,
                    year=year,
                    amount=-remaining,
                    transaction_type="carry_forward_close",
                    source_key=f"{base}:debit",
                )
                result["transactions"] += _post_once(
                    user_id=employee.user_id,
                    leave_type=policy.leave_type,
                    year=year + 1,
                    amount=remaining,
                    transaction_type="carry_forward_credit",
                    source_key=f"{base}:credit",
                )
            else:
                result["transactions"] += _post_once(
                    user_id=employee.user_id,
                    leave_type=policy.leave_type,
                    year=year,
                    amount=-remaining,
                    transaction_type="year_end_lapse",
                    source_key=f"{base}:lapse",
                )
    return result
