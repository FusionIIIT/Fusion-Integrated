from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from modules.lms.api.serializers import AssignmentSerializer, SubmissionSerializer


def test_submission_status_distinguishes_on_time_from_late():
    due_at = datetime(2026, 11, 1, tzinfo=UTC)
    serializer = SubmissionSerializer()

    assert serializer.get_status(SimpleNamespace(
        submitted_at=due_at - timedelta(seconds=1),
        assignment=SimpleNamespace(due_at=due_at),
    )) == "submitted"
    assert serializer.get_status(SimpleNamespace(
        submitted_at=due_at,
        assignment=SimpleNamespace(due_at=due_at),
    )) == "late"


def test_assignment_download_url_targets_the_course_assignment_endpoint():
    assignment = SimpleNamespace(
        file=SimpleNamespace(name="f1a2.pdf"),
        course=SimpleNamespace(source_course_id="course 1"),
        pk=42,
    )

    assert AssignmentSerializer().get_download_url(assignment) == (
        "/api/v1/lms/courses/course%201/assignments/42/download")
