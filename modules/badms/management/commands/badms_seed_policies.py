from django.core.management.base import BaseCommand

from modules.badms.models import RetentionPolicy, SecurityPolicy


class Command(BaseCommand):
    help = "Seed default BADMS security policies and retention policies."

    def handle(self, *args, **options):
        policies = [
            ("Routine", 30, False),
            ("Sensitive", 365, False),
            ("Critical", 2555, False),
            ("Archival", 3650, False),
        ]
        created_count = 0
        for name, days, auto_purge in policies:
            _, created = RetentionPolicy.objects.get_or_create(
                data_classification=name,
                is_active=True,
                defaults={
                    "name": f"Default {name} Policy",
                    "retention_days": days,
                    "auto_purge_enabled": auto_purge,
                    "configured_by_user_id": 1,
                },
            )
            if created:
                created_count += 1

        SecurityPolicy.objects.get_or_create(
            policy_key="default_user_quota_bytes",
            is_active=True,
            defaults={
                "policy_value": {"quota_bytes": 10737418240},
                "configured_by_user_id": 1,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} retention policies and security policies.")
        )
