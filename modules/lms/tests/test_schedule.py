"""Tests for LMS background scheduled tasks."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.lms.domain.constants import (
    AssignmentStatus,
    MaterialStatus,
    MaterialType,
    SubmissionType,
)
from modules.lms.models import Assignment, CourseMaterial
from modules.lms.tasks import process_scheduled_content_release

pytestmark = pytest.mark.django_db


def test_process_scheduled_content_release():
    now = timezone.now()

    # Past scheduled material -> should be published
    mat_due = CourseMaterial.objects.create(
        course_id=701,
        title="Due Material",
        material_type=MaterialType.LINK,
        external_url="https://example.com/due",
        status=MaterialStatus.SCHEDULED,
        release_date=now - timedelta(minutes=5),
        uploaded_by=1,
    )

    # Future scheduled material -> should remain scheduled
    mat_future = CourseMaterial.objects.create(
        course_id=701,
        title="Future Material",
        material_type=MaterialType.LINK,
        external_url="https://example.com/future",
        status=MaterialStatus.SCHEDULED,
        release_date=now + timedelta(hours=2),
        uploaded_by=1,
    )

    # Past scheduled assignment -> should be published
    asg_due = Assignment.objects.create(
        course_id=701,
        title="Due Assignment",
        instructions="Complete now",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        release_date=now - timedelta(minutes=5),
        status=AssignmentStatus.SCHEDULED,
        created_by=1,
    )

    # Future scheduled assignment -> should remain scheduled
    asg_future = Assignment.objects.create(
        course_id=701,
        title="Future Assignment",
        instructions="Complete later",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=7),
        release_date=now + timedelta(hours=5),
        status=AssignmentStatus.SCHEDULED,
        created_by=1,
    )

    # Run the Celery task
    result = process_scheduled_content_release()
    assert result["materials_released"] == 1
    assert result["assignments_released"] == 1

    mat_due.refresh_from_db()
    mat_future.refresh_from_db()
    asg_due.refresh_from_db()
    asg_future.refresh_from_db()

    assert mat_due.status == MaterialStatus.PUBLISHED
    assert mat_future.status == MaterialStatus.SCHEDULED
    assert asg_due.status == AssignmentStatus.PUBLISHED
    assert asg_future.status == AssignmentStatus.SCHEDULED
