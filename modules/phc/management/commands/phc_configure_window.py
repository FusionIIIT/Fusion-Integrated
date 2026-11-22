"""Configure the PHC-BR-06 reimbursement submission window as a new effective-dated version."""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.phc.services import reimbursements


class Command(BaseCommand):
    help = "Add a reimbursement submission-window policy version"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, required=True)
        parser.add_argument("--includes-last-day", choices=("yes", "no"), required=True)
        parser.add_argument("--effective-from", type=date.fromisoformat, default=None,
                            help="YYYY-MM-DD; defaults to today.")

    def handle(self, *args, **opts):
        try:
            policy = reimbursements.configure_policy(
                window_days=opts["days"], includes_last_day=opts["includes_last_day"] == "yes",
                effective_from=opts["effective_from"] or timezone.localdate())
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        self.stdout.write(self.style.SUCCESS(f"Submission window set: {policy}"))
