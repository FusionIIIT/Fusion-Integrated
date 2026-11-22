"""Database-backed tests for Quiz transactional service workflows."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.quiz.domain.quiz_definition import DefinitionAction, QuizDefinition
from modules.quiz.models import (
    Attempt,
    AttemptQuestion,
    OutboxEvent,
    Question,
    Quiz,
    QuizResult,
    Response,
)
from modules.quiz.services import attempts, authoring, lifecycle, responses

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


class TestActor:
    def __init__(self, user_id: object, permissions: set[str]) -> None:
        self.user_id = user_id
        self.permissions = permissions

    def has_permission(self, permission_code: str) -> bool:
        return permission_code in self.permissions


class PermissionOnlyActor:
    def has_permission(self, permission_code: str) -> bool:
        return permission_code == "quiz.quiz.create"


PROFESSOR = TestActor(
    501,
    {"quiz.quiz.create", "quiz.quiz.update", "quiz.quiz.publish"},
)
STUDENT = TestActor(1001, {"quiz.response.update", "quiz.attempt.update"})


def complete_definition(**overrides: object) -> QuizDefinition:
    values: dict[str, object] = {
        "title": "Assessment",
        "course_id": 77,
        "duration_seconds": 600,
        "maximum_marks": Decimal("10"),
        "passing_marks": Decimal("5"),
        "permitted_attempts": 2,
        "start_at": NOW - timedelta(minutes=1),
        "close_at": NOW + timedelta(hours=1),
    }
    values.update(overrides)
    return QuizDefinition(**values)  # type: ignore[arg-type]


def draft(*, definition: QuizDefinition | None = None) -> Quiz:
    return authoring.create_draft(
        actor=PROFESSOR,
        authorized_course_ids=[77],
        definition=definition or complete_definition(),
    )


def make_attempt(*, quiz: Quiz, student_user_id: int = 1001, **overrides: object) -> Attempt:
    values: dict[str, object] = {
        "quiz": quiz,
        "student_user_id": student_user_id,
        "attempt_number": 1,
        "started_at": NOW - timedelta(minutes=2),
        "deadline_at": NOW + timedelta(minutes=8),
    }
    values.update(overrides)
    return Attempt.objects.create(**values)  # type: ignore[arg-type]


def test_create_and_update_draft_use_authenticated_actor_and_course_scope() -> None:
    quiz = authoring.create_draft(
        actor=PROFESSOR,
        authorized_course_ids=[77],
        definition=complete_definition(title="First title"),
    )
    updated = authoring.update_draft(
        public_id=quiz.public_id,
        actor=PROFESSOR,
        authorized_course_ids=[77],
        definition=complete_definition(title="Revised title"),
        description="Description",
        instructions="Instructions",
    )
    assert updated.title == "Revised title"
    assert updated.description == "Description"
    assert updated.instructions == "Instructions"
    assert updated.created_by_user_id == PROFESSOR.user_id


def test_draft_update_preserves_omitted_description_and_instructions() -> None:
    quiz = draft()
    quiz.description = "Keep this description"
    quiz.instructions = "Keep these instructions"
    quiz.save(update_fields=["description", "instructions"])

    updated = authoring.update_draft(
        public_id=quiz.public_id,
        actor=PROFESSOR,
        authorized_course_ids=[77],
        definition=complete_definition(title="Changed title"),
    )

    assert updated.title == "Changed title"
    assert updated.description == "Keep this description"
    assert updated.instructions == "Keep these instructions"


def test_student_cannot_call_professor_authoring_operation() -> None:
    with pytest.raises(PermissionDeniedError):
        authoring.create_draft(
            actor=STUDENT,
            authorized_course_ids=[77],
            definition=complete_definition(),
        )


def test_professor_without_specific_create_permission_is_rejected() -> None:
    with pytest.raises(PermissionDeniedError):
        authoring.create_draft(
            actor=TestActor(501, set()),
            authorized_course_ids=[77],
            definition=complete_definition(),
        )


@pytest.mark.parametrize(
    "actor",
    [
        PermissionOnlyActor(),
        TestActor(None, {"quiz.quiz.create"}),
        TestActor(0, {"quiz.quiz.create"}),
        TestActor(-1, {"quiz.quiz.create"}),
        TestActor(True, {"quiz.quiz.create"}),
    ],
    ids=["missing", "none", "zero", "negative", "boolean"],
)
def test_draft_authoring_rejects_invalid_actor_user_ids(actor: object) -> None:
    with pytest.raises(PermissionDeniedError) as error:
        authoring.create_draft(
            actor=actor,
            authorized_course_ids=[77],
            definition=complete_definition(),
        )
    assert error.value.code == "actor_required"


def test_draft_authoring_rejects_invalid_fields_and_out_of_scope_course() -> None:
    with pytest.raises(DomainError) as error:
        authoring.create_draft(
            actor=PROFESSOR,
            authorized_course_ids=[77],
            definition=complete_definition(title=42),  # type: ignore[arg-type]
        )
    assert error.value.code == "invalid_quiz_definition"

    with pytest.raises(PermissionDeniedError):
        authoring.create_draft(
            actor=PROFESSOR,
            authorized_course_ids=[88],
            definition=complete_definition(),
        )


def test_draft_write_rolls_back_if_audit_write_fails(monkeypatch) -> None:
    def fail_audit(**kwargs: object) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(authoring, "record_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        draft()
    assert Quiz.objects.count() == 0


def test_lifecycle_publish_and_schedule_use_state_table_and_write_outbox(monkeypatch) -> None:
    monkeypatch.setattr(lifecycle.timezone, "now", lambda: NOW)
    immediate = draft()
    published = lifecycle.publish_quiz(
        public_id=immediate.public_id,
        actor=PROFESSOR,
        authorized_course_ids=[77],
        action=DefinitionAction.PUBLISH_NOW,
    )
    assert published.status == "available"

    future = draft(definition=complete_definition(start_at=NOW + timedelta(minutes=5)))
    scheduled = lifecycle.publish_quiz(
        public_id=future.public_id,
        actor=PROFESSOR,
        authorized_course_ids=[77],
        action=DefinitionAction.SCHEDULE,
    )
    assert scheduled.status == "scheduled"
    assert OutboxEvent.objects.count() == 2


def test_lifecycle_scope_and_invalid_publication_are_rejected(monkeypatch) -> None:
    monkeypatch.setattr(lifecycle.timezone, "now", lambda: NOW)
    quiz = draft(definition=complete_definition(start_at=NOW + timedelta(minutes=5)))
    with pytest.raises(NotFoundError):
        lifecycle.publish_quiz(
            public_id=quiz.public_id,
            actor=PROFESSOR,
            authorized_course_ids=[999],
            action=DefinitionAction.SCHEDULE,
        )
    with pytest.raises(DomainError) as error:
        lifecycle.publish_quiz(
            public_id=quiz.public_id,
            actor=PROFESSOR,
            authorized_course_ids=[77],
            action=DefinitionAction.PUBLISH_NOW,
        )
    assert error.value.code == "invalid_quiz_definition"


@pytest.mark.parametrize("status", ["scheduled", "available"])
def test_non_draft_quiz_cannot_be_updated(status: str) -> None:
    quiz = draft()
    quiz.status = status
    quiz.save(update_fields=["status"])

    with pytest.raises(DomainError) as error:
        authoring.update_draft(
            public_id=quiz.public_id,
            actor=PROFESSOR,
            authorized_course_ids=[77],
            definition=complete_definition(title="Not allowed"),
        )
    assert error.value.code == "quiz_not_editable"


def test_response_save_is_owner_scoped_revision_checked_and_key_free(monkeypatch) -> None:
    monkeypatch.setattr(responses.timezone, "now", lambda: NOW)
    quiz = draft()
    quiz.status = "available"
    quiz.save(update_fields=["status"])
    attempt = make_attempt(quiz=quiz)
    question = Question.objects.create(
        created_by_user_id=PROFESSOR.user_id,
        question_type="short_answer",
        prompt="Explain.",
        marks=Decimal("2"),
        answer_key={"private": "answer"},
        evaluation_criteria={"private": "rubric"},
    )
    item = AttemptQuestion.objects.create(
        attempt=attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[],
        marks_at_start=Decimal("2"),
    )

    created = responses.save_response(
        attempt_id=attempt.pk,
        attempt_question_id=item.pk,
        actor=STUDENT,
        answer_payload={"text": "my answer"},
        expected_revision=0,
    )
    assert created.revision == 1
    response = Response.objects.get(attempt_question=item)
    assert response.answer_payload == {"text": "my answer"}

    updated = responses.save_response(
        attempt_id=attempt.pk,
        attempt_question_id=item.pk,
        actor=STUDENT,
        answer_payload={"text": "revised"},
        expected_revision=1,
    )
    response.refresh_from_db()
    assert updated.revision == 2
    assert response.answer_payload == {"text": "revised"}
    assert "private" not in repr(created)
    with pytest.raises(ConflictError) as error:
        responses.save_response(
            attempt_id=attempt.pk,
            attempt_question_id=item.pk,
            actor=STUDENT,
            answer_payload={"text": "stale"},
            expected_revision=1,
        )
    assert error.value.code == "response_revision_conflict"


def test_response_save_rejects_peer_item_expiry_and_submitted_attempt(monkeypatch) -> None:
    monkeypatch.setattr(responses.timezone, "now", lambda: NOW)
    quiz = draft()
    attempt = make_attempt(quiz=quiz)
    peer_attempt = make_attempt(quiz=quiz, student_user_id=2002)
    question = Question.objects.create(
        created_by_user_id=PROFESSOR.user_id,
        question_type="true_false",
        prompt="A statement.",
        marks=Decimal("1"),
    )
    peer_item = AttemptQuestion.objects.create(
        attempt=peer_attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[],
        marks_at_start=Decimal("1"),
    )
    with pytest.raises(NotFoundError):
        responses.save_response(
            attempt_id=attempt.pk,
            attempt_question_id=peer_item.pk,
            actor=STUDENT,
            answer_payload=True,
            expected_revision=0,
        )

    item = AttemptQuestion.objects.create(
        attempt=attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[],
        marks_at_start=Decimal("1"),
    )
    monkeypatch.setattr(responses.timezone, "now", lambda: NOW + timedelta(hours=1))
    with pytest.raises(ConflictError) as error:
        responses.save_response(
            attempt_id=attempt.pk,
            attempt_question_id=item.pk,
            actor=STUDENT,
            answer_payload=True,
            expected_revision=0,
        )
    assert error.value.code == "attempt_deadline_passed"

    attempt.status = "submitted"
    attempt.submitted_at = NOW
    attempt.submission_method = "manual"
    attempt.save(update_fields=["status", "submitted_at", "submission_method"])
    with pytest.raises(ConflictError, match="cannot be changed"):
        responses.save_response(
            attempt_id=attempt.pk,
            attempt_question_id=item.pk,
            actor=STUDENT,
            answer_payload=True,
            expected_revision=0,
        )


def test_manual_submission_creates_one_result_and_duplicate_retry_is_idempotent(
    monkeypatch,
) -> None:
    monkeypatch.setattr(attempts.timezone, "now", lambda: NOW)
    quiz = draft()
    attempt = make_attempt(quiz=quiz)

    submitted = attempts.submit_attempt(attempt_id=attempt.pk, actor=STUDENT)
    retry = attempts.submit_attempt(attempt_id=attempt.pk, actor=STUDENT)

    assert submitted.status == "submitted"
    assert retry.pk == attempt.pk
    assert QuizResult.objects.filter(attempt=attempt).count() == 1
    assert OutboxEvent.objects.filter(dedupe_key=f"attempt.submitted:{attempt.pk}").count() == 1


def test_manual_submission_rejects_nonowner_and_expired_attempt(monkeypatch) -> None:
    monkeypatch.setattr(attempts.timezone, "now", lambda: NOW)
    quiz = draft()
    attempt = make_attempt(quiz=quiz, student_user_id=2002)
    with pytest.raises(NotFoundError):
        attempts.submit_attempt(attempt_id=attempt.pk, actor=STUDENT)

    own_attempt = make_attempt(quiz=quiz, student_user_id=STUDENT.user_id, attempt_number=2)
    monkeypatch.setattr(attempts.timezone, "now", lambda: NOW + timedelta(hours=1))
    with pytest.raises(ConflictError):
        attempts.submit_attempt(attempt_id=own_attempt.pk, actor=STUDENT)
    own_attempt.refresh_from_db()
    assert own_attempt.status == "in_progress"


def test_manual_submission_rejects_unexpected_persisted_state(monkeypatch) -> None:
    attempt = Attempt(pk=1, status="unexpected")

    class AttemptQuery:
        def select_for_update(self, *, of: tuple[str, ...]) -> "AttemptQuery":
            assert of == ("self",)
            return self

        def first(self) -> Attempt:
            return attempt

    monkeypatch.setattr(attempts, "attempt_for_student", lambda **kwargs: AttemptQuery())

    with pytest.raises(ConflictError) as error:
        attempts.submit_attempt(attempt_id=1, actor=STUDENT)
    assert error.value.code == "invalid_attempt_state"


def test_submission_rolls_back_if_audit_write_fails(monkeypatch) -> None:
    monkeypatch.setattr(attempts.timezone, "now", lambda: NOW)
    quiz = draft()
    attempt = make_attempt(quiz=quiz)

    def fail_audit(**kwargs: object) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(attempts, "record_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        attempts.submit_attempt(attempt_id=attempt.pk, actor=STUDENT)
    attempt.refresh_from_db()
    assert attempt.status == "in_progress"
    assert not QuizResult.objects.filter(attempt=attempt).exists()
    assert not OutboxEvent.objects.filter(aggregate_id=attempt.pk).exists()


def test_initial_response_creation_collision_returns_revision_conflict(monkeypatch) -> None:
    monkeypatch.setattr(responses.timezone, "now", lambda: NOW)
    quiz = draft()
    attempt = make_attempt(quiz=quiz)
    question = Question.objects.create(
        created_by_user_id=PROFESSOR.user_id,
        question_type="short_answer",
        prompt="Explain.",
        marks=Decimal("2"),
    )
    item = AttemptQuestion.objects.create(
        attempt=attempt,
        question=question,
        display_order=1,
        displayed_option_keys=[],
        marks_at_start=Decimal("2"),
    )
    Response.objects.create(
        attempt_question=item,
        answer_payload={"text": "already persisted"},
        saved_at=NOW,
        revision=1,
    )

    with pytest.raises(ConflictError) as error:
        responses.save_response(
            attempt_id=attempt.pk,
            attempt_question_id=item.pk,
            actor=STUDENT,
            answer_payload={"text": "collision"},
            expected_revision=0,
        )
    assert error.value.code == "response_revision_conflict"
