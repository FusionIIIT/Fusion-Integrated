"""Concurrency tests for BADMS state transitions using threading.Barrier.
"""
import threading

import pytest
from django.db import connection

from core.api.exceptions import ConflictError
from modules.badms.models import ArchivalRequest
from modules.badms.services import decide_archival_request

pytestmark = pytest.mark.django_db(transaction=True)


class _Actor:
    def __init__(self, user_id, active_role, department):
        self.user_id = user_id
        self.active_role = active_role
        self.department = department


def test_concurrent_archival_decision_prevents_double_transition():
    req = ArchivalRequest.objects.create(
        requester_user_id=101,
        department="CSE",
        file_name="research_data.tar",
        file_type="tar",
        file_size_bytes=1024,
        reason="Preservation",
        file_storage_path="/tmp/r.tar",
        initial_classification="Routine",
        status="submitted",
    )

    barrier = threading.Barrier(2, timeout=10)
    successes = []
    failures = []

    def run_decision(decision):
        try:
            barrier.wait()
            actor = _Actor(user_id=901, active_role="HOD (CSE)", department="CSE")
            res = decide_archival_request(
                actor=actor,
                request_id=req.id,
                decision=decision,
            )
            successes.append(res.status)
        except ConflictError as exc:
            failures.append(str(exc))
        finally:
            connection.close()

    t1 = threading.Thread(target=run_decision, args=("approve",))
    t2 = threading.Thread(target=run_decision, args=("reject",))

    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    assert len(successes) == 1
    assert len(failures) == 1
    req.refresh_from_db()
    assert req.status in ("hod_approved", "rejected")
