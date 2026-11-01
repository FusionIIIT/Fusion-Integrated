# modules/quiz/services/question.py
from typing import Optional
from django.db import transaction
from ..models import Question

def create_question(quiz_id: int, type: str, text: str, answer: Optional[str]) -> Question:
    with transaction.atomic():
        question = Question.objects.create(quiz_id=quiz_id, type=type, text=text, answer=answer)
        return question

def update_question(question_id: int, type: str, text: str, answer: Optional[str]) -> Question:
    with transaction.atomic():
        question = Question.objects.select_for_update().get(pk=question_id)
        question.type = type
        question.text = text
        question.answer = answer
        question.save()
        return question

def delete_question(question_id: int) -> None:
    with transaction.atomic():
        question = Question.objects.select_for_update().get(pk=question_id)
        question.delete()

