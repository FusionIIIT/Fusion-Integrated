"""Celery background tasks for FTS."""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from modules.fts.models import FTSFile

log = logging.getLogger("fusion.fts.tasks")


@shared_task(
    name="fts.cleanup_discarded_drafts",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=120,
    time_limit=180,
)
def cleanup_discarded_drafts() -> str:
    """Clean up orphan records from discarded drafts older than 30 days."""
    cutoff = timezone.now() - timedelta(days=30)
    count, _ = FTSFile.objects.filter(status="discarded", updated_at__lt=cutoff).delete()
    return f"Purged {count} discarded drafts."
