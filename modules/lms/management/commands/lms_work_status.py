"""Check status of scheduled LMS background releases and report overdue unreleased items."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.lms.domain.constants import AssignmentStatus, MaterialStatus
from modules.lms.models import Assignment, CourseMaterial


class Command(BaseCommand):
    help = "Report overdue unreleased materials and assignments that should have been published."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-lag",
            type=int,
            default=0,
            help="Maximum allowed lag in seconds before failing (default: 0).",
        )

    def _inspect_materials(self, now, max_lag):
        overdue = CourseMaterial.objects.filter(
            status=MaterialStatus.SCHEDULED,
            release_date__lt=now,
        )
        count = overdue.count()
        oldest = overdue.order_by("release_date").values_list("release_date", flat=True).first()
        lag = int((now - oldest).total_seconds()) if oldest else 0
        self.stdout.write(f"  overdue materials   {count}")
        self.stdout.write(f"  oldest material lag {lag}s")
        if count > 0 and (max_lag == 0 or lag > max_lag):
            return (
                f"{count} scheduled material(s) are past release_date "
                f"(lag: {lag}s) — Celery beat sweep may be stalled."
            )
        return None

    def _inspect_assignments(self, now, max_lag):
        overdue = Assignment.objects.filter(
            status=AssignmentStatus.SCHEDULED,
            release_date__lt=now,
        )
        count = overdue.count()
        oldest = overdue.order_by("release_date").values_list("release_date", flat=True).first()
        lag = int((now - oldest).total_seconds()) if oldest else 0
        self.stdout.write(f"  overdue assignments {count}")
        self.stdout.write(f"  oldest assignment lag {lag}s")
        if count > 0 and (max_lag == 0 or lag > max_lag):
            return (
                f"{count} scheduled assignment(s) are past release_date "
                f"(lag: {lag}s) — Celery beat sweep may be stalled."
            )
        return None

    def handle(self, *args, **options):
        now = timezone.now()
        max_lag = options["max_lag"]
        problems = [
            p
            for p in [
                self._inspect_materials(now, max_lag),
                self._inspect_assignments(now, max_lag),
            ]
            if p
        ]

        if problems:
            self.stdout.write("")
            for p in problems:
                self.stdout.write(self.style.ERROR(f"  {p}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("\n  LMS scheduled work looks healthy"))
