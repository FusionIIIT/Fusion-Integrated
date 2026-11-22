"""Administrative CLI, intentionally unavailable to operational API actors."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.visitor_hostel.models import AuditEvent, RoleAssignment


class Command(BaseCommand):
    help = "Assign the current time-bound hostel operator (IAM grants are also required)."

    def add_arguments(self, parser):
        parser.add_argument("role", choices=["vh_caretaker", "vh_in_charge"])
        parser.add_argument("user_id", type=int)
        parser.add_argument("--email", required=True)
        parser.add_argument("--ends-at", required=True, help="ISO 8601 with time-zone offset")
        parser.add_argument("--actor-id", required=True, type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        end = parse_datetime(options["ends_at"])
        now = timezone.now()
        if not end or timezone.is_naive(end) or end <= now:
            raise CommandError("End must be a future timezone-aware timestamp.")
        if options["user_id"] < 1 or options["actor_id"] < 1:
            raise CommandError("IAM user ids must be positive.")
        try:
            validate_email(options["email"])
        except ValidationError as exc:
            raise CommandError("A valid email is required.") from exc
        # update_or_create locks existing assignments; the unique role protects first creation.
        appointment, _ = RoleAssignment.objects.update_or_create(
            role=options["role"],
            defaults={
                "user_id": options["user_id"],
                "starts_at": now,
                "ends_at": end,
                "email": options["email"],
            },
        )
        AuditEvent.objects.create(
            actor_id=options["actor_id"],
            action="role_assigned",
            details={
                "role": appointment.role,
                "user_id": appointment.user_id,
                "ends_at": end.isoformat(),
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Assigned {appointment} until {end.isoformat()}"))
