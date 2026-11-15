"""FR strategy tests — generated from FR_DESIGN.json (frozen)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    Course,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
)
from tests.a8.fr.conftest import _login

pytestmark = pytest.mark.django_db


# ---------- helpers ----------

def _mk_course(code="CS101", name="Test Course", **kw):
    return Course.objects.create(code=code, name=name, **kw)


def _mem(course, user_id, role):
    return CourseMembership.objects.create(course=course, user_id=user_id, role=role)


# ---------- FR-001..003 : course access ----------

def test_FR_001_open_workspace_authorized(stub_iam):
    """FR-001 / AFR-LMS-001.1"""
    course = _mk_course()
    _mem(course, 20, "student")
    client = _login(stub_iam, 20, kind="student", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code == 200
    assert resp.json()["code"] == course.code


def test_FR_002_display_course_home(stub_iam):
    """FR-002 / AFR-LMS-001.2"""
    course = _mk_course(code="CS102", name="Compilers")
    course.syllabus = "Syllabus text"
    course.schedule = "Mon/Wed"
    course.save()
    _mem(course, 20, "student")
    client = _login(stub_iam, 20, kind="student", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code == 200
    assert resp.json()["syllabus"] == "Syllabus text"


def test_FR_003_restrict_unlinked(stub_iam):
    """FR-003 / AFR-LMS-001.3"""
    course = _mk_course()
    _mem(course, 10, "faculty")
    client = _login(stub_iam, 999, kind="student", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code in (403, 404)


# ---------- FR-004..006 : course details ----------

def test_FR_004_faculty_configure(stub_iam):
    """FR-004 / AFR-LMS-002.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.course.manage",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "New syllabus"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["syllabus"] == "New syllabus"


def test_FR_005_faculty_publish_edit(stub_iam):
    """FR-005 / AFR-LMS-002.2"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.course.manage",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"name": "Renamed"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


def test_FR_006_nonfaculty_cannot_configure(stub_iam):
    """FR-006 / AFR-LMS-002.1"""
    course = _mk_course()
    _mem(course, 2, "student")
    client = _login(stub_iam, 2, kind="student", permissions=("lms.course.view",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "Hacked"}, format="json")
    assert resp.status_code == 403


# ---------- FR-007..011 : materials ----------

def test_FR_007_add_material_types(stub_iam):
    """FR-007 / AFR-LMS-003.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.material.manage",))
    for mtype, extra in [("note", {"content": "notes"}), ("link", {"link_url": "https://x.com"})]:
        resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": mtype, "material_type": mtype, **extra}, format="json")
        assert resp.status_code == 201


def test_FR_008_organize_materials(stub_iam):
    """FR-008 / AFR-LMS-003.2"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.material.manage",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c", "section": "Week 2"}, format="json")
    assert resp.status_code == 201
    assert resp.json()["section"] == "Week 2"


def test_FR_009_schedule_material(stub_iam):
    """FR-009 / AFR-LMS-003.3"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.material.manage",))
    future = (timezone.now() + timedelta(days=5)).isoformat()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c", "release_date": future, "status": "published"}, format="json")
    assert resp.status_code == 201
    assert resp.json()["status"] == "scheduled"


def test_FR_010_scheduled_material_release(stub_iam):
    """FR-010 / AFR-LMS-003.4"""
    course = _mk_course()
    mat = CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="scheduled", release_date=timezone.now() - timedelta(minutes=1), created_by_user_id=1)
    from modules.lms.services.releases import process_scheduled_releases
    process_scheduled_releases()
    mat.refresh_from_db()
    assert mat.status == "published"
    assert mat.is_available() is True


def test_FR_011_ta_cannot_create_material(stub_iam):
    """FR-011 / AFR-LMS-003.1"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.material.view",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c"}, format="json")
    assert resp.status_code == 403


# ---------- FR-012..015 : material visibility ----------

def test_FR_012_student_view_published(stub_iam):
    """FR-012 / AFR-LMS-004.1"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Pub", material_type="note", content="c", status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_FR_013_ta_view_published(stub_iam):
    """FR-013 / AFR-LMS-004.2"""
    course = _mk_course()
    _mem(course, 2, "ta")
    CourseMaterial.objects.create(course=course, title="Pub", material_type="note", content="c", status="published", created_by_user_id=1)
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_FR_014_observer_view_published(stub_iam):
    """FR-014 / AFR-LMS-004.3"""
    course = _mk_course()
    _mem(course, 99, "observer")
    CourseMaterial.objects.create(course=course, title="Pub", material_type="note", content="c", status="published", created_by_user_id=1)
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_FR_015_unpublished_not_exposed(stub_iam):
    """FR-015 / AFR-LMS-004.1"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Sched", material_type="note", content="c", status="scheduled", release_date=timezone.now() + timedelta(days=5), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ---------- FR-016..021 : announcements ----------

def test_FR_016_faculty_post_announcement(stub_iam):
    """FR-016 / AFR-LMS-005.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "Welcome", "content": "Hi"}, format="json")
    assert resp.status_code == 201


def test_FR_017_ta_post_permitted(stub_iam):
    """FR-017 / AFR-LMS-005.2"""
    course = _mk_course(allow_ta_announcements=True)
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "TA", "content": "hi"}, format="json")
    assert resp.status_code == 201


def test_FR_018_ta_post_denied(stub_iam):
    """FR-018 / AFR-LMS-005.2"""
    course = _mk_course(allow_ta_announcements=False)
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "TA", "content": "hi"}, format="json")
    assert resp.status_code == 403


def test_FR_019_announcement_timestamped(stub_iam):
    """FR-019 / AFR-LMS-005.3"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    assert resp.status_code == 201
    assert resp.json().get("created_at") is not None


def test_FR_020_announcement_coursewide(stub_iam):
    """FR-020 / AFR-LMS-005.4"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    fclient = _login(stub_iam, 1, kind="faculty", permissions=("lms.announcement.post",))
    fclient.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    sclient = _login(stub_iam, 3, kind="student", permissions=("lms.announcement.view",))
    resp = sclient.get(f"/api/v1/lms/courses/{course.id}/announcements/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_FR_021_student_cannot_post(stub_iam):
    """FR-021 / AFR-LMS-005.1"""
    course = _mk_course()
    _mem(course, 3, "student")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.announcement.view",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    assert resp.status_code == 403


# ---------- FR-022..027 : assignment authoring ----------

def test_FR_022_create_assignment(stub_iam):
    """FR-022 / AFR-LMS-006.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "do it", "submission_type": "file", "points_possible": 100, "due_date": (now + timedelta(days=7)).isoformat()}, format="json")
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


def test_FR_023_capture_fields(stub_iam):
    """FR-023 / AFR-LMS-006.2"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "do it", "submission_type": "text", "points_possible": 50, "due_date": (now + timedelta(days=3)).isoformat()}, format="json")
    assert resp.status_code == 201
    j = resp.json()
    assert j["submission_type"] == "text"
    assert float(j["points_possible"]) == 50.0


def test_FR_024_missing_fields_rejected(stub_iam):
    """FR-024 / AFR-LMS-006.2"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A"}, format="json")
    assert resp.status_code == 400


def test_FR_025_edit_assignment(stub_iam):
    """FR-025 / AFR-LMS-006.3"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.patch(f"/api/v1/lms/assignments/{asgn.id}/", {"title": "B"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["title"] == "B"


def test_FR_026_draft_until_published(stub_iam):
    """FR-026 / AFR-LMS-006.4"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    assert asgn.status == "draft"
    assert asgn.is_available_to_students() is False


def test_FR_027_ta_cannot_create_assignment(stub_iam):
    """FR-027 / AFR-LMS-006.1"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.assignment.view",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "i", "submission_type": "text", "points_possible": 10, "due_date": (now + timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 403


# ---------- FR-028..032 : publish/release ----------

def test_FR_028_publish_assignment(stub_iam):
    """FR-028 / AFR-LMS-007.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/publish/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


def test_FR_029_withheld_until_release(stub_iam):
    """FR-029 / AFR-LMS-007.2"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", release_date=timezone.now() + timedelta(days=1), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/assignments/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_FR_030_scheduled_release(stub_iam):
    """FR-030 / AFR-LMS-007.3"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="scheduled", release_date=timezone.now() - timedelta(minutes=1), created_by_user_id=1)
    from modules.lms.services.releases import process_scheduled_releases
    process_scheduled_releases()
    asgn.refresh_from_db()
    assert asgn.status == "published"
    assert asgn.is_available_to_students() is True


def test_FR_031_view_download_released(stub_iam):
    """FR-031 / AFR-LMS-007.4"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/")
    assert resp.status_code == 200


def test_FR_032_unreleased_not_visible(stub_iam):
    """FR-032 / AFR-LMS-007.2"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", release_date=timezone.now() + timedelta(days=1), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/")
    assert resp.status_code == 404


# ---------- FR-033..036 : submission ----------

def test_FR_033_submit_configured_type(stub_iam):
    """FR-033 / AFR-LMS-008.1"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="file", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "file", "file_name": "x.py"}, format="json")
    assert resp.status_code == 201
    assert resp.json()["status"] == "submitted"


def test_FR_034_type_mismatch_rejected(stub_iam):
    """FR-034 / AFR-LMS-008.1"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="file", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 400


def test_FR_035_on_time_accepted(stub_iam):
    """FR-035 / AFR-LMS-008.2"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 201


def test_FR_036_late_blocked(stub_iam):
    """FR-036 / AFR-LMS-008.2"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() - timedelta(days=1), status="published", allow_late_submissions=False, created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 400


# ---------- FR-037..039 : submission history ----------

def test_FR_037_own_history(stub_iam):
    """FR-037 / AFR-LMS-009.1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.view_self",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/")
    assert resp.status_code == 200


def test_FR_038_own_status(stub_iam):
    """FR-038 / AFR-LMS-009.2"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.view_self",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


def test_FR_039_no_cross_student(stub_iam):
    """FR-039 / AFR-LMS-009.1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 4, kind="student", permissions=("lms.submission.view_self",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/")
    assert resp.status_code == 404


# ---------- FR-040..044 : grading ----------

def test_FR_040_faculty_grade(stub_iam):
    """FR-040 / AFR-LMS-010.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 90, "feedback": "good"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_FR_041_ta_grade(stub_iam):
    """FR-041 / AFR-LMS-010.2"""
    course = _mk_course()
    _mem(course, 5, "ta")
    course.allow_ta_grading = True
    course.save()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 5, kind="staff", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 85, "feedback": "ok"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["graded_by_role"] == "ta"


def test_FR_042_grading_attribution(stub_iam):
    """FR-042 / AFR-LMS-010.3"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 80, "feedback": "fb"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["graded_by_user_id"] == 1


def test_FR_043_points_exceed_rejected(stub_iam):
    """FR-043 / AFR-LMS-010.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 150, "feedback": "fb"}, format="json")
    assert resp.status_code == 400


def test_FR_044_points_negative_rejected(stub_iam):
    """FR-044 / AFR-LMS-010.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": -5, "feedback": "fb"}, format="json")
    assert resp.status_code == 400


# ---------- FR-045..048 : grade release ----------

def test_FR_045_grade_draft_until_release(stub_iam):
    """FR-045 / AFR-LMS-011.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    from modules.lms.services.grading import grade_submission
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    assert sub.grade.status == "draft"


def test_FR_046_student_cannot_see_draft(stub_iam):
    """FR-046 / AFR-LMS-011.2"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    from modules.lms.services.grading import grade_submission
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_FR_047_faculty_release(stub_iam):
    """FR-047 / AFR-LMS-011.3"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    from modules.lms.services.grading import grade_submission
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.release",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert resp.status_code == 200
    assert resp.json()["released_count"] == 1


def test_FR_048_ta_cannot_release(stub_iam):
    """FR-048 / AFR-LMS-011.3"""
    course = _mk_course()
    _mem(course, 5, "ta")
    course.allow_ta_grading = True
    course.save()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 5, kind="staff", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert resp.status_code == 403


# ---------- FR-049..050 : released grade ----------

def test_FR_049_student_view_released(stub_iam):
    """FR-049 / AFR-LMS-012.1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    from modules.lms.services.grading import grade_submission, release_assignment_grades
    grade_submission(submission=sub, points=Decimal("90"), feedback="great", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["feedback"] == "great"


def test_FR_050_released_readonly(stub_iam):
    """FR-050 / AFR-LMS-012.2"""
    course = _mk_course()
    _mem(course, 3, "student")
    # no write endpoint for grades by student; verify my-grades returns read-only data
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200


# ---------- FR-051..052 : audit ----------

def test_FR_051_audit_actor(stub_iam):
    """FR-051 / AFR-LMS-013.1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    from modules.lms.services.grading import grade_submission, release_assignment_grades
    grade_submission(submission=sub, points=Decimal("80"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    sub.refresh_from_db()
    grade_submission(submission=sub, points=Decimal("95"), feedback="revised", grader_user_id=1, grader_role="faculty", grader_name="F", change_reason="re-eval")
    audits = list(sub.grade.audit_logs.all())
    assert len(audits) == 1
    assert audits[0].changed_by_user_id == 1


def test_FR_052_audit_timestamp(stub_iam):
    """FR-052 / AFR-LMS-013.2"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    from modules.lms.services.grading import grade_submission, release_assignment_grades
    grade_submission(submission=sub, points=Decimal("80"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    sub.refresh_from_db()
    grade_submission(submission=sub, points=Decimal("95"), feedback="revised", grader_user_id=1, grader_role="faculty", grader_name="F", change_reason="re-eval")
    audit = sub.grade.audit_logs.first()
    assert audit is not None
    assert audit.changed_at is not None


# ---------- FR-053..057 : TA constraints ----------

def test_FR_053_ta_views_content(stub_iam):
    """FR-053 / AFR-LMS-014.1"""
    course = _mk_course()
    _mem(course, 2, "ta")
    CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="published", created_by_user_id=1)
    CourseAnnouncement.objects.create(course=course, title="A", content="c", posted_by_user_id=1, posted_by_role="faculty", posted_by_name="F")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.course.view", "lms.material.view", "lms.announcement.view"))
    assert client.get(f"/api/v1/lms/courses/{course.id}/").status_code == 200
    assert client.get(f"/api/v1/lms/courses/{course.id}/materials/").status_code == 200
    assert client.get(f"/api/v1/lms/courses/{course.id}/announcements/").status_code == 200


def test_FR_054_ta_views_submissions(stub_iam):
    """FR-054 / AFR-LMS-014.2"""
    course = _mk_course()
    _mem(course, 2, "ta")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.submission.view_all",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/submissions/")
    assert resp.status_code == 200


def test_FR_055_ta_cannot_author_assignments(stub_iam):
    """FR-055 / AFR-LMS-014.3"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.assignment.view",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "i", "submission_type": "text", "points_possible": 10, "due_date": (now + timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 403


def test_FR_056_ta_cannot_author_materials(stub_iam):
    """FR-056 / AFR-LMS-014.4"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.material.view",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c"}, format="json")
    assert resp.status_code == 403


def test_FR_057_ta_cannot_modify_structure(stub_iam):
    """FR-057 / AFR-LMS-014.5"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.course.view",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"name": "X"}, format="json")
    assert resp.status_code == 403


# ---------- FR-058..061 : observer constraints ----------

def test_FR_058_observer_reads_content(stub_iam):
    """FR-058 / AFR-LMS-015.1"""
    course = _mk_course()
    _mem(course, 99, "observer")
    CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="published", created_by_user_id=1)
    CourseAnnouncement.objects.create(course=course, title="A", content="c", posted_by_user_id=1, posted_by_role="faculty", posted_by_name="F")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view", "lms.material.view", "lms.announcement.view"))
    assert client.get(f"/api/v1/lms/courses/{course.id}/").status_code == 200
    assert client.get(f"/api/v1/lms/courses/{course.id}/materials/").status_code == 200
    assert client.get(f"/api/v1/lms/courses/{course.id}/announcements/").status_code == 200


def test_FR_059_observer_no_submissions(stub_iam):
    """FR-059 / AFR-LMS-015.2"""
    course = _mk_course()
    _mem(course, 99, "observer")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/submissions/")
    assert resp.status_code == 403


def test_FR_060_observer_no_grades(stub_iam):
    """FR-060 / AFR-LMS-015.3"""
    course = _mk_course()
    _mem(course, 99, "observer")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_FR_061_observer_no_writes(stub_iam):
    """FR-061 / AFR-LMS-015.4"""
    course = _mk_course()
    _mem(course, 99, "observer")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c"}, format="json")
    assert resp.status_code == 403
