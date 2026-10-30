"""Domain rules unit tests (pure python, no database required)."""
import unittest
from datetime import date
from decimal import Decimal

from modules.leave.domain.constants import (
    HALF_DAY_FIRST,
    HALF_DAY_FULL,
    HALF_DAY_SECOND,
    LEAVE_CL,
    LEAVE_COL,
    LEAVE_EL,
    LEAVE_RH,
    LEAVE_SCL,
    LEAVE_VL,
    STATUS_APPROVED,
    STATUS_AWAITING_SUBSTITUTE,
    STATUS_AWAITING_UNIT_HEAD,
    STATUS_WITHDRAWN,
)
from modules.leave.domain.rules import (
    LeaveValidationError,
    calculate_early_resumption_restoration,
    calculate_leave_days,
    can_cancel_approved,
    can_extend,
    can_modify_pending,
    can_withdraw_pending,
    check_non_overlap,
    convert_vl_to_el,
)


class TestDomainRules(unittest.TestCase):
    def test_half_day_cl_deduction(self):
        """BR-EL-010: Half-day CL deducts exactly 0.5 days."""
        d = date(2026, 11, 2)  # Monday
        days = calculate_leave_days(
            category=LEAVE_CL,
            start_date=d,
            end_date=d,
            half_day=HALF_DAY_FIRST,
        )
        self.assertEqual(days, Decimal("0.5"))

        # Half-day not allowed for EL
        with self.assertRaises(LeaveValidationError):
            calculate_leave_days(
                category=LEAVE_EL,
                start_date=d,
                end_date=d,
                half_day=HALF_DAY_SECOND,
            )

    def test_continuing_leave_counting_el_col_vl(self):
        """BR-EL-011: Intervening weekends and closed holidays count for EL, COL, VL."""
        # 2026-11-06 (Friday) to 2026-11-09 (Monday) = 4 calendar days (Fri, Sat, Sun, Mon)
        start = date(2026, 11, 6)
        end = date(2026, 11, 9)
        closed_holidays = {date(2026, 11, 6)}  # Friday is closed holiday

        # For EL: All 4 days count
        el_days = calculate_leave_days(
            category=LEAVE_EL,
            start_date=start,
            end_date=end,
            closed_holidays=closed_holidays,
        )
        self.assertEqual(el_days, Decimal("4.0"))

        # For CL: Friday (holiday), Sat, Sun (weekends) do NOT count. Only Monday counts (1 day)
        cl_days = calculate_leave_days(
            category=LEAVE_CL,
            start_date=start,
            end_date=end,
            closed_holidays=closed_holidays,
        )
        self.assertEqual(cl_days, Decimal("1.0"))

    def test_rh_calendar_validation(self):
        """BR-EL-003: RH must correspond to a published restricted holiday."""
        valid_rh = date(2026, 11, 10)
        invalid_rh = date(2026, 11, 11)
        calendar = {valid_rh}

        # Valid RH
        days = calculate_leave_days(
            category=LEAVE_RH,
            start_date=valid_rh,
            end_date=valid_rh,
            restricted_holidays=calendar,
        )
        self.assertEqual(days, Decimal("1.0"))

        # Invalid RH
        with self.assertRaises(LeaveValidationError):
            calculate_leave_days(
                category=LEAVE_RH,
                start_date=invalid_rh,
                end_date=invalid_rh,
                restricted_holidays=calendar,
            )

    def test_vacation_leave_calendar_validation(self):
        """BR-EL-006: VL can only be availed during published vacation period."""
        vac_start = date(2026, 6, 1)
        vac_end = date(2026, 6, 5)
        vacation_dates = {date(2026, 6, i) for i in range(1, 6)}

        # In vacation
        days = calculate_leave_days(
            category=LEAVE_VL,
            start_date=vac_start,
            end_date=vac_end,
            vacation_dates=vacation_dates,
        )
        self.assertEqual(days, Decimal("5.0"))

        # Outside vacation
        with self.assertRaises(LeaveValidationError):
            calculate_leave_days(
                category=LEAVE_VL,
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 3),
                vacation_dates=vacation_dates,
            )

    def test_non_overlap_and_half_day_exception(self):
        """BR-EL-012, BR-EL-034: Impermissible overlap prevented, distinct half-days allowed."""
        existing = [
            {
                "id": 1,
                "start_date": date(2026, 11, 2),
                "end_date": date(2026, 11, 2),
                "half_day": HALF_DAY_FIRST,
                "status": STATUS_APPROVED,
            }
        ]

        # Same date, second half: PERMITTED (BR-EL-034)
        check_non_overlap(
            existing,
            new_start=date(2026, 11, 2),
            new_end=date(2026, 11, 2),
            new_half_day=HALF_DAY_SECOND,
        )

        # Same date, first half again: OVERLAP
        with self.assertRaises(LeaveValidationError):
            check_non_overlap(
                existing,
                new_start=date(2026, 11, 2),
                new_end=date(2026, 11, 2),
                new_half_day=HALF_DAY_FIRST,
            )

        # Full day overlap: OVERLAP
        with self.assertRaises(LeaveValidationError):
            check_non_overlap(
                existing,
                new_start=date(2026, 11, 2),
                new_end=date(2026, 11, 2),
                new_half_day=HALF_DAY_FULL,
            )

    def test_vl_to_el_conversion(self):
        """BR-EL-007: 2 VL to 1 EL conversion at year end with fractional conversion."""
        self.assertEqual(convert_vl_to_el(Decimal("60.0")), Decimal("30.0"))
        self.assertEqual(convert_vl_to_el(Decimal("15.0")), Decimal("7.5"))
        self.assertEqual(convert_vl_to_el(Decimal("1.0")), Decimal("0.5"))
        self.assertEqual(convert_vl_to_el(Decimal("0.0")), Decimal("0.0"))

    def test_early_resumption_restoration(self):
        """BR-EL-028: Calculate unused leave restoration on verified early resumption."""
        start = date(2026, 11, 2)
        end = date(2026, 11, 6)  # 5 days
        actual_resumption = date(2026, 11, 5)  # Returned 2 days early (5th and 6th)

        restored = calculate_early_resumption_restoration(
            category=LEAVE_EL,
            approved_start=start,
            approved_end=end,
            actual_resumption_date=actual_resumption,
        )
        self.assertEqual(restored, Decimal("2.0"))

    def test_lifecycle_guards(self):
        """Test state transitions and lifecycle predicates (WF-EL-02, WF-EL-03, WF-EL-04)."""
        self.assertTrue(can_modify_pending(STATUS_AWAITING_SUBSTITUTE))
        self.assertTrue(can_modify_pending(STATUS_AWAITING_UNIT_HEAD))
        self.assertFalse(can_modify_pending(STATUS_APPROVED))

        self.assertTrue(can_withdraw_pending(STATUS_AWAITING_UNIT_HEAD))
        self.assertFalse(can_withdraw_pending(STATUS_APPROVED))
        self.assertFalse(can_withdraw_pending(STATUS_WITHDRAWN))

        today = date(2026, 11, 1)
        future_start = date(2026, 11, 5)
        past_start = date(2026, 10, 25)

        self.assertTrue(can_cancel_approved(STATUS_APPROVED, future_start, today))
        self.assertFalse(can_cancel_approved(STATUS_APPROVED, past_start, today))

        self.assertTrue(can_extend(LEAVE_EL, STATUS_APPROVED))
        self.assertTrue(can_extend(LEAVE_COL, STATUS_APPROVED))
        self.assertTrue(can_extend(LEAVE_VL, STATUS_APPROVED))
        self.assertFalse(can_extend(LEAVE_CL, STATUS_APPROVED))


if __name__ == "__main__":
    unittest.main()
