from datetime import timedelta
from decimal import Decimal

from modules.elm.models.leave_application import LeaveApplication
from modules.elm.models.leave_types import HolidayCalendar, LeaveBalance, LeaveType


class LeaveService:
    @staticmethod
    def validate_application(
        user_id: int, leave_type_code: str, start_date, end_date, purpose: str
    ) -> dict:
        leave_type = LeaveType.objects.get(code=leave_type_code)
        balance = LeaveBalance.objects.filter(user_id=user_id, leave_type=leave_type).first()

        if not balance or balance.balance < 1.0:
            return {"valid": False, "reason": "Insufficient balance"}

        if start_date > end_date:
            return {"valid": False, "reason": "Start date must be before end date"}

        # RH Check
        if leave_type_code == "RH":
            holiday = HolidayCalendar.objects.filter(date=start_date).first()
            if not holiday or not holiday.is_holiday or holiday.rh_type != "RH":
                return {"valid": False, "reason": "Start date is not a Restricted Holiday"}

        # Check overlap (excluding half-day CL exception)
        overlapping = (
            LeaveApplication.objects.filter(
                user_id=user_id,
                status__in=["PENDING", "APPROVED"],
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            .exclude(leave_type__code="CL", start_date=start_date, end_date=end_date)
            .exists()
        )

        if overlapping:
            return {"valid": False, "reason": "Overlapping leave detected"}

        return {"valid": True}

    @staticmethod
    def calculate_chargeable_days(start_date, end_date, leave_type_code: str) -> Decimal:
        leave_type = LeaveType.objects.get(code=leave_type_code)

        total_days = (end_date - start_date).days + 1

        if not leave_type.continuous_counting:
            # Non-continuous: only count business days
            # Simplified: excluding weekends + holidays
            chargeable = 0
            current_date = start_date
            while current_date <= end_date:
                is_weekend = current_date.weekday() >= 5
                holiday_entry = HolidayCalendar.objects.filter(date=current_date).first()
                is_holiday = holiday_entry and holiday_entry.is_holiday

                if not is_weekend and not is_holiday:
                    chargeable += 1
                current_date += timedelta(days=1)
            return Decimal(chargeable)
        # Continuous counting includes weekends and holidays
        return Decimal(total_days)
