from modules.quiz.models import QuizAttempt, ResponseEvaluation


def get_quiz_submissions_overview(quiz_id):
    attempts = QuizAttempt.objects.filter(quiz_id=quiz_id).select_related("result")
    total_attempts = attempts.count()
    submitted = attempts.filter(status="SUBMITTED").count()
    results = [a.result for a in attempts if hasattr(a, "result")]
    avg_score = sum(r.marks_obtained for r in results) / len(results) if results else 0
    return {
        "quiz_id": quiz_id,
        "total_attempts": total_attempts,
        "submitted_count": submitted,
        "average_score": float(avg_score),
    }


def get_pending_subjective_evaluations(quiz_id):
    return ResponseEvaluation.objects.filter(
        response__attempt__quiz_id=quiz_id,
        status__in=["PENDING", "AI_SUGGESTED"],
        response__question__question_type__in=["SHORT", "LONG"],
    ).select_related("response__question", "response__attempt")
