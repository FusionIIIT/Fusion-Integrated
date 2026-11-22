from django.db.models import QuerySet
from modules.lms.models import Submission


def get_student_submissions(assignment_id: int, student_user_id: int) -> QuerySet:
    """Returns submissions for an assignment and student ordered by -version."""
    return Submission.objects.filter(
        assignment_id=assignment_id,
        student_user_id=student_user_id,
    ).order_by("-version")


def get_latest_student_submission(assignment_id: int, student_user_id: int) -> Submission | None:
    """Returns the latest submission for an assignment and student."""
    return Submission.objects.filter(
        assignment_id=assignment_id,
        student_user_id=student_user_id,
    ).order_by("-version").first()


def get_grading_queue(assignment_id: int) -> QuerySet:
    """Returns all submissions for an assignment ordered by submission time."""
    return Submission.objects.filter(
        assignment_id=assignment_id,
    ).order_by("-submitted_at")
