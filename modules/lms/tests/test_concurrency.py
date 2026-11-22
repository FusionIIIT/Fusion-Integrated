"""Concurrency tests for LMS submission attempt locking and race conditions (R1-07)."""

import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connections
from django.utils import timezone

from conftest import make_principal
from modules.lms import services
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import Assignment, AssignmentSubmission, CourseMembership, CourseWorkspace

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_submissions_are_safely_serialized():
    now = timezone.now()
    course_id = 450
    CourseWorkspace.objects.create(
        course_id=course_id,
        course_code="CS450",
        title="Parallel Programming",
    )
    CourseMembership.objects.create(
        course_id=course_id,
        user_id=5001,
        role=CourseRole.STUDENT,
        status=MembershipStatus.ACTIVE,
    )
    ass = Assignment.objects.create(
        course_id=course_id,
        title="Parallel Sort",
        instructions="Sort fast",
        points_possible=Decimal("100.00"),
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
        created_by=4001,
    )

    barrier = threading.Barrier(2)
    results = []
    errors = []

    def submit_worker(text: str):
        # Close connection so thread gets its own db connection
        for conn in connections.all():
            conn.close()
        p_student = make_principal(user_id=5001)
        try:
            barrier.wait(timeout=5)
            sub = services.submit_assignment(
                assignment_id=ass.id,
                submission_type=SubmissionType.TEXT,
                content_text=text,
                content_link=None,
                file_attachment=None,
                principal=p_student,
            )
            results.append(sub)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            for conn in connections.all():
                conn.close()

    t1 = threading.Thread(target=submit_worker, args=("Submission from Thread 1",))
    t2 = threading.Thread(target=submit_worker, args=("Submission from Thread 2",))

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Clean up main thread connection
    for conn in connections.all():
        conn.close()

    # Both should be serialized cleanly or recorded without duplicate attempt numbers
    submissions = list(AssignmentSubmission.objects.filter(assignment_id=ass.id, student_id=5001).order_by("attempt_number"))
    attempts = [s.attempt_number for s in submissions]
    assert len(attempts) == len(set(attempts)), f"Duplicate attempts detected: {attempts}"
    assert len(submissions) == 2, f"Expected 2 submissions, found {len(submissions)}. Errors: {errors}"
    assert attempts == [1, 2], f"Expected sequential attempts [1, 2], got {attempts}"
