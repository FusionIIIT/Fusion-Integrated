from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError
from modules.leave.domain import policy
from modules.leave.models import (
    LeaveAction,
    LeaveApplication,
    LeaveBalance,
    ReportingLine,
    RequestKind,
    Stage,
    Status,
    SubstituteStatus,
)


class LeaveError(BadRequestError):
    code = "leave_error"


class NotFound(NotFoundError):
    pass


def log_action(app: LeaveApplication, actor_id: int, action: str, remark: str = "") -> None:
    """Append an entry to the leave action history."""
    LeaveAction.objects.create(
        application=app,
        actor_id=actor_id,
        action=action,
        remark=remark,
    )


def get_balance(user_id: int, kind: str, category: str, year: int) -> LeaveBalance:
    """Get or create leave balance for a user.

    Raises LeaveError if the user is not eligible for the category/kind combination.
    """
    try:
        entitlement = policy.entitlement(category, kind)
    except policy.PolicyError as e:
        raise LeaveError(str(e)) from e

    if entitlement is None:
        raise LeaveError(f"Not eligible for {category} leave as {kind}.")

    balance, created = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        year=year,
        category=category,
        defaults={
            "entitled": policy.ENTITLEMENT[category][0],
            "used": Decimal("0"),
        },
    )

    if not created:
        # Ensure entitled matches policy (in case of manual edits or data sync issues)
        balance.entitled = policy.ENTITLEMENT[category][0]
        balance.save()

    return balance


def has_overlap(
    user_id: int, start: date, end: date, half_day: str, exclude_id: int | None = None
) -> bool:
    """Check if the user has an overlapping leave application.

    Considers PENDING or APPROVED LEAVE-kind applications.
    Applies BR-EL-012 exception for CL half-days on single dates.
    """
    # Determine which categories count as "LEAVE" for overlap purposes (excluding CANCELLATION)
    leave_categories = [
        cat[0]
        for cat in LeaveApplication._meta.get_field("category").choices
        if cat[0] != "CANCELLATION"
    ]

    applications = LeaveApplication.objects.filter(
        user_id=user_id,
        kind=RequestKind.LEAVE.value,
        category__in=leave_categories,
        status__in=[Status.PENDING.value, Status.APPROVED.value],
    )

    # Exclude the current application if provided
    if exclude_id is not None:
        applications = applications.exclude(id=exclude_id)

    for app in applications:
        # Calculate overlap using policy logic
        is_overlapping = policy.overlaps(
            app.start_date, app.end_date, app.half_day, start, end, half_day
        )
        if is_overlapping:
            return True

    return False


def route_to_approver(app: LeaveApplication) -> None:
    """Route the application to the appropriate approver based on hierarchy.

    - If unit_head_id == user_id (self-sanctioning authority): go to SANCTION.
    - If no sanctioning_authority_id: self-sanction (SANCTION).
    - Otherwise: route to UNIT_HEAD first, then ESTABLISHMENT, then SANCTION.
    """
    # Determine the initial assignee based on category and hierarchy
    if app.unit_head_id == app.user_id:
        # Self-sanctioning authority (e.g., Director)
        app.stage = Stage.SANCTION.value
        app.assignee_id = app.sanctioning_authority_id or app.user_id
    else:
        # Standard hierarchy: Unit Head -> Establishment -> Sanctioning Authority
        # Per DESIGN.md, we route to UNIT_HEAD first for review/recommendation
        app.stage = Stage.UNIT_HEAD.value
        app.assignee_id = app.unit_head_id

    app.save()


@transaction.atomic
def apply_leave(user_id: int, kind: str, data: dict) -> LeaveApplication:
    """Create and submit a new leave application.

    Validates eligibility, balance, overlaps, and substitutes.
    Routes the application to the appropriate approver.
    """
    category = data["category"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    half_day = data.get("half_day", "none")
    purpose = data["purpose"]
    station_leave = data.get("station_leave", False)
    station_address = data.get("station_address", "")
    substitute_id = data.get("substitute_id")

    # 1. Check eligibility (BR-EL-001, BR-EL-005, etc.)
    try:
        entitlement = policy.entitlement(category, kind)
    except policy.PolicyError as e:
        raise LeaveError(str(e)) from e

    if entitlement is None:
        raise LeaveError(f"Not eligible for {category} leave as {kind}.")

    # 2. Compute days (BR-EL-010, BR-EL-011)
    try:
        days = policy.count_days(category, start_date, end_date, half_day)
    except policy.PolicyError as e:
        raise LeaveError(str(e)) from e

    if days <= 0:
        raise LeaveError(f"Invalid leave duration: {days} days.")

    # 3. Check balance (BR-EL-025)
    balance = get_balance(user_id, kind, category, start_date.year)

    if balance.available < days:
        raise LeaveError(
            f"Insufficient leave balance. Available: {balance.available}, Required: {days}."
        )

    # 4. Check overlap (BR-EL-012)
    if has_overlap(user_id, start_date, end_date, half_day):
        raise LeaveError("Leave application overlaps with existing pending or approved leave.")

    # 5. Handle substitute logic (BR-EL-014)
    if substitute_id is not None:
        # Reject if substitute is the applicant
        if substitute_id == user_id:
            raise LeaveError("Substitute cannot be the applicant.")

        if has_overlap(substitute_id, start_date, end_date, half_day):
            raise LeaveError("The substitute is on leave on these dates.")

        # Set stage to SUBSTITUTE
        line = ReportingLine.objects.filter(user_id=user_id).first()
        if line is None:
            raise LeaveError("No reporting line configured.")

        app = LeaveApplication.objects.create(
            user_id=user_id,
            kind=RequestKind.LEAVE.value,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            days=days,
            purpose=purpose,
            station_leave=station_leave,
            station_address=station_address,
            substitute_id=substitute_id,
            unit_head_id=line.unit_head_id,
            establishment_id=line.establishment_id,
            sanctioning_authority_id=line.sanctioning_authority_id,
            status=Status.PENDING,
        )

        app.stage = Stage.SUBSTITUTE.value
        app.assignee_id = substitute_id
        app.substitute_status = SubstituteStatus.PENDING.value
        app.save()
    else:
        # No substitute nominated
        line = ReportingLine.objects.filter(user_id=user_id).first()
        if line is None:
            raise LeaveError("No reporting line configured.")

        app = LeaveApplication.objects.create(
            user_id=user_id,
            kind=RequestKind.LEAVE.value,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            days=days,
            purpose=purpose,
            station_leave=station_leave,
            station_address=station_address,
            substitute_id=None,
            unit_head_id=line.unit_head_id,
            establishment_id=line.establishment_id,
            sanctioning_authority_id=line.sanctioning_authority_id,
            status=Status.PENDING,
        )

        app.substitute_status = SubstituteStatus.NOT_REQUIRED.value
        route_to_approver(app)

    # Log action
    log_action(app, user_id, "apply", f"Leave application submitted for {category} leave.")

    return app


@transaction.atomic
def respond_to_substitute(actor_id: int, application_id: int, accept: bool) -> LeaveApplication:
    """Accept or decline a substitute request.

    Only the current assignee (substitute) may respond.
    """
    app = LeaveApplication.objects.select_for_update().filter(id=application_id).first()
    if app is None:
        raise NotFound()

    if app.assignee_id != actor_id:
        raise NotFound("Only the assigned substitute can respond to this application.")

    if app.status != Status.PENDING.value or app.stage != Stage.SUBSTITUTE.value:
        raise NotFound(
            f"Cannot respond to substitute request for application"
            f" in status {app.status} and stage {app.stage}."
        )

    if accept:
        description = "Substitute consent accepted."
        app.substitute_status = SubstituteStatus.ACCEPTED.value
        # Route to approver after acceptance
        route_to_approver(app)
    else:
        description = "Substitute consent declined."
        app.substitute_status = SubstituteStatus.DECLINED.value
        app.assignee_id = None

    app.save()

    log_action(app, actor_id, "substitute_response", description)

    return app


@transaction.atomic
def replace_substitute(actor_id: int, application_id: int, substitute_id: int) -> LeaveApplication:
    """Nominate a replacement substitute after a decline.

    Only the owner (applicant) may replace a declined substitute.
    """
    app = LeaveApplication.objects.select_for_update().get(id=application_id)

    if app.user_id != actor_id:
        raise NotFound("Only the application owner can nominate a replacement substitute.")

    if app.status not in [Status.PENDING.value]:
        raise NotFound(f"Can only replace a declined substitute. Current status: {app.status}.")

    if app.substitute_status != SubstituteStatus.DECLINED.value:
        raise NotFound(
            f"Can only replace a declined substitute. Current status: {app.substitute_status}."
        )

    # Validate new substitute eligibility (simplified: not applicant, no overlap)
    if substitute_id == actor_id:
        raise LeaveError("Substitute cannot be the applicant.")

    # Check for existing pending/approved leave of the new substitute that overlaps
    if has_overlap(substitute_id, app.start_date, app.end_date, app.half_day):
        raise LeaveError("The substitute is on leave on these dates.")

    # Update the nominated substitute ID and status
    app.substitute_id = substitute_id
    app.substitute_status = SubstituteStatus.PENDING.value
    app.stage = Stage.SUBSTITUTE.value
    app.assignee_id = substitute_id
    app.save()

    log_action(app, actor_id, "replace_substitute", f"New substitute {substitute_id} nominated.")

    return app


@transaction.atomic
def withdraw(actor_id: int, application_id: int) -> LeaveApplication:
    """Withdraw a pending leave request.

    Only the owner may withdraw a PENDING request.
    """
    app = LeaveApplication.objects.select_for_update().filter(id=application_id).first()
    if app is None:
        raise NotFound()

    if app.user_id != actor_id:
        raise NotFound("Only the application owner can withdraw this application.")

    if app.status != Status.PENDING.value:
        raise NotFound(f"Cannot withdraw application in status {app.status}.")

    app.status = Status.WITHDRAWN.value
    app.assignee_id = None
    app.save()

    log_action(app, actor_id, "withdraw", f"Application withdrawn by user {actor_id}.")

    return app
