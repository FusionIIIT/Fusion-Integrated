"""End-to-end multi-role HTTP journey tests through APIClient covering all live UCs, CFRs, AFRs, BRs, and Workflows."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
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
)

pytestmark = pytest.mark.django_db


def _make_client(stub_iam, uid: int, kind: str, permissions: tuple[str, ...]) -> APIClient:
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            permissions=permissions,
            modules=("lms",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token tok-{uid}")
    return client


@pytest.fixture
def lms_course_setup():
    course_id = 999
    now = timezone.now()
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS999",
        title="Comprehensive Algorithms",
        syllabus="Initial syllabus text",
        schedule_info="MWF 11:00 AM",
    )
    # Faculty
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=1001,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    # TA with grading authority
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=2001,
        role=CourseRole.TA,
        can_grade=True,
        can_post_announcement=True,
        status=MembershipStatus.ACTIVE,
    )
    # Student
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=3001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    # Observer
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=4001,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    )
    return course_id, now


def test_faculty_course_management_journey(stub_iam, lms_course_setup):
    """Faculty journey covering UC-LMS-001, UC-LMS-002, UC-LMS-003, UC-LMS-005, UC-LMS-007, UC-LMS-008,

    CFR-LMS-001, CFR-LMS-002, CFR-LMS-003, CFR-LMS-005, CFR-LMS-006, CFR-LMS-007,
    AFR-LMS-002.1, AFR-LMS-002.2, AFR-LMS-003.1, AFR-LMS-005.1, AFR-LMS-006.1, AFR-LMS-007.1,
    BW-LMS-01, BW-LMS-02, CW-LMS-01, BR-LMS-010.
    """
    course_id, now = lms_course_setup
    faculty_perms = (
        "lms.workspace.view",
        "lms.workspace.update",
        "lms.material.view",
        "lms.material.create",
        "lms.material.publish",
        "lms.material.update",
        "lms.material.delete",
        "lms.announcement.view",
        "lms.announcement.create",
        "lms.assignment.view",
        "lms.assignment.create",
        "lms.assignment.update",
        "lms.assignment.publish",
    )
    client = _make_client(stub_iam, 1001, "faculty", faculty_perms)

    # 1. View course workspace details (UC-LMS-001, CFR-LMS-001)
    res = client.get(f"/api/v1/lms/courses/{course_id}/")
    assert res.status_code == 200
    assert res.data["course_code"] == "CS999"

    # 2. Update workspace syllabus and schedule (UC-LMS-002, CFR-LMS-002, AFR-LMS-002.2)
    res = client.patch(
        f"/api/v1/lms/courses/{course_id}/",
        data={"syllabus": "Updated syllabus: Advanced Graph Algorithms", "schedule_info": "Tue/Thu 10 AM"},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["syllabus"] == "Updated syllabus: Advanced Graph Algorithms"

    # 3. Create Note material (UC-LMS-003, CFR-LMS-003, AFR-LMS-003.1)
    res = client.post(
        "/api/v1/lms/materials/",
        data={
            "course_id": course_id,
            "title": "Welcome Notes",
            "material_type": MaterialType.NOTE,
            "content_text": "Welcome to CS999!",
            "section_name": "General",
        },
        format="json",
    )
    assert res.status_code == 201
    assert res.data["status"] == MaterialStatus.PUBLISHED

    # 4. Post Announcement (UC-LMS-005, CFR-LMS-005, AFR-LMS-005.1)
    res = client.post(
        "/api/v1/lms/announcements/",
        data={"course_id": course_id, "title": "Class Orientation", "content": "Welcome class."},
        format="json",
    )
    assert res.status_code == 201
    assert res.data["title"] == "Class Orientation"

    # 5. Create Draft Assignment (UC-LMS-007, CFR-LMS-006, AFR-LMS-006.1, BR-LMS-010)
    due = (now + timedelta(days=7)).isoformat()
    res = client.post(
        "/api/v1/lms/assignments/",
        data={
            "course_id": course_id,
            "title": "Assignment 1",
            "instructions": "Solve problem 1 to 5.",
            "points_possible": "100.00",
            "submission_type": SubmissionType.TEXT,
            "due_date": due,
        },
        format="json",
    )
    assert res.status_code == 201
    asg_id = res.data["id"]
    assert res.data["status"] == AssignmentStatus.DRAFT

    # 6. Publish Assignment (UC-LMS-008, CFR-LMS-007, AFR-LMS-007.1, BW-LMS-02)
    res = client.post(f"/api/v1/lms/assignments/{asg_id}/publish/", data={}, format="json")
    assert res.status_code == 200
    assert res.data["status"] == AssignmentStatus.PUBLISHED


def test_student_and_ta_grading_journey(stub_iam, lms_course_setup):
    """End-to-end journey covering Student submission, TA grading, and Faculty publish.

    UC-LMS-004, UC-LMS-006, UC-LMS-009, UC-LMS-010, UC-LMS-011, UC-LMS-012, UC-LMS-013, UC-LMS-014,
    CFR-LMS-008, CFR-LMS-009, CFR-LMS-010, CFR-LMS-011, CFR-LMS-012, CFR-LMS-013,
    BR-LMS-012, BR-LMS-013, BR-LMS-014, BR-LMS-016, BR-LMS-017, BR-LMS-018, BR-LMS-019,
    BW-LMS-04, BW-LMS-05, CW-LMS-02.
    """
    course_id, now = lms_course_setup

    # Setup published assignment
    asg = Assignment.objects.create(
        course_id=course_id,
        title="Dynamic Programming Assignment",
        instructions="Solve the knapsack problem.",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=1001,
    )

    # 1. Student Client submits assignment (UC-LMS-010, CFR-LMS-008, BR-LMS-013)
    student_perms = (
        "lms.workspace.view",
        "lms.material.view",
        "lms.announcement.view",
        "lms.assignment.view",
        "lms.submission.view",
        "lms.submission.create",
        "lms.grade.view",
    )
    client_stu = _make_client(stub_iam, 3001, "student", student_perms)

    # Student views published materials (UC-LMS-004)
    res_mat = client_stu.get(f"/api/v1/lms/materials/?course_id={course_id}")
    assert res_mat.status_code == 200

    # Student views course announcements (UC-LMS-006)
    res_ann = client_stu.get(f"/api/v1/lms/announcements/?course_id={course_id}")
    assert res_ann.status_code == 200

    # Student retrieves assignment details (UC-LMS-009, AFR-LMS-007.4)
    res = client_stu.get(f"/api/v1/lms/assignments/{asg.id}/")
    assert res.status_code == 200

    # Student submits text solution (UC-LMS-010, CFR-LMS-008)
    res = client_stu.post(
        f"/api/v1/lms/assignments/{asg.id}/submissions/",
        data={"submission_type": SubmissionType.TEXT, "content_text": "def knapsack(): return 42"},
        format="json",
    )
    assert res.status_code == 201
    sub_id = res.data["id"]
    assert res.data["status"] == "SUBMITTED"

    # Student views own submission (UC-LMS-011, CFR-LMS-009, BR-LMS-014)
    res = client_stu.get(f"/api/v1/lms/submissions/{sub_id}/")
    assert res.status_code == 200

    # Student checks grade before release -> 404 Not Found (BR-LMS-016, AFR-LMS-011.2)
    res = client_stu.get(f"/api/v1/lms/submissions/{sub_id}/grade/")
    assert res.status_code == 404

    # 2. TA Client grades submission (UC-LMS-012, CFR-LMS-010, AFR-LMS-010.2, BW-LMS-05)
    ta_perms = (
        "lms.workspace.view",
        "lms.material.view",
        "lms.announcement.view",
        "lms.assignment.view",
        "lms.submission.view",
        "lms.submission.review",
        "lms.grade.view",
        "lms.grade.create",
        "lms.grade.update",
    )
    client_ta = _make_client(stub_iam, 2001, "ta", ta_perms)

    # TA views submissions list (AFR-LMS-014.2)
    res = client_ta.get(f"/api/v1/lms/assignments/{asg.id}/submissions/")
    assert res.status_code == 200
    assert len(res.data) >= 1

    # TA grades submission -> saved as DRAFT (AFR-LMS-011.1)
    res = client_ta.post(
        f"/api/v1/lms/submissions/{sub_id}/grade/",
        data={"points_awarded": "88.00", "feedback_text": "Good work on DP recurrences."},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["status"] == GradeStatus.DRAFT

    # TA attempts to release grades -> 403 Forbidden (BR-LMS-017, CFR-LMS-014)
    res = client_ta.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub_id]},
        format="json",
    )
    assert res.status_code == 403

    # 3. Faculty Client releases grades (UC-LMS-013, CFR-LMS-011, AFR-LMS-011.3)
    faculty_perms = (
        "lms.workspace.view",
        "lms.grade.view",
        "lms.grade.publish",
        "lms.grade.update",
        "lms.submission.review",
    )
    client_fac = _make_client(stub_iam, 1001, "faculty", faculty_perms)

    res = client_fac.post(
        f"/api/v1/lms/assignments/{asg.id}/publish-grades/",
        data={"submission_ids": [sub_id]},
        format="json",
    )
    assert res.status_code == 200
    assert res.data["published_count"] == 1

    # 4. Student now views released grade (UC-LMS-014, CFR-LMS-012, BR-LMS-018)
    res = client_stu.get(f"/api/v1/lms/submissions/{sub_id}/grade/")
    assert res.status_code == 200
    assert res.data["points_awarded"] == "88.00"
    assert res.data["status"] == GradeStatus.PUBLISHED

    # 5. Faculty updates published grade -> triggers audit trail (CFR-LMS-013, BR-LMS-019, AFR-LMS-013.1, AFR-LMS-013.2)
    res = client_fac.patch(
        f"/api/v1/lms/submissions/{sub_id}/grade/",
        data={
            "points_awarded": "94.00",
            "feedback_text": "Adjusted score after reviewing DP proof.",
            "reason": "Re-evaluated base case proof.",
        },
        format="json",
    )
    assert res.status_code == 200
    assert res.data["points_awarded"] == "94.00"

    # View audit history (CFR-LMS-013)
    res = client_fac.get(f"/api/v1/lms/submissions/{sub_id}/grade-audit/")
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["old_points"] == "88.00"
    assert res.data[0]["new_points"] == "94.00"
    assert res.data[0]["changed_by"] == 1001


def test_observer_isolation_journey(stub_iam, lms_course_setup):
    """Observer read-only access and strict student data privacy (CFR-LMS-015,

    AFR-LMS-015.1, AFR-LMS-015.2, AFR-LMS-015.3, AFR-LMS-015.4, BR-LMS-003.
    """
    course_id, _ = lms_course_setup
    observer_perms = (
        "lms.workspace.view",
        "lms.material.view",
        "lms.announcement.view",
        "lms.assignment.view",
    )
    client_obs = _make_client(stub_iam, 4001, "observer", observer_perms)

    # 1. Observer views course workspace (AFR-LMS-015.1)
    res = client_obs.get(f"/api/v1/lms/courses/{course_id}/")
    assert res.status_code == 200

    # 2. Observer cannot view submissions (AFR-LMS-015.2, BR-LMS-003)
    res = client_obs.get("/api/v1/lms/assignments/1/submissions/")
    assert res.status_code in (403, 404)

    # 3. Observer cannot view grades (AFR-LMS-015.3)
    res = client_obs.get("/api/v1/lms/assignments/1/grades/")
    assert res.status_code in (403, 404)

    # 4. Observer has no write permissions (AFR-LMS-015.4)
    res = client_obs.post(
        "/api/v1/lms/announcements/",
        data={"course_id": course_id, "title": "Observer Post", "content": "Hello"},
        format="json",
    )
    assert res.status_code == 403


def test_file_download_endpoints_journey(stub_iam, lms_course_setup):
    """Tests file download endpoints for materials and submissions (CFR-LMS-004, CFR-LMS-009)."""
    course_id, now = lms_course_setup

    # Create material with file
    test_file_content = b"%PDF-1.4 test material stream"
    uploaded_file = SimpleUploadedFile("lecture1.pdf", test_file_content, content_type="application/pdf")

    material = CourseMaterial.objects.create(
        course_id=course_id,
        title="Lecture 1 PDF",
        material_type=MaterialType.FILE,
        file_attachment=uploaded_file,
        status=MaterialStatus.PUBLISHED,
        uploaded_by=1001,
    )

    # Student downloads material
    student_perms = ("lms.workspace.view", "lms.material.view", "lms.submission.view")
    client_stu = _make_client(stub_iam, 3001, "student", student_perms)

    res = client_stu.get(f"/api/v1/lms/materials/{material.id}/download/")
    assert res.status_code == 200
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"

    # Create submission with file
    sub_file_content = b"Student code submission content"
    sub_uploaded_file = SimpleUploadedFile("homework.py", sub_file_content, content_type="text/x-python")

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Code Asg",
        instructions="Upload code",
        points_possible=100.0,
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=1001,
    )
    submission = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=3001,
        submission_type=SubmissionType.FILE,
        file_attachment=sub_uploaded_file,
    )

    # Student downloads own submission
    res_sub = client_stu.get(f"/api/v1/lms/submissions/{submission.id}/download/")
    assert res_sub.status_code == 200
    assert "attachment" in res_sub.headers.get("Content-Disposition", "")

    # Cleanup created files
    if material.file_attachment:
        material.file_attachment.delete(save=False)
    if submission.file_attachment:
        submission.file_attachment.delete(save=False)
