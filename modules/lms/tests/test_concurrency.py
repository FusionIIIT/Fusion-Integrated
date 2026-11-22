from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.lms.models import Assignment, Grade, GradeAuditLog, Material, Submission
from modules.lms.selectors.scoping import AccessScope
from modules.lms.services.grading import save_grade
from modules.lms.services.releases import release_one
from modules.lms.services.submissions import create_submission
from modules.lms.tasks import release_due_assignments, release_due_materials
from modules.lms.tests.conftest import KEY

pytestmark = pytest.mark.django_db(transaction=True)


def parallel(fn):
    barrier = Barrier(2)

    def run():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return fn()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(lambda _: run(), range(2)))


def test_duplicate_submissions_real_concurrent_transactions(world):
    assignment = Assignment.objects.create(
        workspace=world.workspace,
        instructions="Work",
        due_at=world.due,
        submission_type="TEXT",
        points_possible=10,
        state="AVAILABLE",
        published_at=timezone.now(),
        author_user_id=1,
    )
    scope = AccessScope(2, "STUDENT", (KEY,))

    def attempt():
        try:
            return create_submission(
                scope, assignment.pk, {"kind": "TEXT", "text": "Concurrent work"}
            ).pk
        except ConflictError:
            return "conflict"

    results = parallel(attempt)
    assert results.count("conflict") == 1 and Submission.objects.count() == 1


@pytest.mark.parametrize("kind,model", [("material", Material), ("assignment", Assignment)])
def test_release_double_delivery_and_concurrent_delivery(world, kind, model):
    common = {
        "workspace": world.workspace,
        "author_user_id": 1,
        "state": "SCHEDULED",
        "release_at": timezone.now() - timedelta(seconds=1),
    }
    if kind == "material":
        row = model.objects.create(**common, kind="NOTE", text="Notes")
    else:
        row = model.objects.create(
            **common,
            instructions="Work",
            due_at=world.due,
            submission_type="TEXT",
            points_possible=10,
        )
    task = release_due_materials if kind == "material" else release_due_assignments
    assert sorted(parallel(task)) == [0, 1]
    row.refresh_from_db()
    published_at = row.published_at
    assert published_at and not release_one(kind, row.pk)
    row.refresh_from_db()
    assert row.published_at == published_at


def test_concurrent_grade_edits_have_serial_before_after_audit(world):
    assignment = Assignment.objects.create(
        workspace=world.workspace,
        instructions="Work",
        due_at=world.due,
        submission_type="TEXT",
        points_possible=10,
        state="AVAILABLE",
        published_at=timezone.now(),
        author_user_id=1,
    )
    student = AccessScope(2, "STUDENT", (KEY,))
    faculty = AccessScope(1, "FACULTY", (KEY,))
    submission = create_submission(student, assignment.pk, {"kind": "TEXT", "text": "Work"})
    save_grade(faculty, submission.pk, {"points": Decimal(1), "feedback": "Initial"})
    save_grade(faculty, submission.pk, release=True)
    parallel(
        lambda: (
            save_grade(faculty, submission.pk, {"points": Decimal(2), "feedback": "Correction"}).pk
        )
    )
    audit = list(GradeAuditLog.objects.order_by("pk"))
    assert len(audit) == 4 and audit[2].old_points == 1 and audit[3].old_points == 2
    assert Grade.objects.get().state == "RELEASED"
