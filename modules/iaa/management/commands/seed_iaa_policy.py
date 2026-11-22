"""Seed default IAA configuration, department budgets, and hierarchy rules."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.iaa.models import ApprovalHierarchyRule, DepartmentBudget, IAAConfiguration


class Command(BaseCommand):
    help = "Seed initial policy, hierarchy, and department budgets for IAA."

    def handle(self, *args, **options):
        config, created = IAAConfiguration.objects.get_or_create(
            is_active=True,
            defaults={
                "financial_year": "2026-2027",
                "high_value_ta_threshold": Decimal("50000.00"),
                "approval_timeout_days": 3,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created active IAA Configuration."))

        depts = ["CSE", "ECE", "ME", "Design", "Natural Sciences"]
        for dept in depts:
            _budget, b_created = DepartmentBudget.objects.get_or_create(
                department=dept,
                financial_year=config.financial_year,
                defaults={
                    "allocated_amount": Decimal("1000000.00"),
                    "utilized_amount": Decimal("0.00"),
                },
            )
            if b_created:
                self.stdout.write(f"Created initial budget for {dept}.")

        # Hierarchy rules
        ApprovalHierarchyRule.objects.get_or_create(
            request_type="expense",
            min_amount=Decimal("0.00"),
            max_amount=Decimal("25000.00"),
            defaults={"required_levels": 1, "approver_roles": ["HOD"]},
        )
        ApprovalHierarchyRule.objects.get_or_create(
            request_type="expense",
            min_amount=Decimal("25000.01"),
            max_amount=Decimal("100000.00"),
            defaults={"required_levels": 2, "approver_roles": ["HOD", "Dean"]},
        )
        ApprovalHierarchyRule.objects.get_or_create(
            request_type="expense",
            min_amount=Decimal("100000.01"),
            max_amount=None,
            defaults={"required_levels": 3, "approver_roles": ["HOD", "Dean", "Director"]},
        )
        self.stdout.write(self.style.SUCCESS("IAA policy and rules successfully seeded."))
