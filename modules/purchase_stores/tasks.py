"""Idempotent scheduled report generation."""

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.utils import timezone


@shared_task(name="purchase_stores.generate_scheduled_reports", acks_late=True)
def generate_scheduled_reports():
    from modules.purchase_stores.models import ReportGeneration, ScheduledReport

    now = timezone.now()
    generated = 0
    for schedule in ScheduledReport.objects.filter(enabled=True, next_run_at__lte=now).order_by(
        "next_run_at", "id"
    ):
        ReportGeneration.objects.create(
            report_code=schedule.report_code,
            requested_by_user_id=schedule.owner_user_id,
            filters=schedule.filters,
            output_format=schedule.output_format,
        )
        interval = {
            ScheduledReport.Frequency.DAILY: relativedelta(days=1),
            ScheduledReport.Frequency.WEEKLY: relativedelta(weeks=1),
            ScheduledReport.Frequency.MONTHLY: relativedelta(months=1),
        }[schedule.frequency]
        while schedule.next_run_at <= now:
            schedule.next_run_at += interval
        schedule.save(update_fields=["next_run_at", "updated_at"])
        generated += 1
    return generated
