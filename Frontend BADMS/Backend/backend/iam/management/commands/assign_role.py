"""Grant or revoke one designation on one ERP-user account.

    manage.py assign_role --user u1001 --designation "Leave Approver"
    manage.py assign_role --user u1001 --designation "Leave Approver" --remove

--user accepts a username or an erp_user_id. --designation is free text: it
does not have to exist in the IamRole catalogue (iam/rbac.py) first — an
uncatalogued designation is allowed, same as the platform already treats one
the ERP invents overnight. This command ships with no built-in designation of
its own; every ELM pilot pair supplies the name their own implementation
invented.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from iam import services
from iam.models import IamUser, IamUserDesignation


class Command(BaseCommand):
    help = "Grant or revoke a designation on one ERP-user test account"

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True,
                            help="Username or erp_user_id")
        parser.add_argument("--designation", required=True,
                            help="Designation name, e.g. 'Leave Approver'")
        parser.add_argument("--remove", action="store_true",
                            help="Revoke instead of grant")

    def _resolve_user(self, value):
        user = (IamUser.objects.filter(erp_user_id=value).first()
                if value.isdigit() else None)
        if user is None:
            user = IamUser.objects.filter(username__iexact=value).first()
        if user is None:
            raise CommandError(f"No ERP user matches {value!r}")
        return user

    @transaction.atomic
    def handle(self, *args, **opts):
        user = self._resolve_user(opts["user"])
        designation = opts["designation"].strip()
        if not designation:
            raise CommandError("--designation cannot be empty")

        if opts["remove"]:
            deleted, _ = IamUserDesignation.objects.filter(
                erp_user_id=user.erp_user_id, designation=designation).delete()
            verb = "Revoked" if deleted else "Was not held:"
        else:
            _, created = IamUserDesignation.objects.get_or_create(
                erp_user_id=user.erp_user_id, designation=designation)
            verb = "Granted" if created else "Already held:"

        self.stdout.write(self.style.SUCCESS(f"{verb} {designation!r} on {user.username}"))

        held = [user.kind, *services.designations_for(user.erp_user_id)]
        self.stdout.write(f"  now holds: {', '.join(held)}")
