"""ELM demo fixtures — an org unit, employee profiles, hierarchy,
holiday calendar, vacation period and leave accounts.

Lives in `devtools` (a tool, not a bounded context) so it may cross
module boundaries; the ELM module itself owns no demo data.

Idempotent: safe to re-run; also picked up by `make seed`.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.elm.models import (
    EmployeeProfile,
    HierarchyConfig,
    Holiday,
    HolidayCalendar,
    LeaveAccount,
    OrgUnit,
    VacationPeriod,
)
from modules.elm.services import policy as policy_service

#: Demo cast (must be IAM users; see seed_demo for directory refs).
APPLICANT = 5328      # fac00001 — the demo employee you log in as
UNIT_HEAD = 5319      # fac00050
DEAN = 5320           # fac00040
ESTABLISHMENT = 3348  # usr03348 — holds "Deputy Registrar (Estt.)"


class Command(BaseCommand):
    help = "Load ELM demo data (idempotent)"

    @transaction.atomic
    def handle(self, *args, **opts):
        unit, _ = OrgUnit.objects.update_or_create(
            code="cse",
            defaults={"name": "Computer Science & Engineering",
                      "unit_type": "department",
                      "head_user_id": UNIT_HEAD},
        )

        for user_id, kind, designation, u in [
            (APPLICANT, "faculty", "Professor", unit),
            (UNIT_HEAD, "faculty", "Associate Professor", unit),
            (DEAN, "faculty", "Dean", None),
            (ESTABLISHMENT, "staff", "Deputy Registrar (Estt.)", None),
        ]:
            EmployeeProfile.objects.update_or_create(
                user_id=user_id,
                defaults={"employee_kind": kind,
                          "designation_name": designation,
                          "unit_code": u,
                          "is_active": True},
            )

        for group, est_required in [("cl_rh", False),
                                    ("higher_sanction", True)]:
            HierarchyConfig.objects.update_or_create(
                category_group=group, unit_type="department",
                defaults={"establishment_required": est_required,
                          "sanctioning_authority": "Dean"},
            )

        calendar, _created = HolidayCalendar.objects.get_or_create(
            name="Institute Calendar 2026", year=2026,
            defaults={"description": "Demo calendar"},
        )
        if calendar.published_at is None:
            for d, label, kind in [
                (date(2026, 1, 26), "Republic Day", "holiday"),
                (date(2026, 8, 15), "Independence Day", "holiday"),
                (date(2026, 10, 2), "Gandhi Jayanti", "holiday"),
                (date(2026, 10, 24), "Diwali", "holiday"),
                (date(2026, 10, 12), "Dussehra", "restricted_holiday"),
                (date(2026, 11, 1), "Guru Nanak Jayanti", "restricted_holiday"),
            ]:
                Holiday.objects.get_or_create(
                    calendar=calendar, date=d,
                    defaults={"label": label, "kind": kind, "closed": True},
                )
            calendar.published_at = timezone.now()
            calendar.save(update_fields=["published_at"])

        VacationPeriod.objects.update_or_create(
            label="Autumn Vacation 2026",
            start_date=date(2026, 10, 1),
            defaults={"end_date": date(2026, 10, 31),
                      "academic_year": "2026-27"},
        )

        leave_year = policy_service.leave_year_for(timezone.now().date())
        for category in ("CL", "RH", "SCL", "EL", "COL", "VL"):
            LeaveAccount.objects.get_or_create(
                user_id=APPLICANT, leave_year=leave_year, category=category,
                defaults={"entitled_days": policy_service.entitlement_for(
                    category, "faculty")},
            )

        self.stdout.write(self.style.SUCCESS("elm demo data loaded"))
