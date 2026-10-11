from datetime import date
from decimal import Decimal

from django.db import transaction

from modules.elm.models import LeaveRequest


class LeaveRequestService:
    @staticmethod
    @transaction.atomic
    def submit_request(
        user_id,
        leave_type_code,
        requested_start_date,
        requested_end_date,
        day_part="FULL",
    ):
        if isinstance(requested_start_date, str):
            requested_start_date = date.fromisoformat(requested_start_date)

        if isinstance(requested_end_date, str):
            requested_end_date = date.fromisoformat(requested_end_date)

        if requested_end_date < requested_start_date:
            raise ValueError("The end date must be on or after the start date.")

        valid_leave_types = dict(LeaveRequest.LEAVE_CHOICES)
        if leave_type_code not in valid_leave_types:
            raise ValueError("Invalid leave type.")

        valid_day_parts = dict(LeaveRequest.DAY_PART_CHOICES)
        if day_part not in valid_day_parts:
            raise ValueError("Invalid day part.")

        if day_part != "FULL":
            if leave_type_code != "CL":
                raise ValueError("Half-day requests are supported for CL only.")
            if requested_start_date != requested_end_date:
                raise ValueError("A half-day request must be for one date.")

        total_days = Decimal((requested_end_date - requested_start_date).days + 1)
        if day_part != "FULL":
            total_days = Decimal("0.5")

        return LeaveRequest.objects.create(
            user_id=user_id,
            leave_type_code=leave_type_code,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            day_part=day_part,
            total_days=total_days,
            status="SUBMITTED",
        )
