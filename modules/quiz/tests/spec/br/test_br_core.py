from datetime import UTC, datetime

import pytest

from modules.quiz.machines.attempt_machine import M2, STUDENT, SYSTEM
from modules.quiz.machines.quiz_machine import M1, PROFESSOR
from modules.quiz.machines.result_machine import M3
from modules.quiz.scope import professor_teaches, student_eligible
from modules.quiz.scoring import compute_result, score_response
from modules.quiz.state_machine import (
    GuardFailed,
    IllegalTransition,
    apply_transition,
)


def test_br_br_qz_011_source_br_qz_011_negative_marking():
    """Design test_id=BR-BR-QZ-011; source_id=BR-QZ-011: negative marking is configurable."""
    question = {"type": "MCQ", "marks": 2, "negative_marks": 0.5, "correct": ["A"]}
    assert score_response(question, "B", True) == -score_response(question, "A", True) / 4
    assert score_response(question, "B", False) == 0


def test_br_br_qz_016_source_br_qz_016_submitted_attempt_is_immutable():
    """Design test_id=BR-BR-QZ-016; source_id=BR-QZ-016: M2 allows no transition after submission."""
    with pytest.raises(IllegalTransition):
        apply_transition(M2, "SUBMITTED", "submit", STUDENT, {})


def test_br_br_qz_017_source_br_qz_017_deadline_auto_submit():
    """Design test_id=BR-BR-QZ-017; source_id=BR-QZ-017: expiry permits one system submission."""
    now = datetime.now(UTC)
    context = {"now": now, "deadline_at": now}
    assert apply_transition(M2, "STARTED", "auto_submit", SYSTEM, context) == "SUBMITTED"
    with pytest.raises(IllegalTransition):
        apply_transition(M2, "SUBMITTED", "auto_submit", SYSTEM, context)


def test_br_br_qz_020_source_br_qz_020_result_calculation():
    """Design test_id=BR-BR-QZ-020; source_id=BR-QZ-020: aggregate score and result fields."""
    result = compute_result(
        [2, -0.5, 2],
        10,
        4,
        {"correct": 2, "incorrect": 1, "unanswered": 0},
    )
    assert result["marks_obtained"] == 2 + 2 - 0.5
    assert result["percentage"] == 35
    assert result["negative_marks_total"] == 0.5
    assert result["passed"] is False
    assert result["correct_count"] == 2
    assert result["incorrect_count"] == 1
    assert result["unanswered_count"] == 0


def test_br_br_qz_002_source_br_qz_002_professor_course_scope():
    """Design test_id=BR-BR-QZ-002; source_id=BR-QZ-002: checks the domain scope predicate only, not API authorization or scoped data retrieval."""
    from types import SimpleNamespace

    course = SimpleNamespace(faculty_ids=[41, 42])
    assert professor_teaches(SimpleNamespace(user_id=41), course) is True
    assert professor_teaches(SimpleNamespace(user_id=99), course) is False
    assert professor_teaches(None, course) is False


def test_br_br_qz_003_source_br_qz_003_student_quiz_eligibility():
    """Design test_id=BR-BR-QZ-003; source_id=BR-QZ-003: checks the domain eligibility predicate only, not API access or attempt creation."""
    from types import SimpleNamespace

    quiz = SimpleNamespace(course=SimpleNamespace(student_ids=[51, 52]))
    assert student_eligible(SimpleNamespace(user_id=51, kind="student"), quiz) is True
    assert student_eligible(SimpleNamespace(user_id=53, kind="student"), quiz) is False
    assert student_eligible(SimpleNamespace(user_id=51, kind="professor"), quiz) is False
    assert student_eligible(None, quiz) is False


def test_br_br_qz_006_source_br_qz_006_availability_window_boundaries():
    """Design test_id=BR-BR-QZ-006; source_id=BR-QZ-006: checks M1 transitions; pre-boundary denials are a candidate failure, integration remains untested."""
    from datetime import timedelta

    now = datetime.now(UTC)
    start_at = now + timedelta(minutes=5)
    scheduled = apply_transition(
        M1,
        "READY_TO_PUBLISH",
        "publish",
        PROFESSOR,
        {
            "owns_course": True,
            "questions_valid": True,
            "config_valid": True,
            "start_at": start_at,
            "now": now,
        },
    )
    assert scheduled == "SCHEDULED"
    with pytest.raises(GuardFailed):
        apply_transition(
            M1,
            scheduled,
            "boundary_start",
            SYSTEM,
            {"now": now, "start_at": start_at},
        )
    assert apply_transition(
        M1, scheduled, "boundary_start", SYSTEM, {"now": start_at, "start_at": start_at}
    ) == "AVAILABLE"
    close_at = start_at + timedelta(minutes=30)
    with pytest.raises(GuardFailed):
        apply_transition(
            M1,
            "AVAILABLE",
            "boundary_close",
            SYSTEM,
            {"now": start_at, "close_at": close_at},
        )
    assert apply_transition(
        M1, "AVAILABLE", "boundary_close", SYSTEM, {"now": close_at, "close_at": close_at}
    ) == "CLOSED"


def test_br_br_qz_008_source_br_qz_008_permitted_attempt_limit():
    """Design test_id=BR-BR-QZ-008; source_id=BR-QZ-008: checks M2 allowance guard only, not persisted counts or concurrency."""
    now = datetime.now(UTC)
    context = {
        "eligible": True,
        "attempts_used": 0,
        "max_attempts": 1,
        "has_active_attempt": False,
        "now": now,
        "quiz_start_at": now,
    }
    assert apply_transition(M2, None, "start", STUDENT, context) == "STARTED"
    exhausted_context = {**context, "attempts_used": 1}
    with pytest.raises(GuardFailed, match="ATTEMPTS_EXHAUSTED"):
        apply_transition(M2, None, "start", STUDENT, exhausted_context)


def test_br_br_qz_012_source_br_qz_012_unanswered_submission_guard():
    """Design test_id=BR-BR-QZ-012; source_id=BR-QZ-012: checks M2 submission guard only, not unanswered confirmation details."""
    now = datetime.now(UTC)
    common = {"confirm": True, "now": now, "deadline_at": now, "unanswered": 1}
    with pytest.raises(GuardFailed, match="UNANSWERED_NOT_ALLOWED"):
        apply_transition(
            M2, "STARTED", "submit", STUDENT, {**common, "allow_unanswered": False}
        )
    assert apply_transition(
        M2, "STARTED", "submit", STUDENT, {**common, "allow_unanswered": True}
    ) == "SUBMITTED"


def test_br_br_qz_018_source_br_qz_018_objective_evaluation_domain():
    """Design test_id=BR-BR-QZ-018; source_id=BR-QZ-018: checks scoring and M3 transition only, not evaluation persistence/orchestration."""
    question = {"type": "MCQ", "marks": 3, "negative_marks": 1, "correct": ["A"]}
    assert score_response(question, "A", True) == 3
    assert score_response(question, "B", True) == -1
    assert apply_transition(M3, "NOT_EVALUATED", "auto_evaluate", SYSTEM, {}) == "EVALUATED"


def test_br_br_qz_021_source_br_qz_021_release_and_permitted_visibility():
    """Design test_id=BR-BR-QZ-021; source_id=BR-QZ-021: checks M3 release/allowed visibility; denied visibility is a candidate failure, API/settings remain untested."""
    with pytest.raises(IllegalTransition):
        apply_transition(
            M3,
            "EVALUATED",
            "view_result",
            STUDENT,
            {"visibility_permits": True},
        )
    released = apply_transition(
        M3, "EVALUATED", "release", PROFESSOR, {"owns_course": True}
    )
    assert released == "RELEASED"
    assert apply_transition(
        M3, released, "view_result", STUDENT, {"visibility_permits": True}
    ) == "RELEASED"
    with pytest.raises(GuardFailed):
        apply_transition(
            M3, released, "view_result", STUDENT, {"visibility_permits": False}
        )


def test_br_br_qz_023_source_br_qz_023_archive_permission():
    """Design test_id=BR-BR-QZ-023; source_id=BR-QZ-023: checks permitted M1 archive; denial is a candidate failure, delete/policy remain unspecified."""
    with pytest.raises(GuardFailed):
        apply_transition(M1, "CLOSED", "archive", PROFESSOR, {"archive_permitted": False})
    assert apply_transition(
        M1, "CLOSED", "archive", PROFESSOR, {"archive_permitted": True}
    ) == "ARCHIVED"


def test_br_br_qz_001_source_br_qz_001_role_separation_not_automated():
    """test_id=BR-BR-QZ-001; source_id=BR-QZ-001."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-001 (source_id=BR-QZ-001): the Professor-only "
        "quiz authorization API/service for protected operations is absent."
    )


def test_br_br_qz_004_source_br_qz_004_student_data_visibility_not_automated():
    """test_id=BR-BR-QZ-004; source_id=BR-QZ-004."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-004 (source_id=BR-QZ-004): a student-scoped "
        "result/report/history API or query service enforcing role and configured visibility is absent."
    )


def test_br_br_qz_005_source_br_qz_005_pre_activation_edit_boundary_not_automated():
    """test_id=BR-BR-QZ-005; source_id=BR-QZ-005."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-005 (source_id=BR-QZ-005): a Quiz/Question "
        "mutation service with persistence enforcing edits against current quiz state is absent."
    )


def test_br_br_qz_007_source_br_qz_007_time_limit_not_automated():
    """test_id=BR-BR-QZ-007; source_id=BR-QZ-007."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-007 (source_id=BR-QZ-007): an attempt timer "
        "service deriving deadlines from Quiz.duration_minutes and exposing the running timer is absent."
    )


def test_br_br_qz_009_source_br_qz_009_question_option_order_not_automated():
    """test_id=BR-BR-QZ-009; source_id=BR-QZ-009."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-009 (source_id=BR-QZ-009): a question "
        "selection/rendering service applying configured question and option ordering is absent."
    )


def test_br_br_qz_010_source_br_qz_010_navigation_display_mode_not_automated():
    """test_id=BR-BR-QZ-010; source_id=BR-QZ-010."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-010 (source_id=BR-QZ-010): an attempt UI "
        "or navigation handler enforcing back-navigation and one-question display settings is absent."
    )


def test_br_br_qz_013_source_br_qz_013_tab_block_rule_not_automated():
    """test_id=BR-BR-QZ-013; source_id=BR-QZ-013."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-013 (source_id=BR-QZ-013): browser attempt "
        "UI and tab-event enforcement for the configured policy are absent; platform semantics remain unresolved."
    )


def test_br_br_qz_014_source_br_qz_014_background_application_check_not_automated():
    """test_id=BR-BR-QZ-014; source_id=BR-QZ-014."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-014 (source_id=BR-QZ-014): OS background-"
        "process detection and the close-option UI integration are absent; platform and permission semantics remain unresolved."
    )


def test_br_br_qz_015_source_br_qz_015_active_response_persistence_not_automated():
    """test_id=BR-BR-QZ-015; source_id=BR-QZ-015."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-015 (source_id=BR-QZ-015): an answer-save "
        "application service/API persisting AttemptResponse during an active attempt is absent."
    )


def test_br_br_qz_019_source_br_qz_019_professor_subjective_evaluation_not_automated():
    """test_id=BR-BR-QZ-019; source_id=BR-QZ-019."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-019 (source_id=BR-QZ-019): a subjective-"
        "evaluation service integrating AI suggestions, Professor confirmation, and final-mark persistence is absent."
    )


def test_br_br_qz_022_source_br_qz_022_audit_trail_not_automated():
    """test_id=BR-BR-QZ-022; source_id=BR-QZ-022."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-022 (source_id=BR-QZ-022): an audit event-"
        "producing service connecting state changes to AuditLogEntry persistence is absent."
    )


def test_br_br_qz_024_source_br_qz_024_notification_events_not_automated():
    """test_id=BR-BR-QZ-024; source_id=BR-QZ-024."""
    pytest.skip(
        "NOT_AUTOMATED: BR-BR-QZ-024 (source_id=BR-QZ-024): a notification "
        "event-generation and recipient-delivery service is absent."
    )
