# modules/quiz/services/quiz.py
from datetime import datetime
from typing import Optional
from django.db import transaction
from ..models import Quiz

def create_quiz(title: str, description: str, start_time: Optional[datetime], end_time: Optional[datetime]) -> Quiz:
    with transaction.atomic():
        quiz = Quiz.objects.create(title=title, description=description, start_time=start_time, end_time=end_time)
        return quiz

def update_quiz(quiz_id: int, title: str, description: str, start_time: Optional[datetime], end_time: Optional[datetime]) -> Quiz:
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
        quiz.title = title
        quiz.description = description
        quiz.start_time = start_time
        quiz.end_time = end_time
        quiz.save()
        return quiz

def delete_quiz(quiz_id: int) -> None:
    with transaction.atomic():
        quiz = Quiz.objects.select_for_update().get(pk=quiz_id)
        quiz.delete()

