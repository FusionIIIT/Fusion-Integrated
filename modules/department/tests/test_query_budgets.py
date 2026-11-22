"""The same query count with 2 rows and with 20, per list endpoint (Step 5.8)."""

from datetime import time

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.department.models import (
    Announcement,
    Feedback,
    FeedbackNote,
    InventoryItem,
    LabResource,
    OfficialChange,
    ProfileRecord,
    RoleTenure,
    StockMovement,
    StockRequest,
    TimetableSlot,
)
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _fill(kind, dept, start, n):
    from django.utils import timezone

    for i in range(start, start + n):
        if kind == "announcements":
            Announcement.objects.create(
                department=dept,
                title=f"t{i}",
                body="b",
                audience_role="all",
                author_id=1,
                published_at=timezone.now(),
            )
        elif kind == "inventory-items":
            InventoryItem.objects.create(department=dept, name=f"i{i}", current_quantity=5)
        elif kind == "stock-requests":
            item = InventoryItem.objects.create(department=dept, name=f"r{i}", current_quantity=5)
            StockRequest.objects.create(department=dept, item=item, requester_id=1, quantity=1)
        elif kind == "stock-movements":
            item = InventoryItem.objects.create(department=dept, name=f"m{i}", current_quantity=5)
            StockMovement.objects.create(item=item, kind="receipt", quantity=5, actor_id=1)
        elif kind == "feedback":
            Feedback.objects.create(
                department=dept, submitter_id=1, submitter_kind="student", subject="s", body="b"
            )
        elif kind == "lab-resources":
            LabResource.objects.create(department=dept, name=f"l{i}", updated_by=1)
        elif kind == "timetable-slots":
            TimetableSlot.objects.create(
                department=dept,
                kind="class",
                course_code=f"c{i}",
                day_of_week=i % 7,
                starts_at=time(8),
                ends_at=time(9),
                room=f"R{i}",
                updated_by=1,
            )
        elif kind == "profiles":
            ProfileRecord.objects.create(
                department=dept, kind="alumni", display_name=f"a{i}", updated_by=1
            )
        elif kind == "official-changes":
            OfficialChange.objects.create(
                department=dept,
                field="name",
                proposed_value=f"n{i}",
                proposed_by=1,
                status="rejected",
                decided_by=2,
            )
        elif kind == "role-assignments":
            from datetime import timedelta

            base = timezone.now() + timedelta(days=1000 + 10 * i)
            RoleTenure.objects.create(
                department=dept,
                role="hod",
                user_id=1,
                valid_from=base,
                valid_to=base + timedelta(days=5),
                assigned_by=1,
            )


CASES = [
    ("announcements", "faculty"),
    ("inventory-items", "admin"),
    ("stock-requests", "admin"),
    ("stock-movements", "admin"),
    ("feedback", "admin"),
    ("lab-resources", "faculty"),
    ("timetable-slots", "student"),
    ("profiles", "hod"),
    ("official-changes", "hod"),
    ("role-assignments", "central"),
    ("departments", "central"),
]


def _count(client, path):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(f"{API}/{path}").status_code == 200
    return len(ctx.captured_queries)


@pytest.mark.parametrize(("path", "who"), CASES)
def test_list_query_count_does_not_grow_with_rows(world, act, path, who):
    _fill(path, world["CSE"], 0, 2)
    small = _count(act(who), path)
    _fill(path, world["CSE"], 2, 18)
    assert _count(act(who), path) == small


def test_feedback_notes_are_prefetched(world, act):
    fbs = [
        Feedback.objects.create(
            department=world["CSE"],
            submitter_id=1,
            submitter_kind="student",
            subject="s",
            body="b",
            status="under_review",
            reviewed_by=uid("admin"),
        )
        for _ in range(2)
    ]
    for fb in fbs:
        FeedbackNote.objects.create(feedback=fb, author_id=1, body="n")
    small = _count(act("hod"), "feedback")
    for _ in range(10):
        fb = Feedback.objects.create(
            department=world["CSE"],
            submitter_id=1,
            submitter_kind="student",
            subject="s",
            body="b",
            status="under_review",
            reviewed_by=uid("admin"),
        )
        FeedbackNote.objects.create(feedback=fb, author_id=1, body="n")
    assert _count(act("hod"), "feedback") == small
