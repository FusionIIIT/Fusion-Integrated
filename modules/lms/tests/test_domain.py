from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import pytest
from django.db import IntegrityError

from modules.lms.models import (
    Course,
    CourseMembership,
    CourseMaterial,
    CourseAnnouncement,
    Assignment,
    AssignmentSubmission,
    SubmissionGrade,
    GradeChangeAudit,
)
from modules.lms.services.grading import grade_submission, release_assignment_grades, release_single_grade
from modules.lms.services.releases import process_scheduled_releases


@pytest.mark.django_db
def test_course_creation_and_str():
    course = Course.objects.create(
        code="CS301",
        name="Operating Systems",
        academic_year=2026,
        semester="autumn",
        syllabus="Processes, threads, scheduling, memory management, file systems.",
        schedule="Mon/Wed 10:00 - 11:30 AM",
    )
    assert str(course) == "CS301 - Operating Systems"
    assert course.is_active is True
    assert course.allow_ta_announcements is True
    assert course.allow_ta_grading is True


@pytest.mark.django_db
def test_course_code_unique():
    Course.objects.create(code="CS201", name="Data Structures")
    with pytest.raises(IntegrityError):
        Course.objects.create(code="CS201", name="Duplicate")


@pytest.mark.django_db
def test_course_membership_and_unique_constraint():
    course = Course.objects.create(code="CS302", name="Database Systems")
    mem = CourseMembership.objects.create(
        course=course,
        user_id=101,
        role="student",
    )
    assert str(mem) == "User 101 as student in CS302"

    # Same user and role in same course should raise IntegrityError
    with pytest.raises(IntegrityError):
        CourseMembership.objects.create(
            course=course,
            user_id=101,
            role="student",
        )


@pytest.mark.django_db
def test_course_material_availability_br_lms_005_006():
    course = Course.objects.create(code="CS303", name="Networks")
    now = timezone.now()

    # Draft material -> not available
    draft_mat = CourseMaterial.objects.create(
        course=course,
        title="Draft Slides",
        material_type="file",
        status="draft",
        created_by_user_id=1,
    )
    assert draft_mat.is_available() is False

    # Scheduled material for future -> not available
    future_mat = CourseMaterial.objects.create(
        course=course,
        title="Future Chapter",
        material_type="note",
        content="Read chapter 4",
        status="scheduled",
        release_date=now + timedelta(days=2),
        created_by_user_id=1,
    )
    assert future_mat.is_available() is False

    # Published material without release_date or past release_date -> available
    pub_mat = CourseMaterial.objects.create(
        course=course,
        title="Syllabus PDF",
        material_type="link",
        link_url="https://example.edu/syllabus.pdf",
        status="published",
        created_by_user_id=1,
    )
    assert pub_mat.is_available() is True


@pytest.mark.django_db
def test_course_announcement_ordering_br_lms_008():
    course = Course.objects.create(code="CS304", name="Algorithms")
    a1 = CourseAnnouncement.objects.create(
        course=course,
        title="First Notice",
        content="Welcome to class.",
        posted_by_user_id=1,
        posted_by_role="faculty",
        posted_by_name="Prof. Sharma",
    )
    a2 = CourseAnnouncement.objects.create(
        course=course,
        title="Pinned Important Notice",
        content="Midterm exam date announced.",
        posted_by_user_id=1,
        posted_by_role="faculty",
        posted_by_name="Prof. Sharma",
        is_pinned=True,
    )

    announcements = list(CourseAnnouncement.objects.filter(course=course))
    assert announcements[0].id == a2.id  # Pinned first
    assert announcements[1].id == a1.id


@pytest.mark.django_db
def test_assignment_lifecycle_br_lms_009_010_011():
    course = Course.objects.create(code="CS305", name="Software Engineering")
    now = timezone.now()

    asgn = Assignment.objects.create(
        course=course,
        title="Lab 1: Git Workflow",
        instructions="Complete the branching assignment.",
        submission_type="link",
        points_possible=Decimal("100.00"),
        due_date=now + timedelta(days=7),
        status="draft",
        created_by_user_id=1,
    )
    assert asgn.status == "draft"
    assert asgn.is_available_to_students() is False

    # Publish with future release date
    asgn.status = "published"
    asgn.release_date = now + timedelta(days=1)
    asgn.save()
    assert asgn.is_available_to_students() is False

    # Release date in past
    asgn.release_date = now - timedelta(hours=1)
    asgn.save()
    assert asgn.is_available_to_students() is True


@pytest.mark.django_db
def test_assignment_submission_and_versioning_br_lms_012_013():
    course = Course.objects.create(code="CS306", name="AI")
    now = timezone.now()
    asgn = Assignment.objects.create(
        course=course,
        title="Project 1",
        instructions="Implement A*",
        submission_type="file",
        points_possible=Decimal("50.00"),
        due_date=now + timedelta(days=3),
        status="published",
        created_by_user_id=1,
    )

    sub1 = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=201,
        submission_type="file",
        file_name="solution_v1.zip",
        version=1,
        status="submitted",
    )
    assert sub1.status == "submitted"
    assert sub1.version == 1

    # Resubmission before due date creates version 2
    sub2 = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=201,
        submission_type="file",
        file_name="solution_v2.zip",
        version=2,
        status="submitted",
    )
    assert sub2.version == 2


@pytest.mark.django_db
def test_grading_and_post_release_audit_br_lms_015_016_017_019():
    course = Course.objects.create(code="CS307", name="Cloud Computing")
    asgn = Assignment.objects.create(
        course=course,
        title="Lab 2",
        instructions="Deploy container",
        submission_type="text",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=2),
        status="published",
        created_by_user_id=1,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=301,
        submission_type="text",
        text_response="https://mycontainer.app",
        status="submitted",
    )

    # Initial grading by TA -> creates draft grade (BR-LMS-016)
    grade = grade_submission(
        submission=sub,
        points=Decimal("88.50"),
        feedback="Good job on deployment.",
        grader_user_id=15,
        grader_role="ta",
        grader_name="Amit TA",
    )
    assert grade.status == "draft"
    assert grade.points_awarded == Decimal("88.50")
    assert grade.graded_by_role == "ta"

    # Faculty releases grade (BR-LMS-017)
    released_count = release_assignment_grades(asgn, faculty_user_id=1)
    assert released_count == 1
    grade.refresh_from_db()
    assert grade.status == "released"
    assert grade.released_by_user_id == 1

    # Faculty edits released grade -> triggers audit log (BR-LMS-019)
    grade_submission(
        submission=sub,
        points=Decimal("94.00"),
        feedback="Bonus points for SSL setup.",
        grader_user_id=1,
        grader_role="faculty",
        grader_name="Dr. Rao",
        change_reason="Re-evaluation after student query",
    )
    grade.refresh_from_db()
    assert grade.points_awarded == Decimal("94.00")

    # Check audit log
    audits = list(grade.audit_logs.all())
    assert len(audits) == 1
    audit = audits[0]
    assert audit.previous_points == Decimal("88.50")
    assert audit.new_points == Decimal("94.00")
    assert audit.changed_by_user_id == 1
    assert "Re-evaluation" in audit.change_reason


@pytest.mark.django_db
def test_scheduled_content_release_service_uc_lms_015():
    course = Course.objects.create(code="CS308", name="Cybersecurity")
    now = timezone.now()

    # Scheduled material in past
    mat = CourseMaterial.objects.create(
        course=course,
        title="Exam Guide",
        material_type="note",
        content="Exam instructions",
        status="scheduled",
        release_date=now - timedelta(minutes=5),
        created_by_user_id=1,
    )
    # Scheduled assignment in past
    asgn = Assignment.objects.create(
        course=course,
        title="Quiz 1",
        instructions="Answer questions",
        submission_type="text",
        points_possible=Decimal("20.00"),
        due_date=now + timedelta(days=1),
        status="scheduled",
        release_date=now - timedelta(minutes=5),
        created_by_user_id=1,
    )

    result = process_scheduled_releases()
    assert result["materials_released"] >= 1
    assert result["assignments_released"] >= 1

    mat.refresh_from_db()
    asgn.refresh_from_db()
    assert mat.status == "published"
    assert asgn.status == "published"
