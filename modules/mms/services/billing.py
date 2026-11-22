"""Monthly billing (BR-MMS-016/017/018/019/030; UC-010/011/030; BW-MMS-16)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import state_machine as sm
from modules.mms.domain.exceptions import ActorNotAllowed, InvalidTransition
from modules.mms.models import MonthlyBill, Registration, SpecialFoodCharge
from modules.mms.selectors import scoping
from modules.mms.services import authz, notifications


def generate_monthly() -> int:
    """UC-030 / BR-MMS-016/017: generate Generated bills for the calendar
    month. Idempotent: one bill per student per month."""
    today = timezone.localdate()
    month = today.replace(day=1)
    registered = set(
        Registration.objects.filter(status="approved").values_list("user_id", flat=True)
    )
    existing = set(MonthlyBill.objects.filter(month=month).values_list("user_id", flat=True))
    count = 0
    for uid in registered - existing:
        special_total = SpecialFoodCharge.objects.filter(
            student_user_id=uid, month=month
        ).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

        served_day_charges = Decimal("3000.00")
        rebate_deductions = Decimal("0.00")
        total = max(Decimal("0.00"), served_day_charges + special_total - rebate_deductions)

        MonthlyBill.objects.create(
            user_id=uid,
            month=month,
            state="generated",
            served_day_charges=served_day_charges,
            special_meal_charges=special_total,
            rebate_deductions=rebate_deductions,
            total=total,
            generated_at=timezone.now(),
        )
        count += 1
    return count


def finalize(actor, pk: int) -> MonthlyBill:
    """BR-MMS-018: Caretaker finalizes a Generated bill."""
    authz.require(actor, "mms.billing.approve")
    try:
        sm.resolve("bill_generated", "bill_finalized", sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        bill = (
            scoping.monthly_bills_for(actor)
            .filter(pk=pk, state="generated")
            .select_for_update()
            .first()
        )
        if bill is None:
            raise NotFoundError("No Generated bill with that id.")
        bill.state = "finalized"
        bill.finalized_at = timezone.now()
        bill.finalized_by_user_id = actor.user_id
        bill.save(update_fields=["state", "finalized_at", "finalized_by_user_id", "updated_at"])
    return bill


def publish(actor, pk: int) -> MonthlyBill:
    """BR-MMS-018: Caretaker publishes a finalized bill; publication
    notification (BR-MMS-035)."""
    authz.require(actor, "mms.billing.publish")
    try:
        sm.resolve("bill_finalized", "bill_published", sm.CARETAKER)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc)) from exc
    with transaction.atomic():
        bill = (
            scoping.monthly_bills_for(actor)
            .filter(pk=pk, state="finalized")
            .select_for_update()
            .first()
        )
        if bill is None:
            raise NotFoundError("No finalized bill with that id.")
        bill.state = "published"
        bill.published_at = timezone.now()
        bill.save(update_fields=["state", "published_at", "updated_at"])
        notifications.enqueue(
            topic="bill.published",
            dedupe_key=f"bill.published:u{bill.user_id}:{bill.pk}",
            subject="Monthly mess bill published",
            body=f"Your monthly mess bill for {bill.month} has been published "
            f"with a total of {bill.total}.",
            recipient_user_id=bill.user_id,
        )
    return bill
