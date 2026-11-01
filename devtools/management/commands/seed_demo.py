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



        from modules.lms.models import Course as LmsCourse
        from modules.lms.models import CourseMembership as LmsMembership

        s_cs301 = (
            "1. Relational Model & SQL\n2. Normalization\n"
            "3. Storage & Indexing\n4. Query Optimization\n5. Transactions"
        )
        cs301, _ = LmsCourse.objects.update_or_create(
            code="CS301",
            defaults={
                "title": "Database Systems",
                "description": "Relational model, SQL, transactions, concurrency, and indexing.",
                "syllabus": s_cs301,
                "schedule": "Monday & Wednesday: 10:00 AM - 11:30 AM (L-201)",
                "status": "published",
            },
        )

        s_cs302 = (
            "1. Intro to OS\n2. Process Management\n"
            "3. CPU Scheduling\n4. Deadlocks\n5. Memory Virtualization"
        )
        cs302, _ = LmsCourse.objects.update_or_create(
            code="CS302",
            defaults={
                "title": "Operating Systems",
                "description": "Processes, threads, scheduling, synchronization, and memory.",
                "syllabus": s_cs302,
                "schedule": "Tuesday & Thursday: 02:00 PM - 03:30 PM (L-202)",
                "status": "published",
            },
        )

        for course, uid, role in [
            (cs301, 9001, "faculty"),
            (cs301, 1001, "student"),
            (cs301, 1002, "ta"),
            (cs301, 1003, "observer"),
            (cs302, 9001, "faculty"),
            (cs302, 1001, "student"),
            (cs302, 1002, "student"),
        ]:
            LmsMembership.objects.update_or_create(
                course=course, user_id=uid, defaults={"role": role}
            )

        self.stdout.write(self.style.SUCCESS("demo data loaded"))
