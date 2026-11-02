"""Seed reference data: 3 zones, 2 gates, published policy v1 (SRS defaults) and
a published, empty blacklist v1. Idempotent: safe to run on every deploy."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.vms.models import (
    AccessPolicy, BlacklistVersion, Gate, Zone,
)


class Command(BaseCommand):
    help = "Seed VMS zones, gates, access policy v1 and blacklist v1."

    @transaction.atomic
    def handle(self, *args, **options):
        lobby, _ = Zone.objects.get_or_create(name="Lobby")
        academic, _ = Zone.objects.get_or_create(name="Academic block")
        hostel, _ = Zone.objects.get_or_create(name="Hostel", defaults={"is_restricted": True})
        Gate.objects.get_or_create(name="Main Gate", defaults={"zone": lobby})
        Gate.objects.get_or_create(name="Academic Gate", defaults={"zone": academic})

        if not AccessPolicy.objects.filter(status=AccessPolicy.Status.PUBLISHED).exists():
            # Model defaults are the SRS defaults: 8h max, 4h walk-in, 24h
            # approval timeout, 2h advance registration.
            policy = AccessPolicy.objects.create(
                version=(AccessPolicy.objects.order_by("-version")
                         .values_list("version", flat=True).first() or 0) + 1,
                status=AccessPolicy.Status.PUBLISHED, published_at=timezone.now())
            policy.restricted_zones.add(hostel)
        if not BlacklistVersion.objects.filter(status=BlacklistVersion.Status.PUBLISHED).exists():
            BlacklistVersion.objects.create(
                version=(BlacklistVersion.objects.order_by("-version")
                         .values_list("version", flat=True).first() or 0) + 1,
                status=BlacklistVersion.Status.PUBLISHED, published_at=timezone.now())
        self.stdout.write(self.style.SUCCESS("VMS seed data ready."))
