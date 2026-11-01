import pytest

from modules.quiz.models import Quiz, Question
from modules.quiz.services.quiz import create_quiz
from modules.quiz.services.question import create_question, update_question, delete_question


@pytest.mark.django_db
def test_create_question():
    quiz = create_quiz("Test Quiz", "Test description", None, None)

    question = create_question(
        quiz.id, "mcq", "What is the capital of France?", "Paris"
    )

    assert question.quiz_id == quiz.id
    assert question.type == "mcq"
    assert question.text == "What is the capital of France?"
    assert question.answer == "Paris"


@pytest.mark.django_db
def test_update_question():
    quiz = create_quiz("Test Quiz", "Test description", None, None)
    question = create_question(quiz.id, "mcq", "Capital of France?", "Paris")

    updated = update_question(
        question.id, "true_false", "Is Paris the capital of France?", "True"
    )

    assert updated.type == "true_false"
    assert updated.text == "Is Paris the capital of France?"
    assert updated.answer == "True"


@pytest.mark.django_db
def test_delete_question():
    quiz = create_quiz("Test Quiz", "Test description", None, None)
    question = create_question(quiz.id, "mcq", "Capital of France?", "Paris")

    delete_question(question.id)

    with pytest.raises(Question.DoesNotExist):
        Question.objects.get(pk=question.id)
