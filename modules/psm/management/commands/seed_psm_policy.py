# Seed initial effective-dated PSM policy idempotently (Step 2.8, Step 4.8).
from django.core.management.base import BaseCommand

from modules.psm.services.policy import seed_default_policy


class Command(BaseCommand):
    help = "Seed the default active PSM policy if none is configured."

    def handle(self, *args, **options):
        policy, created = seed_default_policy()
        verb = "Created" if created else "Already active"
        msg = (
            f"{verb}: PSM policy v{policy.version} "
            f"(direct <= {policy.direct_limit}, final > {policy.final_approval_threshold})"
        )
        self.stdout.write(self.style.SUCCESS(msg))
