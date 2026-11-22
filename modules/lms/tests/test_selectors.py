"""Tests for LMS selectors and scoping isolation."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from modules.lms import selectors
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    GradeStatus,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
    SubmissionGrade,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace_setup():
    now = timezone.now()
    ws = CourseWorkspace.objects.create(
        course_id=201,
        course_code="CS401",
        title="Distributed Systems",
        syllabus="Consensus, Raft, Paxos",
    )

    # Memberships
    # Instructor: user 2001
    CourseMembership.objects.create(
        course_id=201,
        user_id=2001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA: user 2002
    CourseMembership.objects.create(
        course_id=201,
        user_id=2002,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
        can_grade=True,
        can_post_announcement=True,
    )
    # Student 1: user 1001
    CourseMembership.objects.create(
        course_id=201,
        user_id=1001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Student 2: user 1002
    CourseMembership.objects.create(
        course_id=201,
        user_id=1002,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer: user 3001
    CourseMembership.objects.create(
        course_id=201,
        user_id=3001,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )

    # Materials
    # Mat 1: Published, immediate
    mat_pub = CourseMaterial.objects.create(
        course_id=201,
        title="L1 Distributed Basics",
        material_type=MaterialType.LINK,
        external_url="https://example.com/l1",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=2001,
    )
    # Mat 2: Scheduled in future
    mat_sched = CourseMaterial.objects.create(
        course_id=201,
        title="L2 Raft Protocol",
        material_type=MaterialType.LINK,
        external_url="https://example.com/l2",
        status=MaterialStatus.SCHEDULED,
        release_date=now + timedelta(days=2),
        uploaded_by=2001,
    )
    # Mat 3: Draft
    mat_draft = CourseMaterial.objects.create(
        course_id=201,
        title="L3 Paxos Draft",
        material_type=MaterialType.NOTE,
        content_text="Draft notes",
        status=MaterialStatus.DRAFT,
        uploaded_by=2001,
    )

    # Assignments
    # Ass 1: Published
    ass_pub = Assignment.objects.create(
        course_id=201,
        title="Lab 1: RPC",
        instructions="Implement RPC",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        status=AssignmentStatus.PUBLISHED,
        created_by=2001,
    )
    # Ass 2: Draft
    ass_draft = Assignment.objects.create(
        course_id=201,
        title="Lab 2: Raft",
        instructions="Implement Raft",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=14),
        status=AssignmentStatus.DRAFT,
        created_by=2001,
    )

    # Submissions
    sub1 = AssignmentSubmission.objects.create(
        assignment=ass_pub,
        student_id=1001,
        submission_type=SubmissionType.TEXT,
        content_text="RPC code from Student 1",
    )
    sub2 = AssignmentSubmission.objects.create(
        assignment=ass_pub,
        student_id=1002,
        submission_type=SubmissionType.TEXT,
        content_text="RPC code from Student 2",
    )

    # Grades
    # Grade for Student 1: Published
    grade1 = SubmissionGrade.objects.create(
        submission=sub1,
        points_awarded=Decimal("92.00"),
        feedback_text="Good RPC implementation",
        status=GradeStatus.PUBLISHED,
        graded_by=2002,
        published_at=now,
        published_by=2001,
    )
    # Grade for Student 2: Draft (not published!)
    grade2 = SubmissionGrade.objects.create(
        submission=sub2,
        points_awarded=Decimal("85.00"),
        feedback_text="Draft grade under review",
        status=GradeStatus.DRAFT,
        graded_by=2002,
    )

    return {
        "workspace": ws,
        "mat_pub": mat_pub,
        "mat_sched": mat_sched,
        "mat_draft": mat_draft,
        "ass_pub": ass_pub,
        "ass_draft": ass_draft,
        "sub1": sub1,
        "sub2": sub2,
        "grade1": grade1,
        "grade2": grade2,
    }


def test_get_user_courses_queryset_br_lms_001(workspace_setup):
    """BR-LMS-001: Course-specific access control.
    Principal must be actively registered, assigned, or linked to access the course.
    """
    p_student = make_principal(user_id=1001)
    p_unrelated = make_principal(user_id=9999)

    qs_student = selectors.get_user_courses_queryset(p_student)
    assert qs_student.filter(course_id=201).exists()

    qs_unrelated = selectors.get_user_courses_queryset(p_unrelated)
    assert not qs_unrelated.filter(course_id=201).exists()


def test_student_enrollment_governs_access_br_lms_002(workspace_setup):
    """BR-LMS-002: Student registration data governs Student course access."""
    p_student = make_principal(user_id=1001)
    p_unrelated = make_principal(user_id=9999)

    assert selectors.is_student_enrolled(201, p_student) is True
    assert selectors.is_student_enrolled(201, p_unrelated) is False


def test_list_published_materials_visibility_br_lms_005(workspace_setup):
    """BR-LMS-005: Published material visibility.
    Materials are hidden from students until published and release date reached.
    """
    p_student = make_principal(user_id=1001)
    p_instructor = make_principal(user_id=2001, kind="faculty", active_role="faculty")

    # Student only sees published, released materials
    mats_student = selectors.list_published_materials(201, p_student)
    assert len(mats_student) == 1
    assert mats_student[0].title == "L1 Distributed Basics"

    # Instructor sees all materials (published, scheduled, draft)
    mats_inst = selectors.list_published_materials(201, p_instructor)
    assert len(mats_inst) == 3


def test_get_material_detail_failsafe(workspace_setup, monkeypatch):
    p_student = make_principal(user_id=1001)
    p_instructor = make_principal(user_id=2001, kind="faculty", active_role="faculty")

    mat_sched_id = workspace_setup["mat_sched"].id
    mat_draft_id = workspace_setup["mat_draft"].id
    mat_pub_id = workspace_setup["mat_pub"].id

    # Student cannot retrieve scheduled or draft material directly
    assert selectors.get_material_detail(mat_sched_id, p_student) is None
    assert selectors.get_material_detail(mat_draft_id, p_student) is None

    # Student can retrieve published material
    assert selectors.get_material_detail(mat_pub_id, p_student) is not None

    # Instructor can retrieve all
    assert selectors.get_material_detail(mat_sched_id, p_instructor) is not None
    assert selectors.get_material_detail(mat_draft_id, p_instructor) is not None


def test_assignment_scoping_br_lms_011(workspace_setup):
    """BR-LMS-011: Assignment release-date visibility.
    Assignments are hidden from students prior to release date and while unpublished.
    """
    p_student = make_principal(user_id=1001)
    p_instructor = make_principal(user_id=2001, kind="faculty", active_role="faculty")

    ass_pub_id = workspace_setup["ass_pub"].id
    ass_draft_id = workspace_setup["ass_draft"].id

    # Student sees only published assignment
    student_assignments = selectors.list_assignments(201, p_student)
    assert len(student_assignments) == 1
    assert student_assignments[0].id == ass_pub_id
    assert selectors.get_assignment_detail(ass_draft_id, p_student) is None

    # Instructor sees both
    inst_assignments = selectors.list_assignments(201, p_instructor)
    assert len(inst_assignments) == 2
    assert selectors.get_assignment_detail(ass_draft_id, p_instructor) is not None


def test_submission_scoping_student_isolation(workspace_setup):
    p_student1 = make_principal(user_id=1001)
    p_student2 = make_principal(user_id=1002)
    p_instructor = make_principal(user_id=2001, kind="faculty", active_role="faculty")
    p_ta = make_principal(user_id=2002)
    p_observer = make_principal(user_id=3001)

    ass_id = workspace_setup["ass_pub"].id
    sub1_id = workspace_setup["sub1"].id
    sub2_id = workspace_setup["sub2"].id

    # Student 1 sees only Student 1's submission
    s1_subs = selectors.list_course_submissions(ass_id, p_student1)
    assert len(s1_subs) == 1
    assert s1_subs[0].id == sub1_id
    assert selectors.get_submission_by_id(sub2_id, p_student1) is None

    # Student 2 sees only Student 2's submission
    s2_subs = selectors.list_course_submissions(ass_id, p_student2)
    assert len(s2_subs) == 1
    assert s2_subs[0].id == sub2_id
    assert selectors.get_submission_by_id(sub1_id, p_student2) is None

    # Instructor and TA see both submissions
    assert len(selectors.list_course_submissions(ass_id, p_instructor)) == 2
    assert len(selectors.list_course_submissions(ass_id, p_ta)) == 2

    # Observer sees ZERO submissions
    assert len(selectors.list_course_submissions(ass_id, p_observer)) == 0


def test_grade_scoping_student_and_observer(workspace_setup):
    p_student1 = make_principal(user_id=1001)
    p_student2 = make_principal(user_id=1002)
    p_instructor = make_principal(user_id=2001, kind="faculty", active_role="faculty")
    p_observer = make_principal(user_id=3001)

    ass_id = workspace_setup["ass_pub"].id
    sub1_id = workspace_setup["sub1"].id
    sub2_id = workspace_setup["sub2"].id

    # Student 1 has PUBLISHED grade -> can view
    g1 = selectors.get_submission_grade(sub1_id, p_student1)
    assert g1 is not None
    assert g1.points_awarded == Decimal("92.00")

    # Student 2 has DRAFT grade -> CANNOT view (returns None until published)
    g2 = selectors.get_submission_grade(sub2_id, p_student2)
    assert g2 is None

    # Student 1 cannot view Student 2's grade
    assert selectors.get_submission_grade(sub2_id, p_student1) is None

    # Instructor sees both draft and published grades
    inst_grades = selectors.list_course_grades(ass_id, p_instructor)
    assert len(inst_grades) == 2

    # Observer sees zero grades
    assert len(selectors.list_course_grades(ass_id, p_observer)) == 0


def test_course_home_details_roster_privacy(workspace_setup):
    p_student = make_principal(user_id=1001)
    p_observer = make_principal(user_id=3001)

    details = selectors.get_course_home_details(201, p_student)
    assert details is not None
    assert details["course_code"] == "CS401"
    # Staff roster is present (Instructor and TA)
    assert 2001 in details["instructors"]
    assert 2002 in details["teaching_assistants"]
    # Student roster is NEVER returned
    assert "students" not in details
    assert "student_roster" not in details

    # Observer gets workspace details too
    obs_details = selectors.get_course_home_details(201, p_observer)
    assert obs_details is not None
