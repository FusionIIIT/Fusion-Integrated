"""API tests for LMS Course Workspace endpoints."""
from datetime import UTC, datetime, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.lms.domain.entities import (
    CourseRole,
    CourseStatus,
    MaterialStatus,
    MaterialType,
)
from modules.lms.models import Course, CourseMaterial, CourseMembership

pytestmark = pytest.mark.django_db

MODULE = "lms"
VIEW = "lms.course.view"
MANAGE = "lms.course.manage"
MAT_VIEW = "lms.material.view"
MAT_MANAGE = "lms.material.manage"
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

