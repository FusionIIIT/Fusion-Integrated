"""Real threads, real transactions: the account lock and the idempotency keys under contention."""
import threading
from datetime import date
from decimal import Decimal as D

import pytest
from django.db import connection

from core.api.exceptions import DomainError
from modules.leave.models import LeaveRequest, LedgerEntry, Task
from modules.leave.services import accounts, applications, configuration, workflow

pytestmark = pytest.mark.django_db(transaction=True)

N = 6


def race(fn, n=N):
    barrier, results = threading.Barrier(n), []

    def run():
        try:
            barrier.wait()
            results.append(("ok", fn()))
        except DomainError as exc:
            results.append(("refused", exc.code))
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def _data(start, end, category="CL"):
    return {"category": category, "start_date": start, "end_date": end, "purpose": "x"}


def test_overlapping_submissions_admit_exactly_one(configured, actor, stub_iam):
    from modules.leave.tests.conftest import FACULTY_CSE

    me = actor(FACULTY_CSE)
    results = race(lambda: applications.submit(actor=me, data=_data(date(2026, 3, 9),
                                                                     date(2026, 3, 9))))
    assert [r[0] for r in results].count("ok") == 1
    assert {r[1] for r in results if r[0] == "refused"} == {"overlaps_own_leave"}
    assert LeaveRequest.objects.filter(user_id=FACULTY_CSE).count() == 1


def test_one_balance_cannot_be_spent_twice(configured, actor, stub_iam):
    """8 CL: two 5-day requests on different dates; only one may be admitted."""
    from modules.leave.tests.conftest import FACULTY_CSE

    me = actor(FACULTY_CSE)
    weeks = iter([(date(2026, 3, 9), date(2026, 3, 13)), (date(2026, 3, 16), date(2026, 3, 20)),
                  (date(2026, 3, 23), date(2026, 3, 27)), (date(2026, 4, 6), date(2026, 4, 10)),
                  (date(2026, 4, 13), date(2026, 4, 17)), (date(2026, 4, 20), date(2026, 4, 24))])
    lock = threading.Lock()

    def submit():
        with lock:
            s, e = next(weeks)
        return applications.submit(actor=me, data=_data(s, e))

    results = race(submit)
    assert [r[0] for r in results].count("ok") == 1
    assert {r[1] for r in results if r[0] == "refused"} == {"insufficient_balance"}


def test_a_task_is_decided_once_and_debited_once(configured, actor, stub_iam):
    from modules.leave.tests.conftest import FACULTY_CSE, HOD_CSE

    req = applications.submit(actor=actor(FACULTY_CSE), data=_data(date(2026, 3, 9),
                                                                    date(2026, 3, 9)))
    task = Task.objects.get(request=req, status="open")
    hod = actor(HOD_CSE)
    results = race(lambda: workflow.decide(task_id=task.pk, action="approve", actor=hod))
    assert [r[0] for r in results].count("ok") == 1
    assert {r[1] for r in results if r[0] == "refused"} <= {"task_closed", "request_closed"}
    assert LedgerEntry.objects.filter(request=req).count() == 1


def test_annual_credit_is_posted_once(configured):
    from django.db import transaction

    policy = configuration.current_policy()

    def credit():
        with transaction.atomic():
            accounts.lock(4242, employee_kind="staff")
            return accounts.ensure_annual_credit(user_id=4242, employee_kind="staff",
                                                 year=2026, policy=policy)

    results = race(credit)
    assert sum(r[1] for r in results) == 5
    total = sum(e.delta for e in LedgerEntry.objects.filter(user_id=4242, category="CL"))
    assert total == D(8)
