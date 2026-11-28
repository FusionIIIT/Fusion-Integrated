"""Publish a new Gymkhana venue list (BR-GYM-020); earlier lists are kept, never edited."""
from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.gymkhana.services.venues import seed_venue_list


class Command(BaseCommand):
    help = "Seed the venues Gymkhana sessions and events may be booked in"

    def add_arguments(self, parser):
        parser.add_argument("--venue", action="append", default=[], dest="venues",
                            help="A venue name; repeat for each venue.")
        parser.add_argument("--effective-from", dest="effective_from",
                            help="Date the list takes effect (YYYY-MM-DD); default now.")

    def handle(self, *args, **opts):
        effective = None
        if opts["effective_from"]:
            try:
                day = datetime.strptime(opts["effective_from"], "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("--effective-from must look like 2026-12-01.") from exc
            effective = timezone.make_aware(datetime.combine(day, time.min))
        try:
            venue_list = seed_venue_list(names=opts["venues"], effective_from=effective,
                                         created_by_label="seed_gymkhana_venues")
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        names = list(venue_list.venues.order_by("name").values_list("name", flat=True))
        when = timezone.localtime(venue_list.effective_from).strftime("%Y-%m-%d %H:%M")
        self.stdout.write(self.style.SUCCESS(
            f"Venue list {venue_list.pk} takes effect {when}: {', '.join(names)}"))
