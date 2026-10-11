"""Atomic leave submission, substitute consent, review, sanction, and lifecycle services."""

from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.domain.policy import (
    count_days,
    eligible,
    overlaps,
    remaining,
    requires_higher_sanction,
)
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveApplication,
    LeaveBalance,
    LeaveEvent,
)
from modules.elm.selectors.queries import get_published_dates


def log_event(application: LeaveApplication, actor_id: int, action: str, detail: str = "") -> None:
    LeaveEvent.objects.create(
        application=application, actor_id=actor_id, action=action, detail=detail
    )


def _balance_for_update(employee_id: int, year: int, category: str) -> LeaveBalance:
    return get_object_or_404(
        LeaveBalance.objects.select_for_update(),
        employee_id=employee_id,
        year=year,
        category=category,
    )


@transaction.atomic
def submit(principal, data: dict) -> LeaveApplication:
    profile = get_object_or_404(EmployeeLeaveProfile, user_id=principal.user_id)
    category, start, end = data["category"], data["start_date"], data["end_date"]
    half_day = data.get("half_day", "NONE")
    substitute_user_id = data.get("substitute_user_id")
    if not eligible(category, profile.category):
        raise ValidationError({"category": "Leave type is not eligible for this employee."})
    if start.year != end.year:
        raise ValidationError({"end_date": "Leave interval must fall within a single year."})
    if not profile.unit_head_user_id:
        raise ValidationError({"hierarchy": "Leave Unit Head is not configured."})
    if requires_higher_sanction(category) and not profile.sanction_authority_user_id:
        raise ValidationError({"hierarchy": "Final Sanctioning Authority is not configured."})
    if data.get("station_leave") and not data.get("station_location", "").strip():
        raise ValidationError({"station_location": "Station Leave requires a destination."})
    if substitute_user_id == principal.user_id:
        raise ValidationError({"substitute_user_id": "Applicant cannot be their own substitute."})
    if category == "VL":
        vacation_dates = get_published_dates(start, end, "VACATION")
        expected_days = (end - start).days + 1
        if len(vacation_dates) != expected_days:
            raise ValidationError(
                {"category": "Vacation leave requires published vacation calendar dates."}
            )
    if category == "RH" and (
        start != end or not Holiday.objects.filter(date=start, kind="RH", published=True).exists()
    ):
        raise ValidationError({"start_date": "Choose a published restricted holiday."})
    closed = get_published_dates(start, end, "CLOSED")
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
        status__in=("AWAITING_SUB", "PENDING", "RECOMMENDED", "APPROVED"),
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

    has_sub = bool(substitute_user_id)
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
        substitute_user_id=substitute_user_id,
        substitute_status="PENDING" if has_sub else "NOT_REQUIRED",
        status="AWAITING_SUB" if has_sub else "PENDING",
        unit_head_id=profile.unit_head_user_id,
        sanction_authority_id=profile.sanction_authority_user_id,
    )
    log_event(application, principal.user_id, "submitted")
    return application


@transaction.atomic
def decide(principal, pk: int, *, action: str, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(LeaveApplication.objects.select_for_update(), pk=pk)
    if application.employee_id == principal.user_id:
        raise PermissionDenied("The applicant cannot decide their own leave.")

    if application.status == "AWAITING_SUB":
        if principal.user_id != application.substitute_user_id:
            raise PermissionDenied("Only the nominated substitute can respond now.")
        if action not in ("accept_substitute", "decline_substitute"):
            raise ValidationError({"action": "Substitute must accept or decline."})
        accepted = action == "accept_substitute"
        application.substitute_status = "ACCEPTED" if accepted else "DECLINED"
        if accepted:
            application.status = "PENDING"
        application.save(update_fields=["substitute_status", "status", "updated_at"])
        log_event(application, principal.user_id, action, remarks)
        return application

    if application.status not in ("PENDING", "RECOMMENDED"):
        raise ValidationError({"status": "This application is no longer actionable."})
    if application.substitute_status not in ("NOT_REQUIRED", "ACCEPTED"):
        raise ValidationError({"substitute": "Substitute consent is required before review."})

    if application.status == "PENDING":
        if principal.user_id != application.unit_head_id:
            raise PermissionDenied("Only the assigned Unit Head can act now.")
        if requires_higher_sanction(application.category):
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
def withdraw(principal, pk: int) -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status not in ("AWAITING_SUB", "PENDING", "RECOMMENDED"):
        raise ValidationError({"status": "Only pending applications can be withdrawn."})
    application.status = "WITHDRAWN"
    application.save(update_fields=["status", "updated_at"])
    log_event(application, principal.user_id, "withdrawn")
    return application


@transaction.atomic
def cancel_approved(principal, pk: int, *, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status != "APPROVED":
        raise ValidationError({"status": "Only approved leave can be cancelled."})
    if timezone.localdate() >= application.start_date:
        raise ValidationError({"start_date": "Approved leave cannot be cancelled once started."})
    balance = _balance_for_update(
        application.employee_id, application.start_date.year, application.category
    )
    balance.used = max(Decimal("0"), balance.used - application.duration)
    balance.save(update_fields=["used"])
    application.status = "CANCELLED"
    application.save(update_fields=["status", "updated_at"])
    log_event(application, principal.user_id, "cancelled", remarks)
    return application


@transaction.atomic
def upsert_profile(data: dict) -> tuple[EmployeeLeaveProfile, bool]:
    payload = dict(data)
    user_id = payload.pop("user_id")
    return EmployeeLeaveProfile.objects.update_or_create(user_id=user_id, defaults=payload)


@transaction.atomic
def allot_balance(data: dict) -> LeaveBalance:
    payload = dict(data)
    allot = payload.pop("allotted")
    get_object_or_404(EmployeeLeaveProfile, user_id=payload["employee_id"])
    obj, _ = LeaveBalance.objects.select_for_update().get_or_create(
        **payload, defaults={"allotted": allot, "used": 0}
    )
    if obj.used > allot:
        raise ValidationError({"allotted": "Allotment cannot be less than already used leave."})
    obj.allotted = allot
    obj.save(update_fields=["allotted"])
    return obj


@transaction.atomic
def upsert_holiday(data: dict) -> Holiday:
    payload = dict(data)
    holiday_date = payload.pop("date")
    obj, _ = Holiday.objects.update_or_create(date=holiday_date, defaults=payload)
    return obj
