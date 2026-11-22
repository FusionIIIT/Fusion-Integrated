"""MMS reporting services (BR-MMS-034; CFR-MMS-019/020; UC-024/025)."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from modules.mms.models import (
    Feedback,
    MonthlyBill,
    RebateRequest,
    Registration,
    SpecialFoodCharge,
    SpecialFoodRequest,
    VacationResponse,
    VacationSurvey,
)
from modules.mms.services import authz


def get_operational_report(actor, period: str | None = None) -> dict:
    """Caretaker operational report: registration counts, active rebates,
    pending special food, and bill summaries."""
    authz.require(actor, "mms.report.operational")

    today = timezone.localdate()
    period_str = period or today.strftime("%Y-%m")

    total_registered = Registration.objects.filter(status="approved").count()
    pending_registrations = Registration.objects.filter(status="pending").count()
    active_rebates = RebateRequest.objects.filter(
        status="approved",
        approved_start_date__lte=today,
        approved_end_date__gte=today,
    ).count()
    pending_special_food = SpecialFoodRequest.objects.filter(status="requested").count()
    bills_generated = MonthlyBill.objects.filter(
        state__in=["generated", "finalized", "published"]
    ).count()
    feedback_count = Feedback.objects.count()

    return {
        "period": period_str,
        "total_registered_students": total_registered,
        "pending_registrations": pending_registrations,
        "active_rebates": active_rebates,
        "pending_special_food": pending_special_food,
        "bills_generated": bills_generated,
        "feedback_count": feedback_count,
    }


def get_supervisory_report(actor, period: str | None = None) -> dict:
    """Warden supervisory report: financial aggregates, survey participation,
    and student feedback totals."""
    authz.require(actor, "mms.report.supervisory")

    today = timezone.localdate()
    period_str = period or today.strftime("%Y-%m")

    total_billed = MonthlyBill.objects.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    total_rebates = MonthlyBill.objects.aggregate(total=Sum("rebate_deductions"))[
        "total"
    ] or Decimal("0.00")
    total_special = SpecialFoodCharge.objects.aggregate(total=Sum("amount"))["total"] or Decimal(
        "0.00"
    )

    total_students = Registration.objects.filter(status="approved").count()
    latest_survey = VacationSurvey.objects.order_by("-created_at").first()
    participation_rate = 0.0
    if latest_survey and total_students > 0:
        responses = VacationResponse.objects.filter(
            survey=latest_survey.pk, response__in=["yes", "no"]
        ).count()
        participation_rate = round((responses / total_students) * 100, 2)

    feedback_count = Feedback.objects.count()

    return {
        "period": period_str,
        "total_billed_amount": total_billed,
        "total_rebate_deductions": total_rebates,
        "total_special_food_charges": total_special,
        "survey_participation_rate": participation_rate,
        "feedback_count": feedback_count,
    }
