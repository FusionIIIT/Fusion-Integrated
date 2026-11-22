"""Unit tests for pure domain business rules (no database required).

Covers:
- BR-MMS-001 (MMS scope boundaries)
- BR-MMS-014 (menu meal categories: breakfast, lunch, dinner)
- BR-MMS-021..025 (rebate validation: 3-day minimum, 1-day lead time, overlap, reasons)
- BR-MMS-028 (special food lead time: >= 1 calendar day)
- BR-MMS-041 (vacation survey response options: yes, no)
"""

from datetime import date

import pytest

from modules.mms.domain import rules
from modules.mms.domain.exceptions import GuardFailed


class TestSpecialFoodRules:
    def test_special_food_lead_time_ok(self):
        today = date(2026, 11, 22)
        # 1 calendar day in advance is valid
        rules.special_food_lead_time_ok(today, date(2026, 11, 23))
        # 5 days in advance is valid
        rules.special_food_lead_time_ok(today, date(2026, 11, 27))

    def test_special_food_same_day_rejected(self):
        today = date(2026, 11, 22)
        with pytest.raises(GuardFailed) as exc_info:
            rules.special_food_lead_time_ok(today, today)
        assert exc_info.value.code == "lead_time_at_least_1_calendar_day"

    def test_special_food_past_date_rejected(self):
        today = date(2026, 11, 22)
        with pytest.raises(GuardFailed) as exc_info:
            rules.special_food_lead_time_ok(today, date(2026, 11, 21))
        assert exc_info.value.code == "lead_time_at_least_1_calendar_day"


class TestRebateRules:
    def test_valid_rebate(self):
        submitted = date(2026, 11, 22)
        start = date(2026, 11, 25)
        end = date(2026, 11, 29)  # 4 days
        existing = []

        rules.rebate_valid("medical", "", start, end, submitted, existing)
        rules.rebate_valid("institute_leave", "", start, end, submitted, existing)
        rules.rebate_valid("family_function", "", start, end, submitted, existing)
        rules.rebate_valid(
            "other", "Attending national conference", start, end, submitted, existing
        )

    def test_invalid_reason(self):
        submitted = date(2026, 11, 22)
        start = date(2026, 11, 25)
        end = date(2026, 11, 29)
        with pytest.raises(GuardFailed) as exc:
            rules.rebate_valid("vacation", "", start, end, submitted, [])
        assert exc.value.code == "reason_complete"

    def test_other_reason_requires_explanation(self):
        submitted = date(2026, 11, 22)
        start = date(2026, 11, 25)
        end = date(2026, 11, 29)
        with pytest.raises(GuardFailed) as exc:
            rules.rebate_valid("other", "   ", start, end, submitted, [])
        assert exc.value.code == "reason_complete"

    def test_minimum_duration_three_days(self):
        submitted = date(2026, 11, 22)
        start = date(2026, 11, 25)
        # 2 days duration
        end = date(2026, 11, 27)
        with pytest.raises(GuardFailed) as exc:
            rules.rebate_valid("medical", "", start, end, submitted, [])
        assert exc.value.code == "duration_at_least_3_days"

    def test_lead_time_at_least_one_day(self):
        submitted = date(2026, 11, 22)
        start = date(2026, 11, 22)  # Same day
        end = date(2026, 11, 26)
        with pytest.raises(GuardFailed) as exc:
            rules.rebate_valid("medical", "", start, end, submitted, [])
        assert exc.value.code == "lead_time_at_least_1_day"

    def test_no_rebate_overlap(self):
        submitted = date(2026, 11, 22)
        existing = [(date(2026, 11, 25), date(2026, 11, 30))]

        # Overlapping period
        start = date(2026, 11, 28)
        end = date(2026, 12, 3)
        with pytest.raises(GuardFailed) as exc:
            rules.rebate_valid("medical", "", start, end, submitted, existing)
        assert exc.value.code == "no_rebate_overlap"

        # Non-overlapping period
        start_ok = date(2026, 12, 1)
        end_ok = date(2026, 12, 5)
        rules.rebate_valid("medical", "", start_ok, end_ok, submitted, existing)


class TestMenuRules:
    def test_valid_meals(self):
        rules.valid_menu_meal("breakfast")
        rules.valid_menu_meal("lunch")
        rules.valid_menu_meal("dinner")

    def test_invalid_meal(self):
        with pytest.raises(GuardFailed) as exc:
            rules.valid_menu_meal("snacks")
        assert exc.value.code == "menu_structure"


class TestVacationSurveyRules:
    def test_valid_responses(self):
        rules.valid_vacation_response("yes")
        rules.valid_vacation_response("no")

    def test_invalid_response(self):
        with pytest.raises(GuardFailed) as exc:
            rules.valid_vacation_response("maybe")
        assert exc.value.code == "response_option"


class TestScopeRules:
    def test_mms_scope(self):
        rules.assert_mms_scope("mms")
