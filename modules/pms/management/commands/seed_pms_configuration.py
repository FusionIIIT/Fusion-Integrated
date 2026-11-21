"""Create only specification-defined PMS policy defaults that are missing."""

from django.core.management.base import BaseCommand

from modules.pms.models import PmsConfiguration

SEEDED_POLICY = {
    "review_business_days": 15,
    "revision_days": 60,
    "alert_offsets": [30, 15, 5],
}


class Command(BaseCommand):
    help = "Seed the fixed PMS policy values stated in the specifications."

    def handle(self, *args, **options):
        created = 0
        for key, value in SEEDED_POLICY.items():
            _, was_created = PmsConfiguration.objects.get_or_create(
                key=key,
                defaults={"value": value, "description": f"Seeded specification policy: {key}."},
            )
            created += was_created
        self.stdout.write(f"Created {created} missing PMS policy value(s).")
