from modules.quiz.models import QuizAttempt


def get_student_attempts(quiz_id, student_id):
    return QuizAttempt.objects.filter(quiz_id=quiz_id, student_id=student_id).order_by("created_at")


def get_active_attempt(quiz_id, student_id):
    return QuizAttempt.objects.filter(
        quiz_id=quiz_id, student_id=student_id, status="STARTED"
    ).first()
