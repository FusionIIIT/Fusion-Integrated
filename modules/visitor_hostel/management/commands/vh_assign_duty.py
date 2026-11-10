"""Put a Caretaker or VH In-Charge on duty, and move open records to them.

    manage.py vh_assign_duty --role caretaker --user-id 4211 --until 2027-03-31
    manage.py vh_assign_duty --show

The person must also hold the VhCaretaker / VhIncharge designation in the IAM,
or they will be on duty with no permission to act.
"""
from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.directory import contracts as directory
from modules.visitor_hostel.domain import duty
from modules.visitor_hostel.models import DutyAssignment
from modules.visitor_hostel.services import duty as duty_service


class Command(BaseCommand):
    help = "Assign the on-duty Caretaker or VH In-Charge (UC-VH-019)"

    def add_arguments(self, parser):
        parser.add_argument("--role", choices=duty.ROLES)
        parser.add_argument("--user-id", type=int)
        parser.add_argument("--until", help="Last day of the assignment, YYYY-MM-DD.")
        parser.add_argument("--note", default="")
        parser.add_argument("--show", action="store_true", help="List who is on duty.")

    def handle(self, *args, **opts):
        if opts["show"]:
            for row in DutyAssignment.objects.filter(ended_at__isnull=True).order_by("role"):
                self.stdout.write(f"  {row.role:<10} user {row.user_id}  until "
                                  f"{row.valid_until:%Y-%m-%d %H:%M}")
            return
        if not (opts["role"] and opts["user_id"] and opts["until"]):
            raise CommandError("--role, --user-id and --until are required.")
        try:
            last_day = datetime.strptime(opts["until"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("--until must be YYYY-MM-DD.") from exc
        until = timezone.make_aware(datetime.combine(last_day, time.max))

        try:
            known = directory.get_users([opts["user_id"]])
        except Exception as exc:                               # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"  directory unavailable ({exc}); "
                                                 f"not verifying the user id"))
            known = None
        if known is not None and opts["user_id"] not in known:
            raise CommandError(f"No user {opts['user_id']} in the institute directory.")

        try:
            result = duty_service.assign(role=opts["role"], user_id=opts["user_id"],
                                         valid_until=until, note=opts["note"])
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        self.stdout.write(self.style.SUCCESS(
            f"  {duty.LABELS[opts['role']]} is now user {opts['user_id']} until {last_day}"
            f" (was {result.previous_user_id or 'nobody'}); moved "
            f"{result.pending_transferred} pending and {result.ongoing_transferred} "
            f"ongoing booking(s)"))
