from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from psycopg.types.range import Range

from modules.phc.models import ReimbursementPolicy


class Command(BaseCommand):
    help = "Seed the approved initial PHC reimbursement policy if it is absent."

    def handle(self, *args, **options):
        expected = Range(date(2026, 1, 1), None, bounds="[)")
        policy = ReimbursementPolicy.objects.filter(
            effective_period__contains=timezone.localdate()).first()
        if policy:
            if policy.submission_window_days != 30:
                raise CommandError("The current PHC policy is not the approved 30-day policy.")
            self.stdout.write("PHC reimbursement policy is ready.")
            return
        ReimbursementPolicy.objects.create(submission_window_days=30,
                                           effective_period=expected)
        self.stdout.write(self.style.SUCCESS(
            "Seeded the 30-day PHC reimbursement policy effective 2026-01-01."))
