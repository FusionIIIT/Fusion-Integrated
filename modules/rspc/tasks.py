"""Celery asynchronous tasks for RSPC."""

from __future__ import annotations

import logging

from django.utils import timezone

from config.celery import app
from modules.rspc.models import Project

logger = logging.getLogger(__name__)


@app.task(name="modules.rspc.tasks.check_project_deadlines")
def check_project_deadlines() -> int:
    """Check for projects reaching their end date within the next 30 days."""
    today = timezone.now().date()
    expiring = Project.objects.filter(status="active", end_date__lte=today)
    count = expiring.count()
    logger.info(
        "RSPC deadline check: %d active projects have reached or passed their end date.",
        count,
    )
    return count
