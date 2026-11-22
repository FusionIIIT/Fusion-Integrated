"""Check deployment readiness of the IAA module and report unmet prerequisites."""

from django.core.management.base import BaseCommand

from modules.iaa.models import ApprovalHierarchyRule, DepartmentBudget, IAAConfiguration


class Command(BaseCommand):
    help = "Verify IAA module readiness."

    def handle(self, *args, **options):
        unmet = []

        if not IAAConfiguration.objects.filter(is_active=True).exists():
            unmet.append("Active IAAConfiguration row is missing (run 'manage.py seed_iaa_policy')")

        if not DepartmentBudget.objects.exists():
            unmet.append("No department budgets configured (run 'manage.py seed_iaa_policy')")

        if not ApprovalHierarchyRule.objects.exists():
            unmet.append("No approval hierarchy rules configured (run 'manage.py seed_iaa_policy')")

        if unmet:
            self.stderr.write(self.style.ERROR("IAA module is not ready. Unmet prerequisites:"))
            for item in unmet:
                self.stderr.write(f"  - {item}")
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("IAA module is fully configured and ready."))
