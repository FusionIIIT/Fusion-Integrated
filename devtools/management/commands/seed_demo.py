"""Demo fixtures.

Lives in `devtools` rather than inside a module: seeding is cross-cutting and
would otherwise make one module import three others' models. `devtools` is a
tool, not a bounded context, so .importlinter exempts it explicitly.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.directory.models import UserRef
from modules.placement.models import Application, Company, JobPosting


class Command(BaseCommand):
    help = "Load demo data (idempotent)"

    @transaction.atomic
    def handle(self, *args, **opts):
        for uid, name, kind, disc in [
            (1001, "Asha Verma", "student", "CSE"),
            (1002, "Bo Li", "student", "CSE"),
            (1003, "Chandra Rao", "student", "ECE"),
            (9001, "Dr. Meera Nair", "faculty", ""),
        ]:
            UserRef.objects.update_or_create(
                user_id=uid,
                defaults={"username": f"u{uid}", "display_name": name, "kind": kind,
                          "discipline": disc,
                          "batch_year": 2023 if kind == "student" else None},
            )

        acme, _ = Company.objects.update_or_create(
            slug="acme", defaults={"name": "Acme Corp", "sector": "IT",
                                       "tier_rank": 1, "status": "active"})

        posting, _ = JobPosting.objects.update_or_create(
            company=acme, title="SDE-1", placement_year="2026-27",
            defaults={
                "ctc_lpa": "18.00", "seats": 4, "status": "published",
                "eligibility_rule": {"all": [{"gte": ["cpi", 7.0]},
                                             {"in": ["discipline", ["CSE", "ECE"]]}]},
                "eligibility_rule_locked_at": timezone.now(),
                "opens_at": timezone.now(),
                "closes_at": timezone.now() + timedelta(days=14),
                "created_by_user_id": 9001,
            })

        for uid, status in [(1001, "submitted"), (1002, "under_review")]:
            Application.objects.update_or_create(
                posting=posting, user_id=uid,
                defaults={"status": status, "cpi_at_apply": "8.10",
                          "eligibility_snapshot": {"is_eligible": True},
                          "applied_at": timezone.now()})

        # --- ELM Fixtures ---
        from modules.elm.models import (
            ApprovalHierarchy,
            HolidayCalendar,
            LeaveAccount,
            LeavePolicyConfig,
            SlaThresholdConfig,
        )

        LeavePolicyConfig.objects.update_or_create(id=1, defaults={"is_active": True})
        cal, _ = HolidayCalendar.objects.update_or_create(
            year=timezone.now().year,
            defaults={"label": f"Annual Calendar {timezone.now().year}", "is_published": True},
        )
        ApprovalHierarchy.objects.update_or_create(
            id=1,
            defaults={
                "department": "",
                "designation": "",
                "leave_category": "",
                "unit_head_user_id": 9001,
                "sanctioning_authority_user_id": 9001,
                "sanctioning_authority_role": "Director",
                "is_active": True,
            },
        )
        for tt, rh, eh in [
            ("substitute_response", 24, 48),
            ("unit_head_review", 48, 96),
            ("establishment_routing", 48, 96),
            ("final_sanction", 72, 120),
        ]:
            SlaThresholdConfig.objects.update_or_create(
                task_type=tt,
                defaults={"reminder_threshold_hours": rh, "escalation_threshold_hours": eh},
            )

        # Faculty account for 9001
        from decimal import Decimal
        for cat, bal in [("CL", "8.00"), ("RH", "2.00"), ("EL", "30.00"), ("VL", "60.00")]:
            LeaveAccount.objects.update_or_create(
                user_id=9001,
                year=timezone.now().year,
                category=cat,
                defaults={"credited": Decimal(bal), "balance": Decimal(bal)},
            )

        self.stdout.write(self.style.SUCCESS("demo data loaded"))
