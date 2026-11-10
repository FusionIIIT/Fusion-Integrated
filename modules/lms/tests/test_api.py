"""API tests for LMS Course Workspace endpoints."""
from datetime import UTC, datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    MaterialStatus,
    MaterialType,
    SubmissionType,
)
from modules.lms.models import (
    Course,
    CourseAssignment,
    CourseMaterial,
    CourseMembership,
    CourseSubmission,
)

pytestmark = pytest.mark.django_db

MODULE = "lms"
VIEW = "lms.course.view"
MANAGE = "lms.course.manage"
MAT_VIEW = "lms.material.view"
MAT_MANAGE = "lms.material.manage"
ANN_VIEW = "lms.announcement.view"
ANN_MANAGE = "lms.announcement.manage"
ASG_VIEW = "lms.assignment.view"
ASG_MANAGE = "lms.assignment.manage"
DL_VIEW = "lms.deadline.view"
DL_MANAGE = "lms.deadline.manage"
SUB_VIEW = "lms.submission.view"
SUB_SUBMIT = "lms.submission.submit"
GRD_VIEW = "lms.grade.view"
GRD_GRADE = "lms.grade.grade"
URL_COURSES = "/api/v1/lms/courses"



def api_client(stub_iam, *, user_id=1001, role="student", permissions=(VIEW,), modules=(MODULE,)):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=role,
            roles=(role,),
            active_role=role,
            modules=modules,
            permissions=permissions,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-test-token")
    return c


def test_courses_list_returns_only_authorized_memberships(stub_iam):
    c1 = Course.objects.create(code="CS101", title="Intro to CS", schedule="Mon/Wed 9am")
    c2 = Course.objects.create(code="CS102", title="Data Structures", schedule="Tue/Thu 11am")
    Course.objects.create(code="CS999", title="Unrelated Course")

    CourseMembership.objects.create(course=c1, user_id=1001, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=c2, user_id=1001, role=CourseRole.STUDENT)

    client = api_client(stub_iam, user_id=1001, role="student", permissions=(VIEW,))

    resp = client.get(URL_COURSES)
    assert resp.status_code == 200
    results = resp.json()["results"]
    codes = [r["code"] for r in results]
    assert "CS101" in codes
    assert "CS102" in codes
    assert "CS999" not in codes


def test_course_workspace_details_for_student(stub_iam):
    stub_iam(
        make_session(user_id=1001, kind="student", roles=("student",), active_role="student", modules=(MODULE,), permissions=(VIEW,)),
        users={
            9001: UserRef(user_id=9001, username="faculty1", display_name="Dr. Smith", kind="faculty", department="CSE", email="smith@test.ac.in"),
            2001: UserRef(user_id=2001, username="ta1", display_name="John TA", kind="student", department="CSE", email="ta@test.ac.in"),
        },
    )

    c = Course.objects.create(
        code="CS301",
        title="Database Systems",
        description="Comprehensive DBMS course",
        syllabus="Week 1: SQL, Week 2: B-Trees",
        schedule="Mon/Wed 10:00-11:30",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=c, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=c, user_id=2001, role=CourseRole.TA)
    CourseMembership.objects.create(course=c, user_id=1001, role=CourseRole.STUDENT)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-test-token")

    resp = client.get(f"{URL_COURSES}/CS301")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "CS301"
    assert data["title"] == "Database Systems"
    assert data["syllabus"] == "Week 1: SQL, Week 2: B-Trees"
    assert data["schedule"] == "Mon/Wed 10:00-11:30"
    assert data["role"] == "student"
    assert data["can_edit"] is False

    # Check instructors and TAs display (AFR-LMS-001.2)
    instructors = data["instructors"]
    assert len(instructors) == 1
    assert instructors[0]["display_name"] == "Dr. Smith"
    assert instructors[0]["email"] == "smith@test.ac.in"

    tas = data["teaching_assistants"]
    assert len(tas) == 1
    assert tas[0]["display_name"] == "John TA"
    assert tas[0]["email"] == "ta@test.ac.in"


def test_course_workspace_details_restricted_to_enrolled_users(stub_iam):
    c = Course.objects.create(code="CS301", title="Database Systems")
    # User 1001 is enrolled, but User 1002 is NOT
    CourseMembership.objects.create(course=c, user_id=1001, role=CourseRole.STUDENT)

    client = api_client(stub_iam, user_id=1002, role="student", permissions=(VIEW,))

    resp = client.get(f"{URL_COURSES}/CS301")
    # Must fail with 404 (AFR-LMS-001.3, BR-LMS-001)
    assert resp.status_code == 404


def test_ta_and_observer_read_only_access(stub_iam):
    c = Course.objects.create(
        code="CS301",
        title="Database Systems",
        syllabus="Standard syllabus",
        schedule="Fri 2pm",
    )
    CourseMembership.objects.create(course=c, user_id=2001, role=CourseRole.TA)
    CourseMembership.objects.create(course=c, user_id=3001, role=CourseRole.OBSERVER)

    # 1. TA can view (AFR-LMS-014.1) but can_edit is False (AFR-LMS-014.5)
    ta_client = api_client(stub_iam, user_id=2001, role="staff", permissions=(VIEW,))
    resp_ta = ta_client.get(f"{URL_COURSES}/CS301")
    assert resp_ta.status_code == 200
    assert resp_ta.json()["role"] == "ta"
    assert resp_ta.json()["can_edit"] is False

    # 2. Observer can view (AFR-LMS-015.1) but can_edit is False (AFR-LMS-015.4)
    obs_client = api_client(stub_iam, user_id=3001, role="staff", permissions=(VIEW,))
    resp_obs = obs_client.get(f"{URL_COURSES}/CS301")
    assert resp_obs.status_code == 200
    assert resp_obs.json()["role"] == "observer"
    assert resp_obs.json()["can_edit"] is False


def test_faculty_can_edit_course_details(stub_iam):
    c = Course.objects.create(
        code="CS301",
        title="Database Systems",
        syllabus="Initial syllabus",
        schedule="TBA",
    )
    CourseMembership.objects.create(course=c, user_id=9001, role=CourseRole.FACULTY)

    client = api_client(stub_iam, user_id=9001, role="faculty", permissions=(VIEW, MANAGE))

    patch_payload = {
        "title": "Advanced Database Systems",
        "syllabus": "1. Transactions 2. Concurrency Control 3. Query Optimization",
        "schedule": "Mon/Wed/Fri 11:00-12:00",
        "description": "Graduate level DBMS course.",
    }
    resp = client.patch(f"{URL_COURSES}/CS301", data=patch_payload, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Advanced Database Systems"
    assert data["syllabus"] == "1. Transactions 2. Concurrency Control 3. Query Optimization"
    assert data["schedule"] == "Mon/Wed/Fri 11:00-12:00"
    assert data["description"] == "Graduate level DBMS course."
    assert data["can_edit"] is True


def test_ta_and_observer_cannot_modify_course_details(stub_iam):
    c = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=c, user_id=2001, role=CourseRole.TA)
    CourseMembership.objects.create(course=c, user_id=3001, role=CourseRole.OBSERVER)

    # TA attempt
    ta_client = api_client(stub_iam, user_id=2001, role="staff", permissions=(VIEW, MANAGE))
    resp_ta = ta_client.patch(f"{URL_COURSES}/CS301", data={"syllabus": "TA Hack"}, format="json")
    assert resp_ta.status_code == 403

    # Observer attempt
    obs_client = api_client(stub_iam, user_id=3001, role="staff", permissions=(VIEW, MANAGE))
    resp_obs = obs_client.patch(f"{URL_COURSES}/CS301", data={"syllabus": "Observer Hack"}, format="json")
    assert resp_obs.status_code == 403


def test_materials_list_visibility_and_restrictions(stub_iam):
    c = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=c, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=c, user_id=1001, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=c, user_id=2001, role=CourseRole.TA)

    future_release = datetime.now(UTC) + timedelta(days=5)

    # 1. Published note
    CourseMaterial.objects.create(
        course=c,
        title="Published Note",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.PUBLISHED,
        content="Published content",
        created_by_user_id=9001,
    )
    # 2. Draft note
    CourseMaterial.objects.create(
        course=c,
        title="Draft Note",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.DRAFT,
        content="Draft content",
        created_by_user_id=9001,
    )
    # 3. Scheduled note
    CourseMaterial.objects.create(
        course=c,
        title="Future Note",
        section_title="Module 2",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=future_release,
        content="Future content",
        created_by_user_id=9001,
    )

    # Faculty sees all 3 materials
    faculty_client = api_client(
        stub_iam, user_id=9001, role="faculty", permissions=(VIEW, MAT_VIEW, MAT_MANAGE)
    )
    resp_fac = faculty_client.get(f"{URL_COURSES}/CS301/materials")
    assert resp_fac.status_code == 200
    fac_data = resp_fac.json()
    assert fac_data["can_manage"] is True
    assert fac_data["total_count"] == 3

    # Student sees ONLY the 1 published material (BR-LMS-005, BR-LMS-006)
    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, MAT_VIEW)
    )
    resp_stu = student_client.get(f"{URL_COURSES}/CS301/materials")
    assert resp_stu.status_code == 200
    stu_data = resp_stu.json()
    assert stu_data["can_manage"] is False
    assert stu_data["total_count"] == 1
    assert stu_data["sections"][0]["materials"][0]["title"] == "Published Note"

    # TA also sees ONLY published materials in read-only form (AFR-LMS-014.1, BR-LMS-005)
    ta_client = api_client(
        stub_iam, user_id=2001, role="staff", permissions=(VIEW, MAT_VIEW)
    )
    resp_ta = ta_client.get(f"{URL_COURSES}/CS301/materials")
    assert resp_ta.status_code == 200
    ta_data = resp_ta.json()
    assert ta_data["can_manage"] is False
    assert ta_data["total_count"] == 1


def test_faculty_create_and_delete_material_endpoint(stub_iam):
    c = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=c, user_id=9001, role=CourseRole.FACULTY)

    client = api_client(
        stub_iam, user_id=9001, role="faculty", permissions=(VIEW, MAT_VIEW, MAT_MANAGE)
    )

    # Create link material
    payload = {
        "title": "SQL Tutorial",
        "section_title": "Module 1: Foundations",
        "material_type": "link",
        "link_url": "https://sqlzoo.net",
        "status": "published",
    }
    resp = client.post(f"{URL_COURSES}/CS301/materials", data=payload, format="json")
    assert resp.status_code == 201
    created_id = resp.json()["id"]

    # Delete material
    resp_del = client.delete(f"{URL_COURSES}/CS301/materials/{created_id}")
    assert resp_del.status_code == 204
    assert not CourseMaterial.objects.filter(id=created_id).exists()


def test_ta_and_observer_cannot_create_materials_via_api(stub_iam):
    c = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=c, user_id=2001, role=CourseRole.TA)

    ta_client = api_client(
        stub_iam, user_id=2001, role="staff", permissions=(VIEW, MAT_VIEW, MAT_MANAGE)
    )
    payload = {
        "title": "TA Illegal Note",
        "section_title": "Module 1",
        "material_type": "note",
        "content": "Not allowed",
    }
    resp = ta_client.post(f"{URL_COURSES}/CS301/materials", data=payload, format="json")
    assert resp.status_code == 403


def test_material_file_download_endpoint(stub_iam):
    c = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=c, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=c, user_id=1001, role=CourseRole.STUDENT)

    # Upload published file material
    uploaded_file = SimpleUploadedFile("slides.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
    mat_pub = CourseMaterial.objects.create(
        course=c,
        title="Lecture Slides",
        section_title="Module 1",
        material_type=MaterialType.FILE,
        file=uploaded_file,
        file_name="slides.pdf",
        status=MaterialStatus.PUBLISHED,
        created_by_user_id=9001,
    )

    # Student downloads published file
    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, MAT_VIEW)
    )
    resp = student_client.get(f"{URL_COURSES}/CS301/materials/{mat_pub.id}/download")
    assert resp.status_code == 200
    assert resp.getvalue() == b"%PDF-1.4 sample content"

    # Create draft file material
    draft_file = SimpleUploadedFile("exam.pdf", b"%PDF-1.4 confidential exam", content_type="application/pdf")
    mat_draft = CourseMaterial.objects.create(
        course=c,
        title="Confidential Exam",
        section_title="Exams",
        material_type=MaterialType.FILE,
        file=draft_file,
        file_name="exam.pdf",
        status=MaterialStatus.DRAFT,
        created_by_user_id=9001,
    )

    # Student cannot download draft material (404 Not Found)
    resp_draft = student_client.get(f"{URL_COURSES}/CS301/materials/{mat_draft.id}/download")
    assert resp_draft.status_code == 404


def test_course_announcements_list_and_post_by_faculty(stub_iam):
    c = Course.objects.create(code="CS601", title="Compiler Design")
    CourseMembership.objects.create(course=c, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=c, user_id=1001, role=CourseRole.STUDENT)

    faculty_client = api_client(
        stub_iam, user_id=9001, role="faculty", permissions=(VIEW, ANN_VIEW, ANN_MANAGE)
    )

    # Post an announcement
    payload = {
        "title": "Welcome to CS601",
        "content": "First lecture begins tomorrow at 9:00 AM.",
    }
    resp_post = faculty_client.post(f"{URL_COURSES}/CS601/announcements", payload, format="json")
    assert resp_post.status_code == 201
    assert resp_post.data["title"] == "Welcome to CS601"
    assert resp_post.data["created_by_user_id"] == 9001
    assert resp_post.data["author_role"] == CourseRole.FACULTY
    assert resp_post.data["created_at"] is not None

    ann_id = resp_post.data["id"]

    # Student lists announcements
    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, ANN_VIEW)
    )
    resp_list = student_client.get(f"{URL_COURSES}/CS601/announcements")
    assert resp_list.status_code == 200
    assert resp_list.data["course_code"] == "CS601"
    assert resp_list.data["can_post"] is False
    assert len(resp_list.data["announcements"]) == 1
    assert resp_list.data["announcements"][0]["title"] == "Welcome to CS601"

    # Student retrieves announcement detail
    resp_detail = student_client.get(f"{URL_COURSES}/CS601/announcements/{ann_id}")
    assert resp_detail.status_code == 200
    assert resp_detail.data["title"] == "Welcome to CS601"


def test_unauthorized_roles_cannot_post_announcements_api(stub_iam):
    c = Course.objects.create(code="CS602", title="Distributed Systems")
    CourseMembership.objects.create(course=c, user_id=1001, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=c, user_id=2001, role=CourseRole.TA)
    CourseMembership.objects.create(course=c, user_id=3001, role=CourseRole.OBSERVER)

    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, ANN_VIEW, ANN_MANAGE)
    )
    ta_client = api_client(
        stub_iam, user_id=2001, role="ta", permissions=(VIEW, ANN_VIEW, ANN_MANAGE)
    )
    observer_client = api_client(
        stub_iam, user_id=3001, role="observer", permissions=(VIEW, ANN_VIEW, ANN_MANAGE)
    )

    payload = {"title": "Test Title", "content": "Test Content"}

    # Student posting is forbidden (403)
    resp_student = student_client.post(f"{URL_COURSES}/CS602/announcements", payload, format="json")
    assert resp_student.status_code == 403

    # TA posting is forbidden (403)
    resp_ta = ta_client.post(f"{URL_COURSES}/CS602/announcements", payload, format="json")
    assert resp_ta.status_code == 403

    # Observer posting is forbidden (403)
    resp_obs = observer_client.post(f"{URL_COURSES}/CS602/announcements", payload, format="json")
    assert resp_obs.status_code == 403


def test_announcements_course_isolation_and_validation(stub_iam):
    c1 = Course.objects.create(code="CS603", title="Course Alpha")
    CourseMembership.objects.create(course=c1, user_id=9001, role=CourseRole.FACULTY)

    non_member_client = api_client(
        stub_iam, user_id=5555, role="faculty", permissions=(VIEW, ANN_VIEW, ANN_MANAGE)
    )

    # Non-member cannot list announcements (404 Not Found, BR-LMS-001)
    resp_list = non_member_client.get(f"{URL_COURSES}/CS603/announcements")
    assert resp_list.status_code == 404

    # Non-member cannot post announcements (404 Not Found)
    resp_post = non_member_client.post(
        f"{URL_COURSES}/CS603/announcements",
        {"title": "Intrusion", "content": "Hello"},
        format="json",
    )
    assert resp_post.status_code == 404

    # Faculty member receives 400 on empty/missing fields
    faculty_client = api_client(
        stub_iam, user_id=9001, role="faculty", permissions=(VIEW, ANN_VIEW, ANN_MANAGE)
    )
    resp_bad = faculty_client.post(
        f"{URL_COURSES}/CS603/announcements",
        {"title": "", "content": ""},
        format="json",
    )
    assert resp_bad.status_code == 400


def test_assignment_crud_lifecycle_for_faculty(stub_iam):
    course = Course.objects.create(code="CS701", title="Algorithms")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty_client = api_client(
        stub_iam, user_id=9001, role="faculty", permissions=(VIEW, ASG_VIEW, ASG_MANAGE)
    )

    # 1. Faculty creates draft assignment
    create_payload = {
        "title": "Homework 1: Graph Traversal",
        "instructions": "Implement BFS and DFS in Python.",
        "submission_type": "file",
        "points_possible": 100.0,
        "status": "draft",
    }
    resp_create = faculty_client.post(
        f"{URL_COURSES}/CS701/assignments",
        create_payload,
        format="json",
    )
    assert resp_create.status_code == 201
    asg_id = resp_create.data["id"]
    assert resp_create.data["title"] == "Homework 1: Graph Traversal"
    assert resp_create.data["status"] == "draft"

    # 2. Faculty retrieves detail
    resp_get = faculty_client.get(f"{URL_COURSES}/CS701/assignments/{asg_id}")
    assert resp_get.status_code == 200
    assert resp_get.data["title"] == "Homework 1: Graph Traversal"

    # 3. Faculty updates assignment to published with due date
    now = datetime.now(UTC)
    due = (now + timedelta(days=7)).isoformat()
    update_payload = {
        "status": "published",
        "due_at": due,
        "points_possible": 120.0,
    }
    resp_patch = faculty_client.patch(
        f"{URL_COURSES}/CS701/assignments/{asg_id}",
        update_payload,
        format="json",
    )
    assert resp_patch.status_code == 200
    assert resp_patch.data["status"] == "published"
    assert resp_patch.data["points_possible"] == 120.0

    # 4. Faculty deletes assignment
    resp_del = faculty_client.delete(f"{URL_COURSES}/CS701/assignments/{asg_id}")
    assert resp_del.status_code == 204

    # Confirm deletion
    resp_after = faculty_client.get(f"{URL_COURSES}/CS701/assignments/{asg_id}")
    assert resp_after.status_code == 404


def test_assignment_list_filters_draft_and_scheduled_from_students(stub_iam):
    course = Course.objects.create(code="CS702", title="Networking")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)

    now = datetime.now(UTC)
    due = now + timedelta(days=5)
    future_release = now + timedelta(days=2)

    draft = CourseAssignment.objects.create(
        course=course,
        title="Draft Exam",
        instructions="Hidden draft",
        status=AssignmentStatus.DRAFT,
        created_by_user_id=9001,
    )
    scheduled = CourseAssignment.objects.create(
        course=course,
        title="Scheduled Lab",
        instructions="Hidden lab",
        status=AssignmentStatus.SCHEDULED,
        release_at=future_release,
        due_at=due,
        created_by_user_id=9001,
    )
    published = CourseAssignment.objects.create(
        course=course,
        title="Published Project",
        instructions="Public project",
        status=AssignmentStatus.PUBLISHED,
        due_at=due,
        created_by_user_id=9001,
    )

    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, ASG_VIEW)
    )

    # List endpoint strictly shows only published
    resp_list = student_client.get(f"{URL_COURSES}/CS702/assignments")
    assert resp_list.status_code == 200
    assert resp_list.data["can_manage"] is False
    assert len(resp_list.data["assignments"]) == 1
    assert resp_list.data["assignments"][0]["id"] == published.id

    # Direct detail access
    assert student_client.get(f"{URL_COURSES}/CS702/assignments/{draft.id}").status_code == 404
    assert student_client.get(f"{URL_COURSES}/CS702/assignments/{scheduled.id}").status_code == 404
    assert student_client.get(f"{URL_COURSES}/CS702/assignments/{published.id}").status_code == 200


def test_ta_student_observer_cannot_author_or_modify_assignments(stub_iam):
    course = Course.objects.create(code="CS703", title="OS")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=3001, role=CourseRole.OBSERVER)

    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, ASG_VIEW, ASG_MANAGE)
    )
    ta_client = api_client(
        stub_iam, user_id=2001, role="ta", permissions=(VIEW, ASG_VIEW, ASG_MANAGE)
    )
    obs_client = api_client(
        stub_iam, user_id=3001, role="observer", permissions=(VIEW, ASG_VIEW, ASG_MANAGE)
    )

    payload = {"title": "Unauthorized Assignment", "status": "draft"}

    # Post is forbidden (403)
    assert student_client.post(f"{URL_COURSES}/CS703/assignments", payload).status_code == 403
    assert ta_client.post(f"{URL_COURSES}/CS703/assignments", payload).status_code == 403
    assert obs_client.post(f"{URL_COURSES}/CS703/assignments", payload).status_code == 403

    # Existing assignment
    asg = CourseAssignment.objects.create(
        course=course,
        title="Faculty Assignment",
        status=AssignmentStatus.DRAFT,
        created_by_user_id=9001,
    )

    # Patch is forbidden (403)
    patch_payload = {"title": "Hacked Title"}
    assert (
        student_client.patch(
            f"{URL_COURSES}/CS703/assignments/{asg.id}", patch_payload
        ).status_code
        == 403
    )
    assert (
        ta_client.patch(
            f"{URL_COURSES}/CS703/assignments/{asg.id}", patch_payload
        ).status_code
        == 403
    )
    assert (
        obs_client.patch(
            f"{URL_COURSES}/CS703/assignments/{asg.id}", patch_payload
        ).status_code
        == 403
    )

    # Delete is forbidden (403)
    assert student_client.delete(f"{URL_COURSES}/CS703/assignments/{asg.id}").status_code == 403
    assert ta_client.delete(f"{URL_COURSES}/CS703/assignments/{asg.id}").status_code == 403
    assert obs_client.delete(f"{URL_COURSES}/CS703/assignments/{asg.id}").status_code == 403


def test_assignment_download_endpoint(stub_iam):
    course = Course.objects.create(code="CS704", title="Databases")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)

    faculty_client = api_client(
        stub_iam, user_id=9001, role="faculty", permissions=(VIEW, ASG_VIEW, ASG_MANAGE)
    )

    test_file = SimpleUploadedFile("assignment1.pdf", b"%PDF-1.4 dummy assignment content")
    now = datetime.now(UTC)
    due = (now + timedelta(days=7)).isoformat()

    resp_create = faculty_client.post(
        f"{URL_COURSES}/CS704/assignments",
        {
            "title": "SQL Assignment with File",
            "instructions": "Download and solve the problems.",
            "submission_type": "file",
            "points_possible": 100,
            "status": "published",
            "due_at": due,
            "file": test_file,
        },
        format="multipart",
    )
    assert resp_create.status_code == 201
    asg_id = resp_create.data["id"]

    # Student downloads attachment
    student_client = api_client(
        stub_iam, user_id=1001, role="student", permissions=(VIEW, ASG_VIEW)
    )
    resp_dl = student_client.get(f"{URL_COURSES}/CS704/assignments/{asg_id}/download")
    assert resp_dl.status_code == 200
    assert b"%PDF-1.4" in b"".join(resp_dl.streaming_content)


def test_assignment_deadline_endpoint_privacy(stub_iam):
    course = Course.objects.create(code="CS801", title="Compiler", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=2002, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=2003, role=CourseRole.STUDENT)

    now = datetime.now(UTC)
    due = now + timedelta(days=2)
    ext_due = now + timedelta(days=5)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Lexer",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=2001,
        due_at=due,
    )

    from modules.lms.models import CourseAssignmentExtension

    CourseAssignmentExtension.objects.create(
        assignment=asg,
        user_id=2002,
        extended_due_at=ext_due,
        reason="Medical emergency",
        granted_by_user_id=2001,
    )

    # 1. Student 1 checks deadline: sees personal extension
    client_s1 = api_client(
        stub_iam, user_id=2002, role="student", permissions=(VIEW, ASG_VIEW, DL_VIEW)
    )
    r1 = client_s1.get(f"{URL_COURSES}/CS801/assignments/{asg.id}/deadline")
    assert r1.status_code == 200
    assert r1.data["is_extended"] is True
    assert r1.data["extension_reason"] == "Medical emergency"
    assert r1.data["can_manage_deadlines"] is False

    # 2. Student 2 checks deadline: does NOT see student 1's extension (privacy)
    client_s2 = api_client(
        stub_iam, user_id=2003, role="student", permissions=(VIEW, ASG_VIEW, DL_VIEW)
    )
    r2 = client_s2.get(f"{URL_COURSES}/CS801/assignments/{asg.id}/deadline")
    assert r2.status_code == 200
    assert r2.data["is_extended"] is False
    assert r2.data["extended_due_at"] is None
    assert r2.data["extension_reason"] == ""

    # 3. Faculty checks deadline: can manage deadlines and see total extensions count
    client_fac = api_client(
        stub_iam, user_id=2001, role="faculty", permissions=(VIEW, ASG_VIEW, DL_VIEW, DL_MANAGE)
    )
    rf = client_fac.get(f"{URL_COURSES}/CS801/assignments/{asg.id}/deadline")
    assert rf.status_code == 200
    assert rf.data["can_manage_deadlines"] is True
    assert rf.data["total_extensions"] == 1


def test_assignment_window_patch_endpoint(stub_iam):
    course = Course.objects.create(code="CS802", title="Graphics", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=2002, role=CourseRole.STUDENT)

    now = datetime.now(UTC)
    asg = CourseAssignment.objects.create(
        course=course,
        title="Ray Tracing",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=2001,
        due_at=now + timedelta(days=3),
    )

    client_fac = api_client(
        stub_iam, user_id=2001, role="faculty", permissions=(VIEW, ASG_VIEW, DL_VIEW, DL_MANAGE)
    )
    patch_data = {
        "due_at": (now + timedelta(days=4)).isoformat(),
        "closes_at": (now + timedelta(days=7)).isoformat(),
        "allow_late": True,
    }
    rf = client_fac.patch(f"{URL_COURSES}/CS802/assignments/{asg.id}/window", patch_data, format="json")
    assert rf.status_code == 200
    assert rf.data["allow_late"] is True
    assert rf.data["window_status"] == "open"

    # Student cannot patch window
    client_s = api_client(
        stub_iam, user_id=2002, role="student", permissions=(VIEW, ASG_VIEW, DL_VIEW)
    )
    rs = client_s.patch(f"{URL_COURSES}/CS802/assignments/{asg.id}/window", patch_data, format="json")
    assert rs.status_code == 403


def test_assignment_extensions_crud_and_rbac(stub_iam):
    course = Course.objects.create(code="CS803", title="Cloud", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=3001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=3002, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=3003, role=CourseRole.TA)

    now = datetime.now(UTC)
    asg = CourseAssignment.objects.create(
        course=course,
        title="Microservices",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=3001,
        due_at=now + timedelta(days=2),
    )

    def faculty_c():
        return api_client(
            stub_iam, user_id=3001, role="faculty", permissions=(VIEW, ASG_VIEW, DL_VIEW, DL_MANAGE)
        )

    def ta_c():
        return api_client(
            stub_iam, user_id=3003, role="ta", permissions=(VIEW, ASG_VIEW, DL_VIEW)
        )

    def student_c():
        return api_client(
            stub_iam, user_id=3002, role="student", permissions=(VIEW, ASG_VIEW, DL_VIEW)
        )

    # 1. Student cannot list all extensions (privacy)
    rs_list = student_c().get(f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions")
    assert rs_list.status_code == 403

    # 2. TA can list extensions (empty initially)
    rta_list = ta_c().get(f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions")
    assert rta_list.status_code == 200
    assert len(rta_list.data) == 0

    # 3. TA cannot grant extension (faculty only)
    ext_payload = {
        "student_user_id": 3002,
        "extended_due_at": (now + timedelta(days=5)).isoformat(),
        "reason": "Family emergency",
    }
    rta_post = ta_c().post(
        f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions", ext_payload, format="json"
    )
    assert rta_post.status_code == 403

    # 4. Faculty grants extension
    rf_post = faculty_c().post(
        f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions", ext_payload, format="json"
    )
    assert rf_post.status_code == 201
    ext_id = rf_post.data["id"]
    assert rf_post.data["user_id"] == 3002
    assert rf_post.data["reason"] == "Family emergency"

    # 5. TA can now view this extension in the list
    rta_list2 = ta_c().get(f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions")
    assert rta_list2.status_code == 200
    assert len(rta_list2.data) == 1
    assert rta_list2.data[0]["id"] == ext_id

    # 6. Faculty revokes extension
    rf_del = faculty_c().delete(f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions/{ext_id}")
    assert rf_del.status_code == 204

    # 7. TA checks list again -> empty
    rta_list3 = ta_c().get(f"{URL_COURSES}/CS803/assignments/{asg.id}/extensions")
    assert rta_list3.status_code == 200
    assert len(rta_list3.data) == 0


def test_submission_api_student_flow(stub_iam):
    course = Course.objects.create(code="CS901", title="Algorithms", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=4001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=4002, role=CourseRole.STUDENT)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Dynamic Programming",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=4001,
        due_at=now + timedelta(days=4),
    )

    client = api_client(
        stub_iam,
        user_id=4002,
        role="student",
        permissions=(VIEW, ASG_VIEW, SUB_VIEW, SUB_SUBMIT),
    )

    # 1. GET /mine initially -> not_submitted
    r_mine = client.get(f"{URL_COURSES}/CS901/assignments/{asg.id}/submissions/mine")
    assert r_mine.status_code == 200
    assert r_mine.data["status"] == "not_submitted"
    assert r_mine.data["has_submitted"] is False
    assert r_mine.data["total_attempts"] == 0

    # 2. POST submission
    payload1 = {
        "submission_type": "text",
        "content_text": "def knapsack(): pass",
    }
    r_sub1 = client.post(
        f"{URL_COURSES}/CS901/assignments/{asg.id}/submissions/mine",
        payload1,
        format="json",
    )
    assert r_sub1.status_code == 201
    assert r_sub1.data["attempt_number"] == 1
    assert r_sub1.data["status"] == "submitted"
    assert r_sub1.data["content_text"] == "def knapsack(): pass"

    # 3. GET /mine after submission -> submitted, 1 attempt
    r_mine2 = client.get(f"{URL_COURSES}/CS901/assignments/{asg.id}/submissions/mine")
    assert r_mine2.status_code == 200
    assert r_mine2.data["status"] == "submitted"
    assert r_mine2.data["has_submitted"] is True
    assert r_mine2.data["total_attempts"] == 1
    assert len(r_mine2.data["history"]) == 1

    # 4. Resubmission
    payload2 = {
        "submission_type": "text",
        "content_text": "def knapsack(): return 42",
    }
    r_sub2 = client.post(
        f"{URL_COURSES}/CS901/assignments/{asg.id}/submissions/mine",
        payload2,
        format="json",
    )
    assert r_sub2.status_code == 201
    assert r_sub2.data["attempt_number"] == 2
    assert r_sub2.data["status"] == "submitted"

    # 5. GET /mine after resubmission -> 2 attempts in history
    r_mine3 = client.get(f"{URL_COURSES}/CS901/assignments/{asg.id}/submissions/mine")
    assert r_mine3.status_code == 200
    assert r_mine3.data["total_attempts"] == 2
    assert len(r_mine3.data["history"]) == 2
    assert r_mine3.data["history"][0]["attempt_number"] == 2
    assert r_mine3.data["history"][1]["attempt_number"] == 1


def test_submission_api_file_upload_and_download(stub_iam):
    course = Course.objects.create(code="CS902", title="Networks", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=4010, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=4011, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=4012, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=4013, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=4014, role=CourseRole.OBSERVER)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Packet Tracer",
        submission_type=SubmissionType.FILE,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=4010,
        due_at=now + timedelta(days=2),
    )

    def s1_c():
        return api_client(
            stub_iam,
            user_id=4012,
            role="student",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW, SUB_SUBMIT),
        )

    def s2_c():
        return api_client(
            stub_iam,
            user_id=4013,
            role="student",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW, SUB_SUBMIT),
        )

    def ta_c():
        return api_client(
            stub_iam,
            user_id=4011,
            role="ta",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW),
        )

    def obs_c():
        return api_client(
            stub_iam,
            user_id=4014,
            role="observer",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW),
        )

    # 1. Student 1 submits file
    file_data = SimpleUploadedFile("network.pkt", b"PKT_DUMMY_CONTENT")
    r_sub = s1_c().post(
        f"{URL_COURSES}/CS902/assignments/{asg.id}/submissions/mine",
        {"submission_type": "file", "file": file_data},
        format="multipart",
    )
    assert r_sub.status_code == 201
    sub_id = r_sub.data["id"]
    assert r_sub.data["file_name"] == "network.pkt"

    # 2. Student 1 downloads own file -> 200
    r_dl_s1 = s1_c().get(
        f"{URL_COURSES}/CS902/assignments/{asg.id}/submissions/{sub_id}/download"
    )
    assert r_dl_s1.status_code == 200

    # 3. Student 2 cannot download Student 1's file -> 404 (or access denied)
    r_dl_s2 = s2_c().get(
        f"{URL_COURSES}/CS902/assignments/{asg.id}/submissions/{sub_id}/download"
    )
    assert r_dl_s2.status_code == 404

    # 4. TA can download Student 1's file -> 200
    r_dl_ta = ta_c().get(
        f"{URL_COURSES}/CS902/assignments/{asg.id}/submissions/{sub_id}/download"
    )
    assert r_dl_ta.status_code == 200

    # 5. Observer cannot download Student 1's file -> 404
    r_dl_obs = obs_c().get(
        f"{URL_COURSES}/CS902/assignments/{asg.id}/submissions/{sub_id}/download"
    )
    assert r_dl_obs.status_code == 404


def test_submission_api_list_permissions(stub_iam):
    course = Course.objects.create(code="CS903", title="Databases", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=4020, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=4021, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=4022, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=4023, role=CourseRole.OBSERVER)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Schema Design",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=4020,
        due_at=now + timedelta(days=1),
    )

    def s_c():
        return api_client(
            stub_iam,
            user_id=4022,
            role="student",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW),
        )

    def obs_c():
        return api_client(
            stub_iam,
            user_id=4023,
            role="observer",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW),
        )

    def ta_c():
        return api_client(
            stub_iam,
            user_id=4021,
            role="ta",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW),
        )

    # 1. Student cannot list submissions -> 403
    r_s = s_c().get(f"{URL_COURSES}/CS903/assignments/{asg.id}/submissions")
    assert r_s.status_code == 403

    # 2. Observer cannot list submissions -> 403
    r_obs = obs_c().get(f"{URL_COURSES}/CS903/assignments/{asg.id}/submissions")
    assert r_obs.status_code == 403

    # 3. TA can list submissions -> 200
    r_ta = ta_c().get(f"{URL_COURSES}/CS903/assignments/{asg.id}/submissions")
    assert r_ta.status_code == 200
    assert "submissions" in r_ta.data
    assert "total_submissions" in r_ta.data


def test_submission_api_deadline_closed_and_mismatch(stub_iam):
    course = Course.objects.create(code="CS904", title="Web", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=4030, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=4031, role=CourseRole.STUDENT)

    # Past due, late not allowed
    asg = CourseAssignment.objects.create(
        course=course,
        title="HTML Form",
        submission_type=SubmissionType.LINK,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=4030,
        due_at=now - timedelta(days=1),
        allow_late=False,
    )

    s_client = api_client(
        stub_iam,
        user_id=4031,
        role="student",
        permissions=(VIEW, ASG_VIEW, SUB_VIEW, SUB_SUBMIT),
    )

    # 1. Closed deadline rejected with 409 Conflict
    r_closed = s_client.post(
        f"{URL_COURSES}/CS904/assignments/{asg.id}/submissions/mine",
        {"submission_type": "link", "link_url": "https://example.com"},
        format="json",
    )
    assert r_closed.status_code == 409
    assert "submission_window_closed" in str(r_closed.data)

    # Update assignment to open
    asg.due_at = now + timedelta(days=3)
    asg.save()

    # 2. Type mismatch rejected with 409 Conflict
    r_mismatch = s_client.post(
        f"{URL_COURSES}/CS904/assignments/{asg.id}/submissions/mine",
        {"submission_type": "text", "content_text": "text not link"},
        format="json",
    )
    assert r_mismatch.status_code == 409
    assert "does not match" in str(r_mismatch.data)


def test_grading_api_faculty_and_ta_flow(stub_iam):
    course = Course.objects.create(code="CS905", title="Distributed Systems", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=5001, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=5002, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=5010, role=CourseRole.STUDENT)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Raft Consensus",
        points_possible=100,
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=5001,
        due_at=now + timedelta(days=2),
    )

    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=5010,
        submission_type=SubmissionType.TEXT,
        status="submitted",
        submitted_at=now,
        content_text="Raft leader election code",
        attempt_number=1,
        is_latest=True,
    )

    def fac_c():
        return api_client(
            stub_iam,
            user_id=5001,
            role="faculty",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW, GRD_VIEW, GRD_GRADE),
        )

    def ta_c():
        return api_client(
            stub_iam,
            user_id=5002,
            role="ta",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW, GRD_VIEW, GRD_GRADE),
        )

    # 1. Faculty grades submission
    rf_post = fac_c().post(
        f"{URL_COURSES}/CS905/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "88.50"},
        format="json",
    )
    assert rf_post.status_code == 201
    assert rf_post.data["score"] == "88.50"
    assert rf_post.data["points_possible"] == "100.00"
    assert rf_post.data["status"] == "draft"
    assert rf_post.data["graded_by_user_id"] == 5001

    # 2. Faculty retrieves grade
    rf_get = fac_c().get(
        f"{URL_COURSES}/CS905/assignments/{asg.id}/submissions/{sub.id}/grade"
    )
    assert rf_get.status_code == 200
    assert rf_get.data["score"] == "88.50"

    # 3. TA updates grade
    rta_post = ta_c().post(
        f"{URL_COURSES}/CS905/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "92.00"},
        format="json",
    )
    assert rta_post.status_code == 201
    assert rta_post.data["score"] == "92.00"
    assert rta_post.data["graded_by_user_id"] == 5002

    # 4. TA retrieves grade
    rta_get = ta_c().get(
        f"{URL_COURSES}/CS905/assignments/{asg.id}/submissions/{sub.id}/grade"
    )
    assert rta_get.status_code == 200
    assert rta_get.data["score"] == "92.00"


def test_grading_api_student_and_observer_restrictions(stub_iam):
    course = Course.objects.create(code="CS906", title="Cloud Computing", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=5020, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=5030, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=5040, role=CourseRole.OBSERVER)

    asg = CourseAssignment.objects.create(
        course=course,
        title="MapReduce Lab",
        points_possible=100,
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=5020,
        due_at=now + timedelta(days=2),
    )

    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=5030,
        submission_type=SubmissionType.TEXT,
        status="submitted",
        submitted_at=now,
        content_text="Mapper and Reducer implementation",
        attempt_number=1,
        is_latest=True,
    )

    def fac_c():
        return api_client(
            stub_iam,
            user_id=5020,
            role="faculty",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW, GRD_VIEW, GRD_GRADE),
        )

    def std_c():
        return api_client(
            stub_iam,
            user_id=5030,
            role="student",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW, SUB_SUBMIT, GRD_VIEW),
        )

    def obs_c():
        return api_client(
            stub_iam,
            user_id=5040,
            role="observer",
            permissions=(VIEW, ASG_VIEW, SUB_VIEW),
        )

    # 1. Student cannot grade -> 403 Forbidden
    r_std_post = std_c().post(
        f"{URL_COURSES}/CS906/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "100.00"},
        format="json",
    )
    assert r_std_post.status_code == 403

    # 2. Observer cannot grade -> 403 Forbidden
    r_obs_post = obs_c().post(
        f"{URL_COURSES}/CS906/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "100.00"},
        format="json",
    )
    assert r_obs_post.status_code == 403

    # Faculty records grade
    fac_c().post(
        f"{URL_COURSES}/CS906/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "80.00"},
        format="json",
    )

    # 3. Student GET draft grade -> 404 (hidden until release, BR-LMS-016, AFR-LMS-011.2)
    r_std_get = std_c().get(
        f"{URL_COURSES}/CS906/assignments/{asg.id}/submissions/{sub.id}/grade"
    )
    assert r_std_get.status_code == 404

    # 4. Observer GET grade -> 403 Forbidden
    r_obs_get = obs_c().get(
        f"{URL_COURSES}/CS906/assignments/{asg.id}/submissions/{sub.id}/grade"
    )
    assert r_obs_get.status_code == 403


def test_grading_api_score_validation(stub_iam):
    course = Course.objects.create(code="CS907", title="ML", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=5050, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=5060, role=CourseRole.STUDENT)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Linear Regression",
        points_possible=50,
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=5050,
        due_at=now + timedelta(days=2),
    )

    sub = CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=5060,
        submission_type=SubmissionType.TEXT,
        status="submitted",
        submitted_at=now,
        content_text="Gradient descent code",
        attempt_number=1,
        is_latest=True,
    )

    client = api_client(
        stub_iam,
        user_id=5050,
        role="faculty",
        permissions=(VIEW, ASG_VIEW, SUB_VIEW, GRD_VIEW, GRD_GRADE),
    )

    # Score exceeding points_possible (50) -> 409 Conflict
    r_over = client.post(
        f"{URL_COURSES}/CS907/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "51.00"},
        format="json",
    )
    assert r_over.status_code == 409
    assert "cannot exceed maximum points possible" in str(r_over.data)

    # Negative score -> 400 Bad Request (serializer min_value=0)
    r_neg = client.post(
        f"{URL_COURSES}/CS907/assignments/{asg.id}/submissions/{sub.id}/grade",
        {"score": "-5.00"},
        format="json",
    )
    assert r_neg.status_code == 400
