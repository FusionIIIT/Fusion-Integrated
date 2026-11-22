"""Quiz management services — create, update, publish, archive."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.quiz.domain.errors import QuizNotEditable
from modules.quiz.domain.state_machine import QuizStatus, validate_quiz_transition
from modules.quiz.models import Quiz, QuizAuditLog


def create_quiz(*, principal, title: str, description: str = "", course: str,
                instructions: str = "", duration_minutes: int,
                max_marks, passing_marks=None, max_attempts: int = 1,
                start_at=None, close_at=None,
                allow_back_navigation: bool = True,
                one_question_at_a_time: bool = False,
                randomize_questions: bool = False,
                randomize_options: bool = False,
                allow_unanswered: bool = True,
                tab_block: bool = False,
                negative_marking: bool = False,
                result_visibility: str = "after_release") -> Quiz:
    """Create a new quiz as Draft."""
    with transaction.atomic():
        quiz = Quiz.objects.create(
            title=title,
            description=description,
            course=course,
            instructions=instructions,
            duration_minutes=duration_minutes,
            max_marks=max_marks,
            passing_marks=passing_marks,
            max_attempts=max_attempts,
            start_at=start_at,
            close_at=close_at,
            allow_back_navigation=allow_back_navigation,
            one_question_at_a_time=one_question_at_a_time,
            randomize_questions=randomize_questions,
            randomize_options=randomize_options,
            allow_unanswered=allow_unanswered,
            tab_block=tab_block,
            negative_marking=negative_marking,
            result_visibility=result_visibility,
            created_by_user_id=principal.erp_user_id,
            status=QuizStatus.DRAFT,
        )
        QuizAuditLog.objects.create(
            quiz=quiz,
            action="quiz_created",
            actor_user_id=principal.erp_user_id,
            detail={"title": quiz.title, "course": quiz.course},
        )
    return quiz


def update_quiz(*, quiz_id: int, principal, **kwargs) -> Quiz:
    """Update quiz details — only allowed when status is Draft."""
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        if not quiz.is_editable:
            raise QuizNotEditable(
                "Quiz details can only be edited while in Draft status."
            )
        updatable = [
            "title", "description", "course", "instructions",
            "duration_minutes", "max_marks", "passing_marks", "max_attempts",
            "start_at", "close_at", "allow_back_navigation",
            "one_question_at_a_time", "randomize_questions", "randomize_options",
            "allow_unanswered", "tab_block", "negative_marking", "result_visibility",
        ]
        changed = []
        for field in updatable:
            if field in kwargs:
                setattr(quiz, field, kwargs[field])
                changed.append(field)
        quiz.save(update_fields=[*changed, "updated_at"])
        QuizAuditLog.objects.create(
            quiz=quiz,
            action="quiz_updated",
            actor_user_id=principal.erp_user_id,
            detail={"fields": changed},
        )
    return quiz


def delete_quiz(*, quiz_id: int, principal) -> None:
    """Delete a quiz — only allowed when status is Draft and no attempts exist."""
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        if not quiz.is_editable:
            raise QuizNotEditable("Only Draft quizzes can be deleted.")
        quiz.delete()


def publish_quiz(*, quiz_id: int, principal) -> Quiz:
    """Publish a configured quiz — transitions Draft → Available or Scheduled."""
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        now = timezone.now()
        if quiz.start_at and quiz.start_at > now:
            new_status = QuizStatus.SCHEDULED
        else:
            new_status = QuizStatus.AVAILABLE

        validate_quiz_transition(quiz.status, new_status)
        quiz.status = new_status
        quiz.save(update_fields=["status", "updated_at"])
        QuizAuditLog.objects.create(
            quiz=quiz,
            action="quiz_published",
            actor_user_id=principal.erp_user_id,
            detail={"new_status": new_status},
        )
    return quiz


def close_quiz(*, quiz_id: int, principal) -> Quiz:
    """Close an Available quiz (UC-QZ-006 / UC-QZ-018)."""
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        validate_quiz_transition(quiz.status, QuizStatus.CLOSED)
        quiz.status = QuizStatus.CLOSED
        quiz.save(update_fields=["status", "updated_at"])
        QuizAuditLog.objects.create(
            quiz=quiz,
            action="quiz_closed",
            actor_user_id=principal.erp_user_id,
        )
    return quiz


def archive_quiz(*, quiz_id: int, principal) -> Quiz:
    """Archive a Closed quiz (BR-QZ-023)."""
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        validate_quiz_transition(quiz.status, QuizStatus.ARCHIVED)
        quiz.status = QuizStatus.ARCHIVED
        quiz.save(update_fields=["status", "updated_at"])
        QuizAuditLog.objects.create(
            quiz=quiz,
            action="quiz_archived",
            actor_user_id=principal.erp_user_id,
        )
    return quiz
