"""Idempotent calendar-year leave-account closure and opening."""
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.domain.rules import LEAVE_TYPES, year_end_credit
from modules.elm.models import (
    EmployeeProfile,
    LeaveAccount,
    LeaveTransaction,
    YearEndRun,
)
from modules.elm.services.leave import account_for


@transaction.atomic
def process_year_end(*, year: int, actor_user_id: int | None = None) -> YearEndRun:
    if year >= timezone.localdate().year:
        raise ConflictError("Year-end processing is only available for a completed year.",
                            code="year_not_complete")
    if YearEndRun.objects.filter(year=year).exists():
        raise ConflictError(f"Year-end processing for {year} has already completed.",
                            code="year_end_already_run")

    run = YearEndRun.objects.create(year=year)
    profiles = EmployeeProfile.objects.filter(is_active=True).order_by("user_id")
    processed = 0
    for profile in profiles.iterator():
        previous = {
            category: account_for(profile.user_id, category, year)
            for category in LEAVE_TYPES
        }
        carry: dict[str, Decimal] = {}
        converted_el = Decimal("0")
        for category, account in previous.items():
            account = LeaveAccount.objects.select_for_update().get(pk=account.pk)
            carry_forward, el_credit = year_end_credit(category, account.balance)
            carry[category] = carry_forward
            converted_el += el_credit
            if account.balance:
                transaction_type = (
                    "vl_conversion" if category == "VL" and el_credit
                    else "year_end_lapse" if category in ("CL", "RH", "SCL", "VL")
                    else "carry_forward")
                LeaveTransaction.objects.create(
                    account=account, amount=-account.balance,
                    transaction_type=transaction_type,
                    reference=f"year-end:{year}",
                    idempotency_key=f"year-end:{year}:close:{profile.user_id}:{category}",
                    actor_user_id=actor_user_id)
                account.balance = F("balance") - account.balance
                account.save(update_fields=["balance", "updated_at"])

        for category in LEAVE_TYPES:
            next_account = account_for(profile.user_id, category, year + 1)
            amount = carry[category] + (converted_el if category == "EL" else Decimal("0"))
            if amount:
                LeaveAccount.objects.filter(pk=next_account.pk).update(
                    balance=F("balance") + amount,
                    carry_forward=F("carry_forward") + amount)
                LeaveTransaction.objects.create(
                    account=next_account, amount=amount,
                    transaction_type=("vl_conversion" if category == "EL"
                                      and converted_el else "carry_forward"),
                    reference=f"year-end:{year}",
                    idempotency_key=f"year-end:{year}:open:{profile.user_id}:{category}",
                    actor_user_id=actor_user_id)
        processed += len(previous)

    run.processed_accounts = processed
    run.completed_at = timezone.now()
    run.save(update_fields=["processed_accounts", "completed_at"])
    return run
