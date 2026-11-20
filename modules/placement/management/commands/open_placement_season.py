"""Open a placement season with the signed policy's default categories."""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.placement.domain import offer_policy as pol
from modules.placement.models import PlacementPolicy, PolicyCategory


class Command(BaseCommand):
    help = "Create a season's policy. An existing season is left unchanged."

    def add_arguments(self, parser):
        parser.add_argument("--season", required=True, help="For example 2026-27.")
        parser.add_argument("--registration-closes", type=date.fromisoformat,
                            help="Last day to register without the late fee, YYYY-MM-DD.")
        parser.add_argument("--offer-hours", type=int, default=72,
                            help="Offer response deadline when a recruiter sets none.")

    @transaction.atomic
    def handle(self, *args, **opts):
        season = opts["season"].strip()
        if not season:
            raise CommandError("Give the season, for example --season 2026-27.")
        if opts["offer_hours"] < 1:
            raise CommandError("--offer-hours must be at least 1.")
        policy, created = PlacementPolicy.objects.get_or_create(
            season=season, defaults={
                "label": f"Placement season {season}", "is_active": True,
                "discipline_groups": dict(pol.DEFAULT_GROUP_MAP),
                "registration_closes_on": opts["registration_closes"],
                "default_offer_response_hours": opts["offer_hours"]})
        if not created:
            self.stdout.write(f"Season {season} already exists; nothing changed.")
            return
        for c in pol.default_categories():
            PolicyCategory.objects.create(
                policy=policy, group=c.group, number=c.number, ctc_min=c.ctc_min,
                ctc_max=c.ctc_max, switch_multiplier=c.switch_multiplier,
                switch_floor=c.switch_floor, exit_above=c.exit_above,
                max_switches=c.max_switches)
        self.stdout.write(self.style.SUCCESS(
            f"Opened season {season} with {policy.categories.count()} categories."))
