"""Application lifecycle write services."""
from __future__ import annotations

import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.domain.categories import (
    CL,
    CONTINUOUS_COUNT_CATEGORIES,
    is_eligible_for_category,
)
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.state_machine import validate_transition
from modules.leave.models import (
    HolidayCalendar,
    LeaveActionHistory,
    LeaveApplication,
    LeaveBalance,
    SubstituteRequest,
    VacationPeriod,
)
from modules.leave.selectors.applications import (
    get_active_overlapping_leaves,
    get_application_by_id,
)
from modules.leave.selectors.balances import get_or_create_balance
from modules.leave.services.notifications import enqueue as enqueue_notification


@transaction.atomic
def apply_for_leave(
    *,
    user_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    purpose: str,
    half_day_type: str = "full",
    substitute_user_id: int | None = None,
    responsibilities: str = "",
    is_station_leave: bool = False,
    station_departure_date: datetime.date | None = None,
    station_arrival_date: datetime.date | None = None,
    station_destination: str = "",
    address_during_leave: str = "",
    is_faculty: bool = False,
    unit_head_user_id: int | None = None,
    establishment_user_id: int | None = None,
    sanctioning_authority_user_id: int | None = None,
) -> LeaveApplication:
    """Submit a leave application (WF-EL-01, EL-UC-001)."""
    if not is_eligible_for_category(category, is_faculty):
        raise BadRequestError(
            f"Employee category is not eligible for leave type {category!r}.",
            code="ineligible_category",
        )

    if category == "VL" and not VacationPeriod.objects.filter(
        year=start_date.year, is_active=True, start_date__lte=start_date, end_date__gte=end_date
    ).exists():
        raise BadRequestError("Vacation Leave must fall inside an active academic vacation period.", code="outside_vacation_period")

    # Overlap validation (BR-EL-012)
    overlapping = get_active_overlapping_leaves(user_id, start_date, end_date)
    for other in overlapping:
        # Half-day CL exception: first_half and second_half on same day can coexist
        if (
            category == CL
            and other.category == CL
            and start_date == other.start_date
            and half_day_type in ("first_half", "second_half")
            and other.half_day_type in ("first_half", "second_half")
            and half_day_type != other.half_day_type
        ):
            continue
        raise ConflictError(
            f"Leave dates overlap with existing leave application #{other.pk} ({other.start_date} to {other.end_date}).",
            code="overlapping_leave",
        )

    # Fetch closed holidays and restricted holidays
    holidays = HolidayCalendar.objects.filter(year=start_date.year, is_published=True)
    closed_dates = {h.date for h in holidays if h.kind == "closed"}
    rh_dates = {h.date for h in holidays if h.kind == "restricted"}

    days_count = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day_type=half_day_type,
        closed_holidays=closed_dates,
        rh_holidays=rh_dates,
    )

    # Balance check
    balance = get_or_create_balance(user_id, start_date.year, is_faculty=is_faculty)
    balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
    available = balance.get_category_balance(category)
    reserved = LeaveApplication.objects.filter(
        user_id=user_id, category=category, start_date__year=start_date.year,
        status__in=["substitute_pending", "under_review", "extension_requested"],
    ).aggregate(total=Sum("days_count"))["total"] or Decimal("0.0")
    if available - reserved < days_count:
        raise ConflictError(
            f"Insufficient unreserved {category} balance. Available: {available - reserved}, Required: {days_count}.",
            code="insufficient_balance",
        )

    # Station leave validation (BR-EL-013)
    if is_station_leave and not station_destination:
        raise BadRequestError("Station leave requires a destination.", code="station_destination_missing")

    # Substitute validation (BR-EL-014)
    initial_status = "under_review"
    if substitute_user_id is not None:
        if substitute_user_id == user_id:
            raise BadRequestError("You cannot nominate yourself as your substitute.", code="substitute_self")
        from modules.directory import contracts as directory
        substitute = directory.get_users([substitute_user_id]).get(substitute_user_id)
        if substitute is None or substitute.kind not in {"faculty", "staff"}:
            raise BadRequestError("Substitute must be another active employee.", code="invalid_substitute")
        # Check if substitute has overlapping leave
        sub_overlap = get_active_overlapping_leaves(substitute_user_id, start_date, end_date)
        if sub_overlap.exists():
            raise ConflictError(
                "Nominated substitute has pending or approved leave during this period.",
                code="substitute_unavailable",
            )
        initial_status = "substitute_pending"

    app = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day_type=half_day_type,
        days_count=days_count,
        purpose=purpose,
        address_during_leave=address_during_leave,
        is_station_leave=is_station_leave,
        station_departure_date=station_departure_date,
        station_arrival_date=station_arrival_date,
        station_destination=station_destination,
        unit_head_user_id=unit_head_user_id,
        establishment_user_id=establishment_user_id,
        sanctioning_authority_user_id=sanctioning_authority_user_id,
        status=initial_status,
    )

    if substitute_user_id is not None:
        SubstituteRequest.objects.create(
            application=app,
            substitute_user_id=substitute_user_id,
            responsibilities=responsibilities,
            status="pending",
        )
        enqueue_notification(
            recipient_user_id=substitute_user_id, topic="substitute.assigned",
            dedupe_key=f"leave:{app.pk}:substitute:{substitute_user_id}",
            subject="Leave responsibility request",
            body=f"You have been nominated as a substitute for leave request #{app.pk}.",
        )
    else:
        enqueue_notification(
            recipient_user_id=unit_head_user_id or sanctioning_authority_user_id,
            topic="application.assigned", dedupe_key=f"leave:{app.pk}:assigned",
            subject="Leave request requires review",
            body=f"Leave request #{app.pk} is awaiting your review.",
        )

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=user_id,
        actor_role="employee",
        action="submitted",
        remarks=purpose[:100],
    )
    return app


@transaction.atomic
def withdraw_application(*, user_id: int, application_id: int, reason: str = "") -> LeaveApplication:
    """Withdraw a pending application immediately (BR-EL-022, EL-UC-007, WF-EL-02)."""
    app = get_application_by_id(application_id, user_id=user_id, for_update=True)
    if app.status not in ("substitute_pending", "under_review", "extension_requested"):
        raise ConflictError(
            f"Cannot withdraw an application in status {app.status!r}. Only pending applications can be withdrawn.",
            code="cannot_withdraw",
        )

    validate_transition(app.status, "withdrawn")
    app.status = "withdrawn"
    app.save(update_fields=["status", "updated_at"])

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=user_id,
        actor_role="employee",
        action="withdrawn",
        remarks=reason,
    )
    for assigned_id in {app.unit_head_user_id, app.establishment_user_id, app.sanctioning_authority_user_id}:
        enqueue_notification(
            recipient_user_id=assigned_id, topic="application.withdrawn",
            dedupe_key=f"leave:{app.pk}:withdrawn:{assigned_id}",
            subject="Leave request withdrawn", body=f"Leave request #{app.pk} was withdrawn by the employee.",
        )

    return app


@transaction.atomic
def request_cancellation(*, user_id: int, application_id: int, reason: str) -> LeaveApplication:
    """Request cancellation of an approved leave before it starts (BR-EL-023, EL-UC-008, WF-EL-03)."""
    app = get_application_by_id(application_id, user_id=user_id, for_update=True)
    if app.status != "approved":
        raise ConflictError("Only approved leave can be cancelled.", code="not_approved")
    if app.extensions.filter(status="cancel_requested").exists():
        raise ConflictError("A cancellation request is already pending for this leave.", code="cancellation_already_pending")

    today = timezone.localdate()
    if app.start_date <= today:
        raise ConflictError(
            "Pre-start cancellation cannot be requested after leave has started. Use resumption instead.",
            code="leave_already_started",
        )

    validate_transition(app.status, "cancel_requested")
    cancellation = LeaveApplication.objects.create(
        user_id=app.user_id, category=app.category, start_date=app.start_date,
        end_date=app.end_date, half_day_type=app.half_day_type, days_count=Decimal("0.0"),
        purpose=f"Cancellation of leave #{app.pk}", status="cancel_requested",
        parent_leave=app, cancellation_reason=reason,
        unit_head_user_id=app.unit_head_user_id,
        establishment_user_id=app.establishment_user_id,
        sanctioning_authority_user_id=app.sanctioning_authority_user_id,
    )

    LeaveActionHistory.objects.create(
        application=cancellation,
        actor_user_id=user_id,
        actor_role="employee",
        action="cancel_requested",
        remarks=reason,
    )
    enqueue_notification(
        recipient_user_id=cancellation.unit_head_user_id or cancellation.establishment_user_id or cancellation.sanctioning_authority_user_id,
        topic="cancellation.assigned", dedupe_key=f"leave:{cancellation.pk}:assigned",
        subject="Leave cancellation requires review",
        body=f"Cancellation request #{cancellation.pk} for leave #{app.pk} is awaiting review.",
    )

    return cancellation


@transaction.atomic
def request_extension(
    *, user_id: int, application_id: int, start_date: datetime.date,
    end_date: datetime.date, purpose: str, substitute_user_id: int | None = None,
    responsibilities: str = "", is_faculty: bool = False,
) -> LeaveApplication:
    """Create an incremental extension application for an ongoing EL/COL/VL."""
    parent = get_application_by_id(application_id, user_id=user_id, for_update=True)
    today = timezone.localdate()
    if parent.status != "approved" or parent.category not in {"EL", "COL", "VL"}:
        raise ConflictError("Only approved ongoing EL, COL, or VL can be extended.", code="extension_not_allowed")
    if not (parent.start_date <= today <= parent.end_date):
        raise ConflictError("Extensions are available only while the leave is ongoing.", code="leave_not_ongoing")
    if start_date != parent.end_date + datetime.timedelta(days=1):
        raise BadRequestError("An extension must begin the day after the approved end date.", code="invalid_extension_period")
    extension = apply_for_leave(
        user_id=user_id, category=parent.category, start_date=start_date, end_date=end_date,
        purpose=purpose, substitute_user_id=substitute_user_id,
        responsibilities=responsibilities, is_faculty=is_faculty,
        unit_head_user_id=parent.unit_head_user_id,
        establishment_user_id=parent.establishment_user_id,
        sanctioning_authority_user_id=parent.sanctioning_authority_user_id,
    )
    extension.parent_leave = parent
    if extension.status != "substitute_pending":
        extension.status = "extension_requested"
    extension.save(update_fields=["parent_leave", "status", "updated_at"])
    LeaveActionHistory.objects.create(
        application=extension, actor_user_id=user_id, actor_role="employee",
        action="extension_requested", remarks=f"Extends leave #{parent.pk}",
    )
    return extension


@transaction.atomic
def maintain_finalized_record(*, admin_user_id: int, application_id: int, reason: str, changes: dict) -> LeaveApplication:
    """Correct descriptive fields on a finalized record without changing sanction or balance."""
    app = get_application_by_id(application_id, for_update=True)
    if app.status not in {"approved", "rejected", "cancelled", "resumption_reviewed"}:
        raise ConflictError("Only finalized leave records can be administratively corrected.", code="record_not_finalized")
    allowed = {
        "purpose", "address_during_leave", "is_station_leave", "station_departure_date",
        "station_arrival_date", "station_destination",
    }
    updates = {key: value for key, value in changes.items() if key in allowed}
    if not updates:
        raise BadRequestError("Provide at least one record field to correct.", code="empty_record_correction")
    destination = updates.get("station_destination", app.station_destination)
    station_leave = updates.get("is_station_leave", app.is_station_leave)
    if station_leave and not destination:
        raise BadRequestError("Station leave requires a destination.", code="station_destination_missing")
    departure = updates.get("station_departure_date", app.station_departure_date)
    arrival = updates.get("station_arrival_date", app.station_arrival_date)
    if departure and arrival and arrival < departure:
        raise BadRequestError("Station arrival cannot be earlier than departure.", code="invalid_station_dates")
    for key, value in updates.items():
        setattr(app, key, value)
    app.save(update_fields=[*updates, "updated_at"])
    LeaveActionHistory.objects.create(
        application=app, actor_user_id=admin_user_id, actor_role="leave_admin",
        action="record_maintained", remarks=reason,
    )
    return app
