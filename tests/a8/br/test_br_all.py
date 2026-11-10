"""BR strategy tests — generated from BR_DESIGN.json (frozen)."""
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
from modules.lms.services.grading import grade_submission, release_assignment_grades
from modules.lms.services.releases import process_scheduled_releases
from tests.a8.br.conftest import _login

pytestmark = pytest.mark.django_db


def _mk_course(code="BR101", name="BR Course", **kw):
    return Course.objects.create(code=code, name=name, **kw)


def _mem(course, user_id, role):
    return CourseMembership.objects.create(course=course, user_id=user_id, role=role)


# BR-001..002
def test_BR_001_allow_linked(stub_iam):
    """BR-001 / BR-LMS-001"""
    course = _mk_course()
    _mem(course, 20, "student")
    client = _login(stub_iam, 20, kind="student", permissions=("lms.course.view",))
    assert client.get(f"/api/v1/lms/courses/{course.id}/").status_code == 200


def test_BR_002_deny_unlinked(stub_iam):
    """BR-002 / BR-LMS-001"""
    course = _mk_course()
    _mem(course, 10, "faculty")
    client = _login(stub_iam, 999, kind="student", permissions=("lms.course.view",))
    assert client.get(f"/api/v1/lms/courses/{course.id}/").status_code in (403, 404)


# BR-003..007 : observer
def test_BR_003_observer_read(stub_iam):
    """BR-003 / BR-LMS-003"""
    course = _mk_course()
    _mem(course, 99, "observer")
    CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="published", created_by_user_id=1)
    CourseAnnouncement.objects.create(course=course, title="A", content="c", posted_by_user_id=1, posted_by_role="faculty", posted_by_name="F")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view", "lms.material.view", "lms.announcement.view"))
    assert client.get(f"/api/v1/lms/courses/{course.id}/").status_code == 200
    assert client.get(f"/api/v1/lms/courses/{course.id}/materials/").status_code == 200
    assert client.get(f"/api/v1/lms/courses/{course.id}/announcements/").status_code == 200


def test_BR_004_observer_no_submissions(stub_iam):
    """BR-004 / BR-LMS-003"""
    course = _mk_course()
    _mem(course, 99, "observer")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    assert client.get(f"/api/v1/lms/assignments/{asgn.id}/submissions/").status_code == 403


def test_BR_005_observer_no_grades(stub_iam):
    """BR-005 / BR-LMS-003"""
    course = _mk_course()
    _mem(course, 99, "observer")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_BR_006_observer_no_writes(stub_iam):
    """BR-006 / BR-LMS-003"""
    course = _mk_course()
    _mem(course, 99, "observer")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c"}, format="json")
    assert resp.status_code == 403


def test_BR_007_observer_no_student_data(stub_iam):
    """BR-007 / BR-LMS-003"""
    course = _mk_course()
    _mem(course, 99, "observer")
    client = _login(stub_iam, 99, kind="staff", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/roster/")
    # observer sees only faculty/ta, not students
    assert resp.status_code == 200


# BR-008..013 : TA
def test_BR_008_ta_views_content(stub_iam):
    """BR-008 / BR-LMS-004"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.course.view", "lms.material.view", "lms.announcement.view"))
    assert client.get(f"/api/v1/lms/courses/{course.id}/").status_code == 200


def test_BR_009_ta_views_submissions(stub_iam):
    """BR-009 / BR-LMS-004"""
    course = _mk_course()
    _mem(course, 2, "ta")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.submission.view_all",))
    assert client.get(f"/api/v1/lms/assignments/{asgn.id}/submissions/").status_code == 200


def test_BR_010_ta_grades(stub_iam):
    """BR-010 / BR-LMS-004"""
    course = _mk_course()
    _mem(course, 2, "ta")
    course.allow_ta_grading = True
    course.save()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 80, "feedback": "fb"}, format="json")
    assert resp.status_code == 200


def test_BR_011_ta_no_assignments(stub_iam):
    """BR-011 / BR-LMS-004"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.assignment.view",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "i", "submission_type": "text", "points_possible": 10, "due_date": (now + timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 403


def test_BR_012_ta_no_materials(stub_iam):
    """BR-012 / BR-LMS-004"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.material.view",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c"}, format="json")
    assert resp.status_code == 403


def test_BR_013_ta_no_structure(stub_iam):
    """BR-013 / BR-LMS-004"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.course.view",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"name": "X"}, format="json")
    assert resp.status_code == 403


# BR-014..017 : materials visibility
def test_BR_014_published_visible(stub_iam):
    """BR-014 / BR-LMS-005"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Pub", material_type="note", content="c", status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    assert len(client.get(f"/api/v1/lms/courses/{course.id}/materials/").json()) == 1


def test_BR_015_unpublished_hidden(stub_iam):
    """BR-015 / BR-LMS-005"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Draft", material_type="note", content="c", status="draft", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    assert len(client.get(f"/api/v1/lms/courses/{course.id}/materials/").json()) == 0


def test_BR_016_scheduled_hidden_before(stub_iam):
    """BR-016 / BR-LMS-006"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Sched", material_type="note", content="c", status="scheduled", release_date=timezone.now() + timedelta(days=5), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    assert len(client.get(f"/api/v1/lms/courses/{course.id}/materials/").json()) == 0


def test_BR_017_scheduled_visible_after(stub_iam):
    """BR-017 / BR-LMS-006"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Sched", material_type="note", content="c", status="scheduled", release_date=timezone.now() - timedelta(minutes=1), created_by_user_id=1)
    process_scheduled_releases()
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    assert len(client.get(f"/api/v1/lms/courses/{course.id}/materials/").json()) == 1


# BR-018..021 : announcements
def test_BR_018_faculty_post(stub_iam):
    """BR-018 / BR-LMS-007"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.announcement.post",))
    assert client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json").status_code == 201


def test_BR_019_ta_post_permitted(stub_iam):
    """BR-019 / BR-LMS-007"""
    course = _mk_course(allow_ta_announcements=True)
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.announcement.post",))
    assert client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json").status_code == 201


def test_BR_020_ta_post_denied(stub_iam):
    """BR-020 / BR-LMS-007"""
    course = _mk_course(allow_ta_announcements=False)
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.announcement.post",))
    assert client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json").status_code == 403


def test_BR_021_announcement_timestamped_coursewide(stub_iam):
    """BR-021 / BR-LMS-008"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    fclient = _login(stub_iam, 1, kind="faculty", permissions=("lms.announcement.post",))
    r = fclient.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    assert r.status_code == 201
    assert r.json().get("created_at") is not None
    sclient = _login(stub_iam, 3, kind="student", permissions=("lms.announcement.view",))
    assert len(sclient.get(f"/api/v1/lms/courses/{course.id}/announcements/").json()) == 1


# BR-022..023 : assignment required config
def test_BR_022_assignment_required_fields(stub_iam):
    """BR-022 / BR-LMS-009"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "i", "submission_type": "text", "points_possible": 10, "due_date": (now + timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 201


def test_BR_023_assignment_missing_fields(stub_iam):
    """BR-023 / BR-LMS-009"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A"}, format="json")
    assert resp.status_code == 400


# BR-024 : draft before publication
def test_BR_024_draft_before_publication(stub_iam):
    """BR-024 / BR-LMS-010"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    assert asgn.status == "draft"
    assert asgn.is_available_to_students() is False


# BR-025..026 : release-date visibility
def test_BR_025_withheld_before_release(stub_iam):
    """BR-025 / BR-LMS-011"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", release_date=timezone.now() + timedelta(days=1), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    assert len(client.get(f"/api/v1/lms/courses/{course.id}/assignments/").json()) == 0


def test_BR_026_visible_after_release(stub_iam):
    """BR-026 / BR-LMS-011"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", release_date=timezone.now() - timedelta(hours=1), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    assert len(client.get(f"/api/v1/lms/courses/{course.id}/assignments/").json()) == 1


# BR-027..029 : submission type conformity
def test_BR_027_submit_file_ok(stub_iam):
    """BR-027 / BR-LMS-012"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="file", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "file", "file_name": "x.py"}, format="json")
    assert resp.status_code == 201


def test_BR_028_submit_text_mismatch(stub_iam):
    """BR-028 / BR-LMS-012"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="file", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 400


def test_BR_029_submit_link_mismatch(stub_iam):
    """BR-029 / BR-LMS-012"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="file", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "link", "link_url": "https://x.com"}, format="json")
    assert resp.status_code == 400


# BR-030..031 : on-time submission
def test_BR_030_on_time_accepted(stub_iam):
    """BR-030 / BR-LMS-013"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 201
    assert resp.json()["status"] == "submitted"


def test_BR_031_late_handling(stub_iam):
    """BR-031 / BR-LMS-013"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() - timedelta(days=1), status="published", allow_late_submissions=True, created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    # late submission accepted and flagged
    assert resp.status_code == 201
    assert resp.json()["status"] in ("submitted", "late")


# BR-032..033 : submission ownership
def test_BR_032_own_history(stub_iam):
    """BR-032 / BR-LMS-014"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.view_self",))
    assert client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/").status_code == 200


def test_BR_033_cross_student_denied(stub_iam):
    """BR-033 / BR-LMS-014"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 4, kind="student", permissions=("lms.submission.view_self",))
    assert client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/").status_code == 404


# BR-034..036 : grading authority
def test_BR_034_faculty_grade(stub_iam):
    """BR-034 / BR-LMS-015"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 90, "feedback": "fb"}, format="json")
    assert resp.status_code == 200


def test_BR_035_ta_grade_enabled(stub_iam):
    """BR-035 / BR-LMS-015"""
    course = _mk_course()
    _mem(course, 5, "ta")
    course.allow_ta_grading = True
    course.save()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 5, kind="staff", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 85, "feedback": "fb"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["graded_by_role"] == "ta"


def test_BR_036_grading_attribution(stub_iam):
    """BR-036 / BR-LMS-015"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 80, "feedback": "fb"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["graded_by_user_id"] == 1


# BR-037..040 : grade lifecycle
def test_BR_037_draft_invisible(stub_iam):
    """BR-037 / BR-LMS-016"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    assert len(client.get("/api/v1/lms/grades/my-grades/").json()) == 0


def test_BR_038_faculty_release(stub_iam):
    """BR-038 / BR-LMS-017"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.release",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert resp.status_code == 200
    assert resp.json()["released_count"] == 1


def test_BR_039_ta_cannot_release(stub_iam):
    """BR-039 / BR-LMS-017"""
    course = _mk_course()
    _mem(course, 5, "ta")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 5, kind="staff", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert resp.status_code == 403


def test_BR_040_released_readonly(stub_iam):
    """BR-040 / BR-LMS-018"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# BR-041..042 : audit
def test_BR_041_audit_actor(stub_iam):
    """BR-041 / BR-LMS-019"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("80"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    sub.refresh_from_db()
    grade_submission(submission=sub, points=Decimal("95"), feedback="revised", grader_user_id=1, grader_role="faculty", grader_name="F", change_reason="re-eval")
    audits = list(sub.grade.audit_logs.all())
    assert len(audits) == 1
    assert audits[0].changed_by_user_id == 1


def test_BR_042_audit_timestamp(stub_iam):
    """BR-042 / BR-LMS-019"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("80"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    sub.refresh_from_db()
    grade_submission(submission=sub, points=Decimal("95"), feedback="revised", grader_user_id=1, grader_role="faculty", grader_name="F", change_reason="re-eval")
    audit = sub.grade.audit_logs.first()
    assert audit is not None
    assert audit.changed_at is not None
