"""Is the leave scheduled work actually happening?

    manage.py scheduled_work_status --module leave
    manage.py scheduled_work_status --module leave --max-lag 600

Beat not running is silent by nature: nothing errors, work simply stops. What
that looks like here is an outbox that only grows and requests that sit past
their SLA threshold without anybody being reminded.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.models import NotificationOutbox, SlaThreshold
from modules.leave.selectors import sla as sla_selector


class Command(BaseCommand):
    help = "Report leave outbox lag and overdue SLA tasks"

    def add_arguments(self, parser):
        parser.add_argument("--max-lag", type=int, default=0,
                            help="Exit 1 if the oldest pending row is older than "
                                 "this many seconds.")
        parser.add_argument("--module", default="leave",
                            help="Accepted for consistency with the placement "
                                 "command; this one only reports leave.")

    def handle(self, *args, **opts):
        now = timezone.now()
        problems = []

        pending = NotificationOutbox.objects.filter(status="pending")
        oldest = (pending.order_by("created_at").values_list("created_at", flat=True)
                  .first())
        lag = int((now - oldest).total_seconds()) if oldest else 0
        self.stdout.write(f"  outbox pending    {pending.count()}")
        self.stdout.write(f"  oldest pending    {lag}s")
        if opts["max_lag"] and lag > opts["max_lag"]:
            problems.append(f"outbox lag {lag}s exceeds {opts['max_lag']}s — is the "
                            "notifications worker draining?")

        overdue = 0
        for task in sla_selector.waiting(now=now):
            thresholds = _threshold_for(task.task_class)
            if thresholds is None:
                continue
            if task.age_hours >= thresholds.escalation_hours:
                overdue += 1
        self.stdout.write(f"  tasks past SLA    {overdue}")
        if overdue:
            problems.append(f"{overdue} leave task(s) are past their escalation "
                            "threshold — run_sla_sweep is not running.")

        configured = SlaThreshold.objects.count()
        self.stdout.write(f"  thresholds        {configured}")
        if not configured:
            problems.append("No SLA threshold is configured, so nothing is ever "
                            "reminded or escalated.")

        if problems:
            self.stdout.write("")
            for problem in problems:
                self.stdout.write(self.style.ERROR(f"  {problem}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("\n  scheduled leave work looks healthy"))


def _threshold_for(task_class: str):
    from modules.leave.selectors import config as config_selector

    return config_selector.thresholds(task_class)
