"""Provision the first IAA administrator against an existing Fusion identity."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.directory import contracts as directory
from modules.iaa.domain.rules import Role
from modules.iaa.models import RoleAssignment
from modules.iaa.services import audit


class Command(BaseCommand):
    help = "Bootstrap one existing Fusion user's IAA configuration role (no IAM/module grant)"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", required=True, type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        uid = options["user_id"]
        if uid < 1 or uid not in directory.get_users([uid]):
            raise CommandError("Supply an existing Fusion user ID reachable through IAM.")
        if RoleAssignment.objects.filter(role=Role.ADMIN, active=True).exists():
            raise CommandError("An IAA administrator already exists; use IAA role configuration.")
        assignment, _ = RoleAssignment.objects.update_or_create(
            user_id=uid, role=Role.ADMIN, department="", defaults={"active": True}
        )
        audit(None, "bootstrap_administrator", assignment, details={"user_id": uid})
        self.stdout.write("IAA configuration administrator created; grant module access in IAM.")
