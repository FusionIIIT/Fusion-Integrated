"""Report outbox lag, undecided requests, and survey status for MMS.

manage.py mms_scheduled_work_status
manage.py mms_scheduled_work_status --max-lag 600
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.mms.models import (
    NotificationOutbox,
    SpecialFoodRequest,
    VacationSurvey,
)


class Command(BaseCommand):
    help = "Report MMS outbox lag, undecided special food requests and survey status"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-lag",
            type=int,
            default=0,
            help="Exit 1 if the oldest pending notification row is older than this many seconds.",
        )

    def handle(self, *args, **opts):
        now = timezone.now()
        problems = []

        pending = NotificationOutbox.objects.filter(status="pending")
        oldest = pending.order_by("created_at").values_list("created_at", flat=True).first()
        lag = int((now - oldest).total_seconds()) if oldest else 0
        self.stdout.write(f"  outbox pending:              {pending.count()}")
        self.stdout.write(f"  oldest pending lag:          {lag}s")

        if opts["max_lag"] and lag > opts["max_lag"]:
            problems.append(
                f"Outbox lag {lag}s exceeds {opts['max_lag']}s — "
                "is the MMS notifications worker draining?"
            )

        overdue_sf = SpecialFoodRequest.objects.filter(
            status="requested", decision_due_at__lt=now
        ).count()
        self.stdout.write(f"  overdue special food reqs:   {overdue_sf}")
        if overdue_sf:
            problems.append(
                f"{overdue_sf} special food request(s) past decision_due_at — "
                "default rejection task not running?"
            )

        expired_surveys = VacationSurvey.objects.filter(
            is_open=True, response_deadline__lte=now
        ).count()
        self.stdout.write(f"  expired open surveys:        {expired_surveys}")
        if expired_surveys:
            problems.append(
                f"{expired_surveys} survey(s) past response deadline still open — "
                "default-No task not running?"
            )

        if problems:
            for p in problems:
                self.stderr.write(self.style.ERROR(f"ALERT: {p}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("All MMS scheduled health indicators nominal."))
