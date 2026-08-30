"""Say whether Leave can accept an application, and what is missing if not.

The same check seed_modules runs at deploy time, available on its own so the
answer can be had without a deploy.
"""
from django.core.management.base import BaseCommand

from modules.accesscontrol.models import Module
from modules.leave.registry import readiness


class Command(BaseCommand):
    help = "Report whether the leave module is ready to be used."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail", action="store_true",
            help="Exit non-zero when something is missing, for a deploy gate.")

    def handle(self, *args, **opts) -> None:
        unmet = readiness()
        registered = Module.objects.filter(code="leave").first()
        status = registered.status if registered else "not registered"

        if not unmet:
            self.stdout.write(self.style.SUCCESS(
                f"  leave is ready and registered as {status}"))
            if status != "active":
                self.stdout.write(self.style.WARNING(
                    "  prerequisites are met but it is not active — run seed_modules"))
            return

        self.stdout.write(self.style.ERROR(
            f"  leave is not ready ({len(unmet)} prerequisite(s) unmet), "
            f"registered as {status}:"))
        for reason in unmet:
            self.stdout.write(self.style.ERROR(f"    {reason}"))
        self.stdout.write(
            "\n  Until these are met the module stays out of the sidebar, which is "
            "the intended behaviour rather than a fault.")
        if opts["fail"]:
            raise SystemExit(1)
