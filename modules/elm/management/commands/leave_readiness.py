"""Name every unmet prerequisite before elm can serve a first request.

The deployment order is migrate -> seed_leave_policy -> seed_modules ->
leave_readiness; this command exists so a failed first request is explained by
the deploy log instead of discovered by a user.
"""
from django.core.management.base import BaseCommand

from modules.elm.registry import readiness


class Command(BaseCommand):
    help = "Report what is missing before the leave module can serve requests"

    def handle(self, *args, **options):
        problems = readiness()
        for problem in problems:
            self.stdout.write(self.style.WARNING(f"  - {problem}"))
        if problems:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("leave module is ready"))
