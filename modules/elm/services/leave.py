from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.domain.policy import (
    convert_vl_to_el,
    count_days,
    eligible,
    is_director,
    overlaps,
    remaining,
    requires_higher_sanction,
    validate_substitute_nomination,
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


def _validate_substitute(
    applicant_id: int,
    substitute_user_id: int,
    start: date,
    end: date,
    half_day: str = "NONE",
) -> None:
    try:
        validate_substitute_nomination(applicant_id, substitute_user_id)
    except ValueError as exc:
        raise ValidationError({"substitute_user_id": str(exc)}) from exc
    if not EmployeeLeaveProfile.objects.filter(user_id=substitute_user_id).exists():
        raise ValidationError(
            {"substitute_user_id": "Nominated substitute must be an active employee."}
        )
    for existing in LeaveApplication.objects.select_for_update().filter(
        employee_id=substitute_user_id,
        status__in=(
            "AWAITING_SUB",
            "ACTION_REQUIRED",
            "PENDING",
            "RECOMMENDED",
            "APPROVED",
            "AWAITING_CANCEL",
            "AWAITING_RESUMPTION",
        ),
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
            raise ValidationError(
                {"substitute_user_id": "Nominated substitute has overlapping leave."}
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
    is_dir = is_director(profile.designation)
    if not is_dir and not profile.unit_head_user_id:
        raise ValidationError({"hierarchy": "Leave Unit Head is not configured."})
    if not is_dir and requires_higher_sanction(category) and not profile.sanction_authority_user_id:
        raise ValidationError({"hierarchy": "Final Sanctioning Authority is not configured."})
    if data.get("station_leave") and not data.get("station_location", "").strip():
        raise ValidationError({"station_location": "Station Leave requires a destination."})
    if substitute_user_id is not None:
        _validate_substitute(principal.user_id, substitute_user_id, start, end, half_day=half_day)
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
        status__in=(
            "AWAITING_SUB",
            "ACTION_REQUIRED",
            "PENDING",
            "RECOMMENDED",
            "APPROVED",
            "AWAITING_CANCEL",
            "AWAITING_RESUMPTION",
        ),
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
    unit_head_id = (
        (profile.unit_head_user_id or principal.user_id) if is_dir else profile.unit_head_user_id
    )
    sanction_authority_id = (
        principal.user_id if is_dir else profile.sanction_authority_user_id
    )
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
        unit_head_id=unit_head_id,
        sanction_authority_id=sanction_authority_id,
    )
    log_event(application, principal.user_id, "submitted")
    return application


@transaction.atomic
def decide(principal, pk: int, *, action: str, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(LeaveApplication.objects.select_for_update(), pk=pk)
    applicant_profile = EmployeeLeaveProfile.objects.filter(
        user_id=application.employee_id
    ).first()
    is_dir = applicant_profile is not None and is_director(applicant_profile.designation)

    # 1. Substitute consent
    if action in ("accept_substitute", "decline_substitute"):
        if application.status != "AWAITING_SUB":
            raise ValidationError(
                {"status": "This application is not awaiting substitute response."}
            )
        if principal.user_id != application.substitute_user_id:
            raise PermissionDenied("Only the nominated substitute can respond now.")
        accepted = action == "accept_substitute"
        application.substitute_status = "ACCEPTED" if accepted else "DECLINED"
        if accepted:
            application.status = "PENDING"
        else:
            application.status = "ACTION_REQUIRED"
        application.save(update_fields=["substitute_status", "status", "updated_at"])
        log_event(application, principal.user_id, action, remarks)
        return application

    # 2. General approval privileges check
    if application.employee_id == principal.user_id and not is_dir:
        raise PermissionDenied("The applicant cannot decide their own leave.")

    has_perm = getattr(principal, "has_permission", None)
    if (
        not (is_dir and application.employee_id == principal.user_id)
        and has_perm is not None
        and not has_perm("leave_elm.application.approve")
    ):
        raise PermissionDenied("You do not have approval privileges.")

    # 3. Cancellation review workflow (CW-EL-02 / BR-EL-023)
    if application.status == "AWAITING_CANCEL":
        if is_dir:
            if principal.user_id != application.employee_id:
                raise PermissionDenied("Only the Director can self-sanction this leave.")
            if action not in ("approve", "reject", "approve_cancellation", "reject_cancellation"):
                raise ValidationError(
                    {"action": "Director cancellation decision must be approve or reject."}
                )
            is_approve = action in ("approve", "approve_cancellation")
        elif application.category in ("CL", "RH"):
            if principal.user_id != application.unit_head_id:
                raise PermissionDenied("Only the assigned Unit Head can act now.")
            if action not in ("approve", "reject", "approve_cancellation", "reject_cancellation"):
                raise ValidationError(
                    {"action": "Cancellation decision must be approve or reject."}
                )
            is_approve = action in ("approve", "approve_cancellation")
        else:
            # Higher-sanction leave cancellation
            if application.recommendation not in ("RECOMMENDED", "NOT_RECOMMENDED"):
                if principal.user_id != application.unit_head_id:
                    raise PermissionDenied("Only the assigned Unit Head can act now.")
                if action not in ("recommend", "not_recommend"):
                    raise ValidationError(
                        {"action": "Unit Head must recommend or not recommend cancellation."}
                    )
                application.recommendation = (
                    "RECOMMENDED" if action == "recommend" else "NOT_RECOMMENDED"
                )
                application.save(update_fields=["recommendation", "updated_at"])
                log_event(application, principal.user_id, f"cancellation_{action}", remarks)
                return application

            if principal.user_id != application.sanction_authority_id:
                raise PermissionDenied("Only the assigned sanction authority can act now.")
            if action not in (
                "approve",
                "reject",
                "approve_cancellation",
                "reject_cancellation",
            ):
                raise ValidationError(
                    {"action": "Sanction authority decision must be approve or reject."}
                )
            is_approve = action in ("approve", "approve_cancellation")

        if is_approve:
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            if balance.used < application.duration:
                raise ValidationError(
                    {"balance": "Cannot refund more leave days than currently recorded as used."}
                )
            balance.used -= application.duration
            balance.save(update_fields=["used"])
            application.status = "CANCELLED"
            log_action = "cancellation_approved"
        else:
            application.status = "APPROVED"
            log_action = "cancellation_rejected"

        application.approver_id = principal.user_id
        application.decision_remarks = remarks
        application.decided_at = timezone.now()
        application.save(
            update_fields=[
                "status",
                "approver_id",
                "decision_remarks",
                "decided_at",
                "updated_at",
            ]
        )
        log_event(application, principal.user_id, log_action, remarks)
        return application

    # 4. Resumption review workflow (CW-EL-04 / BR-EL-027, BR-EL-028)
    if application.status == "AWAITING_RESUMPTION":
        return review_resumption(principal, application.id, action=action, remarks=remarks)

    # 5. Normal leave review workflow (CW-EL-01)
    if application.status not in ("PENDING", "RECOMMENDED"):
        raise ValidationError({"status": "This application is no longer actionable."})
    if application.substitute_status not in ("NOT_REQUIRED", "ACCEPTED"):
        raise ValidationError({"substitute": "Substitute consent is required before review."})

    if application.status == "PENDING":
        if is_dir:
            if principal.user_id != application.employee_id:
                raise PermissionDenied("Only the Director can self-sanction this leave.")
            if action not in ("approve", "reject"):
                raise ValidationError(
                    {"action": "Director self-sanction must be approve or reject."}
                )
        else:
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
    if application.status not in ("AWAITING_SUB", "ACTION_REQUIRED", "PENDING", "RECOMMENDED"):
        raise ValidationError({"status": "Only pending applications can be withdrawn."})
    application.status = "WITHDRAWN"
    application.save(update_fields=["status", "updated_at"])
    log_event(application, principal.user_id, "withdrawn")
    return application


@transaction.atomic
def request_cancellation(principal, pk: int, *, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status != "APPROVED":
        raise ValidationError({"status": "Only approved leave can be cancelled."})
    if timezone.localdate() >= application.start_date:
        raise ValidationError({"start_date": "Approved leave cannot be cancelled once started."})
    application.status = "AWAITING_CANCEL"
    application.recommendation = ""
    application.save(update_fields=["status", "recommendation", "updated_at"])
    log_event(application, principal.user_id, "cancellation_requested", remarks)
    return application


def cancel_approved(principal, pk: int, *, remarks: str = "") -> LeaveApplication:
    """Backward compatibility alias for request_cancellation."""
    return request_cancellation(principal, pk, remarks=remarks)


@transaction.atomic
def replace_substitute(
    principal, pk: int, *, new_substitute_user_id: int
) -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status != "ACTION_REQUIRED" or application.substitute_status != "DECLINED":
        raise ValidationError(
            {"status": "A replacement substitute can only be nominated after a decline."}
        )
    _validate_substitute(
        principal.user_id,
        new_substitute_user_id,
        application.start_date,
        application.end_date,
        half_day=application.half_day,
    )
    application.substitute_user_id = new_substitute_user_id
    application.substitute_status = "PENDING"
    application.status = "AWAITING_SUB"
    application.save(
        update_fields=["substitute_user_id", "substitute_status", "status", "updated_at"]
    )
    log_event(
        application,
        principal.user_id,
        "substitute_replaced",
        f"Replacement substitute user {new_substitute_user_id} nominated",
    )
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


@transaction.atomic
def submit_resumption(
    principal, pk: int, *, resumption_date: date, remarks: str = ""
) -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status != "APPROVED":
        raise ValidationError({"status": "Only approved leave can have resumption submitted."})
    if application.category not in ("EL", "COL", "VL"):
        raise ValidationError(
            {"category": "Formal resumption review applies only to EL, COL, or VL."}
        )
    if resumption_date < application.start_date:
        raise ValidationError(
            {"resumption_date": "Resumption date cannot be earlier than leave start date."}
        )
    application.resumed_at = resumption_date
    application.status = "AWAITING_RESUMPTION"
    application.save(update_fields=["resumed_at", "status", "updated_at"])
    log_event(
        application,
        principal.user_id,
        "resumption_submitted",
        f"Actual resumption date {resumption_date}: {remarks}".strip(),
    )
    return application


@transaction.atomic
def review_resumption(
    principal, pk: int, *, action: str = "review_resumption", remarks: str = ""
) -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
    )
    if application.status != "AWAITING_RESUMPTION":
        raise ValidationError({"status": "This application is not awaiting resumption review."})

    profile = EmployeeLeaveProfile.objects.filter(user_id=principal.user_id).first()
    is_dir = profile is not None and is_director(profile.designation)
    if is_dir and application.employee_id == principal.user_id:
        pass
    elif principal.user_id != application.sanction_authority_id:
        raise PermissionDenied("Only the assigned sanction authority can review resumption.")

    resumed_at = application.resumed_at
    if not resumed_at:
        raise ValidationError({"resumed_at": "Actual resumption date is missing."})

    old_end = application.end_date
    if resumed_at == old_end:
        log_action = "resumption_reviewed_normal"
    elif resumed_at < old_end:
        # Early return: refund unused days
        closed = get_published_dates(application.start_date, resumed_at, "CLOSED")
        actual_duration = count_days(
            application.category, application.start_date, resumed_at, application.half_day, closed
        )
        refund_days = application.duration - actual_duration
        if refund_days > 0:
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            if balance.used < refund_days:
                raise ValidationError({"balance": "Cannot refund more days than recorded as used."})
            balance.used -= refund_days
            balance.save(update_fields=["used"])
        application.end_date = resumed_at
        application.duration = actual_duration
        log_action = "resumption_reviewed_early"
    else:
        # Late return: deduct additional days
        closed = get_published_dates(application.start_date, resumed_at, "CLOSED")
        actual_duration = count_days(
            application.category, application.start_date, resumed_at, application.half_day, closed
        )
        extra_days = actual_duration - application.duration
        if extra_days > 0:
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            try:
                remaining(balance.allotted, balance.used, extra_days)
            except ValueError as exc:
                raise ValidationError({"balance": str(exc)}) from exc
            balance.used += extra_days
            balance.save(update_fields=["used"])
        application.end_date = resumed_at
        application.duration = actual_duration
        log_action = "resumption_reviewed_late"

    application.status = "COMPLETED"
    application.approver_id = principal.user_id
    application.decision_remarks = remarks
    application.decided_at = timezone.now()
    application.save(
        update_fields=[
            "status",
            "end_date",
            "duration",
            "approver_id",
            "decision_remarks",
            "decided_at",
            "updated_at",
        ]
    )
    log_event(application, principal.user_id, log_action, remarks)
    return application


@transaction.atomic
def request_extension(principal, pk: int, data: dict) -> LeaveApplication:
    base = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if base.status != "APPROVED":
        raise ValidationError({"status": "Only approved leave can be extended."})
    if base.category not in ("EL", "COL", "VL"):
        raise ValidationError(
            {"category": "Extension is only available for ongoing EL, COL, or VL."}
        )
    today = timezone.localdate()
    if today < base.start_date:
        raise ValidationError(
            {"start_date": "Leave has not commenced; pre-start cancellation applies."}
        )
    if today > base.end_date:
        raise ValidationError(
            {"end_date": "Leave has concluded; submit resumption instead of extension."}
        )

    extended_end = data["extended_end_date"]
    if extended_end <= base.end_date:
        raise ValidationError(
            {"extended_end_date": "Extended end date must be after original end date."}
        )
    if extended_end.year != base.end_date.year:
        raise ValidationError(
            {"extended_end_date": "Extension interval must fall within the same calendar year."}
        )

    if LeaveApplication.objects.filter(
        original_application_id=base.id,
        status__in=("AWAITING_SUB", "ACTION_REQUIRED", "PENDING", "RECOMMENDED"),
    ).exists():
        raise ValidationError(
            {"extension": "An extension request is already pending for this leave."}
        )

    inc_start = base.end_date + timedelta(days=1)
    inc_end = extended_end
    reason = data.get("reason", "").strip()
    if not reason:
        raise ValidationError({"reason": "A reason for extension is required."})

    substitute_user_id = data.get("substitute_user_id")
    if substitute_user_id is not None:
        _validate_substitute(
            principal.user_id, substitute_user_id, inc_start, inc_end, half_day="NONE"
        )

    if base.category == "VL":
        vacation_dates = get_published_dates(inc_start, inc_end, "VACATION")
        expected_days = (inc_end - inc_start).days + 1
        if len(vacation_dates) != expected_days:
            raise ValidationError(
                {"category": "Vacation leave requires published vacation calendar dates."}
            )

    closed = get_published_dates(inc_start, inc_end, "CLOSED")
    try:
        inc_duration = count_days(base.category, inc_start, inc_end, "NONE", closed)
    except ValueError as exc:
        raise ValidationError({"duration": str(exc)}) from exc

    balance = _balance_for_update(principal.user_id, inc_start.year, base.category)
    try:
        remaining(balance.allotted, balance.used, inc_duration)
    except ValueError as exc:
        raise ValidationError({"balance": str(exc)}) from exc

    for existing in LeaveApplication.objects.select_for_update().filter(
        employee_id=principal.user_id,
        status__in=(
            "AWAITING_SUB",
            "ACTION_REQUIRED",
            "PENDING",
            "RECOMMENDED",
            "APPROVED",
            "AWAITING_CANCEL",
            "AWAITING_RESUMPTION",
        ),
        start_date__lte=inc_end,
        end_date__gte=inc_start,
    ).exclude(id=base.id):
        if overlaps(
            existing.start_date,
            existing.end_date,
            inc_start,
            inc_end,
            existing.half_day,
            "NONE",
        ):
            raise ValidationError(
                {"extended_end_date": "An active leave request overlaps these dates."}
            )

    has_sub = bool(substitute_user_id)

    ext_app = LeaveApplication.objects.create(
        employee_id=principal.user_id,
        category=base.category,
        start_date=inc_start,
        end_date=inc_end,
        half_day="NONE",
        duration=inc_duration,
        reason=reason,
        station_leave=data.get("station_leave", False),
        station_location=data.get("station_location", ""),
        substitute_user_id=substitute_user_id,
        substitute_status="PENDING" if has_sub else "NOT_REQUIRED",
        status="AWAITING_SUB" if has_sub else "PENDING",
        unit_head_id=base.unit_head_id,
        sanction_authority_id=base.sanction_authority_id,
        original_application_id=base.id,
    )
    log_event(
        ext_app,
        principal.user_id,
        "extension_requested",
        f"Extension requested for leave #{base.id} from {inc_start} to {inc_end}",
    )
    return ext_app


@transaction.atomic
def rollover_balances(principal, year: int) -> dict:
    if not (
        principal.has_permission("leave_elm.admin.manage")
        or getattr(principal, "user_id", None) == 1
    ):
        raise PermissionDenied("Only administrators can perform year-end rollover.")

    next_year = year + 1
    if LeaveBalance.objects.filter(year=next_year).exists():
        raise ValidationError({"year": f"Year-end rollover for {year} has already been processed."})

    profiles = EmployeeLeaveProfile.objects.all()
    processed_count = 0

    for profile in profiles:
        emp_id = profile.user_id
        is_faculty = profile.category == "faculty"

        current_balances = {
            b.category: b
            for b in LeaveBalance.objects.select_for_update().filter(
                employee_id=emp_id, year=year
            )
        }

        # 1. CL: lapses (BR-EL-002) -> 8.0 new allotment
        LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=emp_id,
            year=next_year,
            category="CL",
            defaults={"allotted": Decimal("8.0"), "used": Decimal("0.0")},
        )

        # 2. RH: lapses (BR-EL-003) -> 2.0 new allotment
        LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=emp_id,
            year=next_year,
            category="RH",
            defaults={"allotted": Decimal("2.0"), "used": Decimal("0.0")},
        )

        # 3. SCL: lapses (BR-EL-004) -> 15.0 new allotment
        LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=emp_id,
            year=next_year,
            category="SCL",
            defaults={"allotted": Decimal("15.0"), "used": Decimal("0.0")},
        )

        # 4. EL carry forward & VL->EL conversion (BR-EL-005, BR-EL-007, BR-EL-008)
        unused_el = Decimal("0.0")
        if "EL" in current_balances:
            cur_el = current_balances["EL"]
            unused_el = max(Decimal("0.0"), cur_el.allotted - cur_el.used)

        if is_faculty:
            LeaveBalance.objects.select_for_update().get_or_create(
                employee_id=emp_id,
                year=next_year,
                category="VL",
                defaults={"allotted": Decimal("60.0"), "used": Decimal("0.0")},
            )
            if "VL" in current_balances:
                cur_vl = current_balances["VL"]
                unused_vl = max(Decimal("0.0"), cur_vl.allotted - cur_vl.used)
                _credited, new_el_allotted = convert_vl_to_el(unused_vl, unused_el)
            else:
                new_el_allotted = unused_el
        else:
            new_el_allotted = min(Decimal("300.0"), unused_el + Decimal("30.0"))

        el_obj, _ = LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=emp_id,
            year=next_year,
            category="EL",
            defaults={"allotted": new_el_allotted, "used": Decimal("0.0")},
        )
        if el_obj.allotted != new_el_allotted:
            el_obj.allotted = new_el_allotted
            el_obj.save(update_fields=["allotted"])

        # 6. COL carry forward (BR-EL-009)
        unused_col = Decimal("0.0")
        if "COL" in current_balances:
            cur_col = current_balances["COL"]
            unused_col = max(Decimal("0.0"), cur_col.allotted - cur_col.used)
        new_col_allotted = unused_col + Decimal("20.0")

        col_obj, _ = LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=emp_id,
            year=next_year,
            category="COL",
            defaults={"allotted": new_col_allotted, "used": Decimal("0.0")},
        )
        if col_obj.allotted != new_col_allotted:
            col_obj.allotted = new_col_allotted
            col_obj.save(update_fields=["allotted"])

        processed_count += 1

    return {
        "year": year,
        "next_year": next_year,
        "processed_employees": processed_count,
    }


@transaction.atomic
def record_offline_leave(principal, data: dict) -> LeaveApplication:
    if not (
        principal.has_permission("leave_elm.admin.manage")
        or getattr(principal, "user_id", None) == 1
    ):
        raise PermissionDenied("Only administrators can record offline-sanctioned leave.")

    sanction_ref = data.get("sanction_reference", "").strip()
    if not sanction_ref:
        raise ValidationError(
            {"sanction_reference": "Sanction reference evidence is mandatory for offline leave."}
        )

    employee_id = data.get("employee_id")
    if not employee_id:
        raise ValidationError({"employee_id": "Employee ID is required."})

    profile = get_object_or_404(EmployeeLeaveProfile, user_id=employee_id)
    if LeaveApplication.objects.filter(
        employee_id=employee_id, sanction_reference=sanction_ref
    ).exists():
        raise ValidationError(
            {
                "sanction_reference": (
                    "An offline leave with this sanction reference has already been recorded."
                )
            }
        )
    category = data["category"]
    start = data["start_date"]
    end = data["end_date"]
    half_day = data.get("half_day", "NONE")

    if not eligible(category, profile.category):
        raise ValidationError({"category": "Leave type is not eligible for this employee."})
    if start.year != end.year:
        raise ValidationError({"end_date": "Leave interval must fall within a single year."})
    if start > end:
        raise ValidationError({"end_date": "End date cannot be earlier than start date."})

    closed = get_published_dates(start, end, "CLOSED")
    try:
        duration = count_days(category, start, end, half_day, closed)
    except ValueError as exc:
        raise ValidationError({"duration": str(exc)}) from exc

    balance = _balance_for_update(employee_id, start.year, category)
    try:
        remaining(balance.allotted, balance.used, duration)
    except ValueError as exc:
        raise ValidationError({"balance": str(exc)}) from exc

    for existing in LeaveApplication.objects.select_for_update().filter(
        employee_id=employee_id,
        status__in=(
            "AWAITING_SUB",
            "ACTION_REQUIRED",
            "PENDING",
            "RECOMMENDED",
            "APPROVED",
            "AWAITING_CANCEL",
            "AWAITING_RESUMPTION",
        ),
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

    balance.used += duration
    balance.save(update_fields=["used"])

    unit_head_id = profile.unit_head_user_id or principal.user_id
    sanction_authority_id = profile.sanction_authority_user_id or principal.user_id

    application = LeaveApplication.objects.create(
        employee_id=employee_id,
        category=category,
        start_date=start,
        end_date=end,
        half_day=half_day,
        duration=duration,
        reason=data.get("reason", "Offline sanctioned leave"),
        station_leave=data.get("station_leave", False),
        station_location=data.get("station_location", ""),
        status="APPROVED",
        is_offline=True,
        sanction_reference=sanction_ref,
        unit_head_id=unit_head_id,
        sanction_authority_id=sanction_authority_id,
        approver_id=principal.user_id,
        decided_at=timezone.now(),
        decision_remarks=f"Recorded offline sanction: {sanction_ref}",
    )
    log_event(
        application,
        principal.user_id,
        "offline_leave_recorded",
        f"Sanction reference: {sanction_ref}",
    )
    return application
