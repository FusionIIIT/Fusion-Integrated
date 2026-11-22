"""Manual trigger for RSPC project deadline checks."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.rspc.tasks import check_project_deadlines


class Command(BaseCommand):
    help = "Run the RSPC project deadline sweep manually."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Running RSPC project deadline sweep...")
        count = check_project_deadlines()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully checked deadlines: {count} project(s) reached or passed end date."
            )
        )
