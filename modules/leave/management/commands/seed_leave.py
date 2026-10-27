from django.core.management.base import BaseCommand
from modules.leave.models import LeaveBalance, LeaveType


class Command(BaseCommand):
    help = "Seed standard leave types and initial balances for testing"

    def handle(self, *args, **options):
        types = [
            ("Casual Leave", "Annual casual leave entitlement (10 days)"),
            ("Medical Leave", "Leave on medical grounds (15 days)"),
            ("Earned Leave", "Earned privilege leave (30 days)"),
            ("Special Casual Leave", "Special duty or academic conference leave"),
        ]
        created_types = []
        for name, desc in types:
            lt, _ = LeaveType.objects.get_or_create(name=name, defaults={"description": desc})
            created_types.append(lt)

        for uid in (1001, 1002, 1003, 9001):
            LeaveBalance.objects.get_or_create(user_id=uid, leave_type=created_types[0], defaults={"balance": 8})
            LeaveBalance.objects.get_or_create(user_id=uid, leave_type=created_types[1], defaults={"balance": 15})
            LeaveBalance.objects.get_or_create(user_id=uid, leave_type=created_types[2], defaults={"balance": 30})

        self.stdout.write(self.style.SUCCESS("Successfully seeded leave types and initial balances."))
