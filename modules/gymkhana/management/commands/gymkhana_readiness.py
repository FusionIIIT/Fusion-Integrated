"""Report what Gymkhana still needs before it can be used."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from modules.gymkhana.registry import readiness


class Command(BaseCommand):
    help = "List every unmet prerequisite of the Gymkhana module."

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            raise CommandError("Gymkhana is not ready:\n" + "\n".join(f"- {u}" for u in unmet))
        self.stdout.write("Gymkhana is ready.")
