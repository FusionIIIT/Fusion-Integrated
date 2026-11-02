"""PMS Post-Grant Maintenance and Renewal Tracking service.

Enforces business rules BR-PMS-059, 060, 061, and Workflows BW-PMS-14, 15, CW-PMS-04.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import ALLOWED_RENEWAL_DECISIONS
from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
    validate_transition,
)
from modules.pms.models import PostGrantMaintenance
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def request_renewal_decision(
    *,
    maintenance_id: int,
    attorney_user_id: int,
) -> PostGrantMaintenance:
    """Attorney initiates renewal decision request to Director (UC-PMS-017, BR-PMS-061, BW-PMS-14)."""
    with transaction.atomic():
        maint = PostGrantMaintenance.objects.select_for_update().get(pk=maintenance_id)
        app = maint.application

        if app.status not in (
            PatentApplicationStatus.GRANTED.value,
            PatentApplicationStatus.RENEWED.value,
        ):
            raise PreconditionNotMetError(
                f"Renewal decision can only be requested for Granted or Renewed patents, not '{app.status}' (BR-PMS-059)."
            )

        validate_transition(
            app.status, PatentApplicationStatus.RENEWAL_DECISION_REQUESTED, actor_role="Attorney"
        )
        prev_status = app.status

        maint.decision_requested = True
        maint.maintenance_status = "decision_requested"
        maint.save(update_fields=["decision_requested", "maintenance_status", "updated_at"])

        app.status = PatentApplicationStatus.RENEWAL_DECISION_REQUESTED.value
        app.save(update_fields=["status", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="maintenance_decision_requested",
            from_state=prev_status,
            to_state=app.status,
            details={"cycle": maint.cycle_number, "fee_due_date": str(maint.fee_due_date)},
        )

        enqueue_notification(
            topic="maintenance.decision_requested",
            dedupe_key=f"pms:maint:req:{maint.id}",
            subject=f"PMS: Patent Renewal Decision Required ({app.application_no})",
            body=f"Maintenance fee renewal decision required for patent '{app.title}' (Cycle {maint.cycle_number}). Due: {maint.fee_due_date}.",
            recipient_user_id=app.assigned_director_user_id,
        )

    return maint


def decide_renewal(
    *,
    maintenance_id: int,
    director_user_id: int,
    decision: str,  # "Renew" or "Do Not Renew"
) -> PostGrantMaintenance:
    """Director makes explicit renewal decision (UC-PMS-018, BR-PMS-061)."""
    if decision not in ALLOWED_RENEWAL_DECISIONS:
        raise PreconditionNotMetError(
            f"Invalid renewal decision '{decision}'. Must be one of: {ALLOWED_RENEWAL_DECISIONS} (BR-PMS-061)."
        )

    with transaction.atomic():
        maint = PostGrantMaintenance.objects.select_for_update().get(pk=maintenance_id)
        app = maint.application

        target_status = (
            PatentApplicationStatus.RENEWAL_APPROVED
            if decision == "Renew"
            else PatentApplicationStatus.DO_NOT_RENEW
        )
        validate_transition(app.status, target_status, actor_role="Director")
        prev_status = app.status

        now = timezone.now()
        maint.director_decision = decision
        maint.renewal_decided_at = now
        maint.maintenance_status = "renewal_approved" if decision == "Renew" else "do_not_renew"
        maint.save()

        app.status = target_status.value
        app.save(update_fields=["status", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=director_user_id,
            action_type="maintenance_decided",
            from_state=prev_status,
            to_state=app.status,
            details={"decision": decision, "cycle": maint.cycle_number},
        )

        enqueue_notification(
            topic="maintenance.decided",
            dedupe_key=f"pms:maint:decided:{maint.id}",
            subject=f"PMS: Patent Renewal Decision - {decision} ({app.application_no})",
            body=f"Director has decided: {decision} for maintenance renewal of '{app.title}'.",
            recipient_user_id=app.assigned_attorney_user_id or app.applicant_user_id,
        )

    return maint


def record_maintenance_action(
    *,
    maintenance_id: int,
    attorney_user_id: int,
    transaction_reference: str,
) -> PostGrantMaintenance:
    """Record completed maintenance action and schedule next cycle (UC-PMS-017, BW-PMS-14)."""
    if not transaction_reference or not transaction_reference.strip():
        raise PreconditionNotMetError(
            "Transaction reference is required to record maintenance action."
        )

    with transaction.atomic():
        maint = PostGrantMaintenance.objects.select_for_update().get(pk=maintenance_id)
        app = maint.application

        if app.status != PatentApplicationStatus.RENEWAL_APPROVED.value:
            raise PreconditionNotMetError(
                "Maintenance renewal must be approved by Director before recording action."
            )

        validate_transition(app.status, PatentApplicationStatus.RENEWED, actor_role="Attorney")
        prev_status = app.status

        now = timezone.now()
        maint.action_recorded_date = now.date()
        maint.transaction_reference = transaction_reference.strip()
        maint.maintenance_status = "renewed"
        maint.save()

        app.status = PatentApplicationStatus.RENEWED.value
        app.save(update_fields=["status", "updated_at"])

        # Schedule next maintenance cycle (next year)
        next_due = maint.fee_due_date + timedelta(days=365)
        PostGrantMaintenance.objects.create(
            application=app,
            cycle_number=maint.cycle_number + 1,
            fee_due_date=next_due,
            fee_amount=maint.fee_amount + Decimal("1000.00"),
            maintenance_status="scheduled",
        )

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="maintenance_action_recorded",
            from_state=prev_status,
            to_state=app.status,
            details={
                "cycle": maint.cycle_number,
                "transaction_ref": transaction_reference,
                "next_due": str(next_due),
            },
        )

        enqueue_notification(
            topic="maintenance.recorded",
            dedupe_key=f"pms:maint:rec:{maint.id}",
            subject=f"PMS: Patent Renewal Completed ({app.application_no})",
            body=f"Maintenance fee renewal completed for '{app.title}'. Next cycle due: {next_due}.",
            recipient_user_id=app.applicant_user_id,
        )

    return maint
