import pytest
from django.utils import timezone

from modules.quiz.models import Quiz
from modules.quiz.services.quiz import create_quiz, update_quiz, delete_quiz


@pytest.mark.django_db
def test_create_quiz():
    start = timezone.now()
    end = start + timezone.timedelta(hours=1)

    quiz = create_quiz("Test Quiz", "Test description", start, end)

    assert quiz.title == "Test Quiz"
    assert quiz.description == "Test description"
    assert quiz.start_time == start
    assert quiz.end_time == end


@pytest.mark.django_db
def test_update_quiz():
    start = timezone.now()
    quiz = create_quiz("Test Quiz", "Test description", start, None)

    new_start = start + timezone.timedelta(hours=2)
    updated = update_quiz(quiz.id, "Updated Quiz", "Updated description", new_start, None)

    assert updated.title == "Updated Quiz"
    assert updated.description == "Updated description"
    assert updated.start_time == new_start
    assert updated.end_time is None


@pytest.mark.django_db
def test_delete_quiz():
    quiz = create_quiz("Test Quiz", "Test description", None, None)

    delete_quiz(quiz.id)

    with pytest.raises(Quiz.DoesNotExist):
        Quiz.objects.get(pk=quiz.id)
