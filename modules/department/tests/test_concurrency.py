"""Real threads against the real database, released together (Step 5.7)."""

import threading
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from core.api.exceptions import DomainError
from modules.department.domain.roles import DEPT_ADMIN, FACULTY, HOD, ActorContext
from modules.department.models import (
    Department,
    DepartmentNotification,
    InventoryItem,
    RoleTenure,
    StockMovement,
    StockRequest,
)
from modules.department.services import inventory, notifications, roles

pytestmark = pytest.mark.django_db(transaction=True)

ADMIN = ActorContext(4010, DEPT_ADMIN, "CSE")
HOD_CTX = ActorContext(3010, HOD, "CSE")
CENTRAL = ActorContext(5001, "central", None)


def _race(fn, n=2):
    barrier = threading.Barrier(n)
    results: list = [None] * n

    def run(i):
        try:
            barrier.wait()
            results[i] = ("ok", fn(i))
        except DomainError as exc:
            results[i] = ("refused", exc.code)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


@pytest.fixture
def cse():
    call_command("seed_departments", stdout=StringIO())
    dept = Department.objects.get(code="CSE")
    now = timezone.now()
    for uid, role in ((3010, "hod"), (4010, "dept_admin")):
        RoleTenure.objects.create(
            department=dept,
            role=role,
            user_id=uid,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            assigned_by=1,
            transition_applied_at=now,
        )
    return dept


def _approved_requests(item, n, qty):
    reqs = []
    for i in range(n):
        req = inventory.request_stock(
            ActorContext(3001 + i, FACULTY, "CSE"), item_id=item.pk, quantity=qty
        )
        inventory.decide(HOD_CTX, req.pk, approve=True)
        reqs.append(req.pk)
    return reqs


def test_two_issues_racing_for_the_last_stock_never_go_negative(cse):
    # BR-DEPT-007, AFR-DEPT-013, Q13: the ledger balance holds under concurrency
    item = inventory.add_item(ADMIN, name="Kit", unit="unit", quantity=5)
    reqs = _approved_requests(item, 2, 4)
    results = _race(lambda i: inventory.issue(ADMIN, reqs[i]).status)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert InventoryItem.objects.get(pk=item.pk).current_quantity == 1
    assert StockMovement.objects.filter(kind="issue").count() == 1


def test_the_same_request_issued_twice_at_once_takes_effect_once(cse):
    item = inventory.add_item(ADMIN, name="Kit", unit="unit", quantity=10)
    (req,) = _approved_requests(item, 1, 3)
    results = _race(lambda i: inventory.issue(ADMIN, req).status)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert InventoryItem.objects.get(pk=item.pk).current_quantity == 7


def test_two_hod_decisions_at_once_record_one(cse):
    # BR-DEPT-006: approve and reject race; exactly one wins
    item = inventory.add_item(ADMIN, name="Kit", unit="unit", quantity=10)
    req = inventory.request_stock(ActorContext(3001, FACULTY, "CSE"), item_id=item.pk, quantity=1)
    results = _race(lambda i: inventory.decide(HOD_CTX, req.pk, approve=(i == 0)).status)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert StockRequest.objects.get(pk=req.pk).status in ("approved", "rejected")


def test_two_overlapping_tenures_recorded_at_once_leave_one(cse, stub_iam):
    # BR-DEPT-022: never two holders of one role at once
    from fusion_auth.client import UserRef

    stub_iam(
        None,
        users={
            u: UserRef(user_id=u, username=f"u{u}", display_name="P", kind="faculty")
            for u in (3101, 3102)
        },
    )
    start = timezone.now() + timedelta(days=40)

    def assign(i):
        return roles.assign(
            CENTRAL,
            department_code="CSE",
            role="hod",
            user_id=3101 + i,
            valid_from=start,
            valid_to=start + timedelta(days=10),
        ).pk

    results = _race(assign)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert RoleTenure.objects.filter(role="hod", valid_from=start).count() == 1


def test_role_transitions_applied_twice_at_once_apply_once(cse):
    # UC-DEPT-022: acks_late can deliver the task twice
    RoleTenure.objects.update(transition_applied_at=None)
    results = _race(lambda i: roles.apply_transitions())
    assert sum(r[1] for r in results) == 2  # two tenures, each stamped by exactly one runner
    assert DepartmentNotification.objects.filter(topic="role.effective").count() == 2


def test_delivery_run_twice_at_once_sends_each_row_once(cse, stub_iam, mailoutbox):
    from fusion_auth.client import UserRef

    stub_iam(
        None,
        users={
            3010: UserRef(
                user_id=3010,
                username="u",
                display_name="P",
                kind="faculty",
                email="hod@example.test",
            )
        },
    )
    notifications.enqueue(
        topic="feedback.created", recipients=[3010], key="1", subject="s", body="b"
    )
    _race(lambda i: str(notifications.deliver_pending()))
    assert len(mailoutbox) == 1
    assert DepartmentNotification.objects.get().status == "sent"


def test_the_database_refuses_overlapping_tenures_written_around_the_service(cse):
    # R1-04, BR-DEPT-022: two raw ORM writes at once, with no lock taken by Python
    from django.db import IntegrityError

    start = timezone.now() + timedelta(days=60)

    def write(i):
        try:
            RoleTenure.objects.create(
                department=cse,
                role="hod",
                user_id=3200 + i,
                valid_from=start,
                valid_to=start + timedelta(days=5),
                assigned_by=1,
            )
        except IntegrityError:
            return "refused"
        return "written"

    results = _race(write)
    assert sorted(r[1] for r in results) == ["refused", "written"]
    assert RoleTenure.objects.filter(valid_from=start).count() == 1


def test_the_database_refuses_clashing_slots_written_around_the_service(cse):
    # R1-04, BR-DEPT-010: inserted directly, so only the database can refuse them
    from datetime import time

    from django.db import IntegrityError, transaction

    from modules.department.models import TimetableSlot

    def slot(code, start, end, room="", programme="", batch_year=None):
        return TimetableSlot.objects.create(
            department=cse,
            kind="class",
            course_code=code,
            day_of_week=0,
            starts_at=start,
            ends_at=end,
            room=room,
            programme=programme,
            batch_year=batch_year,
            updated_by=1,
        )

    slot("A", time(9), time(10), room="L-1", programme="B.Tech", batch_year=2024)
    with pytest.raises(IntegrityError), transaction.atomic():
        slot("B", time(9, 30), time(11), room=" l-1 ")  # same room, case and spaces ignored
    with pytest.raises(IntegrityError), transaction.atomic():
        slot(
            "C", time(9, 30), time(11), room="L-2", programme="B.Tech", batch_year=2024
        )  # same group
    slot("D", time(10), time(11), room="L-1")  # touching end-to-start is allowed
    slot("E", time(9), time(10), room="L-3", programme="M.Tech", batch_year=2024)  # nothing shared
    assert TimetableSlot.objects.count() == 3
