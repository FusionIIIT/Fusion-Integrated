from datetime import UTC, datetime, timedelta

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT, SYSTEM
from modules.quiz.machines.quiz_machine import M1, PROFESSOR
from modules.quiz.machines.result_machine import M3
from modules.quiz.scoring import score_response
from modules.quiz.state_machine import (
    GuardFailed,
    IllegalTransition,
    apply_transition,
)


def test_uc_uc_qz_005_publish_quiz_immediately_or_on_schedule():
    """Test ID UC-UC-QZ-005; source_id UC-QZ-005: verify M1 state only,
    not persistence/API flow.
    """
    now = datetime.now(UTC)
    common = {
        "owns_course": True,
        "questions_valid": True,
        "config_valid": True,
        "now": now,
    }

    assert (
        apply_transition(
            M1,
            "READY_TO_PUBLISH",
            "publish",
            PROFESSOR,
            {**common, "start_at": now + timedelta(minutes=1)},
        )
        == "SCHEDULED"
    )
    assert (
        apply_transition(
            M1,
            "READY_TO_PUBLISH",
            "publish",
            PROFESSOR,
            {**common, "start_at": now},
        )
        == "AVAILABLE"
    )

    for context, reason in (
        ({**common, "owns_course": False}, "NOT_COURSE_OWNER"),
        ({**common, "questions_valid": False}, "QUESTIONS_INVALID"),
        ({**common, "config_valid": False}, "CONFIG_INVALID"),
    ):
        with pytest.raises(GuardFailed, match=reason):
            apply_transition(
                M1,
                "READY_TO_PUBLISH",
                "publish",
                PROFESSOR,
                {**context, "start_at": now},
            )


def test_uc_uc_qz_006_archive_quiz_domain_transition():
    """Test ID UC-UC-QZ-006; source_id UC-QZ-006: exercise M1 archive transition only.

    A8_BASE has no quiz deletion service; this does not verify deletion or persistence.
    """
    assert (
        apply_transition(M1, "CLOSED", "archive", PROFESSOR, {"archive_permitted": True})
        == "ARCHIVED"
    )


def test_uc_uc_qz_008_start_attempt():
    """Test ID UC-UC-QZ-008; source_id UC-QZ-008: M2 guards/state only,
    not timer or environment integration.
    """
    now = datetime.now(UTC)
    state = apply_transition(
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
    assert state == "STARTED"

    rejected_contexts = (
        ({"eligible": False}, "INELIGIBLE"),
        ({"attempts_used": 1, "max_attempts": 1}, "ATTEMPTS_EXHAUSTED"),
        ({"has_active_attempt": True}, "ACTIVE_ATTEMPT_EXISTS"),
        ({"quiz_start_at": now + timedelta(seconds=1)}, "NOT_AVAILABLE"),
    )
    for overrides, reason in rejected_contexts:
        context = {
            "eligible": True,
            "attempts_used": 0,
            "max_attempts": 1,
            "has_active_attempt": False,
            "quiz_start_at": now,
            "now": now,
            **overrides,
        }
        with pytest.raises(GuardFailed, match=reason):
            apply_transition(M2, None, "start", STUDENT, context)


def test_uc_uc_qz_010_manual_submit():
    """Test ID UC-UC-QZ-010; source_id UC-QZ-010: M2 state only,
    not submission persistence or evaluation.
    """
    now = datetime.now(UTC)
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

    with pytest.raises(GuardFailed, match="CONFIRM_REQUIRED"):
        apply_transition(
            M2,
            "STARTED",
            "submit",
            STUDENT,
            {
                "confirm": False,
                "now": now,
                "deadline_at": now + timedelta(minutes=5),
                "allow_unanswered": True,
                "unanswered": 0,
            },
        )
    with pytest.raises(IllegalTransition):
        apply_transition(M2, "SUBMITTED", "submit", STUDENT, {})


def test_uc_uc_qz_011_auto_submit_at_deadline():
    """Test ID UC-UC-QZ-011; source_id UC-QZ-011: M2 expiry state only,
    not response/timestamp persistence.
    """
    now = datetime.now(UTC)
    assert (
        apply_transition(
            M2,
            "STARTED",
            "auto_submit",
            SYSTEM,
            {"now": now, "deadline_at": now},
        )
        == "SUBMITTED"
    )
    with pytest.raises(IllegalTransition):
        apply_transition(
            M2,
            "SUBMITTED",
            "auto_submit",
            SYSTEM,
            {"now": now, "deadline_at": now},
        )


def test_uc_uc_qz_012_objective_scoring_and_evaluation_domain():
    """Test ID UC-UC-QZ-012; source_id UC-QZ-012: verify scorer and M3 transition separately.

    These domain checks do not verify submitted-attempt orchestration or persisted evaluation.
    """
    score = score_response(
        {"type": "MCQ", "marks": 2, "correct": ["a"]},
        "a",
        negative_marking_enabled=False,
    )
    assert score == 2
    assert (
        apply_transition(
            M3,
            "NOT_EVALUATED",
            "auto_evaluate",
            SYSTEM,
            {"responses": [{"kind": "objective"}]},
        )
        == "EVALUATED"
    )


def test_uc_uc_qz_014_release_result_domain_transition():
    """Test ID UC-UC-QZ-014; source_id UC-QZ-014: verify M3 release state only.

    Does not verify release authorization, visibility rules, persistence, or result delivery.
    """
    assert (
        apply_transition(M3, "EVALUATED", "release", PROFESSOR, {"owns_course": True}) == "RELEASED"
    )


def test_uc_uc_qz_018_process_quiz_availability_boundaries():
    """Test ID UC-UC-QZ-018; source_id UC-QZ-018: M1 lifecycle state only,
    not persisted scheduling.
    """
    now = datetime.now(UTC)
    available = apply_transition(
        M1,
        "SCHEDULED",
        "boundary_start",
        SYSTEM,
        {"now": now, "start_at": now},
    )
    assert available == "AVAILABLE"
    assert (
        apply_transition(
            M1,
            available,
            "boundary_close",
            SYSTEM,
            {"now": now, "close_at": now},
        )
        == "CLOSED"
    )
    with pytest.raises(IllegalTransition):
        apply_transition(M1, "DRAFT", "boundary_start", SYSTEM, {"now": now, "start_at": now})
