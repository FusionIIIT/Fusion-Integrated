from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.quiz.models import AuditLogEntry, QuestionBankItem, Quiz, QuizOption, QuizQuestion


@transaction.atomic
def add_question_bank_item(
    owner_user_id: int,
    question_text: str,
    question_type: str,
    marks: Decimal,
    negative_marks: Decimal = Decimal(0),
    topic: str = "",
    difficulty: str = "",
    image=None,
) -> QuestionBankItem:
    return QuestionBankItem.objects.create(
        owner_user_id=owner_user_id,
        question_text=question_text,
        question_type=question_type,
        marks=marks,
        negative_marks=negative_marks,
        topic=topic,
        difficulty=difficulty,
        image=image,
    )


@transaction.atomic
def add_quiz_question(
    quiz_id: int,
    user_id: int,
    question_text: str,
    question_type: str,
    marks: Decimal,
    correct: list,
    negative_marks: Decimal = Decimal(0),
    options: list[dict] | None = None,
) -> QuizQuestion:
    quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
    if quiz.created_by_user_id != user_id:
        raise PermissionDeniedError(
            "You can only modify quizzes for your own courses.", code="NOT_COURSE_OWNER"
        )
    if quiz.status not in ("DRAFT", "DRAFT_CONFIGURED", "READY_TO_PUBLISH"):
        raise ConflictError(
            "Questions cannot be modified once quiz is published or scheduled.", code="QUIZ_ACTIVE"
        )

    current_count = quiz.questions.count()
    question = QuizQuestion.objects.create(
        quiz=quiz,
        question_text=question_text,
        question_type=question_type,
        marks=marks,
        negative_marks=negative_marks,
        correct=correct,
        position=current_count + 1,
    )
    if options:
        for opt in options:
            QuizOption.objects.create(
                question=question,
                option_id=opt["option_id"],
                option_text=opt["option_text"],
            )
    AuditLogEntry.objects.create(quiz_id=quiz.pk, event="QUESTION_ADDED", actor_user_id=user_id)
    return question
