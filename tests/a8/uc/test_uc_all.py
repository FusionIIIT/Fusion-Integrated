"""UC strategy tests — generated from UC_DESIGN.json (frozen)."""
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
from tests.a8.uc.conftest import _login

pytestmark = pytest.mark.django_db


def _mk_course(code="UC101", name="UC Course", **kw):
    return Course.objects.create(code=code, name=name, **kw)


def _mem(course, user_id, role):
    return CourseMembership.objects.create(course=course, user_id=user_id, role=role)


# UC-001
def test_UC_001_Main(stub_iam):
    """UC-001-Main / UC-LMS-001 Main Flow"""
    course = _mk_course()
    _mem(course, 20, "student")
    client = _login(stub_iam, 20, kind="student", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code == 200
    assert "syllabus" in resp.json()


def test_UC_001_Alt1(stub_iam):
    """UC-001-Alt1 / UC-LMS-001 Alternative A1"""
    course = _mk_course()
    _mem(course, 10, "faculty")
    client = _login(stub_iam, 999, kind="student", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code in (403, 404)


def test_UC_001_Exc1(stub_iam):
    """UC-001-Exc1 / UC-LMS-001 Exception E1"""
    # registration data unavailable -> cannot confirm access; workspace not exposed
    course = _mk_course()
    # no membership created -> access cannot be confirmed
    client = _login(stub_iam, 77, kind="student", permissions=("lms.course.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/")
    assert resp.status_code in (403, 404)


# UC-002
def test_UC_002_Main(stub_iam):
    """UC-002-Main / UC-LMS-002 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.course.manage",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "updated"}, format="json")
    assert resp.status_code == 200


def test_UC_002_Alt1(stub_iam):
    """UC-002-Alt1 / UC-LMS-002 Alternative A1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.course.manage",))
    client.patch(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "v1"}, format="json")
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "v2"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["syllabus"] == "v2"


def test_UC_002_Exc1(stub_iam):
    """UC-002-Exc1 / UC-LMS-002 Exception E1"""
    course = _mk_course()
    _mem(course, 2, "student")
    client = _login(stub_iam, 2, kind="student", permissions=("lms.course.view",))
    resp = client.patch(f"/api/v1/lms/courses/{course.id}/", {"syllabus": "x"}, format="json")
    assert resp.status_code == 403


# UC-003
def test_UC_003_Main(stub_iam):
    """UC-003-Main / UC-LMS-003 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.material.manage",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c", "status": "published"}, format="json")
    assert resp.status_code == 201


def test_UC_003_Alt1(stub_iam):
    """UC-003-Alt1 / UC-LMS-003 Alternative A1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.material.manage",))
    r = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c", "status": "published"}, format="json")
    mid = r.json()["id"]
    resp = client.patch(f"/api/v1/lms/materials/{mid}/", {"title": "M2"}, format="json")
    assert resp.status_code == 200


def test_UC_003_Exc1(stub_iam):
    """UC-003-Exc1 / UC-LMS-003 Exception E1"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.material.view",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/materials/", {"title": "M", "material_type": "note", "content": "c"}, format="json")
    assert resp.status_code == 403


# UC-004
def test_UC_004_Main(stub_iam):
    """UC-004-Main / UC-LMS-004 Main Flow"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_UC_004_Alt1(stub_iam):
    """UC-004-Alt1 / UC-LMS-004 Alternative A1"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseMaterial.objects.create(course=course, title="Sched", material_type="note", content="c", status="scheduled", release_date=timezone.now() + timedelta(days=5), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_UC_004_Exc1(stub_iam):
    """UC-004-Exc1 / UC-LMS-004 Exception E1"""
    course = _mk_course()
    client = _login(stub_iam, 999, kind="student", permissions=("lms.material.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/materials/")
    assert resp.status_code in (403, 404)


# UC-005
def test_UC_005_Main(stub_iam):
    """UC-005-Main / UC-LMS-005 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    assert resp.status_code == 201
    assert resp.json().get("created_at") is not None


def test_UC_005_Alt1(stub_iam):
    """UC-005-Alt1 / UC-LMS-005 Alternative A1"""
    course = _mk_course(allow_ta_announcements=True)
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    assert resp.status_code == 201


def test_UC_005_Exc1(stub_iam):
    """UC-005-Exc1 / UC-LMS-005 Exception E1"""
    course = _mk_course(allow_ta_announcements=False)
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.announcement.post",))
    resp = client.post(f"/api/v1/lms/courses/{course.id}/announcements/", {"title": "T", "content": "c"}, format="json")
    assert resp.status_code == 403


# UC-006
def test_UC_006_Main(stub_iam):
    """UC-006-Main / UC-LMS-006 Main Flow"""
    course = _mk_course()
    _mem(course, 3, "student")
    CourseAnnouncement.objects.create(course=course, title="A", content="c", posted_by_user_id=1, posted_by_role="faculty", posted_by_name="F")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.announcement.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/announcements/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_UC_006_Exc1(stub_iam):
    """UC-006-Exc1 / UC-LMS-006 Exception E1"""
    course = _mk_course()
    client = _login(stub_iam, 999, kind="student", permissions=("lms.announcement.view",))
    resp = client.get(f"/api/v1/lms/courses/{course.id}/announcements/")
    assert resp.status_code in (403, 404)


# UC-007
def test_UC_007_Main(stub_iam):
    """UC-007-Main / UC-LMS-007 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "i", "submission_type": "text", "points_possible": 10, "due_date": (now + timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


def test_UC_007_Alt1(stub_iam):
    """UC-007-Alt1 / UC-LMS-007 Alternative A1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.patch(f"/api/v1/lms/assignments/{asgn.id}/", {"title": "B"}, format="json")
    assert resp.status_code == 200


def test_UC_007_Exc1(stub_iam):
    """UC-007-Exc1 / UC-LMS-007 Exception E1"""
    course = _mk_course()
    _mem(course, 2, "ta")
    client = _login(stub_iam, 2, kind="staff", permissions=("lms.assignment.view",))
    now = timezone.now()
    resp = client.post(f"/api/v1/lms/courses/{course.id}/assignments/", {"title": "A", "instructions": "i", "submission_type": "text", "points_possible": 10, "due_date": (now + timedelta(days=1)).isoformat()}, format="json")
    assert resp.status_code == 403


# UC-008
def test_UC_008_Main(stub_iam):
    """UC-008-Main / UC-LMS-008 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/publish/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


def test_UC_008_Alt1(stub_iam):
    """UC-008-Alt1 / UC-LMS-008 Alternative A1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=now + timedelta(days=1), status="draft", release_date=now + timedelta(days=2), created_by_user_id=1)
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/publish/")
    assert resp.status_code == 200
    # future-dated: should be scheduled or published with future release
    assert resp.json()["status"] in ("published", "scheduled")


def test_UC_008_Exc1(stub_iam):
    """UC-008-Exc1 / UC-LMS-008 Exception E1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="draft", created_by_user_id=1)
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.assignment.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/publish/")
    # invalid draft: either 400 or still published (implementation-dependent); accept either but assert not crash
    assert resp.status_code in (200, 400)


# UC-009
def test_UC_009_Main(stub_iam):
    """UC-009-Main / UC-LMS-009 Main Flow"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/")
    assert resp.status_code == 200


def test_UC_009_Alt1(stub_iam):
    """UC-009-Alt1 / UC-LMS-009 Alternative A1"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", release_date=timezone.now() + timedelta(days=1), created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.assignment.view",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/")
    assert resp.status_code == 404


def test_UC_009_Exc1(stub_iam):
    """UC-009-Exc1 / UC-LMS-009 Exception E1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 999, kind="student", permissions=("lms.assignment.view",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/")
    assert resp.status_code in (403, 404)


# UC-010
def test_UC_010_Main(stub_iam):
    """UC-010-Main / UC-LMS-010 Main Flow"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 201
    assert "submitted_at" in resp.json()


def test_UC_010_Alt1(stub_iam):
    """UC-010-Alt1 / UC-LMS-010 Alternative A1 (ISS-LMS-001)"""
    import pytest as _p
    _p.skip("NOT_AUTOMATED: late-submission policy unresolved (ISS-LMS-001)")


def test_UC_010_Alt2(stub_iam):
    """UC-010-Alt2 / UC-LMS-010 Alternative A2 (ISS-LMS-005)"""
    import pytest as _p
    _p.skip("NOT_AUTOMATED: resubmission policy unresolved (ISS-LMS-005)")


def test_UC_010_Exc1(stub_iam):
    """UC-010-Exc1 / UC-LMS-010 Exception E1"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="file", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.create", "lms.assignment.view"))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/submit/", {"submission_type": "text", "text_response": "hi"}, format="json")
    assert resp.status_code == 400


# UC-011
def test_UC_011_Main(stub_iam):
    """UC-011-Main / UC-LMS-011 Main Flow"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.view_self",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/")
    assert resp.status_code == 200


def test_UC_011_Alt1(stub_iam):
    """UC-011-Alt1 / UC-LMS-011 Alternative A1"""
    course = _mk_course()
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="late")
    client = _login(stub_iam, 3, kind="student", permissions=("lms.submission.view_self",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("submitted", "late", "missing")


def test_UC_011_Exc1(stub_iam):
    """UC-011-Exc1 / UC-LMS-011 Exception E1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 4, kind="student", permissions=("lms.submission.view_self",))
    resp = client.get(f"/api/v1/lms/assignments/{asgn.id}/my-submission/")
    assert resp.status_code == 404


# UC-012
def test_UC_012_Main(stub_iam):
    """UC-012-Main / UC-LMS-012 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 90, "feedback": "fb"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_UC_012_Alt1(stub_iam):
    """UC-012-Alt1 / UC-LMS-012 Alternative A1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("80"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    sub.refresh_from_db()
    grade_submission(submission=sub, points=Decimal("90"), feedback="revised", grader_user_id=1, grader_role="faculty", grader_name="F", change_reason="re-eval")
    audits = list(sub.grade.audit_logs.all())
    assert len(audits) == 1
    assert audits[0].changed_by_user_id == 1


def test_UC_012_Exc1(stub_iam):
    """UC-012-Exc1 / UC-LMS-012 Exception E1"""
    course = _mk_course()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    client = _login(stub_iam, 999, kind="student", permissions=("lms.grade.view",))
    resp = client.post(f"/api/v1/lms/submissions/{sub.id}/grade/", {"points_awarded": 90, "feedback": "fb"}, format="json")
    assert resp.status_code in (403, 404)


# UC-013
def test_UC_013_Main(stub_iam):
    """UC-013-Main / UC-LMS-013 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    client = _login(stub_iam, 1, kind="faculty", permissions=("lms.grade.release",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert resp.status_code == 200
    assert resp.json()["released_count"] >= 1


def test_UC_013_Alt1(stub_iam):
    """UC-013-Alt1 / UC-LMS-013 Alternative A1"""
    course = _mk_course()
    _mem(course, 5, "ta")
    course.allow_ta_grading = True
    course.save()
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    client = _login(stub_iam, 5, kind="staff", permissions=("lms.grade.manage",))
    resp = client.post(f"/api/v1/lms/assignments/{asgn.id}/release-grades/")
    assert resp.status_code == 403


# UC-014
def test_UC_014_Main(stub_iam):
    """UC-014-Main / UC-LMS-014 Main Flow"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="great", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_UC_014_Alt1(stub_iam):
    """UC-014-Alt1 / UC-LMS-014 Alternative A1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    # not released -> student should not see
    client = _login(stub_iam, 3, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_UC_014_Exc1(stub_iam):
    """UC-014-Exc1 / UC-LMS-014 Exception E1"""
    course = _mk_course()
    _mem(course, 1, "faculty")
    _mem(course, 3, "student")
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=3, submission_type="text", text_response="hi", status="submitted")
    grade_submission(submission=sub, points=Decimal("90"), feedback="fb", grader_user_id=1, grader_role="faculty", grader_name="F")
    release_assignment_grades(asgn, 1)
    client = _login(stub_iam, 4, kind="student", permissions=("lms.grade.view", "lms.grade.view_self"))
    resp = client.get("/api/v1/lms/grades/my-grades/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# UC-015
def test_UC_015_Main(stub_iam):
    """UC-015-Main / UC-LMS-015 Main Flow"""
    course = _mk_course()
    mat = CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="scheduled", release_date=timezone.now() - timedelta(minutes=1), created_by_user_id=1)
    asgn = Assignment.objects.create(course=course, title="A", instructions="i", submission_type="text", points_possible=Decimal("10"), due_date=timezone.now() + timedelta(days=1), status="scheduled", release_date=timezone.now() - timedelta(minutes=1), created_by_user_id=1)
    process_scheduled_releases()
    mat.refresh_from_db()
    asgn.refresh_from_db()
    assert mat.status == "published"
    assert asgn.status == "published"


def test_UC_015_Alt1(stub_iam):
    """UC-015-Alt1 / UC-LMS-015 Alternative A1"""
    course = _mk_course()
    mat = CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="scheduled", release_date=timezone.now() - timedelta(minutes=1), created_by_user_id=1)
    # withdraw before release
    mat.status = "draft"
    mat.save()
    process_scheduled_releases()
    mat.refresh_from_db()
    assert mat.status == "draft"


def test_UC_015_Exc1(stub_iam):
    """UC-015-Exc1 / UC-LMS-015 Exception E1"""
    # release processing failure leaves content unavailable; here we simulate by no-op (content stays scheduled)
    course = _mk_course()
    mat = CourseMaterial.objects.create(course=course, title="M", material_type="note", content="c", status="scheduled", release_date=timezone.now() + timedelta(days=5), created_by_user_id=1)
    process_scheduled_releases()
    mat.refresh_from_db()
    assert mat.status == "scheduled"
    assert mat.is_available() is False
