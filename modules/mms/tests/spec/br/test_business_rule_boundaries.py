from datetime import date

import pytest

from modules.mms.domain import rules
from modules.mms.domain.exceptions import GuardFailed


def test_br_014_weekly_menu_categories():
    """test_id=BR-014; source_id=BR-MMS-014"""
    for meal in ("breakfast", "lunch", "dinner"):
        rules.valid_menu_meal(meal)
    with pytest.raises(GuardFailed):
        rules.valid_menu_meal("snack")


def test_br_021_three_day_rebate_threshold():
    """test_id=BR-021,BR-021-BOUNDARY; source_id=BR-MMS-021"""
    submitted = date(2026, 11, 22)
    rules.rebate_valid("medical", "", date(2026, 11, 25), date(2026, 11, 28), submitted, [])
    with pytest.raises(GuardFailed):
        rules.rebate_valid("medical", "", date(2026, 11, 25), date(2026, 11, 27), submitted, [])


def test_br_022_one_day_rebate_lead_time():
    """test_id=BR-022,BR-022-BOUNDARY; source_id=BR-MMS-022"""
    start, end = date(2026, 11, 23), date(2026, 11, 27)
    rules.rebate_valid("medical", "", start, end, date(2026, 11, 22), [])
    with pytest.raises(GuardFailed):
        rules.rebate_valid("medical", "", start, end, date(2026, 11, 23), [])


def test_br_023_overlap_rejection():
    """test_id=BR-023; source_id=BR-MMS-023"""
    existing = [(date(2026, 11, 25), date(2026, 11, 30))]
    with pytest.raises(GuardFailed):
        rules.rebate_valid("medical", "", date(2026, 11, 28), date(2026, 12, 2), date(2026, 11, 22), existing)
    rules.rebate_valid("medical", "", date(2026, 12, 1), date(2026, 12, 5), date(2026, 11, 22), existing)


def test_br_024_other_requires_reason_text():
    """test_id=BR-024,BR-024-BOUNDARY; source_id=BR-MMS-024"""
    args = (date(2026, 11, 25), date(2026, 11, 29), date(2026, 11, 22), [])
    rules.rebate_valid("other", "conference", *args)
    with pytest.raises(GuardFailed):
        rules.rebate_valid("other", " ", *args)


def test_br_028_one_calendar_day_special_food_lead_time():
    """test_id=BR-028,BR-028-BOUNDARY; source_id=BR-MMS-028"""
    today = date(2026, 11, 22)
    rules.special_food_lead_time_ok(today, date(2026, 11, 23))
    with pytest.raises(GuardFailed):
        rules.special_food_lead_time_ok(today, today)


def test_br_041_vacation_response_is_yes_or_no():
    """test_id=BR-041; source_id=BR-MMS-041"""
    rules.valid_vacation_response("yes")
    rules.valid_vacation_response("no")
    with pytest.raises(GuardFailed):
        rules.valid_vacation_response("maybe")
