from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.leave_elm.models import LeaveCategory


class Command(BaseCommand):
    help = "Create or update the supported Employee Leave categories"

    def handle(self, *args, **options):
        categories = [
            ("CL", "Casual Leave", "8", False, False),
            ("RH", "Restricted Holiday", "2", False, False),
            ("SCL", "Special Casual Leave", "15", False, False),
            ("EL", "Earned Leave", "30", True, True),
            ("COL", "Commuted Leave", "20", True, True),
            ("VL", "Vacation Leave", "60", False, True),
        ]
        for code, name, entitlement, carry_forward, continuous in categories:
            LeaveCategory.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "annual_entitlement": Decimal(entitlement),
                    "carry_forward": carry_forward,
                    "continuous_counting": continuous,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Leave categories are ready."))
