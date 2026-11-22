"""Question management services."""
from __future__ import annotations

from django.db import transaction

from modules.quiz.domain.errors import QuizNotEditable
from modules.quiz.models import Question, Quiz, QuizAuditLog


def add_question(*, quiz_id: int, principal,
                 question_type: str, text: str,
                 marks, negative_marks=0,
                 topic: str = "", difficulty: str = "",
                 options=None, correct_answer=None,
                 image_url: str = "",
                 reference_answer: str = "",
                 evaluation_criteria: str = "",
                 is_bank_question: bool = False,
                 order: int = 0) -> Question:
    """Add a question to a quiz — quiz must be in Draft."""
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        if not quiz.is_editable:
            raise QuizNotEditable("Questions can only be added to Draft quizzes.")

        question = Question.objects.create(
            quiz=quiz,
            question_type=question_type,
            text=text,
            marks=marks,
            negative_marks=negative_marks,
            topic=topic,
            difficulty=difficulty,
            options=options,
            correct_answer=correct_answer,
            image_url=image_url or "",
            reference_answer=reference_answer,
            evaluation_criteria=evaluation_criteria,
            is_bank_question=is_bank_question,
            order=order,
        )
        QuizAuditLog.objects.create(
            quiz=quiz,
            action="question_added",
            actor_user_id=principal.erp_user_id,
            detail={"question_id": question.pk, "type": question_type},
        )
    return question


def update_question(*, question_id: int, principal, **kwargs) -> Question:
    """Update a question — quiz must be in Draft."""
    with transaction.atomic():
        question = Question.objects.select_for_update().select_related("quiz").get(
            pk=question_id,
            quiz__created_by_user_id=principal.erp_user_id,
        )
        if not question.quiz.is_editable:
            raise QuizNotEditable("Questions can only be edited on Draft quizzes.")

        updatable = [
            "question_type", "text", "marks", "negative_marks", "topic",
            "difficulty", "options", "correct_answer", "image_url",
            "reference_answer", "evaluation_criteria", "is_bank_question", "order",
        ]
        changed = []
        for field in updatable:
            if field in kwargs:
                setattr(question, field, kwargs[field])
                changed.append(field)
        question.save(update_fields=changed)
    return question


def delete_question(*, question_id: int, principal) -> None:
    """Remove a question — quiz must be in Draft."""
    with transaction.atomic():
        question = Question.objects.select_for_update().select_related("quiz").get(
            pk=question_id,
            quiz__created_by_user_id=principal.erp_user_id,
        )
        if not question.quiz.is_editable:
            raise QuizNotEditable("Questions can only be deleted from Draft quizzes.")
        question.delete()


def add_bank_question_to_quiz(*, bank_question_id: int, quiz_id: int, principal) -> Question:
    """Clone a question-bank question into the target quiz."""
    with transaction.atomic():
        source = Question.objects.select_related("quiz").get(
            pk=bank_question_id,
            is_bank_question=True,
            quiz__created_by_user_id=principal.erp_user_id,
        )
        target_quiz = Quiz.objects.select_for_update().get(
            pk=quiz_id, created_by_user_id=principal.erp_user_id
        )
        if not target_quiz.is_editable:
            raise QuizNotEditable("Questions can only be added to Draft quizzes.")

        # Clone: same content, different quiz, not a bank question in clone
        return Question.objects.create(
            quiz=target_quiz,
            question_type=source.question_type,
            text=source.text,
            image_url=source.image_url,
            marks=source.marks,
            negative_marks=source.negative_marks,
            topic=source.topic,
            difficulty=source.difficulty,
            options=source.options,
            correct_answer=source.correct_answer,
            reference_answer=source.reference_answer,
            evaluation_criteria=source.evaluation_criteria,
            is_bank_question=False,
        )
