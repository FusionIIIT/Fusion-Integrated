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
from modules.leave.models import LeaveBalance, RestrictedHoliday
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
            (9002, "Ravi Kulkarni", "staff", ""),
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



        # ELM: an opening balance per employee, and a published RH calendar.
        for uid, kind in [(9001, "faculty"), (9002, "staff")]:
            for leave_type, entitled in [("CL", 8), ("RH", 2), ("SCL", 15),
                                         ("COL", 20),
                                         ("VL" if kind == "faculty" else "EL",
                                          60 if kind == "faculty" else 30)]:
                LeaveBalance.objects.update_or_create(
                    user_id=uid, year="2026-27", leave_type=leave_type,
                    defaults={"entitled": entitled})

        for on_date, name, closed in [("2026-04-14", "Ambedkar Jayanti", False),
                                      ("2026-08-15", "Independence Day", True),
                                      ("2026-10-02", "Gandhi Jayanti", True),
                                      ("2026-11-08", "Guru Nanak Jayanti", False)]:
            RestrictedHoliday.objects.update_or_create(
                on_date=on_date, name=name,
                defaults={"year": "2026-27", "is_closed_holiday": closed,
                          "is_published": True})

        self.stdout.write(self.style.SUCCESS("demo data loaded"))
