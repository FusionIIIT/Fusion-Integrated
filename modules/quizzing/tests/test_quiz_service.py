from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from modules.quizzing.models import Question, QuestionType, QuizStatus, AttemptStatus
from modules.quizzing.services.quiz_service import QuizService


class QuizzingServiceTests(TestCase):
    def setUp(self):
        self.question = Question.objects.create(
            question_text="What is 2 + 2?", question_type=QuestionType.MCQ_SINGLE,
            options=[{"id": "A", "text": "4"}, {"id": "B", "text": "5"}],
            correct_answer={"choice": "A"}, default_marks=Decimal("2.0"),
        )
        now = timezone.now()
        self.quiz = QuizService.create_quiz(
            title="Math Quiz", course_code="CS101", created_by="faculty_1",
            start_time=now - timedelta(minutes=5), end_time=now + timedelta(hours=1),
            duration_minutes=20, question_ids=[str(self.question.id)],
        )

    def test_quiz_flow(self):
        QuizService.publish_quiz(str(self.quiz.id))
        attempt = QuizService.start_attempt(str(self.quiz.id), "student_1")
        self.assertEqual(attempt.status, AttemptStatus.IN_PROGRESS)

        QuizService.save_answer(str(attempt.id), str(self.question.id), {"choice": "A"})
        submitted = QuizService.submit_attempt(str(attempt.id))
        self.assertEqual(submitted.status, AttemptStatus.EVALUATED)
        self.assertEqual(submitted.total_score, Decimal("2.0"))
