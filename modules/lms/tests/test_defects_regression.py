from datetime import timedelta
import pytest
from django.utils import timezone
from rest_framework import status

from conftest import make_session
from modules.lms.domain.constants import ContentStatus, GradeStatus, Role, SubmissionType
from modules.lms.models import (
    Assignment,
    Course,
    CourseMaterial,
    CourseMembership,
    Grade,
    ModuleSection,
    Submission,
)


def get_results(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


@pytest.fixture
def auth_client(stub_iam):
    def _client(user_id: int, is_staff: bool = False, active_role: str = None):
        kind = "staff" if is_staff else "student"
        stub_iam(
            make_session(
                user_id=user_id,
                kind=kind,
                active_role=active_role or ("instructor" if is_staff else "student"),
            )
        )
        from rest_framework.test import APIClient

        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token mock-test-token")
        return c

    return _client


@pytest.fixture
def regression_setup(db):
    course = Course.objects.create(
        code="CS950",
        title="LMS Security Regression Suite",
        academic_year=2026,
        semester=1,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=2001,
        role=Role.INSTRUCTOR,
        is_active=True,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=3001,
        role=Role.TA,
        is_active=True,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=1001,
        role=Role.STUDENT,
        is_active=True,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=1002,
        role=Role.STUDENT,
        is_active=True,
    )
    CourseMembership.objects.create(
        course=course,
        user_id=4001,
        role=Role.OBSERVER,
        is_active=True,
    )
    section = ModuleSection.objects.create(
        course=course,
        title="Section 1: Core Content",
        order=1,
        is_published=True,
    )
    return {
        "course": course,
        "section": section,
        "instructor_id": 2001,
        "ta_id": 3001,
        "student1_id": 1001,
        "student2_id": 1002,
        "observer_id": 4001,
    }


@pytest.mark.django_db
def test_def_lms_01_materials_visibility_and_mutation(regression_setup, auth_client):
    """
    DEF-LMS-01: Verify that draft and unreleased scheduled course materials are
    strictly hidden from students and observers, while remaining visible to staff/instructors.
    Also verifies mutating actions on materials are restricted to instructors/staff.
    """
    section = regression_setup["section"]
    course = regression_setup["course"]
    now = timezone.now()

    mat_draft = CourseMaterial.objects.create(
        section=section,
        title="Draft Syllabus",
        status=ContentStatus.DRAFT,
    )
    mat_scheduled = CourseMaterial.objects.create(
        section=section,
        title="Scheduled Lecture Notes",
        status=ContentStatus.SCHEDULED,
        release_date=now + timedelta(days=7),
    )
    mat_published = CourseMaterial.objects.create(
        section=section,
        title="Published Reading Material",
        status=ContentStatus.PUBLISHED,
        release_date=now - timedelta(days=1),
    )

    # 1. Student access check
    client_student = auth_client(regression_setup["student1_id"], is_staff=False, active_role="student")
    res = client_student.get("/api/v1/lms/materials/")
    assert res.status_code == status.HTTP_200_OK
    returned_ids = [m["id"] for m in get_results(res.data)]
    assert mat_published.id in returned_ids
    assert mat_draft.id not in returned_ids
    assert mat_scheduled.id not in returned_ids

    # Detail view of draft / scheduled returns 404 for student
    res_draft = client_student.get(f"/api/v1/lms/materials/{mat_draft.id}/")
    assert res_draft.status_code == status.HTTP_404_NOT_FOUND

    res_sched = client_student.get(f"/api/v1/lms/materials/{mat_scheduled.id}/")
    assert res_sched.status_code == status.HTTP_404_NOT_FOUND

    # Student cannot create materials
    res_create = client_student.post(
        "/api/v1/lms/materials/",
        {"section": section.id, "title": "Student Upload"},
    )
    assert res_create.status_code == status.HTTP_403_FORBIDDEN

    # 2. Observer access check
    client_observer = auth_client(regression_setup["observer_id"], is_staff=False, active_role="observer")
    res_obs = client_observer.get("/api/v1/lms/materials/")
    assert res_obs.status_code == status.HTTP_200_OK
    obs_returned_ids = [m["id"] for m in get_results(res_obs.data)]
    assert mat_published.id in obs_returned_ids
    assert mat_draft.id not in obs_returned_ids
    assert mat_scheduled.id not in obs_returned_ids

    res_obs_patch = client_observer.patch(
        f"/api/v1/lms/materials/{mat_published.id}/",
        {"title": "Modified Title"},
    )
    assert res_obs_patch.status_code == status.HTTP_403_FORBIDDEN

    # 3. Instructor access check
    client_inst = auth_client(regression_setup["instructor_id"], is_staff=True, active_role="instructor")
    res_inst = client_inst.get("/api/v1/lms/materials/")
    assert res_inst.status_code == status.HTTP_200_OK
    inst_ids = [m["id"] for m in get_results(res_inst.data)]
    assert mat_draft.id in inst_ids
    assert mat_scheduled.id in inst_ids
    assert mat_published.id in inst_ids

    res_inst_create = client_inst.post(
        "/api/v1/lms/materials/",
        {"section": section.id, "title": "Instructor Valid Note"},
    )
    assert res_inst_create.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_def_lms_02_draft_grades_hidden_from_students(regression_setup, auth_client):
    """
    DEF-LMS-02: Verify that draft and unreleased grades cannot be retrieved by students
    either via list, detail, or query parameter filters, and audit logs are restricted.
    """
    course = regression_setup["course"]
    assignment = Assignment.objects.create(
        course=course,
        author_user_id=regression_setup["instructor_id"],
        title="Lab 1: Asymmetric Cryptography",
        status=ContentStatus.PUBLISHED,
        points_possible=100,
    )
    sub = Submission.objects.create(
        assignment=assignment,
        student_user_id=regression_setup["student1_id"],
        submission_type=SubmissionType.TEXT,
        content_text="Solution content",
        version=1,
    )
    grade = Grade.objects.create(
        submission=sub,
        assessor_user_id=regression_setup["instructor_id"],
        assessor_role=Role.INSTRUCTOR,
        points_awarded=88,
        status=GradeStatus.DRAFT,
        feedback_text="Internal draft evaluation",
    )

    # 1. Student queries when grade is DRAFT
    client_student1 = auth_client(regression_setup["student1_id"], is_staff=False, active_role="student")
    res_list = client_student1.get("/api/v1/lms/grades/")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(get_results(res_list.data)) == 0

    # Query with ?submission= filter
    res_filter = client_student1.get(f"/api/v1/lms/grades/?submission={sub.id}")
    assert res_filter.status_code == status.HTTP_200_OK
    assert len(get_results(res_filter.data)) == 0

    # Direct detail access
    res_detail = client_student1.get(f"/api/v1/lms/grades/{grade.id}/")
    assert res_detail.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    # Audit log access denied to students
    res_audit = client_student1.get(f"/api/v1/lms/grades/{grade.id}/audit_logs/")
    assert res_audit.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    # 2. Release grade and verify student can only see their own released grade
    grade.status = GradeStatus.RELEASED
    grade.save()

    res_released = client_student1.get(f"/api/v1/lms/grades/?submission={sub.id}")
    assert res_released.status_code == status.HTTP_200_OK
    results = get_results(res_released.data)
    assert len(results) == 1
    assert results[0]["id"] == grade.id
    assert results[0]["points_awarded"] == 88

    # Student 2 cannot see Student 1's released grade
    client_student2 = auth_client(regression_setup["student2_id"], is_staff=False, active_role="student")
    res_s2 = client_student2.get(f"/api/v1/lms/grades/?submission={sub.id}")
    assert res_s2.status_code == status.HTTP_200_OK
    assert len(get_results(res_s2.data)) == 0

    # Observer cannot access grades
    client_observer = auth_client(regression_setup["observer_id"], is_staff=False, active_role="observer")
    res_obs = client_observer.get(f"/api/v1/lms/grades/?submission={sub.id}")
    assert res_obs.status_code == status.HTTP_200_OK
    assert len(get_results(res_obs.data)) == 0

    # Instructor can see draft/released and audit logs
    client_inst = auth_client(regression_setup["instructor_id"], is_staff=True, active_role="instructor")
    res_inst_audit = client_inst.get(f"/api/v1/lms/grades/{grade.id}/audit_logs/")
    assert res_inst_audit.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_def_lms_03_observer_forbidden_from_student_submissions(regression_setup, auth_client):
    """
    DEF-LMS-03: Verify that Observers are strictly forbidden from viewing student
    submission records either via SubmissionViewSet or AssignmentViewSet.submissions.
    """
    course = regression_setup["course"]
    assignment = Assignment.objects.create(
        course=course,
        author_user_id=regression_setup["instructor_id"],
        title="Lab 2: Network Security",
        status=ContentStatus.PUBLISHED,
        points_possible=100,
    )
    sub = Submission.objects.create(
        assignment=assignment,
        student_user_id=regression_setup["student1_id"],
        submission_type=SubmissionType.TEXT,
        content_text="Confidential student answers",
        version=1,
    )

    # 1. Observer access attempts
    client_observer = auth_client(regression_setup["observer_id"], is_staff=False, active_role="observer")

    res_obs_list = client_observer.get("/api/v1/lms/submissions/")
    assert res_obs_list.status_code == status.HTTP_200_OK
    assert len(get_results(res_obs_list.data)) == 0

    res_obs_detail = client_observer.get(f"/api/v1/lms/submissions/{sub.id}/")
    assert res_obs_detail.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    res_obs_asgn_subs = client_observer.get(f"/api/v1/lms/assignments/{assignment.id}/submissions/")
    assert res_obs_asgn_subs.status_code == status.HTTP_403_FORBIDDEN

    # 2. Student 2 (non-owner) cannot see Student 1's submission
    client_student2 = auth_client(regression_setup["student2_id"], is_staff=False, active_role="student")
    res_s2_detail = client_student2.get(f"/api/v1/lms/submissions/{sub.id}/")
    assert res_s2_detail.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    # 3. Student 1 (owner) can retrieve their own submission
    client_student1 = auth_client(regression_setup["student1_id"], is_staff=False, active_role="student")
    res_s1_detail = client_student1.get(f"/api/v1/lms/submissions/{sub.id}/")
    assert res_s1_detail.status_code == status.HTTP_200_OK
    assert res_s1_detail.data["id"] == sub.id

    # 4. Instructor can retrieve all submissions
    client_inst = auth_client(regression_setup["instructor_id"], is_staff=True, active_role="instructor")
    res_inst_detail = client_inst.get(f"/api/v1/lms/submissions/{sub.id}/")
    assert res_inst_detail.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_def_lms_04_observer_forbidden_from_mutating_course_workspace(regression_setup, auth_client):
    """
    DEF-LMS-04: Verify that Observers are forbidden from executing mutating actions
    (PATCH, PUT, DELETE) on course workspace or creating sections/assignments.
    """
    course = regression_setup["course"]
    original_title = course.title

    # 1. Observer attempts PATCH on course workspace
    client_observer = auth_client(regression_setup["observer_id"], is_staff=False, active_role="observer")
    res_patch = client_observer.patch(
        f"/api/v1/lms/courses/{course.id}/",
        {"title": "Compromised Workspace Title", "syllabus": "Tampered Syllabus"},
    )
    assert res_patch.status_code == status.HTTP_403_FORBIDDEN
    course.refresh_from_db()
    assert course.title == original_title

    # Observer attempts DELETE on course
    res_del = client_observer.delete(f"/api/v1/lms/courses/{course.id}/")
    assert res_del.status_code == status.HTTP_403_FORBIDDEN

    # Observer attempts POST to create module section
    res_sec = client_observer.post(
        "/api/v1/lms/sections/",
        {"course": course.id, "title": "Unauthorized Section"},
    )
    assert res_sec.status_code == status.HTTP_403_FORBIDDEN

    # Observer attempts POST to create assignment
    res_asgn = client_observer.post(
        "/api/v1/lms/assignments/",
        {"course": course.id, "title": "Unauthorized Exam"},
    )
    assert res_asgn.status_code == status.HTTP_403_FORBIDDEN

    # 2. Student attempts PATCH on course
    client_student = auth_client(regression_setup["student1_id"], is_staff=False, active_role="student")
    res_stu_patch = client_student.patch(
        f"/api/v1/lms/courses/{course.id}/",
        {"title": "Student Workspace Modification"},
    )
    assert res_stu_patch.status_code == status.HTTP_403_FORBIDDEN

    # 3. Instructor can successfully mutate course
    client_inst = auth_client(regression_setup["instructor_id"], is_staff=True, active_role="instructor")
    res_inst_patch = client_inst.patch(
        f"/api/v1/lms/courses/{course.id}/",
        {"title": "Authorized Instructor Update"},
    )
    assert res_inst_patch.status_code == status.HTTP_200_OK
    course.refresh_from_db()
    assert course.title == "Authorized Instructor Update"
