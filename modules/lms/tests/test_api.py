from decimal import Decimal
from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
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

pytestmark = pytest.mark.django_db


def _login(stub_iam, user_id: int, kind="student", roles=("student",), permissions=()):
    session = make_session(
        user_id=user_id,
        kind=kind,
        roles=roles,
        permissions=permissions,
        modules=("lms",),
    )
    stub_iam(session)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
    return c


def test_course_list_and_create(stub_iam):
    client = _login(
        stub_iam,
        user_id=1,
        kind="faculty",
        roles=("faculty",),
        permissions=("lms.course.view", "lms.course.manage"),
    )

    # Create a course
    resp = client.post(
        "/api/v1/lms/courses/",
        {
            "code": "CS401",
            "name": "Distributed Systems",
            "academic_year": 2026,
            "semester": "autumn",
            "syllabus": "Raft, Paxos, consensus algorithms.",
            "schedule": "Tue/Thu 2-3:30 PM",
        },
        format="json",
    )
    assert resp.status_code == 201
    course_id = resp.json()["id"]

    # Verify CourseMembership was created for creator
    mem = CourseMembership.objects.filter(course_id=course_id, user_id=1).first()
    assert mem is not None
    assert mem.role == "faculty"
    assert mem.is_primary_instructor is True

    # List courses
    list_resp = client.get("/api/v1/lms/courses/")
    assert list_resp.status_code == 200
    results = list_resp.json()
    assert any(c["code"] == "CS401" for c in results)


def test_course_detail_and_access_control_br_lms_001(stub_iam):
    course = Course.objects.create(code="CS402", name="Compilers")
    CourseMembership.objects.create(course=course, user_id=10, role="faculty")
    CourseMembership.objects.create(course=course, user_id=20, role="student")

    # Linked student can access course workspace (BR-LMS-001)
    student_client = _login(stub_iam, user_id=20, kind="student", permissions=("lms.course.view",))
    resp = student_client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code == 200
    assert resp.json()["code"] == "CS402"
    assert resp.json()["my_role"] == "student"

    # Unlinked user cannot access course workspace (BR-LMS-001)
    unlinked_client = _login(stub_iam, user_id=999, kind="student", permissions=("lms.course.view",))
    unlinked_resp = unlinked_client.get(f"/api/v1/lms/courses/{course.id}/")
    assert unlinked_resp.status_code in (403, 404)


def test_faculty_edits_course_details_cfr_lms_002(stub_iam):
    course = Course.objects.create(code="CS403", name="AI Security")
    CourseMembership.objects.create(course=course, user_id=1, role="faculty")
    CourseMembership.objects.create(course=course, user_id=2, role="student")

    faculty_client = _login(stub_iam, user_id=1, kind="faculty", permissions=("lms.course.manage",))
    resp = faculty_client.patch(
        f"/api/v1/lms/courses/{course.id}/",
        {"syllabus": "Adversarial ML and robustness."},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["syllabus"] == "Adversarial ML and robustness."

    # Student cannot edit course details
    student_client = _login(stub_iam, user_id=2, kind="student", permissions=("lms.course.view",))
    err_resp = student_client.patch(
        f"/api/v1/lms/courses/{course.id}/",
        {"syllabus": "Hacked syllabus"},
        format="json",
    )
    assert err_resp.status_code == 403


def test_course_materials_visibility_br_lms_004_005_006(stub_iam):
    course = Course.objects.create(code="CS404", name="Computer Graphics")
    CourseMembership.objects.create(course=course, user_id=1, role="faculty")
    CourseMembership.objects.create(course=course, user_id=2, role="ta")
    CourseMembership.objects.create(course=course, user_id=3, role="student")

    now = timezone.now()

    # Faculty adds published material
    faculty_client = _login(stub_iam, user_id=1, kind="faculty", permissions=("lms.material.manage",))
    m1 = faculty_client.post(
        f"/api/v1/lms/courses/{course.id}/materials/",
        {
            "title": "Week 1: Ray Tracing",
            "material_type": "note",
            "section": "Week 1",
            "content": "Introduction to ray tracing math.",
            "status": "published",
        },
        format="json",
    )
    assert m1.status_code == 201

    # Faculty adds future scheduled material
    m2 = faculty_client.post(
        f"/api/v1/lms/courses/{course.id}/materials/",
        {
            "title": "Week 2: Shaders",
            "material_type": "link",
            "section": "Week 2",
            "link_url": "https://example.com/shaders",
            "release_date": (now + timedelta(days=5)).isoformat(),
            "status": "published",
        },
        format="json",
    )
    assert m2.status_code == 201

    # TA cannot create material (BR-LMS-004)
    ta_client = _login(stub_iam, user_id=2, kind="staff", permissions=("lms.material.view",))
    ta_create_resp = ta_client.post(
        f"/api/v1/lms/courses/{course.id}/materials/",
        {"title": "TA notes", "material_type": "note", "content": "test"},
        format="json",
    )
    assert ta_create_resp.status_code == 403

    # Student only sees released material (BR-LMS-005, BR-LMS-006)
    student_client = _login(stub_iam, user_id=3, kind="student", permissions=("lms.material.view",))
    s_mats = student_client.get(f"/api/v1/lms/courses/{course.id}/materials/").json()
    assert len(s_mats) == 1
    assert s_mats[0]["title"] == "Week 1: Ray Tracing"


def test_announcements_posting_authority_br_lms_007_008(stub_iam):
    course = Course.objects.create(code="CS405", name="NLP", allow_ta_announcements=False)
    CourseMembership.objects.create(course=course, user_id=1, role="faculty")
    CourseMembership.objects.create(course=course, user_id=2, role="ta")
    CourseMembership.objects.create(course=course, user_id=3, role="student")

    # Faculty posts announcement
    faculty_client = _login(stub_iam, user_id=1, kind="faculty", permissions=("lms.announcement.post",))
    f_resp = faculty_client.post(
        f"/api/v1/lms/courses/{course.id}/announcements/",
        {"title": "Welcome", "content": "Welcome to NLP course."},
        format="json",
    )
    assert f_resp.status_code == 201

    # TA posting denied because allow_ta_announcements is False for this course (BR-LMS-007)
    ta_client = _login(stub_iam, user_id=2, kind="staff", permissions=("lms.announcement.post",))
    ta_resp = ta_client.post(
        f"/api/v1/lms/courses/{course.id}/announcements/",
        {"title": "TA Office Hours", "content": "Fridays 3 PM."},
        format="json",
    )
    assert ta_resp.status_code == 403

    # Enable TA announcements for course
    course.allow_ta_announcements = True
    course.save()

    ta_client = _login(stub_iam, user_id=2, kind="staff", permissions=("lms.announcement.post",))
    ta_ok_resp = ta_client.post(
        f"/api/v1/lms/courses/{course.id}/announcements/",
        {"title": "TA Office Hours", "content": "Fridays 3 PM."},
        format="json",
    )
    assert ta_ok_resp.status_code == 201

    # Student views announcements
    student_client = _login(stub_iam, user_id=3, kind="student", permissions=("lms.announcement.view",))
    view_resp = student_client.get(f"/api/v1/lms/courses/{course.id}/announcements/")
    assert view_resp.status_code == 200
    assert len(view_resp.json()) == 2


def test_assignment_authoring_and_submission_workflow(stub_iam):
    course = Course.objects.create(code="CS406", name="Database Implementation")
    CourseMembership.objects.create(course=course, user_id=1, role="faculty")
    CourseMembership.objects.create(course=course, user_id=101, role="student")

    now = timezone.now()

    # Create assignment (Draft by default, BR-LMS-010)
    faculty_client = _login(stub_iam, user_id=1, kind="faculty", permissions=("lms.assignment.manage",))
    asgn_resp = faculty_client.post(
        f"/api/v1/lms/courses/{course.id}/assignments/",
        {
            "title": "B-Tree Indexing",
            "instructions": "Implement node splitting.",
            "submission_type": "file",
            "points_possible": 100,
            "due_date": (now + timedelta(days=7)).isoformat(),
        },
        format="json",
    )
    assert asgn_resp.status_code == 201
    asgn_id = asgn_resp.json()["id"]
    assert asgn_resp.json()["status"] == "draft"

    # Student cannot see draft assignment (BR-LMS-010)
    student_client = _login(stub_iam, user_id=101, kind="student", permissions=("lms.assignment.view", "lms.submission.create"))
    student_list = student_client.get(f"/api/v1/lms/courses/{course.id}/assignments/").json()
    assert len(student_list) == 0

    # Faculty publishes assignment (BR-LMS-011)
    faculty_client = _login(stub_iam, user_id=1, kind="faculty", permissions=("lms.assignment.manage",))
    pub_resp = faculty_client.post(f"/api/v1/lms/assignments/{asgn_id}/publish/")
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "published"

    # Now student sees assignment
    student_client = _login(stub_iam, user_id=101, kind="student", permissions=("lms.assignment.view", "lms.submission.create"))
    student_list = student_client.get(f"/api/v1/lms/courses/{course.id}/assignments/").json()
    assert len(student_list) == 1

    # Student submits work with invalid type (text instead of file) -> rejected (BR-LMS-012)
    wrong_type_resp = student_client.post(
        f"/api/v1/lms/assignments/{asgn_id}/submit/",
        {"submission_type": "text", "text_response": "Here is code"},
        format="json",
    )
    assert wrong_type_resp.status_code == 400

    # Student submits work with configured type (file) -> accepted (BR-LMS-013)
    ok_sub_resp = student_client.post(
        f"/api/v1/lms/assignments/{asgn_id}/submit/",
        {"submission_type": "file", "file_name": "btree.py"},
        format="json",
    )
    assert ok_sub_resp.status_code == 201
    assert ok_sub_resp.json()["status"] == "submitted"


def test_grading_and_grade_release_api(stub_iam):
    course = Course.objects.create(code="CS407", name="Robotics")
    CourseMembership.objects.create(course=course, user_id=1, role="faculty")
    CourseMembership.objects.create(course=course, user_id=5, role="ta")
    CourseMembership.objects.create(course=course, user_id=201, role="student")

    asgn = Assignment.objects.create(
        course=course,
        title="Kinematics",
        instructions="Inverse kinematics derivation",
        submission_type="text",
        points_possible=Decimal("100.00"),
        due_date=timezone.now() + timedelta(days=2),
        status="published",
        created_by_user_id=1,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=201,
        submission_type="text",
        text_response="DH parameters attached.",
        status="submitted",
    )

    # TA grades submission -> Draft (BR-LMS-016)
    ta_client = _login(stub_iam, user_id=5, kind="staff", permissions=("lms.grade.manage",))
    grade_resp = ta_client.post(
        f"/api/v1/lms/submissions/{sub.id}/grade/",
        {"points_awarded": 91, "feedback": "Well-derived equations."},
        format="json",
    )
    assert grade_resp.status_code == 200
    assert grade_resp.json()["status"] == "draft"
    assert grade_resp.json()["graded_by_role"] == "ta"

    # Student cannot see draft grade (BR-LMS-016)
    student_client = _login(stub_iam, user_id=201, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    my_grades = student_client.get("/api/v1/lms/grades/my-grades/").json()
    assert len(my_grades) == 0

    # TA cannot release grades (BR-LMS-017)
    ta_client = _login(stub_iam, user_id=5, kind="staff", permissions=("lms.grade.manage",))
    ta_release = ta_client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert ta_release.status_code == 403

    # Faculty releases grades (BR-LMS-017)
    faculty_client = _login(stub_iam, user_id=1, kind="faculty", permissions=("lms.grade.manage", "lms.grade.release"))
    f_release = faculty_client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert f_release.status_code == 200
    assert f_release.json()["released_count"] == 1

    # Student now sees released grade (BR-LMS-018)
    student_client = _login(stub_iam, user_id=201, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    my_grades = student_client.get("/api/v1/lms/grades/my-grades/").json()
    assert len(my_grades) == 1
    assert Decimal(str(my_grades[0]["points_awarded"])) == Decimal("91.00")


def test_observer_restrictions_br_lms_003(stub_iam):
    """Observer has read-only access and cannot access student submissions or grades."""
    course = Course.objects.create(code="CS408", name="Observability Course")
    CourseMembership.objects.create(course=course, user_id=1, role="faculty")
    CourseMembership.objects.create(course=course, user_id=99, role="observer")

    asgn = Assignment.objects.create(
        course=course,
        title="Obs Assignment",
        instructions="Instructions",
        submission_type="text",
        points_possible=10,
        due_date=timezone.now() + timedelta(days=1),
        status="published",
        created_by_user_id=1,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asgn,
        student_user_id=101,
        submission_type="text",
        text_response="Work",
    )

    observer_client = _login(stub_iam, user_id=99, kind="staff", permissions=("lms.course.view",))

    # Observer can view course details
    c_resp = observer_client.get(f"/api/v1/lms/courses/{course.id}/")
    assert c_resp.status_code == 200

    # Observer cannot view student submissions (BR-LMS-003)
    sub_resp = observer_client.get(f"/api/v1/lms/assignments/{asgn.id}/submissions/")
    assert sub_resp.status_code == 403

    # Observer cannot submit work
    submit_resp = observer_client.post(
        f"/api/v1/lms/assignments/{asgn.id}/submit/",
        {"submission_type": "text", "text_response": "Observer submit"},
        format="json",
    )
    assert submit_resp.status_code == 403
