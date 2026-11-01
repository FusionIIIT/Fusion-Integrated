"""Workflow tests adhering directly to LMS Workflow Specifications v1.0."""
from decimal import Decimal
from datetime import timedelta
import pytest
from django.utils import timezone

from modules.lms.models import (
    Course,
    CourseMaterial,
    Assignment,
    AssignmentSubmission,
    SubmissionGrade,
)
from modules.lms.services.grading import grade_submission, release_assignment_grades
from modules.lms.services.releases import process_scheduled_releases


@pytest.mark.django_db
def test_bw_lms_01_scheduled_course_material_release():
    """BW-LMS-01: Scheduled Course Material Release.

    Step 1: Faculty schedules material with future release date (State -> Material Scheduled).
    Step 2: Time reached, System releases scheduled content (State -> Material Published/Available).
    """
    course = Course.objects.create(code="BW101", name="Testing BW 01")
    now = timezone.now()

    # Step 1: Faculty schedules material
    mat = CourseMaterial.objects.create(
        course=course,
        title="Lecture 5 Notes",
        material_type="note",
        content="Concurrency and Semaphores",
        status="scheduled",
        release_date=now - timedelta(seconds=1),  # Simulated reached release time
        created_by_user_id=1,
    )
    assert mat.status == "scheduled"
    assert mat.is_available() is False

    # Step 2: System processes scheduled release
    res = process_scheduled_releases()
    assert res["materials_released"] >= 1

    mat.refresh_from_db()
    assert mat.status == "published"
    assert mat.is_available() is True


@pytest.mark.django_db
def test_bw_lms_02_assignment_immediate_release_and_on_time_submission():
    """BW-LMS-02: Assignment Immediate Release and On-Time Submission.

    Step 1: Faculty creates assignment (State -> Assignment Draft).
    Step 2: Faculty publishes assignment with immediate release (State -> Available for Submission).
    Step 3: Student submits work before due date (State -> Student Submission Recorded).
    """
    course = Course.objects.create(code="BW102", name="Testing BW 02")
    now = timezone.now()

    # Step 1: Assignment created in Draft state
    asgn = Assignment.objects.create(
        course=course,
        title="Essay 1",
        instructions="Analyze thread scheduling algorithms.",
        submission_type="text",
        points_possible=Decimal("100.00"),
        due_date=now + timedelta(days=5),
        status="draft",
        created_by_user_id=1,
    )
    assert asgn.status == "draft"
    assert asgn.is_available_to_students() is False

    # Step 2: Immediate publication
    asgn.status = "published"
    asgn.release_date = None
    asgn.save()
    assert asgn.status == "published"
    assert asgn.is_available_to_students() is True

    # Step 3: On-time student submission
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=501,
        submission_type="text",
        text_response="My comparative essay on CFS vs Round Robin.",
        status="submitted",
    )
    assert sub.status == "submitted"
    assert sub.assignment_id == asgn.id


@pytest.mark.django_db
def test_bw_lms_03_assignment_scheduled_release_and_on_time_submission():
    """BW-LMS-03: Assignment Scheduled Release and On-Time Submission.

    Step 1: Faculty creates assignment (State -> Assignment Draft).
    Step 2: Faculty publishes assignment with future release (State -> Published / Scheduled for Release).
    Step 3: Release time reached, System releases assignment (State -> Available for Submission).
    Step 4: Student submits work before due date (State -> Student Submission Recorded).
    """
    course = Course.objects.create(code="BW103", name="Testing BW 03")
    now = timezone.now()

    # Step 1: Draft
    asgn = Assignment.objects.create(
        course=course,
        title="Midterm Project",
        instructions="Complete the project specification.",
        submission_type="file",
        points_possible=Decimal("100.00"),
        due_date=now + timedelta(days=10),
        status="draft",
        created_by_user_id=1,
    )
    assert asgn.status == "draft"

    # Step 2: Scheduled for future release
    asgn.status = "scheduled"
    asgn.release_date = now - timedelta(seconds=1)  # Release time reached
    asgn.save()
    assert asgn.status == "scheduled"
    assert asgn.is_available_to_students() is False

    # Step 3: Event-triggered processor releases assignment
    process_scheduled_releases()
    asgn.refresh_from_db()
    assert asgn.status == "published"
    assert asgn.is_available_to_students() is True

    # Step 4: On-time student submission
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=601,
        submission_type="file",
        file_name="project_midterm.tar.gz",
        status="submitted",
    )
    assert sub.status == "submitted"


@pytest.mark.django_db
def test_bw_lms_04_faculty_grading_and_grade_release():
    """BW-LMS-04: Faculty Grading and Grade Release.

    Step 1: Faculty enters points and feedback (State -> Grade Draft).
    Step 2: Faculty releases grades and feedback (State -> Grade Released / Student Visible).
    """
    course = Course.objects.create(code="BW104", name="Testing BW 04")
    asgn = Assignment.objects.create(
        course=course,
        title="Homework 1",
        instructions="Solve problems 1-5",
        submission_type="text",
        points_possible=Decimal("50.00"),
        due_date=timezone.now() + timedelta(days=1),
        status="published",
        created_by_user_id=1,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=701,
        submission_type="text",
        text_response="Solutions: 1. A, 2. B, 3. C",
        status="submitted",
    )

    # Step 1: Faculty grades submission -> Draft
    grade = grade_submission(
        submission=sub,
        points=Decimal("46.00"),
        feedback="Great work overall.",
        grader_user_id=1,
        grader_role="faculty",
        grader_name="Dr. Smith",
    )
    assert grade.status == "draft"

    # Step 2: Faculty releases grade -> Released
    release_assignment_grades(asgn, faculty_user_id=1)
    grade.refresh_from_db()
    assert grade.status == "released"
    assert grade.released_by_user_id == 1


@pytest.mark.django_db
def test_bw_lms_05_ta_grading_and_faculty_grade_release():
    """BW-LMS-05: TA Grading and Faculty Grade Release.

    Step 1: TA enters points and feedback (State -> Grade Draft attributed to TA).
    Step 2: Faculty releases grade (State -> Grade Released / Student Visible).
    """
    course = Course.objects.create(code="BW105", name="Testing BW 05")
    asgn = Assignment.objects.create(
        course=course,
        title="Lab 3",
        instructions="Socket programming",
        submission_type="file",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=2),
        status="published",
        created_by_user_id=1,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=801,
        submission_type="file",
        file_name="server.c",
        status="submitted",
    )

    # Step 1: TA grades submission -> Draft with TA attribution
    grade = grade_submission(
        submission=sub,
        points=Decimal("92.00"),
        feedback="Good implementation of TCP handshake.",
        grader_user_id=25,
        grader_role="ta",
        grader_name="Rohan TA",
    )
    assert grade.status == "draft"
    assert grade.graded_by_role == "ta"
    assert grade.graded_by_user_id == 25

    # Step 2: Faculty releases grade
    release_assignment_grades(asgn, faculty_user_id=1)
    grade.refresh_from_db()
    assert grade.status == "released"
    assert grade.released_by_user_id == 1
    assert grade.graded_by_role == "ta"  # Attribution to TA preserved!


@pytest.mark.django_db
def test_composite_workflows_cw_lms_01_and_02():
    """CW-LMS-01 & CW-LMS-02: End-to-end integration test."""
    course = Course.objects.create(code="CW201", name="Composite Workflow Course")
    now = timezone.now()

    # CW-LMS-01: Create, schedule, auto-release, and submit
    asgn = Assignment.objects.create(
        course=course,
        title="Capstone Project",
        instructions="Full system design",
        submission_type="link",
        points_possible=Decimal("100.00"),
        due_date=now + timedelta(days=30),
        status="scheduled",
        release_date=now - timedelta(minutes=1),
        created_by_user_id=1,
    )
    process_scheduled_releases()
    asgn.refresh_from_db()
    assert asgn.status == "published"

    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=901,
        submission_type="link",
        link_url="https://github.com/student/capstone",
        status="submitted",
    )
    assert sub.status == "submitted"

    # CW-LMS-02: Grade and Release
    grade = grade_submission(
        submission=sub,
        points=Decimal("98.00"),
        feedback="Outstanding architecture and documentation.",
        grader_user_id=1,
        grader_role="faculty",
        grader_name="Prof. Verma",
    )
    assert grade.status == "draft"

    release_assignment_grades(asgn, faculty_user_id=1)
    grade.refresh_from_db()
    assert grade.status == "released"
