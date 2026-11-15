"""Celery asynchronous tasks for system_admin."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    RoleAssignmentState,
)
from modules.system_admin.models import (
    RoleAssignment,
    RoleAssignmentHistory,
    SuperAdminAuditLog,
    SuperAdminSession,
)
from modules.system_admin.selectors import config as config_selectors
from modules.system_admin.selectors import roles as role_selectors
from modules.system_admin.services import archival, notifications

log = logging.getLogger("fusion.system_admin.tasks")


@shared_task(
    name="system_admin.deliver_notifications",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def deliver_notifications(limit: int = 100) -> str:
    """Drain notification outbox within SLA (CFR-SA-019, BR-SA-023)."""
    report = notifications.deliver_pending_notifications(batch_size=limit)
    log.info("system_admin.notify.run %s", report)
    return str(report)


@shared_task(
    name="system_admin.sweep_scheduled_role_activations",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def sweep_scheduled_role_activations() -> int:
    """Activate future-dated roles reaching start date (BW-SA-04, UC-SA-028)."""
    today = date.today()
    pending = role_selectors.get_assignments_pending_activation(today)
    activated_count = 0

    for assignment in pending:
        with transaction.atomic():
            assignment.state = RoleAssignmentState.ACTIVE
            assignment.activated_at = timezone.now()
            assignment.save(update_fields=["state", "activated_at"])

            RoleAssignmentHistory.objects.create(
                assignment=assignment,
                action="activated",
                from_state=RoleAssignmentState.SCHEDULED,
                to_state=RoleAssignmentState.ACTIVE,
                performed_by=0,
                effective_date=today,
                reason="Automated scheduled start date activation",
            )

            SuperAdminAuditLog.objects.create(
                actor_id=0,
                actor_username="SYSTEM",
                action=AuditAction.ROLE_ASSIGN,
                target_user_id=assignment.user_id,
                target_role_code=assignment.role_id,
                result=AuditResult.SUCCESS,
                reason="Scheduled role activation executed by system timer",
            )
            activated_count += 1

    log.info("system_admin.roles.activated count=%d", activated_count)
    return activated_count


@shared_task(
    name="system_admin.sweep_expired_roles",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def sweep_expired_roles() -> int:
    """Inactivate time-bound roles reaching end date (BW-SA-03..05, UC-SA-029)."""
    today = date.today()
    expired = role_selectors.get_assignments_pending_expiry(today)
    expired_count = 0

    for assignment in expired:
        with transaction.atomic():
            prev_state = assignment.state
            assignment.state = RoleAssignmentState.EXPIRED
            assignment.expired_at = timezone.now()
            assignment.save(update_fields=["state", "expired_at"])

            RoleAssignmentHistory.objects.create(
                assignment=assignment,
                action="expired",
                from_state=prev_state,
                to_state=RoleAssignmentState.EXPIRED,
                performed_by=0,
                effective_date=today,
                reason="Automated time-bound role validity expiration",
            )

            SuperAdminAuditLog.objects.create(
                actor_id=0,
                actor_username="SYSTEM",
                action=AuditAction.ROLE_REVOKE,
                target_user_id=assignment.user_id,
                target_role_code=assignment.role_id,
                result=AuditResult.SUCCESS,
                reason="Automated role expiration executed by system timer",
            )
            expired_count += 1

    log.info("system_admin.roles.expired count=%d", expired_count)
    return expired_count


@shared_task(
    name="system_admin.send_role_expiry_reminders",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def send_role_expiry_reminders() -> int:
    """Dispatch warnings before time-bound role expiry (BR-SA-016, UC-SA-030)."""
    today = date.today()
    approaching = role_selectors.get_assignments_approaching_expiry(lead_days=7, today=today)
    queued = 0

    for assignment in approaching:
        user = getattr(assignment, "user", None)
        email = user.email if user else ""
        notifications.queue_notification(
            recipient_id=assignment.user_id,
            email=email,
            channel="email",
            template_code="role_expiry_reminder",
            subject=f"Notice: Role '{assignment.role.label}' Expiring Soon",
            body=f"Your assignment for '{assignment.role.label}' will expire on {assignment.end_date}. Contact the Super Admin if extension is required.",
            context={"assignment_id": assignment.id, "end_date": str(assignment.end_date)},
        )
        queued += 1

    log.info("system_admin.reminders.sent count=%d", queued)
    return queued


@shared_task(
    name="system_admin.sweep_expired_archived_user_windows",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def sweep_expired_archived_user_windows() -> int:
    """Finalize archived accounts past reversible window as permanent (BW-SA-08, UC-SA-031, ISS-SA-004)."""
    count = archival.finalize_expired_reversible_users()
    log.info("system_admin.archival.finalized_permanent count=%d", count)
    return count


@shared_task(
    name="system_admin.terminate_inactive_admin_sessions",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=180,
    time_limit=200,
)
def terminate_inactive_admin_sessions() -> int:
    """Terminate inactive Super Admin sessions exceeding timeout (UC-SA-034, BR-SA-027)."""
    timeout_minutes = config_selectors.get_system_parameter(
        "session.inactivity_timeout_minutes", default=15
    )
    cutoff = timezone.now() - timedelta(minutes=int(timeout_minutes))

    inactive_sessions = SuperAdminSession.objects.filter(is_active=True, last_active_at__lt=cutoff)
    count = 0

    for session in inactive_sessions:
        with transaction.atomic():
            session.is_active = False
            session.termination_reason = "inactivity_timeout"
            session.save(update_fields=["is_active", "termination_reason"])

            SuperAdminAuditLog.objects.create(
                actor_id=session.admin_user_id,
                action=AuditAction.AUTH_SESSION_TERMINATE,
                ip_address=session.ip_address,
                result=AuditResult.SUCCESS,
                reason=f"Terminated after {timeout_minutes}m of inactivity",
            )
            count += 1

    log.info("system_admin.sessions.timed_out count=%d", count)
    return count
