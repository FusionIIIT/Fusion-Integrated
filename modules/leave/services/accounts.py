from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from modules.leave.models import LeaveAccountTransaction, LeavePolicy


def policy_for(leave_type: str) -> LeavePolicy:
    return LeavePolicy.objects.get(leave_type=leave_type)


def balance(user_id: int, leave_type: str, year: int) -> Decimal:
    value = LeaveAccountTransaction.objects.filter(
        user_id=user_id, leave_type=leave_type, year=year,
    ).aggregate(total=Sum("amount"))["total"]
    return value or Decimal("0")


def lock_balance(user_id: int, leave_type: str, year: int) -> Decimal:
    """Serialize sanctions against the ledger rows that currently make up a balance."""
    list(LeaveAccountTransaction.objects.select_for_update().filter(
        user_id=user_id, leave_type=leave_type, year=year,
    ).order_by("pk").values_list("pk", flat=True))
    # Re-read after acquiring locks: a sanction that waited may now see a debit
    # committed by the transaction it waited behind.
    return balance(user_id, leave_type, year)


def post(*, user_id: int, leave_type: str, year: int, amount: Decimal,
         transaction_type: str, source_key: str, application=None,
         actor_user_id: int | None = None, note: str = "") -> LeaveAccountTransaction:
    try:
        with transaction.atomic():
            return LeaveAccountTransaction.objects.create(
                user_id=user_id, leave_type=leave_type, year=year, amount=amount,
                transaction_type=transaction_type, source_key=source_key,
                application=application, created_by_user_id=actor_user_id, note=note,
            )
    except IntegrityError:
        return LeaveAccountTransaction.objects.get(source_key=source_key)


def ensure_annual_credit(*, user_id: int, leave_type: str, year: int,
                         employee_kind: str) -> None:
    policy = policy_for(leave_type)
    if leave_type == "EL" and employee_kind == "faculty":
        return
    if policy.applies_to == "faculty" and employee_kind != "faculty":
        return
    if policy.applies_to == "staff" and employee_kind != "staff":
        return
    post(
        user_id=user_id, leave_type=leave_type, year=year,
        amount=policy.annual_entitlement, transaction_type="annual_entitlement",
        source_key=f"entitlement:{user_id}:{leave_type}:{year}",
    )
