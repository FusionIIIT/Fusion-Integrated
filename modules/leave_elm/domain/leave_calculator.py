import datetime


class LeaveCalculator:
    """
    A pure Python domain logic class for calculating leave duration based on rules.
    This class has zero dependencies on Django or DRF.
    """

    @staticmethod
    def _is_working_day(date_obj: datetime.date) -> bool:
        """Checks if a date is a standard working day (Mon-Fri, excluding holidays)."""
        # For simplicity in this core implementation, we only check weekdays.
        # Holiday checking would require external data input.
        return date_obj.weekday() < 5

    @staticmethod
    def calculate_working_days(start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculates the number of working days (Mon-Fri) between two dates (inclusive).

        Used for CL, RH, SCL.

        :param start_date: Start date.
        :param end_date: End date.
        :return: Total count of working days.
        """
        if start_date > end_date:
            return 0.0

        count = 0
        current_date = start_date
        while current_date <= end_date:
            if LeaveCalculator._is_working_day(current_date):
                count += 1
            current_date += datetime.timedelta(days=1)

        return float(count)

    @staticmethod
    def calculate_continuous_days(start_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculates the total number of continuous calendar days between two dates (inclusive).

        Used for EL, VL, COL.

        :param start_date: Start date.
        :param end_date: End date.
        :return: Total count of continuous days.
        """
        if start_date > end_date:
            return 0.0

        # Simple difference in days + 1 for inclusive range
        return float((end_date - start_date).days + 1)

    @staticmethod
    def calculate_cl_days(
        start_date: datetime.date,
        end_date: datetime.date,
        is_half_day_start: bool,
        is_half_day_end: bool,
    ) -> float:
        """
        Calculates Casual Leave duration, handling potential half-day inputs.

        Since the model only stores start/end date, we assume if CL is used,
        the system must handle the half-day logic during the service call based on
        additional data, or we must simplify. For now, we calculate working days
        and adjust based on the flags provided here.

        NOTE: In a real-world scenario, the LeaveApplication model might need
        separate fields for half-day start/end indicators. Here, we approximate.

        :param start_date: Start date.
        :param end_date: End date.
        :param is_half_day_start: True if the start day is half-day.
        :param is_half_day_end: True if the end day is half-day.
        :return: Calculated CL days.
        """
        full_days = LeaveCalculator.calculate_working_days(start_date, end_date)

        half_day_reduction = 0.0

        # If start is half day, we lose 0.5 day
        if is_half_day_start:
            half_day_reduction += 0.5

        # If end is half day, we lose 0.5 day
        if is_half_day_end:
            # If the start was also a half day, the reduction is still 0.5 for the end day
            half_day_reduction += 0.5

        return max(0.0, full_days - half_day_reduction)

    @staticmethod
    def convert_vl_to_el(vl_days: float) -> float:
        """
        Converts Vacation Leave (VL) to Earned Leave (EL) at year-end (2 VL : 1 EL).

        :param vl_days: Number of VL days to convert.
        :return: Equivalent number of EL days.
        """
        # 2 VL = 1 EL, so EL = VL / 2
        return vl_days / 2.0


# Example usage test (will not be executed in the final module but demonstrates logic)
# from datetime import date
# print(LeaveCalculator.calculate_working_days(date(2024, 10, 1), date(2024, 10, 7))) # 5 days
# print(LeaveCalculator.calculate_continuous_days(date(2024, 10, 1), date(2024, 10, 3))) # 3 days
