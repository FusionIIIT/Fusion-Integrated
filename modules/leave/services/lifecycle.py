"""Leave decision and cancellation services (rewritten in Phase 2)."""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.leave.domain import policy
from modules.leave.models import LeaveApplication, LeaveBalance, RequestKind, Stage, Status
from modules.leave.services.applications import LeaveError, NotFound, log_action, route_to_approver


@transaction.atomic
def decide(actor_id: int, application_id: int, decision: str, remark: str = "") -> LeaveApplication:
    """
    Process a decision at the current stage of a leave application.

    - Load application with select_for_update.
    - Raise NotFound if not PENDING or actor is not assignee.
    - Validate decision against stage and policy rules (BR-EL-016, BR-EL-017).
    - Update recommendation field for UNIT_HEAD stage if applicable.
    - Route to next approver if needed.
    """
    app = LeaveApplication.objects.select_for_update().filter(id=application_id).first()
    if app is None:
        raise NotFound()

    # Check status and assignee ownership
    if app.status != Status.PENDING.value:
        raise NotFound(f"Cannot decide on application with status {app.status}.")

    if app.assignee_id != actor_id:
        raise NotFound(f"Only the assigned approver ({actor_id}) can decide this application.")

    # Validate stage and decision rules
    current_stage = app.stage

    if current_stage == Stage.SUBSTITUTE.value:
        raise LeaveError("This request is not awaiting a decision (substitute stage).")

    if current_stage == Stage.UNIT_HEAD.value:
        category = app.category
        is_final = policy.unit_head_is_final(category)

        if is_final:
            # BR-EL-016: CL and RH are final at Unit Head
            if decision not in ("approve", "reject"):
                raise LeaveError(f"Unit Head must approve or reject for {category} leave.")

            log_action(app, actor_id, decision, remark)
            finalize(app, actor_id, decision == "approve")
            return app
        # BR-EL-017: Others get a recommendation
        if decision not in ("recommended", "not_recommended"):
            raise LeaveError(f"Unit Head must recommend or not recommend for {category} leave.")

        # Store recommendation
        app.unit_head_recommendation = decision

        # Route to next approver (Establishment or Sanctioning Authority) directly
        if app.establishment_id:
            app.stage = Stage.ESTABLISHMENT.value
            app.assignee_id = app.establishment_id
        else:
            app.stage = Stage.SANCTION.value
            app.assignee_id = app.sanctioning_authority_id or app.user_id

        app.save()
        log_action(app, actor_id, decision, remark)

    elif current_stage == Stage.ESTABLISHMENT.value:
        # BR-EL-018: Establishment verifies and moves to SANCTION
        if decision != "verify":
            raise LeaveError("Establishment must verify the application.")

        app.stage = Stage.SANCTION.value
        app.assignee_id = app.sanctioning_authority_id or app.user_id  # Handle self-sanction case
        app.save()
        log_action(app, actor_id, "establishment_verify", remark)
        return app

    elif current_stage == Stage.SANCTION.value:
        # BR-EL-019: Sanctioning Authority makes final decision
        if decision not in ("approve", "reject"):
            raise LeaveError("Sanctioning Authority must approve or reject.")

        app.status = Status.APPROVED.value if decision == "approve" else Status.REJECTED.value
        app.stage = Stage.DONE.value
        app.assignee_id = None
        app.decided_at = timezone.now()
        app.save()

        log_action(app, actor_id, "sanction_decision", f"{decision.capitalize()}d by {actor_id}.")

        # Finalize the application (update balance)
        finalize(app, actor_id, decision == "approve")

    else:
        raise LeaveError(f"Unknown stage: {current_stage}")

    return app


@transaction.atomic
def finalize(app: LeaveApplication, actor_id: int, approved: bool) -> None:
    """
    Finalize a leave application after approval/rejection.

    - Set status to APPROVED/REJECTED, stage DONE, assignee None, decided_at.
    - On LEAVE approval: add days to user's LeaveBalance.used for the start year.
    - On CANCELLATION approval: set parent status to CANCELLED
    -   and subtract parent's days from balance.
    - Rejection: no balance change.
    """
    app.status = Status.APPROVED.value if approved else Status.REJECTED.value
    app.stage = Stage.DONE.value
    app.assignee_id = None
    app.decided_at = timezone.now()
    app.save()

    log_action(
        app,
        actor_id,
        "finalize",
        f"Application {app.kind} finalized as {'approved' if approved else 'rejected'}.",
    )

    # Handle balance updates based on kind and approval status
    if app.kind == RequestKind.LEAVE.value and approved:
        # BR-EL-021: Approval adds days to used balance
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=app.user_id, year=app.start_date.year, category=app.category
        )
        old_used = balance.used
        new_used = Decimal(str(old_used)) + Decimal(str(app.days))
        balance.used = new_used
        balance.save()
    elif app.kind == RequestKind.CANCELLATION.value and approved:
        # BR-EL-023: Cancellation of an approved LEAVE subtracts days from used
        parent_app = LeaveApplication.objects.get(id=app.parent_id)

        # Only a LEAVE request can be cancelled; a cancellation cannot be.
        if parent_app.kind != RequestKind.LEAVE.value:
            raise LeaveError("Cannot cancel a cancellation request.")

        balance = LeaveBalance.objects.select_for_update().get(
            user_id=parent_app.user_id,
            year=parent_app.start_date.year,
            category=parent_app.category,
        )

        old_used = balance.used
        new_used = Decimal(str(old_used)) - Decimal(str(parent_app.days))
        # Ensure we don't go below zero (though logic should prevent this)
        if new_used < 0:
            new_used = Decimal("0")

        balance.used = new_used
        balance.save()

        # Mark parent as cancelled
        parent_app.status = Status.CANCELLED.value
        parent_app.save()


@transaction.atomic
def request_cancellation(actor_id: int, application_id: int, today: date) -> LeaveApplication:
    """
    Request cancellation of an approved leave.

    - Only the owner can request.
    - Only applicable to APPROVED LEAVE-kind requests where start_date > today.
    - Only if no PENDING cancellation already exists.
    - Creates a CANCELLATION request with parent = original leave, then routes it.
    """
    app = LeaveApplication.objects.select_for_update().get(id=application_id)

    # Check ownership
    if app.user_id != actor_id:
        raise NotFound("Only the owner can request cancellation for this application.")

    # Check kind and approval status
    if app.kind != RequestKind.LEAVE.value:
        raise LeaveError("Can only cancel LEAVE requests.")

    if app.status != Status.APPROVED.value:
        raise LeaveError(f"Can only cancel APPROVED leave requests. Current status: {app.status}.")

    # Check start date is in the future relative to today
    if app.start_date <= today:
        raise LeaveError("Can only cancel leave requests that have not started yet.")

    # Check for existing pending cancellation
    if LeaveApplication.objects.filter(
        parent=app, kind=RequestKind.CANCELLATION.value, status=Status.PENDING.value
    ).exists():
        raise LeaveError("A pending cancellation request already exists for this application.")

    # Create the cancellation request
    cancellation = LeaveApplication.objects.create(
        user_id=actor_id,
        kind=RequestKind.CANCELLATION.value,
        parent=app,
        category=app.category,
        start_date=app.start_date,
        end_date=app.end_date,
        days=app.days,
        purpose="Cancellation requested by applicant",
        station_leave=app.station_leave,
        station_address=app.station_address,
        substitute_id=None,
        unit_head_id=app.unit_head_id,
        establishment_id=app.establishment_id,
        sanctioning_authority_id=app.sanctioning_authority_id,
        status=Status.PENDING.value,
    )

    # Route the cancellation request to the appropriate approver
    route_to_approver(cancellation)

    log_action(
        app,
        actor_id,
        "request_cancellation",
        f"Requested cancellation for application {application_id}.",
    )

    return cancellation
