"""Service layer for Leave Management (ELM).

All write operations, transaction management, and business logic execution live here.
"""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from modules.elm.domain.entities import STANDARD_LEAVE_CATEGORIES
from modules.elm.domain.errors import (
    ElmDomainError,
    InsufficientLeaveBalanceError,
    OverlappingLeaveError,
)
from modules.elm.domain.policy import is_overlapping, validate_leave_application
from modules.elm.domain.state_machine import ElmStateMachine
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveCategory, LeaveHistory
from modules.elm.selectors import applications as application_selectors


def ensure_leave_categories() -> None:
    """Ensure standard leave categories exist in the database."""
    for spec in STANDARD_LEAVE_CATEGORIES.values():
        LeaveCategory.objects.get_or_create(
            code=spec.code,
            defaults={
                "name": spec.name,
                "annual_quota": spec.annual_quota,
                "carries_forward": spec.carries_forward,
                "continuous_counting": spec.continuous_counting,
                "faculty_only": spec.faculty_only,
                "is_active": True,
            },
        )


def get_or_create_balance(
    user_id: int, category: LeaveCategory, year: int = 2026
) -> LeaveBalance:
    """Get or initialize a user's leave balance for a given category and year."""
    balance, _created = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        category=category,
        year=year,
        defaults={
            "credited": category.annual_quota,
            "consumed": Decimal("0.0"),
            "balance": category.annual_quota,
        },
    )
    return balance


def submit_leave_application(
    user_id: int,
    category_code: str,
    start_date: date,
    end_date: date,
    reason: str,
    half_day: str = "none",
    is_faculty: bool = False,
    station_leave: bool = False,
    station_address: str = "",
    station_start_date: date | None = None,
    station_end_date: date | None = None,
    emergency_contact: str = "",
    substitute_id: int | None = None,
    holidays: set[date] | None = None,
) -> LeaveApplication:
    """Validate and persist a new leave application."""
    ensure_leave_categories()
    category = application_selectors.get_category_by_code(category_code)
    if not category:
        raise ElmDomainError(f"Leave category '{category_code}' does not exist.")

    # Retrieve or initialize balance
    year = start_date.year
    user_balance = get_or_create_balance(user_id=user_id, category=category, year=year)

    # Compute currently pending days for this category and user
    pending_statuses = [
        LeaveApplication.STATUS_PENDING_SUBSTITUTE,
        LeaveApplication.STATUS_SUBMITTED,
        LeaveApplication.STATUS_PENDING_SANCTION,
    ]
    pending_sum = (
        LeaveApplication.objects.filter(
            user_id=user_id, category=category, status__in=pending_statuses
        ).aggregate(total=Sum("days_count"))["total"]
        or Decimal("0.0")
    )

    # Validate application business rules
    requested_days = validate_leave_application(
        category_code=category.code,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        is_faculty=is_faculty,
        current_balance=user_balance.balance,
        pending_days=pending_sum,
        station_leave=station_leave,
        station_address=station_address,
        emergency_contact=emergency_contact,
        substitute_id=substitute_id,
        applicant_id=user_id,
        holidays=holidays,
    )

    # Check for impermissible overlap with applicant's active leaves
    existing_intervals = application_selectors.get_active_intervals_for_user(user_id)
    if is_overlapping(start_date, end_date, half_day, existing_intervals):
        raise OverlappingLeaveError(
            "The requested dates overlap with an existing pending or approved leave."
        )

    # Check substitute availability if nominated
    substitute_status = "none"
    initial_status = LeaveApplication.STATUS_SUBMITTED
    if substitute_id:
        sub_intervals = application_selectors.get_active_intervals_for_user(substitute_id)
        if is_overlapping(start_date, end_date, "none", sub_intervals):
            raise OverlappingLeaveError(
                "The nominated substitute has conflicting leave during this period."
            )
        substitute_status = "pending"
        initial_status = LeaveApplication.STATUS_PENDING_SUBSTITUTE

    with transaction.atomic():
        app = LeaveApplication.objects.create(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            days_count=requested_days,
            reason=reason,
            status=initial_status,
            station_leave=station_leave,
            station_address=station_address if station_leave else "",
            station_start_date=station_start_date if station_leave else None,
            station_end_date=station_end_date if station_leave else None,
            emergency_contact=emergency_contact if station_leave else "",
            substitute_id=substitute_id,
            substitute_status=substitute_status,
        )

        LeaveHistory.objects.create(
            application=app,
            actor_id=user_id,
            action="submitted",
            from_status="none",
            to_status=initial_status,
            remarks=reason,
        )

    return app


def respond_substitute(
    application_id: int,
    substitute_id: int,
    action: str,  # "accept" or "decline"
    remarks: str = "",
) -> LeaveApplication:
    """Record substitute consent response."""
    app = LeaveApplication.objects.select_related("category").get(id=application_id)
    if app.substitute_id != substitute_id:
        raise ElmDomainError("User is not the nominated substitute for this application.")

    new_status, sub_status = ElmStateMachine.transition_substitute(app.status, action)

    with transaction.atomic():
        from_status = app.status
        app.status = new_status
        app.substitute_status = sub_status
        app.substitute_remarks = remarks
        app.substitute_acted_at = timezone.now()
        app.save(
            update_fields=[
                "status",
                "substitute_status",
                "substitute_remarks",
                "substitute_acted_at",
            ]
        )

        LeaveHistory.objects.create(
            application=app,
            actor_id=substitute_id,
            action=f"substitute_{action}",
            from_status=from_status,
            to_status=new_status,
            remarks=remarks,
        )

    return app


def review_unit_head(
    application_id: int,
    actor_id: int,
    action: str,  # "approve", "reject", "recommend", "not_recommend"
    remarks: str = "",
) -> LeaveApplication:
    """Record Unit Head review or final decision for CL/RH."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().select_related("category").get(
            id=application_id
        )

        new_status, rec_value = ElmStateMachine.transition_unit_head(
            category_code=app.category.code,
            current_status=app.status,
            action=action,
        )

        # Deduct balance if final approval by Unit Head (CL/RH)
        if new_status == LeaveApplication.STATUS_APPROVED:
            _deduct_leave_balance(
                user_id=app.user_id,
                category=app.category,
                year=app.start_date.year,
                days=app.days_count,
            )

        from_status = app.status
        app.status = new_status
        app.unit_head_id = actor_id
        app.unit_head_recommendation = rec_value
        app.unit_head_remarks = remarks
        app.unit_head_acted_at = timezone.now()
        app.save(
            update_fields=[
                "status",
                "unit_head_id",
                "unit_head_recommendation",
                "unit_head_remarks",
                "unit_head_acted_at",
            ]
        )

        LeaveHistory.objects.create(
            application=app,
            actor_id=actor_id,
            action=f"unit_head_{action}",
            from_status=from_status,
            to_status=new_status,
            remarks=remarks,
        )

    return app


def review_sanctioning_authority(
    application_id: int,
    actor_id: int,
    action: str,  # "approve" or "reject"
    remarks: str = "",
) -> LeaveApplication:
    """Record Sanctioning Authority final decision for higher-sanction leave."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().select_related("category").get(
            id=application_id
        )

        new_status = ElmStateMachine.transition_sanctioning_authority(
            category_code=app.category.code,
            current_status=app.status,
            action=action,
        )

        # Deduct balance on approval
        if new_status == LeaveApplication.STATUS_APPROVED:
            _deduct_leave_balance(
                user_id=app.user_id,
                category=app.category,
                year=app.start_date.year,
                days=app.days_count,
            )

        from_status = app.status
        app.status = new_status
        app.sanctioning_authority_id = actor_id
        app.sanction_remarks = remarks
        app.sanction_acted_at = timezone.now()
        app.save(
            update_fields=[
                "status",
                "sanctioning_authority_id",
                "sanction_remarks",
                "sanction_acted_at",
            ]
        )

        LeaveHistory.objects.create(
            application=app,
            actor_id=actor_id,
            action=f"sanction_{action}",
            from_status=from_status,
            to_status=new_status,
            remarks=remarks,
        )

    return app


def withdraw_application(
    application_id: int,
    user_id: int,
    remarks: str = "",
) -> LeaveApplication:
    """Withdraw a pending leave application before final approval."""
    with transaction.atomic():
        app = LeaveApplication.objects.select_for_update().select_related("category").get(
            id=application_id
        )

        if app.user_id != user_id:
            raise ElmDomainError("Only the applicant may withdraw this leave application.")

        new_status = ElmStateMachine.transition_withdraw(app.status)
        from_status = app.status
        app.status = new_status
        app.save(update_fields=["status"])

        LeaveHistory.objects.create(
            application=app,
            actor_id=user_id,
            action="withdrawn",
            from_status=from_status,
            to_status=new_status,
            remarks=remarks,
        )

    return app


def _deduct_leave_balance(
    user_id: int, category: LeaveCategory, year: int, days: Decimal
) -> None:
    """Atomically deduct approved leave days from user's balance."""
    bal = (
        LeaveBalance.objects.select_for_update()
        .filter(user_id=user_id, category=category, year=year)
        .first()
    )
    if not bal:
        bal = get_or_create_balance(user_id, category, year)
        bal = (
            LeaveBalance.objects.select_for_update()
            .get(id=bal.id)
        )

    if bal.balance < days:
        raise InsufficientLeaveBalanceError(
            f"Cannot approve: balance ({bal.balance}) is lower than leave duration ({days})."
        )

    bal.consumed += days
    bal.balance -= days
    bal.save(update_fields=["consumed", "balance"])
