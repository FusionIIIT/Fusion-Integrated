import pytest
from django.core.exceptions import PermissionDenied
from modules.lms.domain.constants import GradeAction
from modules.lms.models import Course, Assignment, Submission, Grade, GradeAuditLog


@pytest.fixture
def course(db):
    return Course.objects.create(code="CS501", title="Audit Test Course", academic_year=2026, semester=1)


@pytest.fixture
def assignment(course):
    return Assignment.objects.create(course=course, author_user_id=1, title="Audit Assignment")


@pytest.fixture
def submission(assignment):
    return Submission.objects.create(assignment=assignment, student_user_id=10, submission_type="file")


@pytest.fixture
def grade(submission):
    return Grade.objects.create(
        submission=submission,
        assessor_user_id=1,
        assessor_role="instructor",
        points_awarded=95,
        status="released",
    )


@pytest.fixture
def audit_log(grade):
    return GradeAuditLog.objects.create(
        grade=grade,
        assessor_user_id=1,
        action=GradeAction.RELEASED,
        new_points=95,
        reason="initial release",
    )


@pytest.mark.django_db
def test_grade_audit_log_create_allowed(grade):
    log = GradeAuditLog.objects.create(
        grade=grade,
        assessor_user_id=1,
        action=GradeAction.RELEASED,
        new_points=95,
        reason="initial",
    )
    assert log.pk is not None
    assert log.reason == "initial"


@pytest.mark.django_db
def test_grade_audit_log_instance_save_forbidden(audit_log):
    with pytest.raises(PermissionDenied, match="GradeAuditLog records cannot be modified once written"):
        audit_log.reason = "edited"
        audit_log.save()


@pytest.mark.django_db
def test_grade_audit_log_instance_delete_forbidden(audit_log):
    with pytest.raises(PermissionDenied, match="GradeAuditLog records cannot be deleted"):
        audit_log.delete()


@pytest.mark.django_db
def test_grade_audit_log_queryset_update_forbidden(audit_log):
    with pytest.raises(PermissionDenied, match="GradeAuditLog records are immutable and cannot be updated"):
        GradeAuditLog.objects.filter(id=audit_log.id).update(reason="edited")


@pytest.mark.django_db
def test_grade_audit_log_queryset_delete_forbidden(audit_log):
    with pytest.raises(PermissionDenied, match="GradeAuditLog records cannot be deleted"):
        GradeAuditLog.objects.filter(id=audit_log.id).delete()
