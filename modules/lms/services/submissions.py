from django.utils import timezone
from modules.lms.domain.constants import SubmissionStatus, SubmissionType
from modules.lms.models import Assignment, Submission


def submit_assignment(
    assignment_id: int,
    student_user_id: int,
    submission_type: str = SubmissionType.FILE,
    content_text: str = "",
    file_storage_key: str = "",
    link_url: str = "",
) -> Submission:
    assignment = Assignment.objects.get(id=assignment_id)
    latest = (
        Submission.objects.filter(
            assignment_id=assignment_id,
            student_user_id=student_user_id,
        )
        .order_by("-version")
        .first()
    )
    next_version = (latest.version + 1) if latest else 1
    now = timezone.now()
    status = (
        SubmissionStatus.LATE
        if (assignment.due_date and now > assignment.due_date)
        else SubmissionStatus.SUBMITTED
    )
    return Submission.objects.create(
        assignment=assignment,
        student_user_id=student_user_id,
        version=next_version,
        submission_type=submission_type,
        content_text=content_text,
        file_storage_key=file_storage_key,
        link_url=link_url,
        submitted_at=now,
        status=status,
    )
