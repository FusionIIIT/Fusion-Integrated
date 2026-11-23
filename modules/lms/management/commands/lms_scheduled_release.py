"""Management command to process scheduled LMS content release."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.lms.tasks import process_scheduled_content_release


class Command(BaseCommand):
    help = "Publish materials and assignments whose scheduled release date has arrived."

    def handle(self, *args, **options):
        result = process_scheduled_content_release()
        mat_count = result.get("materials_released", 0)
        asg_count = result.get("assignments_released", 0)
        self.stdout.write(
            self.style.SUCCESS(
                f"Content release sweep complete: {mat_count} materials, "
                f"{asg_count} assignments published."
            )
        )
