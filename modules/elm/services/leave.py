"""Atomic leave submission, recommendation, final decision, and withdrawal."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.domain.policy import count_days, eligible, overlaps, remaining
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveApplication,
    LeaveBalance,
    LeaveEvent,
)


def log_event(application, actor_id, action, detail=""):
    LeaveEvent.objects.create(
        application=application, actor_id=actor_id, action=action, detail=detail
    )


def _balance_for_update(employee_id, year, category):
    return get_object_or_404(
        LeaveBalance.objects.select_for_update(),
        employee_id=employee_id,
        year=year,
        category=category,
    )


@transaction.atomic
def submit(principal, data):
    profile = get_object_or_404(EmployeeLeaveProfile, user_id=principal.user_id)
    category, start, end = data["category"], data["start_date"], data["end_date"]
    half_day = data.get("half_day", "NONE")
    if not eligible(category, profile.category):
        raise ValidationError({"category": "Leave type is not eligible for this employee."})
    if start.year != end.year:
        raise ValidationError({"end_date": "The pilot requires a leave interval within one year."})
    if not profile.unit_head_user_id:
        raise ValidationError({"hierarchy": "Leave Unit Head is not configured."})
    if category not in ("CL", "RH") and not profile.sanction_authority_user_id:
        raise ValidationError({"hierarchy": "Final Sanctioning Authority is not configured."})
    if data.get("station_leave") and not data.get("station_location", "").strip():
        raise ValidationError({"station_location": "Station Leave requires a destination."})
    if category == "VL":
        raise ValidationError(
            {"category": "Vacation leave requires Academic Calendar integration."}
        )
    if category == "RH" and (
        start != end or not Holiday.objects.filter(date=start, kind="RH", published=True).exists()
    ):
        raise ValidationError({"start_date": "Choose a published restricted holiday."})
    closed = frozenset(
        Holiday.objects.filter(date__range=(start, end), kind="CLOSED", published=True).values_list(
            "date", flat=True
        )
    )
    try:
        duration = count_days(category, start, end, half_day, closed)
    except ValueError as exc:
        raise ValidationError({"duration": str(exc)}) from exc
    balance = _balance_for_update(principal.user_id, start.year, category)
    try:
        remaining(balance.allotted, balance.used, duration)
    except ValueError as exc:
        raise ValidationError({"balance": str(exc)}) from exc

    for existing in LeaveApplication.objects.select_for_update().filter(
        employee_id=principal.user_id,
        status__in=("PENDING", "RECOMMENDED", "APPROVED"),
        start_date__lte=end,
        end_date__gte=start,
    ):
        if overlaps(
            existing.start_date,
            existing.end_date,
            start,
            end,
            existing.half_day,
            half_day,
        ):
            raise ValidationError({"start_date": "An active leave request overlaps these dates."})

    application = LeaveApplication.objects.create(
        employee_id=principal.user_id,
        category=category,
        start_date=start,
        end_date=end,
        half_day=half_day,
        duration=duration,
        reason=data["reason"].strip(),
        station_leave=data.get("station_leave", False),
        station_location=data.get("station_location", "").strip(),
        unit_head_id=profile.unit_head_user_id,
        sanction_authority_id=profile.sanction_authority_user_id,
    )
    log_event(application, principal.user_id, "submitted")
    return application


@transaction.atomic
def decide(principal, pk, *, action, remarks=""):
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
    )
    if application.status not in ("PENDING", "RECOMMENDED"):
        raise ValidationError({"status": "This application is no longer actionable."})
    if application.employee_id == principal.user_id:
        raise PermissionDenied("The applicant cannot decide their own leave.")
    if application.status == "PENDING":
        if principal.user_id != application.unit_head_id:
            raise PermissionDenied("Only the assigned Unit Head can act now.")
        if application.category not in ("CL", "RH"):
            if action not in ("recommend", "not_recommend"):
                raise ValidationError({"action": "Unit Head must recommend or not recommend."})
            application.recommendation = (
                "RECOMMENDED" if action == "recommend" else "NOT_RECOMMENDED"
            )
            application.status = "RECOMMENDED"
            application.save(update_fields=["recommendation", "status", "updated_at"])
            log_event(application, principal.user_id, action, remarks)
            return application
    else:
        if principal.user_id != application.sanction_authority_id:
            raise PermissionDenied("Only the assigned sanction authority can act now.")

    if action not in ("approve", "reject"):
        raise ValidationError({"action": "Final action must be approve or reject."})
    if action == "approve":
        balance = _balance_for_update(
            application.employee_id, application.start_date.year, application.category
        )
        try:
            remaining(balance.allotted, balance.used, application.duration)
        except ValueError as exc:
            raise ValidationError({"balance": str(exc)}) from exc
        balance.used += application.duration
        balance.save(update_fields=["used"])
    application.status = "APPROVED" if action == "approve" else "REJECTED"
    application.approver_id = principal.user_id
    application.decision_remarks = remarks
    application.decided_at = timezone.now()
    application.save(
        update_fields=["status", "approver_id", "decision_remarks", "decided_at", "updated_at"]
    )
    log_event(application, principal.user_id, action, remarks)
    return application


@transaction.atomic
def withdraw(principal, pk):
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status not in ("PENDING", "RECOMMENDED"):
        raise ValidationError({"status": "Only pending applications can be withdrawn."})
    application.status = "WITHDRAWN"
    application.save(update_fields=["status", "updated_at"])
    log_event(application, principal.user_id, "withdrawn")
    return application
