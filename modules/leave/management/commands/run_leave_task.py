"""Runs a scheduled ELM task by hand: `run_leave_task sla` or `year-end --year 2026`."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.services import periodic


class Command(BaseCommand):
    help = "Run ELM's SLA or year-end processing once"

    def add_arguments(self, parser):
        parser.add_argument("task", choices=["sla", "year-end"])
        parser.add_argument("--year", type=int)

    def handle(self, *args, task, year=None, **opts):
        if task == "sla":
            report = periodic.process_sla(timezone.now())
        else:
            report = periodic.run_year_end(year or timezone.localdate().year - 1)
        self.stdout.write(str(report))
