from django.core.exceptions import ValidationError
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

    # Gating for ISS-LMS-005 (Resubmission policy)
    if Submission.objects.filter(
        assignment_id=assignment_id,
        student_user_id=student_user_id,
    ).exists():
        raise ValidationError(
            "Resubmission is currently gated pending policy clarification (ISS-LMS-005)."
        )

    # Gating for ISS-LMS-001 (Late-submission policy)
    now = timezone.now()
    if assignment.due_date and now > assignment.due_date:
        raise ValidationError(
            "Late submissions are currently gated pending policy clarification (ISS-LMS-001)."
        )

    return Submission.objects.create(
        assignment=assignment,
        student_user_id=student_user_id,
        version=1,
        submission_type=submission_type,
        content_text=content_text,
        file_storage_key=file_storage_key,
        link_url=link_url,
        submitted_at=now,
        status=SubmissionStatus.SUBMITTED,
    )
