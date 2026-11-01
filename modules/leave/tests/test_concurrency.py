"""Real threads against the real database.

Green single-threaded tests prove nothing about a double-post: this is the one
class of bug that survives a passing suite, because both approvals find a
request that looks approvable.
"""
import threading

import pytest

from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveLedgerEntry, LeaveRequest, LeaveRequestTransition
from modules.leave.tests.conftest import UNIT_HEAD_PERMISSIONS, leave_client
from modules.leave.tests.test_request_flow import apply_leave

pytestmark = pytest.mark.django_db(transaction=True)


def test_two_approvals_credit_the_balance_once(configured, stub_iam, employee,
                                               unit_head):
    row = apply_leave(employee()).json()

    outcomes = []

    def _approve():
        client = leave_client(stub_iam, user_id=9001,
                              permissions=UNIT_HEAD_PERMISSIONS,
                              active_role="HOD (CSE)")
        response = client.post(f"/api/v1/leave/requests/{row['id']}/decision",
                               {"event": sm.APPROVE}, format="json")
        outcomes.append(response.status_code)

    threads = [threading.Thread(target=_approve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count(200) == 1, f"both approvals succeeded: {outcomes}"
    assert LeaveLedgerEntry.objects.filter(reference=f"request:{row['id']}").count() == 1
    assert LeaveRequestTransition.objects.filter(
        request_id=row["id"], to_status=sm.APPROVED).count() == 1


def test_a_withdrawal_racing_an_approval_ends_in_exactly_one_state(
        configured, stub_iam, employee, unit_head):
    row = apply_leave(employee()).json()
    outcomes = []

    def _withdraw():
        outcomes.append(employee().post(
            f"/api/v1/leave/requests/{row['id']}/withdraw",
            {"reason": "changed my mind"}, format="json").status_code)

    def _approve():
        outcomes.append(unit_head().post(
            f"/api/v1/leave/requests/{row['id']}/decision",
            {"event": sm.APPROVE}, format="json").status_code)

    threads = [threading.Thread(target=_withdraw), threading.Thread(target=_approve)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    row_row = LeaveRequest.objects.get(pk=row["id"])
    assert row_row.status in (sm.WITHDRAWN, sm.APPROVED)
    assert outcomes.count(200) == 1
    posted = LeaveLedgerEntry.objects.filter(reference=f"request:{row['id']}").count()
    assert posted == (1 if row_row.status == sm.APPROVED else 0)
