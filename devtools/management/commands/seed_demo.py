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
from modules.leave.models import (
    AuthorityAssignment,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    OrganizationalUnit,
    SlaThreshold,
    VacationPeriod,
)
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
            (9002, "Ravi Kumar", "staff", ""),
            (9003, "Dr. Sunil Joshi", "faculty", ""),
            (9004, "Kavita Rao", "staff", ""),
            (9005, "Dr. Anil Sharma", "faculty", ""),
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

        # -- leave: the configuration a fresh install needs before the first
        # application can route (policy and calendars are data, not code).
        LeavePolicy.objects.get_or_create(id=1)

        cse, _ = OrganizationalUnit.objects.update_or_create(
            code="CSE", defaults={"name": "Computer Science & Engineering",
                                  "kind": "department", "head_user_id": 9001})
        ece, _ = OrganizationalUnit.objects.update_or_create(
            code="ECE", defaults={"name": "Electronics & Communication",
                                  "kind": "department", "head_user_id": 9003})
        for role, uid, unit in [
            ("establishment", 9002, None), ("dean", 9003, None),
            ("registrar", 9004, None), ("director", 9005, None),
        ]:
            AuthorityAssignment.objects.update_or_create(
                role_code=role, org_unit=unit,
                defaults={"user_id": uid, "categories": []})
        AuthorityAssignment.objects.update_or_create(
            role_code="establishment", org_unit=cse,
            defaults={"user_id": 9002, "categories": []})
        AuthorityAssignment.objects.update_or_create(
            role_code="establishment", org_unit=ece,
            defaults={"user_id": 9004, "categories": []})

        calendar, _ = HolidayCalendar.objects.update_or_create(
            title="Institute Calendar 2026", academic_year="2026-27",
            defaults={"status": "published",
                      "published_at": timezone.now(),
                      "published_by_user_id": 9004})
        for day, name, kind in [
            ("2026-08-15", "Independence Day", "closed"),
            ("2026-10-02", "Gandhi Jayanti", "closed"),
            ("2026-11-08", "Diwali", "restricted"),
            ("2026-03-04", "Holi", "restricted"),
        ]:
            Holiday.objects.update_or_create(
                calendar=calendar, date=day,
                defaults={"name": name, "kind": kind})
        VacationPeriod.objects.update_or_create(
            name="Winter Vacation", academic_year="2026-27",
            defaults={"start_date": "2026-12-21", "end_date": "2027-01-01",
                      "source_ref": "Academic Calendar 2026-27"})

        for task_class, reminder, escalation in [
            ("substitute_response", 24, 72),
            ("unit_head_review", 48, 120),
            ("establishment_routing", 48, 120),
            ("final_sanction", 72, 168),
            ("director_sanction", 72, 168),
            ("resumption_review", 72, 168),
        ]:
            SlaThreshold.objects.update_or_create(
                task_class=task_class,
                defaults={"reminder_hours": reminder,
                          "escalation_hours": escalation,
                          "escalation_user_id": None})

        self.stdout.write(self.style.SUCCESS("demo data loaded"))
