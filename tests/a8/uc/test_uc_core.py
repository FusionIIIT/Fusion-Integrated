from datetime import datetime, timedelta, timezone

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT, SYSTEM
from modules.quiz.state_machine import apply_transition


def test_uc_qz_008_start_attempt():
    """UC-QZ-008 BR-QZ-003/006/008: eligible student can start an available attempt."""
    now = datetime.now(timezone.utc)
    state = apply_transition(
        M2,
        None,
        "start",
        STUDENT,
        {"eligible": True, "attempts_used": 0, "max_attempts": 1, "has_active_attempt": False,
         "quiz_start_at": now, "now": now},
    )
    assert state == "STARTED"


def test_uc_qz_010_manual_submit():
    """UC-QZ-010 BR-QZ-016: confirmed student submission enters the submitted state."""
    now = datetime.now(timezone.utc)
    assert apply_transition(
        M2, "STARTED", "submit", STUDENT,
        {"confirm": True, "now": now, "deadline_at": now + timedelta(minutes=5),
         "allow_unanswered": True, "unanswered": 0},
    ) == "SUBMITTED"


def test_uc_qz_011_auto_submit_at_deadline():
    """UC-QZ-011 BR-QZ-017: system auto-submits an attempt at its deadline."""
    now = datetime.now(timezone.utc)
    assert apply_transition(
        M2, "STARTED", "auto_submit", SYSTEM,
        {"now": now, "deadline_at": now},
    ) == "SUBMITTED"


@pytest.mark.parametrize("source_id", ["UC-QZ-001", "UC-QZ-002", "UC-QZ-003", "UC-QZ-004",
                                       "UC-QZ-005", "UC-QZ-006", "UC-QZ-007", "UC-QZ-009",
                                       "UC-QZ-012", "UC-QZ-013", "UC-QZ-014", "UC-QZ-015",
                                       "UC-QZ-016", "UC-QZ-017", "UC-QZ-018", "UC-QZ-019"])
def test_uc_not_automated_without_service_surface(source_id):
    """UC-source-id: service/API obligations are explicitly not automatable in A8_BASE."""
    pytest.skip(f"NOT_AUTOMATED: {source_id} has no corresponding quiz API/service in A8_BASE.")

