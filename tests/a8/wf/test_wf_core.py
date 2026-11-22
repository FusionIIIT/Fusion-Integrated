from datetime import datetime, timedelta, timezone

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT, SYSTEM
from modules.quiz.machines.quiz_machine import M1, PROFESSOR
from modules.quiz.machines.result_machine import M3
from modules.quiz.state_machine import apply_transition


def _prepare_quiz(now, start_at):
    state = apply_transition(M1, "DRAFT", "configure", PROFESSOR, {})
    assert state == "DRAFT_CONFIGURED"
    state = apply_transition(M1, state, "prepare", PROFESSOR, {})
    assert state == "READY_TO_PUBLISH"
    return apply_transition(
        M1,
        state,
        "publish",
        PROFESSOR,
        {
            "now": now,
            "start_at": start_at,
            "owns_course": True,
            "questions_valid": True,
            "config_valid": True,
        },
    )


def _start_attempt(now):
    return apply_transition(
        M2,
        None,
        "start",
        STUDENT,
        {
            "eligible": True,
            "attempts_used": 0,
            "max_attempts": 1,
            "has_active_attempt": False,
            "quiz_start_at": now,
            "now": now,
        },
    )


def test_wf_bw_qz_01__bw_qz_01_immediate_availability():
    """test_id=WF-BW-QZ-01; source_id=BW-QZ-01; domain-state transitions only."""
    now = datetime.now(timezone.utc)
    assert _prepare_quiz(now, now) == "AVAILABLE"


def test_wf_bw_qz_02__bw_qz_02_scheduled_availability():
    """test_id=WF-BW-QZ-02; source_id=BW-QZ-02; domain-state transitions only."""
    now = datetime.now(timezone.utc)
    start_at = now + timedelta(hours=1)
    state = _prepare_quiz(now, start_at)
    assert state == "SCHEDULED"
    assert (
        apply_transition(
            M1,
            state,
            "boundary_start",
            SYSTEM,
            {"now": start_at, "start_at": start_at},
        )
        == "AVAILABLE"
    )


def test_wf_bw_qz_03__bw_qz_03_close_and_archive():
    """test_id=WF-BW-QZ-03; source_id=BW-QZ-03; close then permitted archive."""
    now = datetime.now(timezone.utc)
    assert (
        apply_transition(M1, "AVAILABLE", "boundary_close", SYSTEM, {
            "now": now,
            "close_at": now,
        })
        == "CLOSED"
    )
    assert (
        apply_transition(
            M1, "CLOSED", "archive", PROFESSOR, {"archive_permitted": True}
        )
        == "ARCHIVED"
    )


def test_wf_bw_qz_04__bw_qz_04_manual_submission():
    """test_id=WF-BW-QZ-04; source_id=BW-QZ-04; domain start/submit transitions."""
    now = datetime.now(timezone.utc)
    assert _start_attempt(now) == "STARTED"
    assert (
        apply_transition(
            M2,
            "STARTED",
            "submit",
            STUDENT,
            {
                "confirm": True,
                "now": now,
                "deadline_at": now + timedelta(minutes=5),
                "allow_unanswered": True,
                "unanswered": 0,
            },
        )
        == "SUBMITTED"
    )


def test_wf_bw_qz_05__bw_qz_05_time_expiry_auto_submission():
    """test_id=WF-BW-QZ-05; source_id=BW-QZ-05; domain start/expiry transitions."""
    now = datetime.now(timezone.utc)
    assert _start_attempt(now) == "STARTED"
    assert (
        apply_transition(
            M2, "STARTED", "auto_submit", SYSTEM, {"now": now, "deadline_at": now}
        )
        == "SUBMITTED"
    )


def test_wf_bw_qz_06__bw_qz_06_objective_result_release():
    """test_id=WF-BW-QZ-06; source_id=BW-QZ-06; objective state path and release."""
    state = apply_transition(M3, "NOT_EVALUATED", "auto_evaluate", SYSTEM, {})
    assert state == "EVALUATED"
    assert (
        apply_transition(M3, state, "release", PROFESSOR, {"owns_course": True})
        == "RELEASED"
    )


def test_wf_bw_qz_07__bw_qz_07_subjective_review_release():
    """test_id=WF-BW-QZ-07; source_id=BW-QZ-07; full workflow needs missing evaluation path."""
    pytest.skip(
        "NOT_AUTOMATED: test_id=WF-BW-QZ-07; source_id=BW-QZ-07; the frozen workflow "
        "starts subjective evaluation from Submitted, but M3 has no Submitted transition "
        "for finalize_subjective (it only accepts PARTIALLY_EVALUATED). No available "
        "domain interface performs the required Submitted-to-evaluation orchestration."
    )


def test_wf_bw_qz_08__bw_qz_08_mixed_evaluation_release():
    """test_id=WF-BW-QZ-08; source_id=BW-QZ-08; full workflow needs missing orchestration."""
    pytest.skip(
        "NOT_AUTOMATED: test_id=WF-BW-QZ-08; source_id=BW-QZ-08; the frozen mixed "
        "workflow requires Submitted-to-PARTIALLY_EVALUATED automatic evaluation, but "
        "M3 auto_evaluate accepts only NOT_EVALUATED/PARTIALLY_EVALUATED. No available "
        "domain interface implements the required Submitted transition."
    )


def test_wf_bw_qz_09__bw_qz_09_released_result_access():
    """test_id=WF-BW-QZ-09; source_id=BW-QZ-09; release then permitted result access."""
    state = apply_transition(M3, "NOT_EVALUATED", "auto_evaluate", SYSTEM, {})
    state = apply_transition(
        M3, state, "release", PROFESSOR, {"owns_course": True}
    )
    assert state == "RELEASED"
    assert (
        apply_transition(
            M3, state, "view_result", STUDENT, {"visibility_permits": True}
        )
        == "RELEASED"
    )


def test_wf_cw_qz_01__cw_qz_01_preparation_availability_lifecycle():
    """test_id=WF-CW-QZ-01; source_id=CW-QZ-01; immediate, scheduled, close/archive."""
    now = datetime.now(timezone.utc)
    future = now + timedelta(hours=1)
    immediate_state = _prepare_quiz(now, now)
    scheduled_state = _prepare_quiz(now, future)
    assert immediate_state == "AVAILABLE"
    assert scheduled_state == "SCHEDULED"
    scheduled_state = apply_transition(
        M1,
        scheduled_state,
        "boundary_start",
        SYSTEM,
        {"now": future, "start_at": future},
    )
    for state, boundary in ((immediate_state, now), (scheduled_state, future)):
        state = apply_transition(
            M1,
            state,
            "boundary_close",
            SYSTEM,
            {"now": boundary, "close_at": boundary},
        )
        assert state == "CLOSED"
        assert (
            apply_transition(
                M1, state, "archive", PROFESSOR, {"archive_permitted": True}
            )
            == "ARCHIVED"
        )


def test_wf_cw_qz_02__cw_qz_02_attempt_submission_lifecycle():
    """test_id=WF-CW-QZ-02; source_id=CW-QZ-02; manual and expiry submission paths."""
    now = datetime.now(timezone.utc)
    manual_state = _start_attempt(now)
    auto_state = _start_attempt(now)
    assert manual_state == auto_state == "STARTED"
    manual_state = apply_transition(
        M2,
        manual_state,
        "submit",
        STUDENT,
        {
            "confirm": True,
            "now": now,
            "deadline_at": now + timedelta(minutes=5),
            "allow_unanswered": True,
            "unanswered": 0,
        },
    )
    auto_state = apply_transition(
        M2, auto_state, "auto_submit", SYSTEM, {"now": now, "deadline_at": now}
    )
    assert manual_state == auto_state == "SUBMITTED"


def test_wf_cw_qz_03__cw_qz_03_evaluation_result_release():
    """test_id=WF-CW-QZ-03; source_id=CW-QZ-03; composite needs missing eval paths."""
    pytest.skip(
        "NOT_AUTOMATED: test_id=WF-CW-QZ-03; source_id=CW-QZ-03; although M3 supports "
        "an objective transition from NOT_EVALUATED, this composite also requires the "
        "frozen Submitted-to-PARTIALLY_EVALUATED mixed path and Submitted subjective "
        "review path. M3 exposes neither Submitted transition, so a partial objective "
        "check would not verify the complete composite workflow."
    )
