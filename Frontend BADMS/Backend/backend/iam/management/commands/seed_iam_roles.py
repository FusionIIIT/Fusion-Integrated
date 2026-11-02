"""Seed the role catalogue from the declared policy in iam/rbac.py.

    manage.py seed_iam_roles [--dry-run]

Idempotent. A role removed from the declaration is deactivated, not deleted:
IamRoleViolation rows and any report referencing it stay readable.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from iam import rbac
from iam.models import IamRole


class Command(BaseCommand):
    help = "Seed the designation role catalogue and who may hold each role"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change without writing.")

    @transaction.atomic
    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        declared = {code: (label, category, kinds)
                    for code, label, category, kinds in rbac.CATALOGUE}
        existing = {r.code: r for r in IamRole.objects.all()}

        added = changed = deactivated = 0
        for code, (label, category, kinds) in sorted(declared.items()):
            allowed = ",".join(sorted(kinds))
            row = existing.get(code)
            if row is None:
                added += 1
                self.stdout.write(f"  + {code} ({category}) -> {allowed}")
                if not dry_run:
                    IamRole.objects.create(code=code, label=label,
                                           category=category,
                                           allowed_kinds=allowed)
            elif (row.label, row.category, row.allowed_kinds, row.is_active) != (
                    label, category, allowed, True):
                changed += 1
                self.stdout.write(f"  ~ {code} ({category}) -> {allowed}")
                if not dry_run:
                    row.label, row.category = label, category
                    row.allowed_kinds, row.is_active = allowed, True
                    row.save()

        for code, row in sorted(existing.items()):
            if code not in declared and row.is_active:
                deactivated += 1
                self.stdout.write(self.style.WARNING(f"  - {code} deactivated"))
                if not dry_run:
                    row.is_active = False
                    row.save(update_fields=["is_active"])

        self.stdout.write(self.style.SUCCESS(
            f"{added} added, {changed} updated, {deactivated} deactivated; "
            f"{len(declared)} role(s) declared"))
