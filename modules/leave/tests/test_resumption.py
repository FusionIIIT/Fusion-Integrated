"""Regression coverage for BR-EL-027/028: resumption and account reconciliation."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from conftest import make_principal
from modules.leave import contracts
from modules.leave.models import LeaveAccountTransaction, LeaveApplication, ResumptionRecord
from modules.leave.services import accounts, applications

pytestmark = pytest.mark.django_db


@pytest.fixture
def approved_leave():
    application = LeaveApplication.objects.create(
        applicant_user_id=101,
        leave_type="EL",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 10),
        requested_days=Decimal("10"),
        purpose="Approved leave",
        status="approved",
        final_authority_user_id=202,
    )
    accounts.post(
        user_id=101,
        leave_type="EL",
        year=2026,
        amount=Decimal("20"),
        transaction_type="annual_entitlement",
        source_key="entitlement:101:EL:2026",
    )
    accounts.post(
        user_id=101,
        leave_type="EL",
        year=2026,
        amount=Decimal("-10"),
        transaction_type="leave_approved",
        source_key=f"approved:{application.pk}",
        application=application,
    )
    return application


@pytest.fixture
def reviewer():
    return make_principal(
        user_id=202,
        kind="staff",
        roles=("Sanctioning Authority",),
        active_role="Sanctioning Authority",
        permissions=("leave.resumption.review",),
    )


@pytest.mark.parametrize(
    ("actual", "expected_days", "expected_balance", "adjustment"),
    [
        (date(2026, 5, 10), Decimal("10"), Decimal("10"), None),
        (date(2026, 5, 7), Decimal("7"), Decimal("13"), Decimal("3")),
        (date(2026, 5, 12), Decimal("12"), Decimal("8"), Decimal("-2")),
    ],
)
def test_review_reconciles_leave_period_and_ledger(
    approved_leave,
    reviewer,
    monkeypatch,
    actual,
    expected_days,
    expected_balance,
    adjustment,
):
    synchronized = []
    monkeypatch.setattr(
        contracts,
        "synchronize_attendance",
        lambda **values: synchronized.append(values),
    )
    record = ResumptionRecord.objects.create(
        application=approved_leave,
        employee_user_id=101,
        actual_resumption_date=actual,
    )

    reviewed = applications.review_resumption(reviewer, record)

    approved_leave.refresh_from_db()
    reviewed.refresh_from_db()
    assert approved_leave.end_date == actual
    assert approved_leave.requested_days == expected_days
    assert accounts.balance(101, "EL", 2026) == expected_balance
    adjustments = LeaveAccountTransaction.objects.filter(
        transaction_type="resumption_adjustment",
        application=approved_leave,
    )
    if adjustment is None:
        assert not adjustments.exists()
        assert synchronized == []
    else:
        assert list(adjustments.values_list("amount", flat=True)) == [adjustment]
        assert synchronized == [
            {"user_id": 101, "start_date": date(2026, 5, 1), "end_date": actual},
        ]
    assert reviewed.reviewed_by_user_id == 202
    assert reviewed.reviewed_at is not None


def test_duplicate_review_does_not_repost_or_repeat_sync(approved_leave, reviewer, monkeypatch):
    synchronized = []
    monkeypatch.setattr(
        contracts,
        "synchronize_attendance",
        lambda **values: synchronized.append(values),
    )
    record = ResumptionRecord.objects.create(
        application=approved_leave,
        employee_user_id=101,
        actual_resumption_date=date(2026, 5, 7),
    )

    record = applications.review_resumption(reviewer, record)
    first_reviewed_at = record.reviewed_at
    with pytest.raises(ValidationError):
        applications.review_resumption(reviewer, record)

    record.refresh_from_db()
    assert record.reviewed_at == first_reviewed_at
    assert accounts.balance(101, "EL", 2026) == Decimal("13")
    assert (
        LeaveAccountTransaction.objects.filter(
            transaction_type="resumption_adjustment",
            application=approved_leave,
        ).count()
        == 1
    )
    assert len(synchronized) == 1


def test_missing_external_attendance_provider_keeps_adjustment(
    approved_leave,
    reviewer,
    monkeypatch,
):
    def unavailable(**kwargs):
        raise contracts.ExternalDependencyUnavailable("Not configured")

    monkeypatch.setattr(contracts, "synchronize_attendance", unavailable)
    record = ResumptionRecord.objects.create(
        application=approved_leave,
        employee_user_id=101,
        actual_resumption_date=date(2026, 5, 7),
    )
    applications.review_resumption(reviewer, record)
    record.refresh_from_db()

    assert accounts.balance(101, "EL", 2026) == Decimal("13")
    assert record.synchronization_status == "pending_external"


def test_only_assigned_authority_with_permission_can_review(approved_leave, reviewer):
    record = ResumptionRecord.objects.create(
        application=approved_leave,
        employee_user_id=101,
        actual_resumption_date=date(2026, 5, 7),
    )
    with pytest.raises(NotFound):
        applications.review_resumption(
            make_principal(user_id=999, permissions=("leave.resumption.review",)),
            record,
        )
    with pytest.raises(PermissionDenied):
        applications.review_resumption(
            make_principal(user_id=202, permissions=()),
            record,
        )
    assert accounts.balance(101, "EL", 2026) == Decimal("10")
    assert not LeaveAccountTransaction.objects.filter(
        transaction_type="resumption_adjustment",
    ).exists()
