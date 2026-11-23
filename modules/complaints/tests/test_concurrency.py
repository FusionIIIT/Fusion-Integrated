"""Concurrency and invariant tests for CMS role assignment (BR-CMS-037).

Enforces:
- BR-CMS-037: Exactly one active Complaint Handler and one active Complaint Supervisor.
- BR-CMS-036: Mid-cycle reassignment automatically deactivates prior holders.
- Role isolation: Handler assignment does not deactivate Supervisor, and vice versa.
"""
import concurrent.futures
import datetime
import pytest
from django.db import connection, connections
from django.utils import timezone

from modules.complaints import services
from modules.complaints.models import CmsRoleAssignment

# Use transaction=True to ensure real transaction semantics across threads
pytestmark = pytest.mark.django_db(transaction=True)


def test_sequential_role_reassignment_maintains_single_active_holder():
    """Verify sequential reassignment always preserves exactly one active role holder."""
    now = timezone.now()
    end = now + datetime.timedelta(days=180)

    for uid in range(1001, 1011):
        services.assign_cms_role(
            role_type=CmsRoleAssignment.ROLE_HANDLER,
            user_id=uid,
            assigned_by_user_id=1,
            start_date=now,
            end_date=end,
        )

    # Exactly one active handler exists (the last one assigned)
    active_handlers = CmsRoleAssignment.objects.filter(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        is_active=True,
    )
    assert active_handlers.count() == 1
    assert active_handlers.first().user_id == 1010

    # All 9 previous assignments are deactivated
    inactive_handlers = CmsRoleAssignment.objects.filter(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        is_active=False,
    )
    assert inactive_handlers.count() == 9


def test_role_type_cardinality_is_isolated():
    """Verify Handler assignments and Supervisor assignments are completely independent."""
    now = timezone.now()
    end = now + datetime.timedelta(days=180)

    # Assign Handler
    h = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        user_id=2001,
        assigned_by_user_id=1,
        start_date=now,
        end_date=end,
    )
    # Assign Supervisor
    s = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
        user_id=3001,
        assigned_by_user_id=1,
        start_date=now,
        end_date=end,
    )

    # Both are active simultaneously (1 handler + 1 supervisor)
    assert CmsRoleAssignment.objects.filter(role_type=CmsRoleAssignment.ROLE_HANDLER, is_active=True).count() == 1
    assert CmsRoleAssignment.objects.filter(role_type=CmsRoleAssignment.ROLE_SUPERVISOR, is_active=True).count() == 1

    # Reassign Handler -> Supervisor must remain untouched
    services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        user_id=2002,
        assigned_by_user_id=1,
        start_date=now,
        end_date=end,
    )
    s.refresh_from_db()
    assert s.is_active is True
    assert CmsRoleAssignment.objects.filter(role_type=CmsRoleAssignment.ROLE_HANDLER, is_active=True).count() == 1
    assert CmsRoleAssignment.objects.filter(role_type=CmsRoleAssignment.ROLE_SUPERVISOR, is_active=True).count() == 1


def _worker_assign_role(user_id: int):
    """Worker task executed in separate thread with independent connection."""
    now = timezone.now()
    end = now + datetime.timedelta(days=90)
    try:
        # Close connection so thread gets its own db connection
        connections.close_all()
        services.assign_cms_role(
            role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
            user_id=user_id,
            assigned_by_user_id=1,
            start_date=now,
            end_date=end,
        )
        return True, None
    except Exception as exc:
        return False, str(exc)
    finally:
        connections.close_all()


def test_concurrent_role_assignment_cardinality():
    """Verify concurrent role assignments under multi-threaded execution.

    In SQLite, concurrent writes serialize via table lock or raise OperationalError.
    In PostgreSQL, transactions serialize row mutations.
    In all cases, after threads settle, the database must never contain multiple active holders.
    """
    candidate_user_ids = [4001, 4002, 4003, 4004, 4005]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker_assign_role, uid) for uid in candidate_user_ids]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # At least one assignment succeeded
    successes = [r for r, err in results if r]
    assert len(successes) >= 1

    # Invariant assertion: active count for supervisor MUST BE EXACTLY 1
    active_supervisors = CmsRoleAssignment.objects.filter(
        role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
        is_active=True,
    )
    assert active_supervisors.count() == 1, (
        f"BR-CMS-037 Invariant Violation: Found {active_supervisors.count()} active supervisors. "
        f"Active IDs: {[s.user_id for s in active_supervisors]}"
    )
