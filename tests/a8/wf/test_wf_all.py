"""WF strategy tests — generated from WF_DESIGN.json (frozen)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    Course,
    CourseMaterial,
)
from modules.lms.services.grading import grade_submission, release_assignment_grades
from modules.lms.services.releases import process_scheduled_releases

pytestmark = pytest.mark.django_db


def _mk_course(code="WF101", name="WF Course"):
    return Course.objects.create(code=code, name=name)


# BW-01
def test_WF_BW01_S1():
    """WF-BW01-S1 / BW-LMS-01 Step 1"""
    course = _mk_course()
    now = timezone.now()
    mat = CourseMaterial.objects.create(course=course, title="L5", material_type="note", content="c", status="scheduled", release_date=now + timedelta(days=2), created_by_user_id=1)
    assert mat.status == "scheduled"


def test_WF_BW01_S2():
    """WF-BW01-S2 / BW-LMS-01 Step 2"""
    course = _mk_course(code="WF102")
    now = timezone.now()
    mat = CourseMaterial.objects.create(course=course, title="L5", material_type="note", content="c", status="scheduled", release_date=now - timedelta(seconds=1), created_by_user_id=1)
    assert mat.is_available() is False
    process_scheduled_releases()
    mat.refresh_from_db()
    assert mat.status == "published"
    assert mat.is_available() is True


def test_WF_BW01_Alt1():
    """WF-BW01-Alt1 / BW-LMS-01 Alternative A1"""
    course = _mk_course(code="WF103")
    now = timezone.now()
    mat = CourseMaterial.objects.create(course=course, title="L5", material_type="note", content="c", status="scheduled", release_date=now - timedelta(seconds=1), created_by_user_id=1)
    mat.status = "draft"
    mat.save()
    process_scheduled_releases()
    mat.refresh_from_db()
    assert mat.status == "draft"


def test_WF_BW01_Exc1():
    """WF-BW01-Exc1 / BW-LMS-01 Exception E1"""
    course = _mk_course(code="WF104")
    now = timezone.now()
    mat = CourseMaterial.objects.create(course=course, title="L5", material_type="note", content="c", status="scheduled", release_date=now + timedelta(days=5), created_by_user_id=1)
    process_scheduled_releases()
    mat.refresh_from_db()
    assert mat.status == "scheduled"
    assert mat.is_available() is False


# BW-02
def test_WF_BW02_S1():
    """WF-BW02-S1 / BW-LMS-02 Step 1"""
    course = _mk_course(code="WF201")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="E1", instructions="analyze", submission_type="text", points_possible=Decimal("100"), due_date=now + timedelta(days=5), status="draft", created_by_user_id=1)
    assert asgn.status == "draft"


def test_WF_BW02_S2():
    """WF-BW02-S2 / BW-LMS-02 Step 2"""
    course = _mk_course(code="WF202")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="E1", instructions="analyze", submission_type="text", points_possible=Decimal("100"), due_date=now + timedelta(days=5), status="draft", created_by_user_id=1)
    asgn.status = "published"
    asgn.release_date = None
    asgn.save()
    assert asgn.is_available_to_students() is True


def test_WF_BW02_S3():
    """WF-BW02-S3 / BW-LMS-02 Step 3"""
    course = _mk_course(code="WF203")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="E1", instructions="analyze", submission_type="text", points_possible=Decimal("100"), due_date=now + timedelta(days=5), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=501, submission_type="text", text_response="essay", status="submitted")
    assert sub.status == "submitted"


# BW-03
def test_WF_BW03_S1():
    """WF-BW03-S1 / BW-LMS-03 Step 1"""
    course = _mk_course(code="WF301")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Mid", instructions="spec", submission_type="file", points_possible=Decimal("100"), due_date=now + timedelta(days=10), status="draft", created_by_user_id=1)
    assert asgn.status == "draft"


def test_WF_BW03_S2():
    """WF-BW03-S2 / BW-LMS-03 Step 2"""
    course = _mk_course(code="WF302")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Mid", instructions="spec", submission_type="file", points_possible=Decimal("100"), due_date=now + timedelta(days=10), status="scheduled", release_date=now + timedelta(days=2), created_by_user_id=1)
    assert asgn.status == "scheduled"
    assert asgn.is_available_to_students() is False


def test_WF_BW03_S3():
    """WF-BW03-S3 / BW-LMS-03 Step 3"""
    course = _mk_course(code="WF303")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Mid", instructions="spec", submission_type="file", points_possible=Decimal("100"), due_date=now + timedelta(days=10), status="scheduled", release_date=now - timedelta(seconds=1), created_by_user_id=1)
    process_scheduled_releases()
    asgn.refresh_from_db()
    assert asgn.status == "published"
    assert asgn.is_available_to_students() is True


def test_WF_BW03_S4():
    """WF-BW03-S4 / BW-LMS-03 Step 4"""
    course = _mk_course(code="WF304")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Mid", instructions="spec", submission_type="file", points_possible=Decimal("100"), due_date=now + timedelta(days=10), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=601, submission_type="file", file_name="project.tar.gz", status="submitted")
    assert sub.status == "submitted"


# BW-04
def test_WF_BW04_S1():
    """WF-BW04-S1 / BW-LMS-04 Step 1"""
    course = _mk_course(code="WF401")
    asgn = Assignment.objects.create(course=course, title="HW1", instructions="solve", submission_type="text", points_possible=Decimal("50"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=701, submission_type="text", text_response="sol", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("46"), feedback="great", grader_user_id=1, grader_role="faculty", grader_name="Dr Smith")
    assert grade.status == "draft"


def test_WF_BW04_S2():
    """WF-BW04-S2 / BW-LMS-04 Step 2"""
    course = _mk_course(code="WF402")
    asgn = Assignment.objects.create(course=course, title="HW1", instructions="solve", submission_type="text", points_possible=Decimal("50"), due_date=timezone.now() + timedelta(days=1), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=701, submission_type="text", text_response="sol", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("46"), feedback="great", grader_user_id=1, grader_role="faculty", grader_name="Dr Smith")
    release_assignment_grades(asgn, faculty_user_id=1)
    grade.refresh_from_db()
    assert grade.status == "released"
    assert grade.released_by_user_id == 1


# BW-05
def test_WF_BW05_S1():
    """WF-BW05-S1 / BW-LMS-05 Step 1"""
    course = _mk_course(code="WF501")
    asgn = Assignment.objects.create(course=course, title="Lab3", instructions="socket", submission_type="file", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=2), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=801, submission_type="file", file_name="server.c", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("92"), feedback="good", grader_user_id=25, grader_role="ta", grader_name="Rohan TA")
    assert grade.status == "draft"
    assert grade.graded_by_role == "ta"
    assert grade.graded_by_user_id == 25


def test_WF_BW05_S2():
    """WF-BW05-S2 / BW-LMS-05 Step 2"""
    course = _mk_course(code="WF502")
    asgn = Assignment.objects.create(course=course, title="Lab3", instructions="socket", submission_type="file", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=2), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=801, submission_type="file", file_name="server.c", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("92"), feedback="good", grader_user_id=25, grader_role="ta", grader_name="Rohan TA")
    release_assignment_grades(asgn, faculty_user_id=1)
    grade.refresh_from_db()
    assert grade.status == "released"
    assert grade.released_by_user_id == 1
    assert grade.graded_by_role == "ta"


# CW-01
def test_WF_CW01_S1():
    """WF-CW01-S1 / CW-LMS-01 Step 1"""
    course = _mk_course(code="WFC1")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Capstone", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=now + timedelta(days=30), status="draft", created_by_user_id=1)
    assert asgn.status == "draft"


def test_WF_CW01_S2():
    """WF-CW01-S2 / CW-LMS-01 Step 2"""
    course = _mk_course(code="WFC2")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Capstone", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=now + timedelta(days=30), status="published", release_date=None, created_by_user_id=1)
    assert asgn.is_available_to_students() is True


def test_WF_CW01_S3():
    """WF-CW01-S3 / CW-LMS-01 Step 3"""
    course = _mk_course(code="WFC3")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Capstone", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=now + timedelta(days=30), status="scheduled", release_date=now + timedelta(days=2), created_by_user_id=1)
    assert asgn.status == "scheduled"
    assert asgn.is_available_to_students() is False


def test_WF_CW01_S4():
    """WF-CW01-S4 / CW-LMS-01 Step 4"""
    course = _mk_course(code="WFC4")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Capstone", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=now + timedelta(days=30), status="scheduled", release_date=now - timedelta(minutes=1), created_by_user_id=1)
    process_scheduled_releases()
    asgn.refresh_from_db()
    assert asgn.status == "published"


def test_WF_CW01_S5():
    """WF-CW01-S5 / CW-LMS-01 Step 5"""
    course = _mk_course(code="WFC5")
    now = timezone.now()
    asgn = Assignment.objects.create(course=course, title="Capstone", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=now + timedelta(days=30), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=901, submission_type="link", link_url="https://github.com/student/capstone", status="submitted")
    assert sub.status == "submitted"


# CW-02
def test_WF_CW02_S1():
    """WF-CW02-S1 / CW-LMS-02 Step 1"""
    course = _mk_course(code="WFC6")
    asgn = Assignment.objects.create(course=course, title="Cap", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=30), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=901, submission_type="link", link_url="https://github.com/student/capstone", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("98"), feedback="outstanding", grader_user_id=1, grader_role="faculty", grader_name="Prof Verma")
    assert grade.status == "draft"


def test_WF_CW02_S2():
    """WF-CW02-S2 / CW-LMS-02 Step 2"""
    course = _mk_course(code="WFC7")
    asgn = Assignment.objects.create(course=course, title="Cap", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=30), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=901, submission_type="link", link_url="https://github.com/student/capstone", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("98"), feedback="outstanding", grader_user_id=25, grader_role="ta", grader_name="TA")
    assert grade.status == "draft"
    assert grade.graded_by_role == "ta"


def test_WF_CW02_S3():
    """WF-CW02-S3 / CW-LMS-02 Step 3"""
    course = _mk_course(code="WFC8")
    asgn = Assignment.objects.create(course=course, title="Cap", instructions="design", submission_type="link", points_possible=Decimal("100"), due_date=timezone.now() + timedelta(days=30), status="published", created_by_user_id=1)
    sub = AssignmentSubmission.objects.create(assignment=asgn, student_user_id=901, submission_type="link", link_url="https://github.com/student/capstone", status="submitted")
    grade = grade_submission(submission=sub, points=Decimal("98"), feedback="outstanding", grader_user_id=1, grader_role="faculty", grader_name="Prof Verma")
    release_assignment_grades(asgn, faculty_user_id=1)
    grade.refresh_from_db()
    assert grade.status == "released"
