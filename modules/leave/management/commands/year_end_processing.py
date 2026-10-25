import datetime

from django.core.management.base import BaseCommand

from modules.leave.models import LeaveBalance, LeaveType


class Command(BaseCommand):
    help = "Year-end leave processing: lapse CL/RH/SCL, convert VL->EL (2:1), carry forward EL/COL."

    def handle(self, *args, **options):
        year = datetime.date.today().year
        self.stdout.write(f"Year-end processing for {year}")

        # Lapse CL, RH, SCL (reset allocated to 0 for the new year by not carrying)
        for code in ("CL", "RH", "SCL"):
            lt = LeaveType.objects.filter(code=code).first()
            if lt:
                self.stdout.write(f"  lapse {code}: carry_forward={lt.carry_forward}")

        # VL -> EL conversion (2 VL : 1 EL) for faculty balances
        vl = LeaveType.objects.filter(code="VL").first()
        el = LeaveType.objects.filter(code="EL").first()
        if vl and el:
            for bal in LeaveBalance.objects.filter(leave_type=vl, year=year):
                remaining = float(bal.remaining_days)
                converted = remaining / 2.0
                target, _ = LeaveBalance.objects.get_or_create(
                    user_id=bal.user_id,
                    leave_type=el,
                    year=year + 1,
                    defaults={"allocated_days": 0, "used_days": 0},
                )
                target.allocated_days = float(target.allocated_days) + converted
                target.save(update_fields=["allocated_days"])
                self.stdout.write(f"  user {bal.user_id}: VL {remaining} -> EL {converted}")

        # Carry forward EL and COL
        for code in ("EL", "COL"):
            lt = LeaveType.objects.filter(code=code).first()
            if lt and lt.carry_forward:
                for bal in LeaveBalance.objects.filter(leave_type=lt, year=year):
                    target, _ = LeaveBalance.objects.get_or_create(
                        user_id=bal.user_id,
                        leave_type=lt,
                        year=year + 1,
                        defaults={"allocated_days": 0, "used_days": 0},
                    )
                    target.allocated_days = float(target.allocated_days) + float(bal.remaining_days)
                    target.save(update_fields=["allocated_days"])
                    self.stdout.write(f"  carry {code} user {bal.user_id}: {bal.remaining_days}")

        self.stdout.write(self.style.SUCCESS("year-end processing done"))
