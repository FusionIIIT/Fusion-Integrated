"""Remove everything a service published, when that service is gone.

    manage.py retire_publisher academic --dry-run
    manage.py retire_publisher academic --yes

Seeding cannot do this: a manifest with no modules is refused, deliberately,
so that an empty file can never be read as "revoke everything".
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from iam.models import IamDesignationModule, IamModule, RolePermission


class Command(BaseCommand):
    help = "Remove the grants, navigation and permissions a publisher owned"

    def add_arguments(self, parser):
        parser.add_argument("publisher", help="Publisher name, e.g. academic")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would go and write nothing.")
        parser.add_argument("--yes", action="store_true",
                            help="Required to actually delete.")

    def handle(self, *args, **opts):
        publisher, dry_run = opts["publisher"], opts["dry_run"]
        source = IamDesignationModule.manifest_source(publisher)

        grants = IamDesignationModule.objects.filter(source=source)
        modules = IamModule.objects.filter(source=source)
        codes = sorted(set(grants.values_list("module_code", flat=True))
                       | set(modules.values_list("code", flat=True)))
        if not codes:
            raise CommandError(
                f"No module is published by {publisher!r}. Nothing to retire.")

        # RolePermission carries no publisher, so match on the module prefix.
        prefixes = Q()
        for code in codes:
            prefixes |= Q(permission__startswith=f"{code}.")
        perms = RolePermission.objects.filter(prefixes)

        self.stdout.write(f"publisher {publisher!r} owns: {', '.join(codes)}")
        self.stdout.write(f"  {grants.count()} module grant(s)")
        self.stdout.write(f"  {modules.count()} navigation module(s)")
        self.stdout.write(f"  {perms.count()} role permission(s)")

        # Another live publisher may already own one of these codes.
        kept = (IamDesignationModule.objects
                .filter(module_code__in=codes)
                .filter(source__startswith=IamDesignationModule.MANIFEST_PREFIX)
                .exclude(source=source)
                .values_list("module_code", "source").distinct())
        if kept:
            detail = ", ".join(f"{m} (also {s})" for m, s in sorted(kept))
            raise CommandError(
                f"Another service still publishes: {detail}. Retiring here "
                f"would delete permissions that service still needs.")

        if dry_run:
            self.stdout.write(self.style.WARNING("dry run — nothing written"))
            return
        if not opts["yes"]:
            raise CommandError("Refusing to delete without --yes.")

        with transaction.atomic(using="system_db"):
            perms.delete()
            modules.delete()
            grants.delete()
        self.stdout.write(self.style.SUCCESS(f"retired {publisher}"))
