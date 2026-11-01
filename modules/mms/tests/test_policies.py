from datetime import date, timedelta

import pytest

from modules.mms.domain.policies import PolicyViolation, next_calendar_day, validate_rebate


def test_a_three_day_rebate_with_a_full_day_lead_is_valid():
    validate_rebate(
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 7),
        submitted_on=date(2026, 11, 4),
        reason="medical",
        explanation="",
        overlapping=False,
    )


@pytest.mark.parametrize(
    ("start_offset", "duration", "reason", "explanation", "overlapping"),
    [
        (1, 2, "medical", "", False),
        (0, 3, "medical", "", False),
        (1, 3, "other", "  ", False),
        (1, 3, "medical", "", True),
    ],
)
def test_rebate_policy_rejects_invalid_requests(
    start_offset, duration, reason, explanation, overlapping
):
    today = date(2026, 11, 4)
    with pytest.raises(PolicyViolation):
        validate_rebate(
            start_date=today + timedelta(days=start_offset),
            end_date=today + timedelta(days=start_offset + duration - 1),
            submitted_on=today,
            reason=reason,
            explanation=explanation,
            overlapping=overlapping,
        )


def test_approved_deregistration_effect_is_the_next_calendar_day():
    assert next_calendar_day(date(2026, 11, 4)) == date(2026, 11, 5)
