"""Seed the baseline policy and a starting hierarchy; touches nothing that already exists."""
from django.core.management.base import BaseCommand
from django.db import transaction

from modules.leave.services import configuration


class Command(BaseCommand):
    help = "Seed Leave's baseline policy (PS v1.4 numbers) and a starting approval hierarchy"

    @transaction.atomic
    def handle(self, *args, **options):
        policy = configuration.seed_policy()
        hierarchy = configuration.seed_hierarchy()
        self.stdout.write(f"  policy: {f'seeded r{policy.pk}' if policy else 'already set'}")
        self.stdout.write(
            f"  hierarchy: {f'seeded r{hierarchy.pk}' if hierarchy else 'already set'}")
