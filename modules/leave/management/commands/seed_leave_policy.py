import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.leave.models import (
    AuthorityRule,
    Calendar,
    CategoryRule,
    Holiday,
    Policy,
    SlaRule,
    VacationPeriod,
)


class Command(BaseCommand):
    help = "Seed default leave policy, calendars, category rules, authority rules, and SLA rules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=2026, help="Academic/calendar year to seed."
        )

    def handle(self, *args, **options):
        year = options["year"]
        self.stdout.write(f"Seeding leave policy and calendar for year {year}...")

        # seed or get calendar
        calendar, _ = Calendar.objects.get_or_create(
            year=year,
            version="1.0",
            defaults={
                "published": True,
            },
        )
        if not calendar.published:
            calendar.published = True
            calendar.save(update_fields=["published"])

        # seed holidays
        holidays_data = [
            (datetime.date(year, 1, 26), "Republic Day", False),
            (datetime.date(year, 3, 4), "Holi", False),
            (datetime.date(year, 3, 31), "Id-ul-Fitr", False),
            (datetime.date(year, 8, 15), "Independence Day", False),
            (datetime.date(year, 10, 2), "Mahatma Gandhi Birthday", False),
            (datetime.date(year, 10, 20), "Dussehra", False),
            (datetime.date(year, 11, 8), "Diwali", False),
            (datetime.date(year, 12, 25), "Christmas Day", False),
            # restricted holidays
            (datetime.date(year, 1, 14), "Makar Sankranti", True),
            (datetime.date(year, 2, 16), "Maha Shivratri", True),
            (datetime.date(year, 4, 14), "Vaisakhi", True),
            (datetime.date(year, 11, 24), "Guru Nanak Birthday", True),
        ]
        for dt, h_name, is_rh in holidays_data:
            Holiday.objects.get_or_create(
                calendar=calendar,
                day=dt,
                defaults={"name": h_name, "restricted": is_rh},
            )

        # seed vacation period
        VacationPeriod.objects.get_or_create(
            calendar=calendar,
            name=f"Summer Vacation {year}",
            defaults={
                "starts_on": datetime.date(year, 5, 15),
                "ends_on": datetime.date(year, 7, 15),
            },
        )

        # seed policy
        policy, _ = Policy.objects.get_or_create(
            version=f"{year}.1",
            defaults={
                "effective_from": datetime.date(year, 1, 1),
                "effective_to": datetime.date(year, 12, 31),
                "published": True,
                "note": f"IIITDM Jabalpur Default Leave Policy {year}",
            },
        )
        if not policy.published:
            policy.published = True
            policy.save(update_fields=["published"])

        # seed category rules
        category_rules_data = [
            ("CL", Decimal("8.0"), False, None, True, False),
            ("RH", Decimal("2.0"), False, None, True, False),
            ("EL", Decimal("30.0"), True, Decimal("300.0"), True, False),
            ("SCL", Decimal("15.0"), False, None, True, True),
            ("COL", Decimal("0.0"), False, None, True, False),
            ("VL", Decimal("60.0"), False, None, True, False),
            ("ML", Decimal("180.0"), False, None, True, True),
            ("PL", Decimal("15.0"), False, None, True, True),
            ("CCL", Decimal("730.0"), False, None, True, True),
            ("SL", Decimal("24.0"), False, None, True, True),
            ("LND", Decimal("360.0"), False, None, True, True),
            ("EOL", Decimal("0.0"), False, None, True, False),
        ]
        for cat, annual_credit, carries_fwd, cap, faculty, req_ev in category_rules_data:
            CategoryRule.objects.get_or_create(
                policy=policy,
                category=cat,
                applies_to_faculty=faculty,
                defaults={
                    "annual_credit": annual_credit,
                    "carries_forward": carries_fwd,
                    "carry_forward_cap": cap,
                    "requires_evidence": req_ev,
                },
            )

        # seed authority rules
        authority_rules_data = [
            ("CL", "", "", True, False, "Unit Head", False, 1),
            ("RH", "", "", True, False, "Unit Head", False, 1),
            ("EL", "", "", True, True, "Dean", False, 1),
            ("SCL", "", "", True, True, "Director", False, 1),
            ("COL", "", "", True, False, "Unit Head", False, 1),
            ("VL", "", "", True, True, "Dean", False, 1),
            ("ML", "", "", True, True, "Director", False, 1),
            ("PL", "", "", True, True, "Director", False, 1),
            ("CCL", "", "", True, True, "Director", False, 1),
            ("SL", "", "", True, True, "Director", False, 1),
            ("LND", "", "", True, True, "Director", False, 1),
            ("EOL", "", "", True, True, "Director", False, 1),
        ]
        for cat, unit, desig, faculty, estab, sanc_desig, self_sanc, spec in authority_rules_data:
            AuthorityRule.objects.get_or_create(
                policy=policy,
                category=cat,
                sanctioning_designation=sanc_desig,
                defaults={
                    "unit": unit,
                    "designation": desig,
                    "applies_to_faculty": faculty,
                    "establishment_step": estab,
                    "self_sanction": self_sanc,
                    "specificity": spec,
                },
            )

        # seed sla rules
        sla_rules_data = [
            ("pending_substitute", 24, 48, "HOD"),
            ("pending_review", 48, 72, "Dean"),
            ("pending_routing", 48, 72, "Registrar"),
            ("pending_sanction", 72, 96, "Director"),
            ("pending_resumption", 48, 72, "HOD"),
        ]
        for state, remind_hrs, esc_hrs, esc_desig in sla_rules_data:
            SlaRule.objects.get_or_create(
                policy=policy,
                state=state,
                defaults={
                    "remind_after_hours": remind_hrs,
                    "escalate_after_hours": esc_hrs,
                    "escalate_to_designation": esc_desig,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded leave policy for year {year}."))
