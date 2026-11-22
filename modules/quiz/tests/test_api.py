"""API-level tests for the quiz module."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


def make_principal(user_id=1, perms=None):
    p = MagicMock()
    p.erp_user_id = user_id
    p.permissions = set(perms or [])
    p.has_perm = lambda perm: perm in p.permissions
    return p


@pytest.mark.django_db
class TestQuizCRUD:
    def test_create_quiz(self):
        from modules.quiz.services.quizzes import create_quiz

        principal = make_principal(user_id=10)
        quiz = create_quiz(
            principal=principal,
            title="Test Quiz",
            course="CS101",
            duration_minutes=30,
            max_marks=Decimal("100"),
        )
        assert quiz.id is not None
        assert quiz.status == "draft"
        assert quiz.created_by_user_id == 10

    def test_update_quiz_in_draft(self):
        from modules.quiz.services.quizzes import create_quiz, update_quiz

        principal = make_principal(user_id=10)
        quiz = create_quiz(
            principal=principal,
            title="Old Title",
            course="CS101",
            duration_minutes=30,
            max_marks=Decimal("100"),
        )
        updated = update_quiz(
            quiz_id=quiz.id,
            principal=principal,
            title="New Title",
        )
        assert updated.title == "New Title"

    def test_update_non_draft_quiz_raises(self):
        from modules.quiz.domain.errors import QuizNotEditable
        from modules.quiz.models import Quiz
        from modules.quiz.services.quizzes import create_quiz, update_quiz

        principal = make_principal(user_id=10)
        quiz = create_quiz(
            principal=principal,
            title="Quiz",
            course="CS101",
            duration_minutes=30,
            max_marks=Decimal("50"),
        )
        Quiz.objects.filter(pk=quiz.pk).update(status="available")

        with pytest.raises(QuizNotEditable):
            update_quiz(quiz_id=quiz.pk, principal=principal, title="X")

    def test_publish_quiz_no_start_at_becomes_available(self):
        from modules.quiz.services.quizzes import create_quiz, publish_quiz

        principal = make_principal(user_id=10)
        quiz = create_quiz(
            principal=principal,
            title="Quiz",
            course="CS101",
            duration_minutes=30,
            max_marks=Decimal("50"),
        )
        published = publish_quiz(quiz_id=quiz.pk, principal=principal)
        assert published.status == "available"


@pytest.mark.django_db
class TestAttemptFlow:
    def _make_quiz(self, principal):
        from modules.quiz.services.questions import add_question
        from modules.quiz.services.quizzes import create_quiz, publish_quiz

        quiz = create_quiz(
            principal=principal,
            title="Quiz",
            course="CS101",
            duration_minutes=60,
            max_marks=Decimal("10"),
        )
        add_question(
            quiz_id=quiz.pk,
            principal=principal,
            question_type="mcq",
            text="What is 1+1?",
            marks=Decimal("10"),
            options=[{"id": "A", "text": "2"}, {"id": "B", "text": "3"}],
            correct_answer="A",
        )
        publish_quiz(quiz_id=quiz.pk, principal=principal)
        return quiz

    def test_start_and_submit_attempt(self):
        from modules.quiz.services.attempts import start_attempt, submit_attempt

        principal = make_principal(user_id=20)
        quiz = self._make_quiz(make_principal(user_id=10))

        attempt = start_attempt(quiz_id=quiz.pk, principal=principal)
        assert attempt.status == "in_progress"
        assert attempt.user_id == 20

        submitted = submit_attempt(attempt_id=attempt.pk, principal=principal)
        # Should be evaluated (objective-only quiz)
        assert submitted.status in {"evaluated", "submitted"}

    def test_cannot_start_twice_when_limit_is_1(self):
        from modules.quiz.domain.errors import AttemptLimitExceeded
        from modules.quiz.services.attempts import start_attempt, submit_attempt

        principal = make_principal(user_id=21)
        quiz = self._make_quiz(make_principal(user_id=10))

        a1 = start_attempt(quiz_id=quiz.pk, principal=principal)
        submit_attempt(attempt_id=a1.pk, principal=principal)

        with pytest.raises(AttemptLimitExceeded):
            start_attempt(quiz_id=quiz.pk, principal=principal)

    def test_save_response_persists(self):
        from modules.quiz.models import AttemptResponse
        from modules.quiz.services.attempts import save_response, start_attempt

        principal = make_principal(user_id=22)
        quiz = self._make_quiz(make_principal(user_id=10))
        attempt = start_attempt(quiz_id=quiz.pk, principal=principal)

        q = quiz.questions.first()
        save_response(
            attempt_id=attempt.pk,
            question_id=q.pk,
            response="A",
            principal=principal,
        )
        ar = AttemptResponse.objects.get(attempt=attempt, question=q)
        assert ar.response == "A"

    def test_close_and_archive_quiz(self):
        from modules.quiz.services.quizzes import archive_quiz, close_quiz

        principal = make_principal(user_id=10)
        quiz = self._make_quiz(principal)
        quiz.refresh_from_db()
        assert quiz.status == "available"

        closed = close_quiz(quiz_id=quiz.pk, principal=principal)
        assert closed.status == "closed"

        archived = archive_quiz(quiz_id=quiz.pk, principal=principal)
        assert archived.status == "archived"

    def test_evaluate_subjective_and_release(self):
        from modules.quiz.contracts import get_student_quiz_performances
        from modules.quiz.models import AttemptResponse
        from modules.quiz.services.attempts import start_attempt, submit_attempt
        from modules.quiz.services.evaluation import (
            evaluate_subjective,
            release_attempt_result,
        )
        from modules.quiz.services.questions import add_question
        from modules.quiz.services.quizzes import create_quiz, publish_quiz

        prof = make_principal(user_id=10)
        student = make_principal(user_id=30)
        quiz = create_quiz(
            principal=prof,
            title="Mixed Quiz",
            course="CS101",
            duration_minutes=60,
            max_marks=Decimal("20"),
        )

        add_question(
            quiz_id=quiz.pk,
            principal=prof,
            question_type="mcq",
            text="What is 1+1?",
            marks=Decimal("10"),
            options=[{"id": "A", "text": "2"}, {"id": "B", "text": "3"}],
            correct_answer="A",
        )
        q_sub = add_question(
            quiz_id=quiz.pk,
            question_type="short",
            text="Explain Polymorphism",
            marks=Decimal("10"),
            principal=prof,
        )
        publish_quiz(quiz_id=quiz.pk, principal=prof)

        attempt = start_attempt(quiz_id=quiz.pk, principal=student)
        submit_attempt(attempt_id=attempt.pk, principal=student)
        attempt.refresh_from_db()
        assert attempt.status == "partially_evaluated"

        sub_resp = AttemptResponse.objects.get(attempt=attempt, question=q_sub)
        evaluated = evaluate_subjective(
            attempt_id=attempt.pk,
            principal=prof,
            response_evaluations=[
                {
                    "response_id": sub_resp.pk,
                    "marks_obtained": Decimal("9.0"),
                    "professor_feedback": "Excellent answer",
                }
            ],
        )
        assert evaluated.status == "evaluated"
        assert evaluated.score == Decimal("9.0")  # Objective was unanswered (0) + 9 from subjective

        released = release_attempt_result(attempt_id=attempt.pk, principal=prof)
        assert released.status == "released"

        # Verify contract returns this released performance
        perf = get_student_quiz_performances([student.erp_user_id])
        assert student.erp_user_id in perf
        assert len(perf[student.erp_user_id]) == 1
        assert perf[student.erp_user_id][0].quiz_title == quiz.title
        assert perf[student.erp_user_id][0].score == Decimal("9.0")
