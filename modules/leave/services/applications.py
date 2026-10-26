# Application services handling transactions and workflows for ELM
from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.calculations import calculate_leave_days
from modules.leave.domain.constants import (
    ACTIVE_STATUSES,
    DEFAULT_ANNUAL_ENTITLEMENTS,
    HALF_DAY_NONE,
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
)
from modules.leave.domain.state_machine import (
    ACTOR_APPLICANT,
    ACTOR_APPROVER,
    validate_transition,
)
from modules.leave.domain.validation import (
    validate_approver_identity,
    validate_balance_sufficiency,
    validate_leave_overlap,
    validate_station_leave,
)
from modules.leave.models import LeaveApplication, LeaveBalance


def initialize_user_balances(user_id: int, year: int) -> list[LeaveBalance]:
    """Ensure default balances exist for user for the given year."""
    balances = []
    with transaction.atomic():
        for leave_type, allocated in DEFAULT_ANNUAL_ENTITLEMENTS.items():
            balance, _ = LeaveBalance.objects.get_or_create(
                user_id=user_id,
                leave_type=leave_type,
                year=year,
                defaults={"allocated": allocated, "used": Decimal("0.00")},
            )
            balances.append(balance)
    return balances


def submit_application(
    user_id: int,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    half_day: str = HALF_DAY_NONE,
    is_station_leave: bool = False,
    station_leave_address: str = "",
    replacement_user_id: int | None = None,
) -> LeaveApplication:
    """Submit a new leave application with validation, counting, and concurrency locking."""
    # Validate station leave requirements (BR-EL-013)
    validate_station_leave(is_station_leave, station_leave_address)

    # Calculate leave days accurately (BR-EL-010, BR-EL-011)
    days = calculate_leave_days(leave_type, start_date, end_date, half_day)

    with transaction.atomic():
        # Check leave balance under row lock
        balance = LeaveBalance.objects.select_for_update().filter(
            user_id=user_id,
            leave_type=leave_type,
            year=start_date.year,
        ).first()

        if not balance:
            # Initialize if not yet created for this year
            initialize_user_balances(user_id, start_date.year)
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=user_id,
                leave_type=leave_type,
                year=start_date.year,
            )

        validate_balance_sufficiency(balance.allocated, balance.used, days, leave_type)

        # Check for overlap against active applications (BR-EL-012)
        existing_active = list(
            LeaveApplication.objects.filter(
                user_id=user_id,
                status__in=ACTIVE_STATUSES,
            )
        )
        validate_leave_overlap(
            start_date,
            end_date,
            leave_type,
            half_day,
            existing_active,
        )

        return LeaveApplication.objects.create(
            user_id=user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            days=days,
            reason=reason,
            is_station_leave=is_station_leave,
            station_leave_address=station_leave_address if is_station_leave else "",
            replacement_user_id=replacement_user_id,
            status=STATUS_PENDING,
        )


def review_application(
    application_id: int,
    reviewer_user_id: int,
    action: str,
    remarks: str = "",
) -> LeaveApplication:
    """Review (approve or reject) a pending leave application."""
    target_status = STATUS_APPROVED if action.upper() == "APPROVE" else STATUS_REJECTED

    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().filter(pk=application_id).first()
        if not application:
            raise NotFoundError("Leave application not found.")

        # Self-approval prevention (BR-EL-036)
        validate_approver_identity(application.user_id, reviewer_user_id)

        # State transition validation
        validate_transition(application.status, target_status, ACTOR_APPROVER)

        if target_status == STATUS_APPROVED:
            balance = LeaveBalance.objects.select_for_update().filter(
                user_id=application.user_id,
                leave_type=application.leave_type,
                year=application.start_date.year,
            ).first()

            if not balance:
                initialize_user_balances(application.user_id, application.start_date.year)
                balance = LeaveBalance.objects.select_for_update().get(
                    user_id=application.user_id,
                    leave_type=application.leave_type,
                    year=application.start_date.year,
                )

            validate_balance_sufficiency(
                balance.allocated,
                balance.used,
                application.days,
                application.leave_type,
            )
            balance.used += application.days
            balance.save()

        application.status = target_status
        application.reviewed_by = reviewer_user_id
        application.review_remarks = remarks
        application.save()

    return application


def withdraw_application(
    application_id: int,
    user_id: int,
) -> LeaveApplication:
    """Withdraw a pending leave application before final approval (BR-EL-022)."""
    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().filter(pk=application_id).first()
        if not application:
            raise NotFoundError("Leave application not found.")

        if application.user_id != user_id:
            raise PermissionDeniedError("Only the applicant may withdraw their own application.")

        validate_transition(application.status, STATUS_WITHDRAWN, ACTOR_APPLICANT)

        application.status = STATUS_WITHDRAWN
        application.save()

    return application


def cancel_application(
    application_id: int,
    user_id: int,
    is_approver: bool = False,
) -> LeaveApplication:
    """Cancel an approved leave application prior to start date and restore balance (BR-EL-023)."""
    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().filter(pk=application_id).first()
        if not application:
            raise NotFoundError("Leave application not found.")

        if not is_approver and application.user_id != user_id:
            raise PermissionDeniedError("Only applicant or approver may cancel this application.")

        actor_kind = ACTOR_APPROVER if is_approver else ACTOR_APPLICANT
        validate_transition(application.status, STATUS_CANCELLED, actor_kind)

        # Enforce pre-start boundary (BR-EL-023)
        today = date.today()
        if today >= application.start_date:
            raise ConflictError("An approved leave cannot be cancelled once start date arrived.")

        # Restore deducted balance
        balance = LeaveBalance.objects.select_for_update().filter(
            user_id=application.user_id,
            leave_type=application.leave_type,
            year=application.start_date.year,
        ).first()

        if balance:
            balance.used = max(Decimal("0.00"), balance.used - application.days)
            balance.save()

        application.status = STATUS_CANCELLED
        application.save()

    return application
