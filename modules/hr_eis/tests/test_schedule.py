import pytest
from modules.hr_eis.schedule import SCHEDULE

def test_schedule_contains_expected_jobs():
    assert "eis-daily-reminders" in SCHEDULE
    assert "eis-deadline-check" in SCHEDULE
