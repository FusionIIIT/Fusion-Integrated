from django.core.management.base import BaseCommand

from modules.leave.models import LeaveType

# code, name, max_days, carry_forward, continuous_count, allow_half_day,
# requires_rh_calendar, requires_vacation_period
DEFAULTS = [
    ("CL", "Casual Leave", 8, False, False, True, False, False),
    ("RH", "Restricted Holiday", 2, False, False, False, True, False),
    ("SCL", "Special Casual Leave", 15, False, False, False, False, False),
    ("EL", "Earned Leave", 30, True, True, False, False, False),
    ("COL", "Commuted Leave", 20, True, True, False, False, False),
    ("VL", "Vacation Leave", 60, False, True, False, False, True),
]


class Command(BaseCommand):
    help = "Seed the default ELM leave types (idempotent)."

    def handle(self, *args, **options):
        created = 0
        for code, name, days, carry, continuous, half, rh, vac in DEFAULTS:
            obj, was_created = LeaveType.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "max_days_per_year": days,
                    "carry_forward": carry,
                    "continuous_count": continuous,
                    "allow_half_day": half,
                    "requires_rh_calendar": rh,
                    "requires_vacation_period": vac,
                },
            )
            if not was_created:
                obj.name = name
                obj.max_days_per_year = days
                obj.carry_forward = carry
                obj.continuous_count = continuous
                obj.allow_half_day = half
                obj.requires_rh_calendar = rh
                obj.requires_vacation_period = vac
                obj.save()
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"seeded {created} new leave types"))
