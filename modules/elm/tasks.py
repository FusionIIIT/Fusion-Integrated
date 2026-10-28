
"""Scheduled ELM jobs. Side effects are idempotent and auditable."""

from celery import shared_task
from django.utils import timezone

from modules.elm.models import WorkflowTask, YearEndRun


@shared_task(name="elm.process_sla")
def process_sla():
    now = timezone.now()
    overdue = WorkflowTask.objects.filter(
        status="open",
        due_at__lte=now,
        escalated_at__isnull=True,
    )
    count = overdue.update(escalated_at=now)
    return {"escalated_tasks": count}


@shared_task(name="elm.process_year_end")
def process_year_end(year=None):
    """Create an idempotent run record and surface unconfigured credits explicitly.

    Employee enumeration and authority for annual entitlement population are not
    available through the current directory contract; this task therefore does
    not fabricate employee rows or silently issue credits. It records a run that
    requires the agreed directory integration to finish the year-end operation.
    """
    from django.db import IntegrityError

    year = int(year or (timezone.localdate().year - 1))
    try:
        run = YearEndRun.objects.create(
            year=year,
            status="failed",
            completed_at=timezone.now(),
            summary={"processed_requests": 0},
            error=(
                "Blocked: bulk employee enumeration and approved entitlement/"
                "carry-forward policy integration are not configured."
            ),
        )
    except IntegrityError:
        run = YearEndRun.objects.get(year=year)

    return {"year": year, "status": run.status, "error": run.error}
