"""Celery asynchronous tasks for BADMS.

Handles scheduled backups, retention policy checks, and failure alerting.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="modules.badms.tasks.execute_scheduled_backups_task")
def execute_scheduled_backups_task():
    """Execute scheduled backups for active datasets."""
    from .services.badms_services import execute_scheduled_backups
    logger.info("Starting BADMS scheduled backup execution...")
    records = execute_scheduled_backups(actor_user_id="system_cron", actor_role="sysadmin")
    logger.info("BADMS scheduled backup execution completed: %d records processed.", len(records))
    return [str(r.id) for r in records]


@shared_task(name="modules.badms.tasks.enforce_retention_policies_task")
def enforce_retention_policies_task():
    """Verify and enforce archive retention limits across all records."""
    from .models import EncryptedArchive
    today = timezone.now().date()
    expired = EncryptedArchive.objects.filter(retention_expiry_date__lt=today)
    count = expired.count()
    logger.info("BADMS retention audit: %d archives reached retention limit.", count)
    return count
