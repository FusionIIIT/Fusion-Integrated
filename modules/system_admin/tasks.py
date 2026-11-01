"""Scheduled automation tasks for System Admin module.

Implements background lifecycle automation:
- UC-SA-028: Activate Scheduled Role Assignment
- UC-SA-029: Expire Time-Bound Role
- UC-SA-030: Send Role-Expiry Reminder
- UC-SA-031: Finalize Archived User as Permanently Non-Restorable
- UC-SA-034: Terminate Inactive Super Admin Session
"""
from __future__ import annotations

import logging
from celery import shared_task

log = logging.getLogger("fusion.system_admin.tasks")


@shared_task(
    name="system_admin.activate_scheduled_roles",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=180,
    time_limit=240,
)
def task_activate_scheduled_roles() -> int:
    """UC-SA-028 / BW-SA-04: Activate scheduled role assignments whose start_date has arrived."""
    from modules.system_admin.services.role_service import activate_scheduled_roles

    count = activate_scheduled_roles()
    if count:
        log.info("system_admin.roles.activated count=%d", count)
    return count


@shared_task(
    name="system_admin.expire_time_bound_roles",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=180,
    time_limit=240,
)
def task_expire_time_bound_roles() -> int:
    """UC-SA-029 / BW-SA-03..05: Inactivate roles that have reached their validity end_date."""
    from modules.system_admin.services.role_service import expire_time_bound_roles

    count = expire_time_bound_roles()
    if count:
        log.info("system_admin.roles.expired count=%d", count)
    return count


@shared_task(
    name="system_admin.send_role_expiry_reminders",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=180,
    time_limit=240,
)
def task_send_role_expiry_reminders() -> int:
    """UC-SA-030 / BR-SA-016: Send reminder notifications for upcoming role expiries."""
    from modules.system_admin.services.role_service import send_role_expiry_reminders

    count = send_role_expiry_reminders()
    if count:
        log.info("system_admin.roles.expiry_reminders_sent count=%d", count)
    return count


@shared_task(
    name="system_admin.finalize_expired_archived_users",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=180,
    time_limit=240,
)
def task_finalize_expired_archived_users() -> int:
    """UC-SA-031 / BW-SA-08: Transition archived users past reversibility window to permanently non-restorable."""
    from modules.system_admin.services.archival_service import finalize_non_restorable_archived_users

    count = finalize_non_restorable_archived_users()
    if count:
        log.info("system_admin.archival.users_finalized count=%d", count)
    return count


@shared_task(
    name="system_admin.cleanup_inactive_sessions",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=120,
    time_limit=150,
)
def task_cleanup_inactive_sessions(timeout_minutes: int = 15) -> int:
    """UC-SA-034 / BR-SA-027: Inactivate operator sessions idle for more than timeout threshold."""
    from modules.system_admin.services.auth_service import cleanup_inactive_sessions

    count = cleanup_inactive_sessions(timeout_minutes=timeout_minutes)
    if count:
        log.info("system_admin.sessions.cleaned_up count=%d", count)
    return count
