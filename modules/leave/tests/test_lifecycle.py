"""Tests for Employee Leave Management lifecycle services (CW-EL-02..04, BR-EL-029)."""

from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import (
    ConflictError,
    PermissionDeniedError,
)
from fusion_auth.client import UserRef
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveType,
)
from modules.leave.services import (
    apply_for_leave,
    record_offline_leave,
    request_cancellation,
    request_extension,
    review_cancellation_unit_head,
    review_extension_unit_head,
    review_resumption,
    review_unit_head,
    sanction_extension,
    sanction_leave,
    submit_resumption,
)


@pytest.fixture
def setup_lifecycle_env(db, stub_iam):
    stub_iam(
        users={
            1001: UserRef(
                user_id=1001,
                username="fac_alice",
                display_name="Alice CSE",
                kind="faculty",
                department="Computer Science & Engineering",
            ),
            2001: UserRef(
                user_id=2001,
                username="hod_cse",
                display_name="Dr. Smith HOD CSE",
                kind="faculty",
                department="Computer Science & Engineering",
            ),
            3001: UserRef(
                user_id=3001,
                username="dean_acad",
                display_name="Prof. Johnson Dean",
                kind="faculty",
                department="Administration",
            ),
            4001: UserRef(
                user_id=4001,
                username="hr_admin",
                display_name="Admin HR",
                kind="staff",
                department="Establishment",
            ),
        }
    )

    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        allows_half_day=True,
        lapses_at_year_end=True,
        is_continuous_count=False,
    )
    el = LeaveType.objects.create(
        code="EL",
        name="Earned Leave",
        carries_forward=True,
        is_continuous_count=True,
        allows_extension=True,
    )

    LeaveBalance.objects.create(
        user_id=1001,
        leave_type=cl,
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("8.0"),
    )
    LeaveBalance.objects.create(
        user_id=1001,
        leave_type=el,
        year=2026,
        credited_days=Decimal("30.0"),
        available_days=Decimal("30.0"),
    )

    return {"CL": cl, "EL": el}


# 1. Cancellation Tests (CW-EL-02, BR-EL-023)
@pytest.mark.django_db
def test_cancellation_cl_unit_head_restores_balance(setup_lifecycle_env):
    # Apply and approve CL (deducts 2 days)
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 11, 19),
        end_date=date(2026, 11, 20),
        reason="Family trip",
    )
    review_unit_head(actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="approve")
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="CL", year=2026)
    assert bal.available_days == Decimal("6.0")

    # Request cancellation before start date (on 2026-11-10)
    req = request_cancellation(
        actor_user_id=1001,
        request_id=req.id,
        reason="Trip called off",
        current_date=date(2026, 11, 10),
    )
    assert req.status == LeaveState.CANCELLATION_PENDING_UNIT_HEAD
    assert req.cancellation_reason == "Trip called off"

    # Unit Head approves cancellation -> CANCELLED, balance restored
    reviewed = review_cancellation_unit_head(
        actor_user_id=2001,
        actor_roles=["HOD"],
        request_id=req.id,
        decision="approve",
    )
    assert reviewed.status == LeaveState.CANCELLED

    bal.refresh_from_db()
    assert bal.available_days == Decimal("8.0")  # Restored to 8.0
    assert bal.used_days == Decimal("0.0")
    assert LeaveLedgerEntry.objects.filter(
        balance=bal, entry_type="credit", reference_type="cancellation"
    ).exists()


@pytest.mark.django_db
def test_cancellation_after_start_date_fails(setup_lifecycle_env):
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 6),
        reason="Medical",
    )
    review_unit_head(actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="approve")

    # Attempting cancellation on or after start date fails (BR-EL-023)
    with pytest.raises(ConflictError, match="strictly before the leave start date"):
        request_cancellation(
            actor_user_id=1001,
            request_id=req.id,
            reason="Late cancel",
            current_date=date(2026, 11, 5),
        )


# 2. Extension Tests (CW-EL-03, BR-EL-025)
@pytest.mark.django_db
def test_extension_ongoing_leave_successful_and_incremental_debit(setup_lifecycle_env):
    # Apply and sanction 5 days EL (2026-11-10 to 2026-11-14)
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        reason="Annual rest",
    )
    review_unit_head(
        actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="recommend"
    )
    sanction_leave(
        actor_user_id=3001, actor_roles=["Dean Academic"], request_id=req.id, decision="approve"
    )
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="EL", year=2026)
    assert bal.available_days == Decimal("25.0")  # 30 - 5 = 25

    # While leave is ongoing (on 2026-11-12), request extension to 2026-11-17 (3 incremental days)
    req = request_extension(
        actor_user_id=1001,
        request_id=req.id,
        extension_end_date=date(2026, 11, 17),
        reason="Personal extension",
        current_date=date(2026, 11, 12),
    )
    assert req.status == LeaveState.AWAITING_EXTENSION_UNIT_HEAD
    assert req.extension_days == Decimal("3.0")

    # Balance NOT debited yet
    bal.refresh_from_db()
    assert bal.available_days == Decimal("25.0")

    # Unit Head recommends extension
    review_extension_unit_head(
        actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="recommend"
    )

    # Dean Academic sanctions extension
    sanctioned = sanction_extension(
        actor_user_id=3001,
        actor_roles=["Dean Academic"],
        request_id=req.id,
        decision="approve",
    )
    assert sanctioned.status == LeaveState.EXTENDED
    assert sanctioned.end_date == date(2026, 11, 17)
    assert sanctioned.requested_days == Decimal("8.0")  # 5 + 3

    # Incremental 3 days debited from balance
    bal.refresh_from_db()
    assert bal.available_days == Decimal("22.0")  # 25 - 3 = 22
    assert bal.used_days == Decimal("8.0")


# 3. Resumption Tests (CW-EL-04, BR-EL-027..028, DEC-ELM-001)
@pytest.mark.django_db
def test_resumption_normal_and_early_and_late(setup_lifecycle_env):
    # Setup approved EL: 10 days (2026-11-1 to 2026-11-10) -> expected return date is 2026-11-11
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 10),
        reason="Research writing",
    )
    review_unit_head(
        actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="recommend"
    )
    sanction_leave(
        actor_user_id=3001, actor_roles=["Dean Academic"], request_id=req.id, decision="approve"
    )
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="EL", year=2026)
    assert bal.available_days == Decimal("20.0")  # 30 - 10 = 20

    # Case A: Normal resumption (returned on 2026-11-11)
    res = submit_resumption(
        actor_user_id=1001,
        request_id=req.id,
        actual_resumption_date=date(2026, 11, 11),
        remarks="Normal return",
    )
    assert res.nature == "normal"
    assert res.difference_days == Decimal("0.0")

    reviewed = review_resumption(
        actor_user_id=3001,
        actor_roles=["Dean Academic"],
        request_id=req.id,
    )
    assert reviewed.decision == "approved"
    req.refresh_from_db()
    assert req.status == LeaveState.RESUMPTION_NO_ADJUSTMENT
    bal.refresh_from_db()
    assert bal.available_days == Decimal("20.0")  # No adjustment


@pytest.mark.django_db
def test_resumption_early_credits_balance(setup_lifecycle_env):
    # Approved 10 days EL (2026-11-1 to 2026-11-10)
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 10),
        reason="Personal rest",
    )
    review_unit_head(
        actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="recommend"
    )
    sanction_leave(
        actor_user_id=3001, actor_roles=["Dean Academic"], request_id=req.id, decision="approve"
    )

    # Returns 2 days early (actual resumption on 2026-11-9 instead of 2026-11-11)
    submit_resumption(
        actor_user_id=1001,
        request_id=req.id,
        actual_resumption_date=date(2026, 11, 9),
        remarks="Returned early",
    )
    review_resumption(actor_user_id=3001, actor_roles=["Dean Academic"], request_id=req.id)

    req.refresh_from_db()
    assert req.status == LeaveState.RESUMPTION_EARLY_SYNCHRONIZED
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="EL", year=2026)
    assert bal.available_days == Decimal("22.0")  # 20 + 2 credited back = 22
    assert req.actual_days == Decimal("8.0")


@pytest.mark.django_db
def test_resumption_late_deficit_safeguard_dec_elm_001(setup_lifecycle_env):
    # Leave was 5 days (2026-11-1 to 2026-11-5)
    req = apply_for_leave(
        actor_user_id=1001,
        leave_type_code="EL",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5),
        reason="Work",
    )
    review_unit_head(
        actor_user_id=2001, actor_roles=["HOD"], request_id=req.id, decision="recommend"
    )
    sanction_leave(
        actor_user_id=3001, actor_roles=["Dean Academic"], request_id=req.id, decision="approve"
    )

    # Now set remaining available EL balance to only 1.0 day to test late return exceeding balance
    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="EL", year=2026)
    bal.available_days = Decimal("1.0")
    bal.save()

    # Employee returns 3 days late (on 2026-11-9 instead of 2026-11-6 -> 3 excess days)
    # But only 1.0 day available in balance!
    submit_resumption(
        actor_user_id=1001,
        request_id=req.id,
        actual_resumption_date=date(2026, 11, 9),
    )
    review_resumption(actor_user_id=3001, actor_roles=["Dean Academic"], request_id=req.id)

    req.refresh_from_db()
    # DEC-ELM-001 assertions:
    assert req.status == LeaveState.RESUMPTION_LATE_SYNCHRONIZED
    assert req.requires_admin_review is True
    assert req.reconciliation_status == "pending_admin_policy"
    assert req.excess_days == Decimal("3.0")

    # Safeguards: balance is NOT negative, NOT clamped
    bal.refresh_from_db()
    assert bal.available_days == Decimal("1.0")  # Invariant preserved >= 0


# 4. Authorized Offline Leave Records (BR-EL-029)
@pytest.mark.django_db
def test_record_offline_leave_by_admin(setup_lifecycle_env):
    # Non-admin cannot record offline leave
    with pytest.raises(PermissionDeniedError):
        record_offline_leave(
            actor_user_id=1001,
            actor_roles=["faculty"],
            employee_user_id=1001,
            leave_type_code="CL",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 2),
            reason="Pre-approved physical form",
            offline_sanction_reference="EST/2026/OFFLINE/042",
            offline_sanctioned_by="Registrar",
            offline_sanctioned_date=date(2026, 11, 28),
        )

    # Admin records offline leave successfully
    req = record_offline_leave(
        actor_user_id=4001,
        actor_roles=["hr_officer"],
        employee_user_id=1001,
        leave_type_code="CL",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        reason="Pre-approved physical form",
        offline_sanction_reference="EST/2026/OFFLINE/042",
        offline_sanctioned_by="Registrar",
        offline_sanctioned_date=date(2026, 11, 28),
    )
    assert req.status == LeaveState.APPROVED
    assert req.is_offline_record is True
    assert req.offline_sanction_reference == "EST/2026/OFFLINE/042"

    bal = LeaveBalance.objects.get(user_id=1001, leave_type__code="CL", year=2026)
    assert bal.available_days == Decimal("6.0")  # 8 - 2 = 6
    assert LeaveLedgerEntry.objects.filter(balance=bal, reference_type="offline_record").exists()
