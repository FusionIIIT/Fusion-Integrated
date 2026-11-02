from datetime import timedelta
import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from modules.lms.domain.constants import (
    ContentStatus,
    GradeAction,
    GradeStatus,
    MaterialKind,
    Role,
    ScheduleStatus,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.models import Course, GradeAuditLog, ScheduledRelease
from modules.lms.services import (
    add_course_membership,
    create_announcement,
    create_assignment,
    create_course,
    create_material,
    create_scheduled_release,
    create_section,
    generate_storage_key,
    modify_released_grade,
    process_due_scheduled_releases,
    publish_assignment,
    release_grade,
    remove_course_membership,
    save_draft_grade,
    submit_assignment,
    update_section,
)


@pytest.fixture
def course(db):
    return create_course(
        code="CS701",
        title="Advanced Operating Systems",
        academic_year=2026,
        semester=1,
    )


@pytest.mark.django_db
def test_course_services(course):
    mem = add_course_membership(course.id, 10, Role.STUDENT)
    assert mem.is_active is True

    # Test removing membership
    assert remove_course_membership(course.id, 10, Role.STUDENT) is True
    mem.refresh_from_db()
    assert mem.is_active is False

    # Test re-adding reactivates
    mem2 = add_course_membership(course.id, 10, Role.STUDENT)
    assert mem2.id == mem.id
    assert mem2.is_active is True


@pytest.mark.django_db
def test_content_services(course):
    sec = create_section(course.id, title="Module 1", order=1)
    assert sec.id is not None
    assert sec.title == "Module 1"

    updated_sec = update_section(sec.id, title="Module 1 - Architecture")
    assert updated_sec.title == "Module 1 - Architecture"

    mat = create_material(
        section_id=sec.id,
        title="Microkernels Paper",
        kind=MaterialKind.FILE,
        file_storage_key="ab/cd/test.pdf",
    )
    assert mat.id is not None
    assert mat.status == ContentStatus.DRAFT

    ann = create_announcement(
        course_id=course.id,
        author_user_id=1,
        title="Lab 1 Posted",
        content="Check section 1 for lab instructions",
    )
    assert ann.id is not None


@pytest.mark.django_db
def test_assignment_and_submission_services(course):
    due = timezone.now() + timedelta(days=7)
    asg = create_assignment(
        course_id=course.id,
        author_user_id=1,
        title="Kernel Patch 1",
        due_date=due,
    )
    assert asg.status == ContentStatus.DRAFT

    pub_asg = publish_assignment(asg.id)
    assert pub_asg.status == ContentStatus.PUBLISHED

    # On-time submission
    sub1 = submit_assignment(
        assignment_id=asg.id,
        student_user_id=101,
        submission_type=SubmissionType.FILE,
        file_storage_key="12/34/patch1.diff",
    )
    assert sub1.version == 1
    assert sub1.status == SubmissionStatus.SUBMITTED

    # Second submission (resubmission)
    sub2 = submit_assignment(
        assignment_id=asg.id,
        student_user_id=101,
        submission_type=SubmissionType.FILE,
        file_storage_key="12/34/patch2.diff",
    )
    assert sub2.version == 2

    # Late submission
    late_asg = create_assignment(
        course_id=course.id,
        author_user_id=1,
        title="Past Assignment",
        due_date=timezone.now() - timedelta(days=1),
    )
    sub_late = submit_assignment(
        assignment_id=late_asg.id,
        student_user_id=101,
        submission_type=SubmissionType.TEXT,
        content_text="late answer",
    )
    assert sub_late.status == SubmissionStatus.LATE


@pytest.mark.django_db
def test_grading_services(course):
    asg = create_assignment(course_id=course.id, author_user_id=1, title="Lab")
    sub = submit_assignment(assignment_id=asg.id, student_user_id=101)

    # Save draft grade
    draft = save_draft_grade(
        submission_id=sub.id,
        assessor_user_id=2,
        assessor_role=Role.TA,
        points_awarded=85,
        feedback_text="Good effort",
    )
    assert draft.status == GradeStatus.DRAFT
    assert draft.points_awarded == 85

    # TA cannot release grade
    with pytest.raises(PermissionDenied, match="Only instructors can release grades"):
        release_grade(
            submission_id=sub.id,
            assessor_user_id=2,
            assessor_role=Role.TA,
            points_awarded=88,
        )

    # Instructor releases grade
    released = release_grade(
        submission_id=sub.id,
        assessor_user_id=1,
        assessor_role=Role.INSTRUCTOR,
        points_awarded=90,
        feedback_text="Approved by professor",
        reason="Initial release",
    )
    assert released.status == GradeStatus.RELEASED
    assert released.points_awarded == 90
    assert released.released_by_user_id == 1

    # Audit log created for release
    logs = GradeAuditLog.objects.filter(grade=released)
    assert logs.count() == 1
    assert logs.first().action == GradeAction.RELEASED

    # Instructor modifies released grade
    updated = modify_released_grade(
        grade_id=released.id,
        modifier_user_id=1,
        new_points=95,
        new_feedback="Re-evaluated question 3",
        reason="Student regrade request approved",
    )
    assert updated.points_awarded == 95

    # Second audit log created
    assert GradeAuditLog.objects.filter(grade=released).count() == 2


@pytest.mark.django_db
def test_storage_and_scheduled_release_services(course):
    # Storage key generation
    content = b"Binary PDF content for LMS test"
    key = generate_storage_key("document.pdf", content)
    parts = key.split("/")
    assert len(parts) == 3
    assert len(parts[0]) == 2
    assert len(parts[1]) == 2
    assert parts[2].endswith("_document.pdf")

    # Scheduled release service
    sec = create_section(course.id, title="Unit 1")
    mat = create_material(
        section_id=sec.id,
        title="Scheduled Reading",
        status=ContentStatus.DRAFT,
    )
    past_due = timezone.now() - timedelta(minutes=5)
    rel = create_scheduled_release(
        scheduled_date=past_due,
        material=mat,
    )
    assert rel.status == ScheduleStatus.PENDING

    # Process due scheduled releases
    count = process_due_scheduled_releases(batch_size=10)
    assert count == 1

    rel.refresh_from_db()
    assert rel.status == ScheduleStatus.COMPLETED
    assert rel.processed_at is not None

    mat.refresh_from_db()
    assert mat.status == ContentStatus.PUBLISHED
