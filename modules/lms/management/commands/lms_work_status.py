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

    def handle(self, *args, **options):
        now = timezone.now()
        problems = []

        overdue_materials = CourseMaterial.objects.filter(
            status=MaterialStatus.SCHEDULED,
            release_date__lt=now,
        )
        mat_count = overdue_materials.count()
        oldest_mat = (
            overdue_materials.order_by("release_date")
            .values_list("release_date", flat=True)
            .first()
        )
        mat_lag = int((now - oldest_mat).total_seconds()) if oldest_mat else 0

        self.stdout.write(f"  overdue materials   {mat_count}")
        self.stdout.write(f"  oldest material lag {mat_lag}s")

        overdue_assignments = Assignment.objects.filter(
            status=AssignmentStatus.SCHEDULED,
            release_date__lt=now,
        )
        asg_count = overdue_assignments.count()
        oldest_asg = (
            overdue_assignments.order_by("release_date")
            .values_list("release_date", flat=True)
            .first()
        )
        asg_lag = int((now - oldest_asg).total_seconds()) if oldest_asg else 0

        self.stdout.write(f"  overdue assignments {asg_count}")
        self.stdout.write(f"  oldest assignment lag {asg_lag}s")

        max_lag = options["max_lag"]
        if mat_count > 0 and (max_lag == 0 or mat_lag > max_lag):
            problems.append(
                f"{mat_count} scheduled material(s) are past release_date "
                f"(lag: {mat_lag}s) — Celery beat sweep may be stalled."
            )

        if asg_count > 0 and (max_lag == 0 or asg_lag > max_lag):
            problems.append(
                f"{asg_count} scheduled assignment(s) are past release_date "
                f"(lag: {asg_lag}s) — Celery beat sweep may be stalled."
            )

        if problems:
            self.stdout.write("")
            for p in problems:
                self.stdout.write(self.style.ERROR(f"  {p}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("\n  LMS scheduled work looks healthy"))
