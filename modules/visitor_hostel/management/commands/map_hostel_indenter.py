"""Explicit operator-verified identity mapping; local Django ids are not IAM ids."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.visitor_hostel.models import AuditEvent, BookingRequest


class Command(BaseCommand):
    help = "Map preserved legacy booking ownership to an operator-verified IAM identity."

    def add_arguments(self, parser):
        parser.add_argument("legacy_id", type=int)
        parser.add_argument("iam_id", type=int)
        parser.add_argument("--actor-id", required=True, type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        if min(options["legacy_id"], options["iam_id"], options["actor_id"]) < 1:
            raise CommandError("All identity ids must be positive.")
        bookings = list(
            BookingRequest.objects.select_for_update().filter(
                legacy_indenter_id=options["legacy_id"]
            )
        )
        if not bookings:
            raise CommandError("No legacy bookings match this identity.")
        if any(b.indenter_id not in (None, options["iam_id"]) for b in bookings):
            raise CommandError(
                "A different mapping already exists; investigate before changing ownership."
            )
        for booking in bookings:
            if booking.indenter_id is not None:
                continue
            booking.indenter_id = options["iam_id"]
            booking.save(update_fields=["indenter_id", "updated_at"])
            AuditEvent.objects.create(
                booking=booking,
                actor_id=options["actor_id"],
                action="legacy_identity_mapped",
                details={"legacy_id": options["legacy_id"], "iam_id": options["iam_id"]},
            )
        self.stdout.write(f"Mapped {len(bookings)} legacy bookings.")
