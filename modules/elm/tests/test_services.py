from datetime import date
from decimal import Decimal
import pytest

from core.api.exceptions import ConflictError, DomainError
from modules.elm.models import LeaveBalance, LeaveRequest, SubstituteAssignment
from modules.elm.services.leave import (
    apply_for_leave,
    respond_substitute,
    review_leave_request,
    withdraw_leave_request,
    cancel_approved_leave,
    extend_leave,
    execute_year_end_processing,
    submit_resumption_of_duty,
    review_resumption,
    record_offline_sanctioned_leave,
)

@pytest.fixture
def applicant_balance(db):
    return LeaveBalance.objects.create(
        user_id=101,
        category="CL",
        year=2026,
        credited=Decimal("8.00"),
        availed=Decimal("0.00"),
        balance=Decimal("8.00"),
    )

@pytest.mark.django_db
def test_apply_for_leave_with_substitute(applicant_balance):
    req = apply_for_leave(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        half_day="first",
        purpose="Personal errand",
        substitute_id=102,
    )
    assert req.status == "awaiting_substitute"
    assert req.leave_days == Decimal("0.5")
    assert SubstituteAssignment.objects.filter(leave_request=req, substitute_id=102, status="pending").exists()

@pytest.mark.django_db
def test_apply_for_leave_insufficient_balance(applicant_balance):
    applicant_balance.balance = Decimal("0.00")
    applicant_balance.save()
    with pytest.raises(DomainError, match="Insufficient balance"):
        apply_for_leave(
            user_id=101,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 3),
            purpose="Doctor visit",
        )

@pytest.mark.django_db
def test_apply_for_leave_overlap_conflict(applicant_balance):
    apply_for_leave(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 6),
        purpose="Family visit",
    )
    with pytest.raises(ConflictError, match="overlaps with an existing leave request"):
        apply_for_leave(
            user_id=101,
            category="CL",
            start_date=date(2026, 11, 6),
            end_date=date(2026, 11, 7),
            purpose="Another trip",
        )

@pytest.mark.django_db
def test_substitute_respond_and_unit_head_approval(applicant_balance):
    req = apply_for_leave(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 10),
        purpose="Medical checkup",
        substitute_id=102,
    )
    # Substitute accepts
    sub_task = respond_substitute(substitute_id=102, request_id=req.id, action="accept", remarks="Will cover lectures")
    assert sub_task.status == "accepted"
    req.refresh_from_db()
    assert req.status == "under_review"

    # Unit head approves
    review_leave_request(reviewer_id=200, request_id=req.id, action="approve", reason="Approved by HOD")
    req.refresh_from_db()
    assert req.status == "sanctioned"

    # Verify balance was deducted
    applicant_balance.refresh_from_db()
    assert applicant_balance.balance == Decimal("7.00")
    assert applicant_balance.availed == Decimal("1.00")

@pytest.mark.django_db
def test_withdraw_pending_request(applicant_balance):
    req = apply_for_leave(
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 12),
        end_date=date(2026, 11, 12),
        purpose="Personal",
    )
    withdrawn = withdraw_leave_request(user_id=101, request_id=req.id)
    assert withdrawn.status == "withdrawn"

@pytest.mark.django_db
def test_cancel_approved_leave_restores_balance(applicant_balance):
    req = apply_for_leave(
        user_id=101,
        category="CL",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        purpose="Conference",
    )
    review_leave_request(reviewer_id=200, request_id=req.id, action="approve")
    applicant_balance.refresh_from_db()
    assert applicant_balance.balance == Decimal("7.00")

    # Cancel before start date
    cancel_approved_leave(user_id=101, request_id=req.id, today_date=date(2026, 11, 20))
    req.refresh_from_db()
    assert req.status == "cancelled"

    # Balance restored
    applicant_balance.refresh_from_db()
    assert applicant_balance.balance == Decimal("8.00")
    assert applicant_balance.availed == Decimal("0.00")

@pytest.mark.django_db
def test_extend_sanctioned_leave():
    el_balance = LeaveBalance.objects.create(
        user_id=101, category="EL", year=2026,
        credited=Decimal("30.00"), availed=Decimal("5.00"), balance=Decimal("25.00")
    )
    req = LeaveRequest.objects.create(
        user_id=101, category="EL", start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5), leave_days=Decimal("5.00"),
        purpose="Annual leave", status="sanctioned"
    )
    extended = extend_leave(user_id=101, request_id=req.id, new_end_date=date(2026, 11, 7))
    assert extended.end_date == date(2026, 11, 7)
    assert extended.leave_days == Decimal("7.00")
    el_balance.refresh_from_db()
    assert el_balance.balance == Decimal("23.00")
    assert el_balance.availed == Decimal("7.00")

@pytest.mark.django_db
def test_year_end_processing():
    # 20 unutilized VL converts to 10 EL and carried forward
    LeaveBalance.objects.create(
        user_id=101, category="VL", year=2026,
        credited=Decimal("60.00"), availed=Decimal("40.00"), balance=Decimal("20.00")
    )
    LeaveBalance.objects.create(
        user_id=101, category="EL", year=2026,
        credited=Decimal("30.00"), availed=Decimal("10.00"), balance=Decimal("20.00")
    )
    res = execute_year_end_processing(user_id=101, year=2026)
    assert res["credited_el_from_vl"] == Decimal("10.00")
    assert res["carried_forward_el"] == Decimal("30.00")

    # Verify next year's balances (2027)
    el_2027 = LeaveBalance.objects.get(user_id=101, category="EL", year=2027)
    assert el_2027.balance == Decimal("60.00") # 30 carried forward + 30 annual grant
    vl_2027 = LeaveBalance.objects.get(user_id=101, category="VL", year=2027)
    assert vl_2027.balance == Decimal("60.00") # Fresh 60 VL granted, unused 2026 VL zeroed

@pytest.mark.django_db
def test_resumption_submission_and_early_adjustment():
    balance = LeaveBalance.objects.create(
        user_id=101, category="EL", year=2026,
        credited=Decimal("30.00"), availed=Decimal("5.00"), balance=Decimal("25.00")
    )
    req = LeaveRequest.objects.create(
        user_id=101, category="EL", start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6), leave_days=Decimal("5.00"),
        purpose="Out of town vacation", status="sanctioned"
    )
    # Employee reports resumption earlier on 2026-11-05 (only 3 days availed instead of 5)
    submit_resumption_of_duty(user_id=101, request_id=req.id, actual_resumption_date=date(2026, 11, 5))
    req.refresh_from_db()
    assert req.resumption_status == "pending"
    assert req.resumption_date == date(2026, 11, 5)

    # Unit head verifies and approves early resumption
    review_resumption(reviewer_id=200, request_id=req.id, review_remarks="Early resumption verified")
    req.refresh_from_db()
    assert req.resumption_status == "completed"
    assert req.end_date == date(2026, 11, 4)
    assert req.leave_days == Decimal("3.00")

    # Check that 2 unused days were credited back
    balance.refresh_from_db()
    assert balance.balance == Decimal("27.00")
    assert balance.availed == Decimal("3.00")

@pytest.mark.django_db
def test_record_offline_sanctioned_leave():
    balance = LeaveBalance.objects.create(
        user_id=101, category="CL", year=2026,
        credited=Decimal("8.00"), availed=Decimal("0.00"), balance=Decimal("8.00")
    )
    req = record_offline_sanctioned_leave(
        admin_id=999,
        user_id=101,
        category="CL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 10),
        sanction_reference="ORDER/DIR/2026/89",
        purpose="Medical emergency approved offline by Director"
    )
    assert req.status == "sanctioned"
    assert req.is_offline_recorded is True
    assert req.offline_reference == "ORDER/DIR/2026/89"
    assert req.leave_days == Decimal("1.00")

    # Balance deducted directly
    balance.refresh_from_db()
    assert balance.balance == Decimal("7.00")
    assert balance.availed == Decimal("1.00")

