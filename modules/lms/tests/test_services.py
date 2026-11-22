from datetime import timedelta
import pytest
from django.core.exceptions import PermissionDenied, ValidationError
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
    get_file_path,
    modify_released_grade,
    process_due_scheduled_releases,
    publish_assignment,
    release_grade,
    remove_course_membership,
    save_draft_grade,
    save_uploaded_file,
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
def test_course_services_and_projection_guardrail(course):
    # Direct student registration in LMS is prohibited
    with pytest.raises(PermissionDenied, match="Direct student registration in LMS is prohibited"):
        add_course_membership(course.id, 10, Role.STUDENT, is_projection=False)

    # Student membership via projection sync succeeds
    mem = add_course_membership(course.id, 10, Role.STUDENT, is_projection=True)
    assert mem.is_active is True

    # Staff assignment (TA) succeeds directly
    ta_mem = add_course_membership(course.id, 20, Role.TA)
    assert ta_mem.is_active is True

    # Test removing membership
    assert remove_course_membership(course.id, 10, Role.STUDENT) is True
    mem.refresh_from_db()
    assert mem.is_active is False

    # Test re-adding via projection reactivates
    mem2 = add_course_membership(course.id, 10, Role.STUDENT, is_projection=True)
    assert mem2.id == mem.id
    assert mem2.is_active is True


@pytest.mark.django_db
def test_content_services_and_ta_announcement_guardrail(course):
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

    # Instructor can create announcement
    ann = create_announcement(
        course_id=course.id,
        author_user_id=1,
        title="Lab 1 Posted",
        content="Check section 1 for lab instructions",
        author_role=Role.INSTRUCTOR,
    )
    assert ann.id is not None

    # TA announcement creation is gated (ISS-LMS-002)
    with pytest.raises(PermissionDenied, match="TA announcement creation is pending policy clarification"):
        create_announcement(
            course_id=course.id,
            author_user_id=2,
            title="TA Post",
            content="TA notes",
            author_role=Role.TA,
        )


@pytest.mark.django_db
def test_assignment_and_submission_guardrails(course):
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

    # On-time initial submission succeeds
    sub1 = submit_assignment(
        assignment_id=asg.id,
        student_user_id=101,
        submission_type=SubmissionType.FILE,
        file_storage_key="12/34/patch1.diff",
    )
    assert sub1.version == 1
    assert sub1.status == SubmissionStatus.SUBMITTED

    # Resubmission is gated pending policy clarification (ISS-LMS-005)
    with pytest.raises(ValidationError, match="Resubmission is currently gated pending policy clarification"):
        submit_assignment(
            assignment_id=asg.id,
            student_user_id=101,
            submission_type=SubmissionType.FILE,
            file_storage_key="12/34/patch2.diff",
        )

    # Late submission past due date is gated pending policy clarification (ISS-LMS-001)
    late_asg = create_assignment(
        course_id=course.id,
        author_user_id=1,
        title="Past Assignment",
        due_date=timezone.now() - timedelta(days=1),
    )
    with pytest.raises(ValidationError, match="Late submissions are currently gated pending policy clarification"):
        submit_assignment(
            assignment_id=late_asg.id,
            student_user_id=102,
            submission_type=SubmissionType.TEXT,
            content_text="late answer",
        )


@pytest.mark.django_db
def test_grading_services_and_post_release_guardrail(course):
    asg = create_assignment(course_id=course.id, author_user_id=1, title="Lab")
    sub = submit_assignment(assignment_id=asg.id, student_user_id=101)

    # Save draft grade (TA or Instructor)
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

    # Post-release modification is gated pending clarification (ISS-LMS-006)
    with pytest.raises(PermissionDenied, match="Post-release grade modification is pending policy clarification"):
        modify_released_grade(
            grade_id=released.id,
            modifier_user_id=1,
            new_points=95,
        )

    # Attempting to re-save draft or re-release on already-released grade is denied
    with pytest.raises(PermissionDenied, match="Grade has already been released"):
        save_draft_grade(
            submission_id=sub.id,
            assessor_user_id=1,
            assessor_role=Role.INSTRUCTOR,
            points_awarded=95,
        )


@pytest.mark.django_db
def test_storage_and_scheduled_release_services(course):
    # Storage key generation and upload
    content = b"Binary PDF content for LMS test"
    key = save_uploaded_file("document.pdf", content)
    assert key.endswith("_document.pdf")

    path = get_file_path(key)
    assert path.exists()
    assert path.read_bytes() == content

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
