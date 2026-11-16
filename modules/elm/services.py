"""Transactional ELM application and decision services."""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm.models import (
    EmployeeLeaveBalance,
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveCategory,
)
from modules.elm.selectors import PENDING_STATUSES

ZERO = Decimal("0.00")
HALF = Decimal("0.50")
SUPPORTED_CATEGORIES = {"CL", "RH", "SCL", "EL", "COL", "VL"}


def get_leave_category(code):
    try:
        return LeaveCategory.objects.get(code=code)
    except LeaveCategory.DoesNotExist as exc:
        raise BadRequestError(
            "Choose a supported leave category.", code="invalid_leave_category"
        ) from exc


def chargeable_days(category, start, end, half_type=""):
    """Count the requested interval using the category's configured rule."""
    if not isinstance(start, date) or not isinstance(end, date) or end < start:
        raise BadRequestError(
            "The end date must be on or after the start date.", code="invalid_leave_period"
        )

    if half_type:
        if category.code != "CL" or start != end or half_type not in {"FIRST_HALF", "SECOND_HALF"}:
            raise BadRequestError(
                "Half-day requests are supported only for one-day CL requests.",
                code="invalid_half_day",
            )
        return HALF

    days = (end - start).days + 1
    if category.continuous_counting:
        return Decimal(days)

    # Non-continuous categories count weekdays. RH additionally requires the
    # published institute calendar, which is not part of this baseline model.
    count = sum(1 for offset in range(days) if (start + timedelta(days=offset)).weekday() < 5)
    return Decimal(count)


def _eligible(category, employee_kind):
    if category.code not in SUPPORTED_CATEGORIES or employee_kind not in {"faculty", "staff"}:
        return False
    if category.code == "VL":
        return employee_kind == "faculty"
    if category.code == "EL":
        return employee_kind == "staff"
    return True


def _balance_for_update(user_id, category):
    balance, _ = EmployeeLeaveBalance.objects.get_or_create(
        user_id=user_id,
        leave_category=category,
        defaults={
            "remaining_days": Decimal(category.entitlement_days),
            "used_days": ZERO,
        },
    )
    return EmployeeLeaveBalance.objects.select_for_update().get(pk=balance.pk)


def _pending_reserved_days(user_id, category, exclude_id=None):
    applications = LeaveApplication.objects.filter(
        user_id=user_id,
        leave_category=category,
        status__in=PENDING_STATUSES,
    )
    if exclude_id is not None:
        applications = applications.exclude(pk=exclude_id)
    return sum(
        (
            chargeable_days(
                app.leave_category, app.requested_start, app.requested_end, app.halftype
            )
            for app in applications
        ),
        ZERO,
    )


def _has_overlap(user_id, category, start, end, half_type="", exclude_id=None):
    applications = LeaveApplication.objects.select_for_update().filter(
        user_id=user_id,
        status__in=(*PENDING_STATUSES, "sanctioned"),
        requested_start__lte=end,
        requested_end__gte=start,
    )
    if exclude_id is not None:
        applications = applications.exclude(pk=exclude_id)

    for existing in applications:
        complementary_cl_halves = (
            category.code == existing.leave_category.code == "CL"
            and start == end == existing.requested_start == existing.requested_end
            and half_type in {"FIRST_HALF", "SECOND_HALF"}
            and existing.halftype in {"FIRST_HALF", "SECOND_HALF"}
            and half_type != existing.halftype
        )
        if not complementary_cl_halves:
            return True
    return False


@transaction.atomic
def can_apply_leave(user_id, employee_kind, category_code, start, end, half_type=""):
    category = get_leave_category(category_code)
    if not _eligible(category, employee_kind):
        return {
            "allowed": False,
            "reason": "This leave category is not available to your employee type.",
        }
    requested = chargeable_days(category, start, end, half_type)
    if requested <= ZERO:
        raise BadRequestError(
            "The requested period contains no chargeable leave days.", code="empty_leave_period"
        )
    balance = EmployeeLeaveBalance.objects.filter(user_id=user_id, leave_category=category).first()
    available = balance.remaining_days if balance else Decimal(category.entitlement_days)
    reserved = _pending_reserved_days(user_id, category)
    if available - reserved < requested:
        return {
            "allowed": False,
            "reason": "The available balance is insufficient for this request.",
        }
    if _has_overlap(user_id, category, start, end, half_type):
        return {"allowed": False, "reason": "The requested period overlaps active leave."}
    if category.code == "RH":
        return {
            "allowed": False,
            "reason": "The published Restricted Holiday calendar is not configured.",
        }
    if category.code == "VL":
        return {
            "allowed": False,
            "reason": "Vacation-period validation requires the Academic Calendar integration.",
        }
    return {"allowed": True, "reason": "Eligible for leave application."}


@transaction.atomic
def submit_leave_application(
    user_id,
    employee_kind,
    category_code,
    start,
    end,
    purpose,
    half_type="",
    station_leave=False,
    station_leave_details="",
):
    category = get_leave_category(category_code)
    _balance_for_update(user_id, category)
    verdict = can_apply_leave(user_id, employee_kind, category_code, start, end, half_type)
    if not verdict["allowed"]:
        raise ConflictError(verdict["reason"], code="leave_request_not_allowed")

    app = LeaveApplication.objects.create(
        user_id=user_id,
        leave_category=category,
        requested_start=start,
        requested_end=end,
        purpose=purpose.strip(),
        halftype=half_type,
        station_leave=station_leave,
        station_leave_details=station_leave_details.strip(),
        status="submitted",
    )
    _record_transition(app, "", "submitted", user_id, "Employee", purpose)
    # Pending requests reserve entitlement during validation, but do not debit
    # the account until a final approval is recorded.
    return app


def _record_transition(app, from_status, to_status, actor_id, actor_label, reason=""):
    LeaveApplicationTransition.objects.create(
        application=app,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor_id,
        actor_label=actor_label[:80],
        reason=(reason or "")[:300],
    )


def _load_locked_application(application_id):
    try:
        return (
            LeaveApplication.objects.select_for_update()
            .select_related("leave_category")
            .get(pk=application_id)
        )
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError("Leave application not found.") from exc


@transaction.atomic
def process_unit_head_review(application_id, outcome, actor_id, actor_label, reason=""):
    app = _load_locked_application(application_id)
    if app.status != "submitted":
        raise ConflictError(
            "This request is no longer awaiting Unit Head review.", code="invalid_leave_transition"
        )
    category_code = app.leave_category.code
    if category_code in {"CL", "RH"}:
        if outcome not in {"approve", "reject"}:
            raise BadRequestError(
                "The Unit Head must approve or reject CL/RH.", code="invalid_decision"
            )
        return _finish_decision(app, outcome, actor_id, actor_label, reason)
    if outcome not in {"recommend", "not_recommend"}:
        raise BadRequestError(
            "The Unit Head must record a recommendation for this category.",
            code="invalid_decision",
        )
    new_status = "recommended" if outcome == "recommend" else "not_recommended"
    old_status = app.status
    app.status = new_status
    app.save(update_fields=["status", "updated_at"])
    _record_transition(app, old_status, new_status, actor_id, actor_label, reason)
    return app


@transaction.atomic
def approve_leave_application(application_id, outcome, actor_id, actor_label, reason=""):
    app = _load_locked_application(application_id)
    if app.status not in {"recommended", "not_recommended", "establishment_review"}:
        raise ConflictError(
            "This request is not awaiting a final sanctioning decision.",
            code="invalid_leave_transition",
        )
    if outcome not in {"approve", "reject"}:
        raise BadRequestError(
            "The final decision must be approve or reject.", code="invalid_decision"
        )
    return _finish_decision(app, outcome, actor_id, actor_label, reason)


def _finish_decision(app, outcome, actor_id, actor_label, reason=""):
    old_status = app.status
    new_status = "sanctioned" if outcome == "approve" else "rejected"
    if new_status == "sanctioned":
        balance = _balance_for_update(app.user_id, app.leave_category)
        days = chargeable_days(
            app.leave_category, app.requested_start, app.requested_end, app.halftype
        )
        reserved_elsewhere = _pending_reserved_days(
            app.user_id, app.leave_category, exclude_id=app.pk
        )
        if balance.remaining_days - reserved_elsewhere < days:
            raise ConflictError(
                "The remaining balance no longer covers this request.",
                code="insufficient_leave_balance",
            )
        balance.remaining_days -= days
        balance.used_days += days
        balance.save(update_fields=["remaining_days", "used_days", "updated_at"])
    app.status = new_status
    app.save(update_fields=["status", "updated_at"])
    _record_transition(app, old_status, new_status, actor_id, actor_label, reason)
    return app


@transaction.atomic
def withdraw_leave_application(application_id, owner_id):
    app = _load_locked_application(application_id)
    if app.user_id != owner_id:
        raise NotFoundError("Leave application not found.")
    if app.status not in PENDING_STATUSES:
        raise ConflictError(
            "Only a pending request can be withdrawn.", code="withdrawal_not_allowed"
        )
    old_status = app.status
    app.status = "withdrawn"
    app.save(update_fields=["status", "updated_at"])
    _record_transition(
        app, old_status, "withdrawn", owner_id, "Employee", "Employee withdrew the pending request."
    )
    return app
