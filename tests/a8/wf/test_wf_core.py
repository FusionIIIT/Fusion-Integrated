from datetime import datetime, timedelta, timezone

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT, SYSTEM
from modules.quiz.machines.quiz_machine import M1, PROFESSOR
from modules.quiz.machines.result_machine import M3
from modules.quiz.state_machine import apply_transition


def test_bw_qz_01_immediate_availability():
    """BW-QZ-01 BR-QZ-006: valid quiz preparation reaches immediate availability."""
    now = datetime.now(timezone.utc)
    ctx = {"now": now, "start_at": now, "owns_course": True,
           "questions_valid": True, "config_valid": True}
    assert apply_transition(M1, "READY_TO_PUBLISH", "publish", PROFESSOR, ctx) == "AVAILABLE"


def test_bw_qz_02_scheduled_availability():
    """BW-QZ-02 BR-QZ-006: future publication reaches scheduled then available."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=1)
    ctx = {"now": now, "start_at": future, "owns_course": True,
           "questions_valid": True, "config_valid": True}
    assert apply_transition(M1, "READY_TO_PUBLISH", "publish", PROFESSOR, ctx) == "SCHEDULED"
    assert apply_transition(M1, "SCHEDULED", "boundary_start", SYSTEM,
                            {"now": future, "start_at": future}) == "AVAILABLE"


def test_bw_qz_03_close_and_archive():
    """BW-QZ-03 UC-QZ-018/006: available quiz closes and may be archived."""
    now = datetime.now(timezone.utc)
    assert apply_transition(M1, "AVAILABLE", "boundary_close", SYSTEM,
                            {"now": now, "close_at": now}) == "CLOSED"
    assert apply_transition(M1, "CLOSED", "archive", PROFESSOR,
                            {"archive_permitted": True}) == "ARCHIVED"


def test_bw_qz_04_manual_submission():
    """BW-QZ-04 UC-QZ-008/009/010: valid attempt can be manually submitted."""
    now = datetime.now(timezone.utc)
    assert apply_transition(M2, "STARTED", "submit", STUDENT,
                            {"confirm": True, "now": now,
                             "deadline_at": now + timedelta(minutes=1),
                             "allow_unanswered": True, "unanswered": 0}) == "SUBMITTED"


def test_bw_qz_05_time_expiry_submission():
    """BW-QZ-05 UC-QZ-011: an expired active attempt is auto-submitted."""
    now = datetime.now(timezone.utc)
    assert apply_transition(M2, "STARTED", "auto_submit", SYSTEM,
                            {"now": now, "deadline_at": now}) == "SUBMITTED"


def test_bw_qz_06_objective_result_release():
    """BW-QZ-06 UC-QZ-012/014: objective evaluation and release are state transitions."""
    assert apply_transition(M3, "NOT_EVALUATED", "auto_evaluate", SYSTEM, {}) == "EVALUATED"
    assert apply_transition(M3, "EVALUATED", "release", PROFESSOR,
                            {"owns_course": True}) == "RELEASED"


def test_bw_qz_09_released_result_access():
    """BW-QZ-09 UC-QZ-014/015: permitted student access preserves Released state."""
    assert apply_transition(M3, "RELEASED", "view_result", STUDENT,
                            {"visibility_permits": True}) == "RELEASED"


@pytest.mark.parametrize("source_id", ["BW-QZ-07", "BW-QZ-08", "CW-QZ-01", "CW-QZ-02", "CW-QZ-03"])
def test_wf_not_automated_without_service_surface(source_id):
    """WF-source-id: evaluation/service integration is explicitly not automatable in A8_BASE."""
    pytest.skip(f"NOT_AUTOMATED: {source_id} has no corresponding quiz service/API in A8_BASE.")
