from django.core.management.base import BaseCommand, CommandError

from fusion_auth.client import IamUnavailable
from modules.lms.services.setup import sync_workspaces


class Command(BaseCommand):
    help = "Initialize workspaces and safe course policies from the real IAM offering catalogue."

    def handle(self, **options):
        try:
            created = sync_workspaces()
        except IamUnavailable as exc:
            raise CommandError(
                "IAM course catalogue unavailable; verify service configuration."
            ) from exc
        self.stdout.write(self.style.SUCCESS(f"Initialized {created} new LMS workspaces."))
