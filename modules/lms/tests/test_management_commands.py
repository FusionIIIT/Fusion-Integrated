"""Tests for LMS management commands (R1-20)."""

import io
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.lms.domain.constants import (
    AssignmentStatus,
    MaterialStatus,
    MaterialType,
    SubmissionType,
)
from modules.lms.models import Assignment, CourseMaterial, CourseWorkspace

pytestmark = pytest.mark.django_db


def test_lms_scheduled_release_command():
    now = timezone.now()
    course_id = 910
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS910",
        title="Command Test Course",
    )
    mat = CourseMaterial.objects.create(
        course_id=course_id,
        title="Scheduled Mat",
        material_type=MaterialType.NOTE,
        content_text="Some text",
        status=MaterialStatus.SCHEDULED,
        release_date=now - timedelta(minutes=5),
        uploaded_by=4001,
    )
    asg = Assignment.objects.create(
        course_id=course_id,
        title="Scheduled Asg",
        instructions="Instructions",
        points_possible=100.0,
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=2),
        release_date=now - timedelta(minutes=5),
        status=AssignmentStatus.SCHEDULED,
        created_by=4001,
    )

    out = io.StringIO()
    call_command("lms_scheduled_release", stdout=out)
    output = out.getvalue()
    assert "Content release sweep complete: 1 materials, 1 assignments published." in output

    mat.refresh_from_db()
    asg.refresh_from_db()
    assert mat.status == MaterialStatus.PUBLISHED
    assert asg.status == AssignmentStatus.PUBLISHED


def test_lms_work_status_command_healthy():
    out = io.StringIO()
    call_command("lms_work_status", stdout=out)
    assert "LMS scheduled work looks healthy" in out.getvalue()


def test_lms_work_status_command_overdue():
    now = timezone.now()
    course_id = 911
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS911",
        title="Overdue Test Course",
    )
    CourseMaterial.objects.create(
        course_id=course_id,
        title="Overdue Mat",
        material_type=MaterialType.NOTE,
        content_text="Notes",
        status=MaterialStatus.SCHEDULED,
        release_date=now - timedelta(hours=2),
        uploaded_by=4001,
    )

    out = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("lms_work_status", stdout=out)
    assert exc.value.code == 1
    assert "past release_date" in out.getvalue()
