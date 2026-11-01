from django.core.management.base import BaseCommand, CommandError

from modules.psm.domain.rules import ROLES
from modules.psm.models import Membership, Vendor


class Command(BaseCommand):
    help = "Assign PSM department scope; the matching IAM PSM role grant is still required."

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, required=True)
        parser.add_argument("--role", choices=ROLES, required=True)
        parser.add_argument("--department", required=True)
        parser.add_argument("--vendor-id")

    def handle(self, *args, **options):
        if (
            options["role"] == "vendor"
            and not Vendor.objects.filter(pk=options["vendor_id"]).exists()
        ):
            raise CommandError("Vendor scope requires an existing vendor-id.")
        row, _ = Membership.objects.update_or_create(
            user_id=options["user_id"],
            defaults={
                "role": options["role"],
                "department": options["department"],
                "vendor_id": options["vendor_id"] if options["role"] == "vendor" else None,
            },
        )
        self.stdout.write(
            f"Assigned PSM scope for IAM user {row.user_id}; IAM permissions are unchanged."
        )
