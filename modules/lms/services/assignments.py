from modules.lms.domain.constants import ContentStatus, SubmissionType
from modules.lms.models import Assignment


def create_assignment(
    course_id: int,
    author_user_id: int,
    title: str,
    instructions: str = "",
    submission_type: str = SubmissionType.FILE,
    points_possible: int = 100,
    due_date=None,
    release_date=None,
    status: str = ContentStatus.DRAFT,
) -> Assignment:
    return Assignment.objects.create(
        course_id=course_id,
        author_user_id=author_user_id,
        title=title,
        instructions=instructions,
        submission_type=submission_type,
        points_possible=points_possible,
        due_date=due_date,
        release_date=release_date,
        status=status,
    )


def publish_assignment(assignment_id: int) -> Assignment:
    assignment = Assignment.objects.get(id=assignment_id)
    assignment.status = ContentStatus.PUBLISHED
    assignment.save(update_fields=["status", "updated_at"])
    return assignment
