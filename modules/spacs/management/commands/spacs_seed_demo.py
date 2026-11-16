"""Management command to seed demo schemes and cycles for testing and development."""

from django.core.management.base import BaseCommand

from modules.spacs.models import SpacsAwardCycle, SpacsCatalogueEntry


class Command(BaseCommand):
    help = "Seed demo SPACS schemes and cycles."

    def handle(self, *args, **options):
        scheme, _ = SpacsCatalogueEntry.objects.get_or_create(
            scheme_code="DIRECTORS-MERIT-2026",
            defaults={
                "name": "Director's Merit Scholarship",
                "scheme_type": "scholarship",
                "description": "Excellence in academics for top rankers",
                "status": "published",
                "min_cpi": 8.5,
                "academic_cycle": "2026-27",
            },
        )
        cycle, _ = SpacsAwardCycle.objects.get_or_create(
            catalogue_entry=scheme,
            academic_cycle="2026-27",
            defaults={
                "state": "open",
                "criteria_version": 1,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded scheme '{scheme.name}' and cycle '{cycle.academic_cycle}'."
            )
        )
