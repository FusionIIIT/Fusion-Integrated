"""Concurrency and query-budget test suites (R1-11)."""
from __future__ import annotations

import threading

import pytest
from django.db import connection

from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import AttorneyPanelMember, PatentApplication, PatentPolicy
from modules.patents.selectors import scoping
from modules.patents.services import attorney as attorney_service


class DummyActor:
    def __init__(self, user_id=1, roles=("applicant",), permissions=()):
        self.user_id = user_id
        self.roles = roles
        self.permissions = set(permissions)

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions


@pytest.mark.django_db(transaction=True)
def test_concurrent_attorney_workload_updates_under_lock():
    # R1-11 & BR-PMS-043: Multi-threaded updates maintain transactional isolation
    PatentPolicy.objects.create(is_active=True, max_attorney_workload=10)
    att = AttorneyPanelMember.objects.create(
        user_id=505,
        firm_name="IP Juris Partners",
        active_workload=0,
        is_approved_panel=True,
    )

    barrier = threading.Barrier(2, timeout=10)
    errors: list[Exception] = []

    def worker():
        try:
            barrier.wait()
            attorney_service.update_attorney_workload(user_id=505, delta=1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()

    t1.join(timeout=10)
    t2.join(timeout=10)

    assert errors == []
    att.refresh_from_db()
    assert att.active_workload == 2


@pytest.mark.django_db
def test_query_budget_constant_under_scale(django_assert_num_queries):
    # R1-11: Proves application scoping query count is O(1) across dataset scales
    actor = DummyActor(user_id=101, roles=("applicant",), permissions=(p.P_APPLICATION_VIEW_SELF,))
    PatentPolicy.objects.create(is_active=True)

    for i in range(3):
        PatentApplication.objects.create(
            user_id=101,
            application_number=f"PMS-2026-QB-{i}",
            title=f"Patent {i}",
            abstract="Abstract",
            description="Description",
            claims="Claims",
            status=sm.SUBMITTED,
        )

    # Base query count for 3 applications
    with django_assert_num_queries(1):
        list(scoping.applications_for(actor))

    # Add 10 more applications
    for i in range(3, 13):
        PatentApplication.objects.create(
            user_id=101,
            application_number=f"PMS-2026-QB-{i}",
            title=f"Patent {i}",
            abstract="Abstract",
            description="Description",
            claims="Claims",
            status=sm.SUBMITTED,
        )

    # Verifies constant query budget for 13 applications without N+1 query leak
    with django_assert_num_queries(1):
        list(scoping.applications_for(actor))
