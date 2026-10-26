from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.exceptions import NotFound, ValidationError

from modules.leave.models import LeaveBalance, LeaveManagerAssignment, LeaveRequest, LeaveType
from modules.leave.services import configuration
from modules.leave.services import requests as service

pytestmark = pytest.mark.django_db


@pytest.fixture
def leave_setup():
    leave_type = LeaveType.objects.create(
        code="annual", name="Annual", annual_allowance=Decimal("20.00"))
    balance = LeaveBalance.objects.create(
        user_id=1001, leave_type=leave_type, year=2026,
        allocated_days=Decimal("10.00"), carried_days=Decimal("2.00"))
    return leave_type, balance


def test_create_request_counts_weekdays_and_persists_reason(leave_setup):
    leave_type, _ = leave_setup

    row = service.create_request(
        user_id=1001, leave_type_id=leave_type.pk,
        start_date=date(2026, 10, 26), end_date=date(2026, 10, 28),
        reason="  Family event  ")

    assert row.days == 3
    assert row.reason == "Family event"
    assert row.status == "pending"


def test_pending_and_approved_requests_reduce_available_balance(leave_setup):
    leave_type, _balance = leave_setup
    for status, days in (("pending", 2), ("approved", 3),
                         ("rejected", 4), ("cancelled", 1)):
        LeaveRequest.objects.create(
            user_id=1001, leave_type=leave_type, start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2), days=days, reason="Existing", status=status)

    with pytest.raises(ValidationError, match="exceeds the available"):
        service.create_request(
            user_id=1001, leave_type_id=leave_type.pk,
            start_date=date(2026, 10, 26), end_date=date(2026, 11, 4),
            reason="More than remaining balance")

    accepted = service.create_request(
        user_id=1001, leave_type_id=leave_type.pk,
        start_date=date(2026, 11, 9), end_date=date(2026, 11, 13),
        reason="Within remaining balance")
    assert accepted.days == 5


@pytest.mark.parametrize("start,end", [
    (date(2026, 10, 31), date(2026, 11, 1)),
    (date(2026, 12, 31), date(2027, 1, 1)),
])
def test_non_working_or_cross_year_ranges_are_rejected(leave_setup, start, end):
    leave_type, _ = leave_setup
    with pytest.raises(ValidationError):
        service.create_request(user_id=1001, leave_type_id=leave_type.pk,
                               start_date=start, end_date=end, reason="Request")


def test_request_without_configured_balance_is_rejected():
    leave_type = LeaveType.objects.create(code="annual", name="Annual")
    with pytest.raises(ValidationError, match="No leave balance"):
        service.create_request(
            user_id=1001, leave_type_id=leave_type.pk,
            start_date=date(2026, 10, 26), end_date=date(2026, 10, 26),
            reason="Request")


def test_current_request_unit_is_a_whole_workday(leave_setup):
    leave_type, balance = leave_setup
    balance.allocated_days = Decimal("0.50")
    balance.carried_days = Decimal("0.00")
    balance.save(update_fields=["allocated_days", "carried_days", "updated_at"])

    with pytest.raises(ValidationError, match="exceeds the available"):
        service.create_request(
            user_id=1001, leave_type_id=leave_type.pk,
            start_date=date(2026, 10, 26), end_date=date(2026, 10, 26),
            reason="Half day is not currently supported")


def test_review_is_audited_and_only_pending_requests_can_be_reviewed(leave_setup):
    leave_type, _ = leave_setup
    row = LeaveRequest.objects.create(
        user_id=1001, leave_type=leave_type, start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2), days=1, reason="Request")

    reviewed = service.review_request(
        leave_request=row, actor_id=9000, decision="approved", note="  OK  ",
        scope=LeaveRequest.objects.all())

    assert reviewed.status == "approved"
    assert reviewed.reviewed_by_user_id == 9000
    assert reviewed.reviewed_at is not None
    assert reviewed.review_note == "OK"
    with pytest.raises(ValidationError, match="Only pending"):
        service.review_request(leave_request=row, actor_id=9000, decision="rejected",
                               scope=LeaveRequest.objects.all())


def test_manager_cannot_review_own_request(leave_setup):
    leave_type, _ = leave_setup
    row = LeaveRequest.objects.create(
        user_id=9000, leave_type=leave_type, start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2), days=1, reason="Request")

    with pytest.raises(ValidationError, match="own leave request"):
        service.review_request(leave_request=row, actor_id=9000, decision="approved",
                               scope=LeaveRequest.objects.all())


def test_cancel_is_owner_scoped_and_only_pending_requests_can_be_cancelled(leave_setup):
    leave_type, _ = leave_setup
    row = LeaveRequest.objects.create(
        user_id=1001, leave_type=leave_type, start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2), days=1, reason="Request")

    with pytest.raises(NotFound):
        service.cancel_request(leave_request_id=row.pk, user_id=2002)
    cancelled = service.cancel_request(leave_request_id=row.pk, user_id=1001)
    assert cancelled.status == "cancelled"
    with pytest.raises(ValidationError, match="Only pending"):
        service.cancel_request(leave_request_id=row.pk, user_id=1001)


def test_configuration_upserts_balance_and_manager_assignment(leave_setup):
    leave_type, _ = leave_setup
    values = {"user_id": 1001, "leave_type": leave_type,
              "year": 2026, "allocated_days": Decimal("8.00"),
              "carried_days": Decimal("1.00")}
    first = configuration.set_balance(values=values)
    second = configuration.set_balance(values={**values,
                                               "allocated_days": Decimal("9.00")})
    assert first.pk == second.pk
    assert second.allocated_days == Decimal("9.00")

    assignment, created = configuration.assign_manager(
        manager_user_id=9000, employee_user_id=1001, assigned_by_user_id=1)
    duplicate, created_again = configuration.assign_manager(
        manager_user_id=9000, employee_user_id=1001, assigned_by_user_id=2)
    assert created and not created_again
    assert assignment.pk == duplicate.pk
    assert LeaveManagerAssignment.objects.count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql",
                    reason="select_for_update concurrency requires PostgreSQL")
def test_concurrent_decisions_allow_only_one_winner(leave_setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    leave_type, _ = leave_setup
    row = LeaveRequest.objects.create(
        user_id=1001, leave_type=leave_type, start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2), days=1, reason="Request")
    barrier = Barrier(2)

    def decide(actor_id, decision):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return service.review_request(
                leave_request=row, actor_id=actor_id, decision=decision,
                scope=LeaveRequest.objects.all()).status
        except ValidationError:
            return "refused"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda args: decide(*args),
                                [(9001, "approved"), (9002, "rejected")]))

    assert results.count("refused") == 1
    assert sum(result in {"approved", "rejected"} for result in results) == 1
    row.refresh_from_db()
    assert row.status in {"approved", "rejected"}


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql",
                    reason="select_for_update concurrency requires PostgreSQL")
def test_review_and_cancellation_race_allows_only_one_winner(leave_setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    leave_type, _ = leave_setup
    row = LeaveRequest.objects.create(
        user_id=1001, leave_type=leave_type, start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2), days=1, reason="Request")
    barrier = Barrier(2)

    def review():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            service.review_request(
                leave_request=row, actor_id=9000, decision="approved",
                scope=LeaveRequest.objects.all())
        except ValidationError:
            return "refused"
        else:
            return "approved"
        finally:
            close_old_connections()

    def cancel():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            service.cancel_request(leave_request_id=row.pk, user_id=1001)
        except ValidationError:
            return "refused"
        else:
            return "cancelled"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(review), pool.submit(cancel)]
        outcomes = [future.result() for future in results]

    assert sum(result in {"approved", "cancelled"} for result in outcomes) == 1
    assert outcomes.count("refused") == 1
    row.refresh_from_db()
    assert row.status in {"approved", "cancelled"}


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor != "postgresql",
                    reason="select_for_update concurrency requires PostgreSQL")
def test_concurrent_requests_cannot_spend_the_same_balance_twice(leave_setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    leave_type, _ = leave_setup
    barrier = Barrier(2)
    ranges = [
        (date(2026, 10, 26), date(2026, 11, 3)),
        (date(2026, 11, 9), date(2026, 11, 17)),
    ]

    def apply(dates):
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            service.create_request(
                user_id=1001, leave_type_id=leave_type.pk,
                start_date=dates[0], end_date=dates[1], reason="Concurrent request")
        except ValidationError:
            return "refused"
        else:
            return "created"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(apply, ranges))

    assert outcomes.count("created") == 1
    assert outcomes.count("refused") == 1
    assert LeaveRequest.objects.filter(user_id=1001, status="pending").count() == 1
