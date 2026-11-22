"""Seed initial or active PatentPolicy (Step 4.8)."""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.patents.domain import deadlines as dl
from modules.patents.domain import state_machine as sm
from modules.patents.models import PatentPolicy


class Command(BaseCommand):
    help = "Seed or ensure active PatentPolicy with defaults"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create a new active policy even if one exists",
        )
        parser.add_argument(
            "--threshold",
            type=str,
            default=None,
            help="Optional cost escalation threshold (BR-PMS-051)",
        )

    def handle(self, *args, **options):
        active = PatentPolicy.objects.filter(is_active=True).first()
        if active and not options["force"]:
            msg = f"Active policy already exists (id={active.id}). Use --force to create a new one."
            self.stdout.write(msg)
            return

        threshold = Decimal(options["threshold"]) if options["threshold"] else None
        # Default pre-filing statuses eligible for withdrawal per BR-PMS-068
        withdrawal_states = [
            sm.DRAFT,
            sm.SUBMITTED,
            sm.UNDER_REVIEW,
            sm.NEEDS_REVISION,
            sm.APPROVED,
            sm.ATTORNEY_ASSIGNED,
            sm.PENDING_REVIEW,
            sm.ASSESSMENT_IN_PROGRESS,
        ]

        if options["force"] and active:
            active.is_active = False
            active.save()

        policy = PatentPolicy.objects.create(
            director_review_days=dl.DEFAULT_REVIEW_DAYS,
            revision_resubmission_days=dl.DEFAULT_REVISION_DAYS,
            cost_escalation_threshold=threshold,
            withdrawal_eligible_states=withdrawal_states,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Created active PatentPolicy (id={policy.id})."))
