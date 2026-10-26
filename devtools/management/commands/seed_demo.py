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

        # --- Leave module fixtures ---
        from decimal import Decimal
        from modules.leave.models import ApprovingAuthority, LeaveBalance, LeaveRequest
        from modules.leave.services.balances import ensure_balances_for_user

        # Seed approving authorities
        for auth_uid, role, dept in [
            (9001, "HOD", "CSE"),
            (9002, "Registrar", ""),
            (9003, "Director", ""),
        ]:
            ApprovingAuthority.objects.update_or_create(
                user_id=auth_uid,
                defaults={"role": role, "department": dept, "is_active": True},
            )

        # Seed balances for demo users
        for uid in [1001, 1002, 1003, 9001]:
            ensure_balances_for_user(uid)

        # Seed sample leave requests
        LeaveRequest.objects.get_or_create(
            user_id=1001,
            leave_type="casual",
            start_date=timezone.now().date() + timedelta(days=5),
            end_date=timezone.now().date() + timedelta(days=6),
            defaults={
                "duration_days": Decimal("2.0"),
                "justification": "Attending national robotics symposium",
                "status": LeaveRequest.Status.PENDING_CURRENT_AUTHORITY,
                "current_authority_id": 9001,
                "current_authority_role": "HOD",
            },
        )
        LeaveRequest.objects.get_or_create(
            user_id=1002,
            leave_type="medical",
            start_date=timezone.now().date() - timedelta(days=10),
            end_date=timezone.now().date() - timedelta(days=8),
            defaults={
                "duration_days": Decimal("3.0"),
                "justification": "Recovering from viral fever and medical observation",
                "status": LeaveRequest.Status.APPROVED,
                "current_authority_id": 9001,
                "current_authority_role": "HOD",
            },
        )



        self.stdout.write(self.style.SUCCESS("demo data loaded"))
