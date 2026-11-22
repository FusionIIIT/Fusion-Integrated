"""Celery tasks for System Admin."""
from celery import shared_task

from modules.system_admin.services.role_service import process_role_expiries


@shared_task(name="system_admin.process_role_expiries")
def process_role_expiries_task() -> int:
    """Daily automated role expiration processing task (BR-SA-009, UC-SA-013)."""
    return process_role_expiries()
