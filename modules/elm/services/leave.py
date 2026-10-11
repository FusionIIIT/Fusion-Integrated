from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from modules.elm.domain.constants import (
    LeaveType,
    HalfDayChoice,
    ApplicationStatus,
    DEFAULT_ENTITLEMENTS,
    CONTINUOUS_COUNTING_LEAVES,
    UNIT_HEAD_FINAL_LEAVES,
)
from modules.elm.models import (
    LeaveBalance,
    LeaveApplication,
    LeaveActionHistory,
    Holiday,
)


def ensure_initial_balances(user_id: int, year: int = 2026) -> list[LeaveBalance]:
    """Ensure standard initial leave balances exist for this user in the given year."""
    balances = []
    for leave_type, default_val in DEFAULT_ENTITLEMENTS.items():
        bal, _ = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=year,
            leave_type=leave_type.value,
            defaults={"allocated": Decimal(str(default_val)), "availed": Decimal("0.0"), "pending": Decimal("0.0")},
        )
        balances.append(bal)
    return balances


def calculate_leave_days(
    leave_type: str,
    start_date: date,
    start_half: str = HalfDayChoice.FULL.value,
    end_date: date | None = None,
    end_half: str = HalfDayChoice.FULL.value,
) -> Decimal:
    """Calculate the number of leave days taking into account counting rules."""
    if end_date is None:
        end_date = start_date

    if end_date < start_date:
        raise ValidationError("End date cannot be earlier than start date.")

    if start_date == end_date:
        if start_half in [HalfDayChoice.FIRST_HALF.value, HalfDayChoice.SECOND_HALF.value]:
            return Decimal("0.5")
        return Decimal("1.0")

    is_continuous = leave_type in CONTINUOUS_COUNTING_LEAVES
    holidays = set(Holiday.objects.filter(is_restricted=False).values_list("date", flat=True))

    curr = start_date
    count = Decimal("0.0")

    while curr <= end_date:
        # If continuous: count all days. Otherwise: skip weekends (Sat=5, Sun=6) and closed holidays.
        if is_continuous:
            count += Decimal("1.0")
        else:
            if curr.weekday() < 5 and curr not in holidays:
                count += Decimal("1.0")
        curr += timedelta(days=1)

    # Adjust for half days at ends if applicable
    if start_half != HalfDayChoice.FULL.value:
        count -= Decimal("0.5")
    if end_half != HalfDayChoice.FULL.value:
        count -= Decimal("0.5")

    return max(count, Decimal("0.5"))


@transaction.atomic
def submit_leave_application(
    user_id: int,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    start_half: str = HalfDayChoice.FULL.value,
    end_half: str = HalfDayChoice.FULL.value,
    station_leave: bool = False,
    station_address: str = "",
    station_contact: str = "",
    emergency_contact: str = "",
    substitute_user_id: int | None = None,
) -> LeaveApplication:
    """Submit a leave application and update pending balance."""
    ensure_initial_balances(user_id, year=start_date.year)

    # Check for active overlaps
    overlapping = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=[
            ApplicationStatus.SUBMITTED.value,
            ApplicationStatus.RECOMMENDED.value,
            ApplicationStatus.APPROVED.value,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if overlapping.exists():
        # Check if it's the half-day CL non-overlap exception on the same day
        if (
            leave_type == LeaveType.CL.value
            and start_date == end_date
            and overlapping.count() == 1
            and overlapping.first().start_date == start_date
            and overlapping.first().end_date == end_date
            and overlapping.first().start_half != start_half
            and start_half != HalfDayChoice.FULL.value
            and overlapping.first().start_half != HalfDayChoice.FULL.value
        ):
            pass  # Allowed exception: different halves of same day
        else:
            raise ValidationError("You already have an active or pending leave request for the selected dates.")

    days = calculate_leave_days(leave_type, start_date, start_half, end_date, end_half)

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=user_id,
        year=start_date.year,
        leave_type=leave_type,
    )

    if Decimal(str(balance.available_balance)) < days:
        raise ValidationError(
            f"Insufficient leave balance. Requested: {days}, Available: {balance.available_balance}"
        )

    # Reserve pending balance
    balance.pending += days
    balance.save(update_fields=["pending", "updated_at"])

    app = LeaveApplication.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        start_half=start_half,
        end_date=end_date,
        end_half=end_half,
        days_requested=days,
        reason=reason,
        station_leave=station_leave,
        station_address=station_address,
        station_contact=station_contact,
        emergency_contact=emergency_contact,
        substitute_user_id=substitute_user_id,
        status=ApplicationStatus.SUBMITTED.value,
    )

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=user_id,
        action="SUBMIT",
        comments=f"Submitted leave request for {days} days.",
    )

    return app


@transaction.atomic
def review_leave_application(
    app_id: int,
    actor_user_id: int,
    recommend: bool,
    comments: str = "",
) -> LeaveApplication:
    """Unit Head review: recommend, not-recommend, or direct decision."""
    app = LeaveApplication.objects.select_for_update().get(id=app_id)

    if app.status != ApplicationStatus.SUBMITTED.value:
        raise ValidationError("Application is not in a state awaiting review.")

    # If this is CL or RH, Unit Head makes the final decision
    if app.leave_type in UNIT_HEAD_FINAL_LEAVES:
        return sanction_leave_application(
            app_id=app_id,
            actor_user_id=actor_user_id,
            approve=recommend,
            comments=comments,
        )

    # For higher-sanction leaves (EL, COL, VL, SCL): record recommendation
    new_status = (
        ApplicationStatus.RECOMMENDED.value
        if recommend
        else ApplicationStatus.NOT_RECOMMENDED.value
    )
    app.status = new_status
    app.unit_head_user_id = actor_user_id
    app.save(update_fields=["status", "unit_head_user_id", "updated_at"])

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=actor_user_id,
        action="RECOMMEND" if recommend else "NOT_RECOMMEND",
        comments=comments,
    )
    return app


@transaction.atomic
def sanction_leave_application(
    app_id: int,
    actor_user_id: int,
    approve: bool,
    comments: str = "",
) -> LeaveApplication:
    """Final sanctioning authority approves or rejects the leave."""
    app = LeaveApplication.objects.select_for_update().get(id=app_id)

    if app.status not in [
        ApplicationStatus.SUBMITTED.value,
        ApplicationStatus.RECOMMENDED.value,
        ApplicationStatus.NOT_RECOMMENDED.value,
    ]:
        raise ValidationError(f"Cannot sanction an application with status {app.status}.")

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=app.user_id,
        year=app.start_date.year,
        leave_type=app.leave_type,
    )

    if approve:
        app.status = ApplicationStatus.APPROVED.value
        balance.pending = max(Decimal("0.0"), balance.pending - app.days_requested)
        balance.availed += app.days_requested
        balance.save(update_fields=["pending", "availed", "updated_at"])
    else:
        app.status = ApplicationStatus.REJECTED.value
        balance.pending = max(Decimal("0.0"), balance.pending - app.days_requested)
        balance.save(update_fields=["pending", "updated_at"])

    app.sanctioning_authority_user_id = actor_user_id
    app.remarks = comments
    app.save(update_fields=["status", "sanctioning_authority_user_id", "remarks", "updated_at"])

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=actor_user_id,
        action="APPROVE" if approve else "REJECT",
        comments=comments,
    )
    return app


@transaction.atomic
def cancel_leave_application(app_id: int, actor_user_id: int) -> LeaveApplication:
    """Withdraw/cancel a pending leave application."""
    app = LeaveApplication.objects.select_for_update().get(id=app_id)

    if app.user_id != actor_user_id:
        raise ValidationError("Only the applicant can cancel this application.")

    if app.status not in [ApplicationStatus.SUBMITTED.value, ApplicationStatus.RECOMMENDED.value]:
        raise ValidationError("Only submitted or recommended leaves can be cancelled.")

    balance = LeaveBalance.objects.select_for_update().get(
        user_id=app.user_id,
        year=app.start_date.year,
        leave_type=app.leave_type,
    )

    balance.pending = max(Decimal("0.0"), balance.pending - app.days_requested)
    balance.save(update_fields=["pending", "updated_at"])

    app.status = ApplicationStatus.CANCELLED.value
    app.save(update_fields=["status", "updated_at"])

    LeaveActionHistory.objects.create(
        application=app,
        actor_user_id=actor_user_id,
        action="CANCEL",
        comments="Cancelled by applicant.",
    )
    return app
