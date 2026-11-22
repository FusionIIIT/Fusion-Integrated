from datetime import UTC, datetime

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT
from modules.quiz.machines.quiz_machine import M1, PROFESSOR
from modules.quiz.state_machine import GuardFailed, IllegalTransition, apply_transition


def test_quiz_publish_selects_immediate_or_scheduled_state():
    now = datetime.now(UTC)
    ctx = {
        "now": now,
        "start_at": now,
        "owns_course": True,
        "questions_valid": True,
        "config_valid": True,
    }
    assert apply_transition(M1, "READY_TO_PUBLISH", "publish", PROFESSOR, ctx) == "AVAILABLE"
    ctx["start_at"] = now.replace(year=now.year + 1)
    assert apply_transition(M1, "READY_TO_PUBLISH", "publish", PROFESSOR, ctx) == "SCHEDULED"


def test_wrong_role_and_guard_are_distinct():
    with pytest.raises(IllegalTransition):
        apply_transition(M1, "READY_TO_PUBLISH", "publish", STUDENT, {})
    with pytest.raises(GuardFailed, match="INELIGIBLE"):
        apply_transition(M2, None, "start", STUDENT, {"eligible": False, "now": datetime.now(UTC)})


def test_attempt_submit_requires_confirmation():
    with pytest.raises(GuardFailed, match="CONFIRM_REQUIRED"):
        apply_transition(
            M2,
            "STARTED",
            "submit",
            STUDENT,
            {"confirm": False, "now": datetime.now(UTC), "deadline_at": datetime.now(UTC)},
        )


def test_submitted_attempt_is_immutable():
    with pytest.raises(IllegalTransition):
        apply_transition(M2, "SUBMITTED", "submit", STUDENT, {})
