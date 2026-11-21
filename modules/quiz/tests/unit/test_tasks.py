"""Database-backed tests for Quiz Celery work and system transitions."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.quiz import tasks as task_module
from modules.quiz.models import Attempt, AuditEvent, OutboxEvent, Quiz, QuizResult
from modules.quiz.services import attempts as attempt_services
from modules.quiz.services import lifecycle as lifecycle_services
from modules.quiz.tasks import auto_submit_expired_attempts, process_quiz_boundaries

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def make_quiz(*, status: str = "available", start_at=None, close_at=None) -> Quiz:
    return Quiz.objects.create(
        course_id=77,
        created_by_user_id=501,
        title="Scheduled assessment",
        duration_seconds=600,
        maximum_marks=Decimal("10"),
        passing_marks=Decimal("5"),
        permitted_attempts=1,
        status=status,
        start_at=start_at or NOW - timedelta(minutes=10),
        close_at=close_at or NOW + timedelta(hours=1),
    )


def make_attempt(
    *, quiz: Quiz, deadline_at, status: str = "in_progress", attempt_number: int = 1
) -> Attempt:
    started_at = deadline_at - timedelta(minutes=10)
    return Attempt.objects.create(
        quiz=quiz,
        student_user_id=1001,
        attempt_number=attempt_number,
        status=status,
        started_at=started_at,
        deadline_at=deadline_at,
        submitted_at=NOW if status == "submitted" else None,
        submission_method="manual" if status == "submitted" else "",
    )


def test_expiry_task_processes_only_attempts_at_or_past_deadline(monkeypatch) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(attempt_services.timezone, "now", lambda: NOW)
    quiz = make_quiz()
    expired = make_attempt(quiz=quiz, deadline_at=NOW)
    future = make_attempt(
        quiz=quiz,
        deadline_at=NOW + timedelta(seconds=1),
        attempt_number=2,
    )

    assert auto_submit_expired_attempts.run() == 1

    expired.refresh_from_db()
    future.refresh_from_db()
    assert expired.status == "submitted"
    assert expired.submission_method == "time_expiry"
    assert future.status == "in_progress"
    assert QuizResult.objects.filter(attempt=expired, status="not_evaluated").exists()


def test_expiry_task_does_not_overwrite_manual_submission(monkeypatch) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(attempt_services.timezone, "now", lambda: NOW)
    quiz = make_quiz()
    manual = make_attempt(quiz=quiz, deadline_at=NOW - timedelta(seconds=1), status="submitted")
    QuizResult.objects.create(attempt=manual)

    assert auto_submit_expired_attempts.run() == 0

    manual.refresh_from_db()
    assert manual.submission_method == "manual"
    assert QuizResult.objects.filter(attempt=manual).count() == 1
    assert not AuditEvent.objects.filter(action="attempt.auto_submitted").exists()


def test_expiry_task_is_idempotent_across_duplicate_runs(monkeypatch) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(attempt_services.timezone, "now", lambda: NOW)
    quiz = make_quiz()
    attempt = make_attempt(quiz=quiz, deadline_at=NOW - timedelta(seconds=1))

    assert auto_submit_expired_attempts.run() == 1
    assert auto_submit_expired_attempts.run() == 0

    assert QuizResult.objects.filter(attempt=attempt).count() == 1
    assert AuditEvent.objects.filter(action="attempt.auto_submitted").count() == 1
    assert (
        OutboxEvent.objects.filter(dedupe_key=f"attempt.auto_submitted:{attempt.pk}").count() == 1
    )


def test_boundary_task_activates_scheduled_and_closes_available_quizzes(monkeypatch) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(lifecycle_services.timezone, "now", lambda: NOW)
    scheduled = make_quiz(
        status="scheduled",
        start_at=NOW,
        close_at=NOW + timedelta(minutes=5),
    )
    available = make_quiz(
        status="available",
        start_at=NOW - timedelta(hours=1),
        close_at=NOW,
    )
    not_yet_started = make_quiz(
        status="scheduled",
        start_at=NOW + timedelta(seconds=1),
        close_at=NOW + timedelta(minutes=5),
    )

    assert process_quiz_boundaries.run() == 2

    scheduled.refresh_from_db()
    available.refresh_from_db()
    not_yet_started.refresh_from_db()
    assert scheduled.status == "available"
    assert available.status == "closed"
    assert not_yet_started.status == "scheduled"
    assert AuditEvent.objects.filter(action__in=["quiz.activated", "quiz.closed"]).count() == 2
    assert OutboxEvent.objects.filter(event_type__in=["quiz.activated", "quiz.closed"]).count() == 2


def test_boundary_transitions_are_idempotent_and_ignore_stale_or_invalid_states(
    monkeypatch,
) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(lifecycle_services.timezone, "now", lambda: NOW)
    scheduled = make_quiz(
        status="scheduled",
        start_at=NOW - timedelta(minutes=1),
        close_at=NOW,
    )
    draft = make_quiz(status="draft", start_at=NOW - timedelta(minutes=1))

    assert process_quiz_boundaries.run() == 0
    assert lifecycle_services.process_quiz_boundary(quiz_id=draft.pk) is False
    assert process_quiz_boundaries.run() == 0

    scheduled.refresh_from_db()
    draft.refresh_from_db()
    assert scheduled.status == "scheduled"
    assert draft.status == "draft"
    assert not AuditEvent.objects.filter(aggregate_type="quiz").exists()


def test_expiry_transition_rolls_back_attempt_result_audit_and_outbox_on_failure(
    monkeypatch,
) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(attempt_services.timezone, "now", lambda: NOW)
    quiz = make_quiz()
    attempt = make_attempt(quiz=quiz, deadline_at=NOW - timedelta(seconds=1))

    def fail_audit(**kwargs: object) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(attempt_services, "record_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        auto_submit_expired_attempts.run()

    attempt.refresh_from_db()
    assert attempt.status == "in_progress"
    assert not QuizResult.objects.filter(attempt=attempt).exists()
    assert not OutboxEvent.objects.filter(aggregate_id=attempt.pk).exists()


def test_quiz_boundary_rolls_back_status_and_audit_when_outbox_write_fails(monkeypatch) -> None:
    monkeypatch.setattr(task_module.timezone, "now", lambda: NOW)
    monkeypatch.setattr(lifecycle_services.timezone, "now", lambda: NOW)
    quiz = make_quiz(
        status="scheduled",
        start_at=NOW - timedelta(minutes=1),
        close_at=NOW + timedelta(minutes=1),
    )

    def fail_outbox(**kwargs: object) -> None:
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr(lifecycle_services, "enqueue_internal_event", fail_outbox)
    with pytest.raises(RuntimeError, match="outbox unavailable"):
        process_quiz_boundaries.run()

    quiz.refresh_from_db()
    assert quiz.status == "scheduled"
    assert not AuditEvent.objects.filter(aggregate_type="quiz").exists()
    assert not OutboxEvent.objects.filter(aggregate_type="quiz").exists()
