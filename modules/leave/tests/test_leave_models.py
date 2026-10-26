from datetime import date
from decimal import Decimal
import pytest
from modules.leave.models import LeaveType, LeaveBalance, LeaveRequest, LeaveLedger
from modules.leave.api.serializers import LeaveRequestSerializer


@pytest.mark.django_db
def test_leave_type_creation():
    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        max_days_per_year=8,
        allows_half_day=True,
        requires_attachment=False,
    )
    assert cl.code == "CL"
    assert cl.allows_half_day is True
    assert cl.max_days_per_year == 8


@pytest.mark.django_db
def test_leave_balance_calculation():
    lt = LeaveType.objects.create(code="EL", name="Earned Leave", max_days_per_year=30)
    balance = LeaveBalance.objects.create(
        user_id=101,
        leave_type=lt,
        year=2026,
        allocated_days=Decimal("30.0"),
        used_days=Decimal("5.5"),
    )
    assert balance.remaining_days == 24.5


@pytest.mark.django_db
def test_station_leave_request_creation():
    lt = LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8, allows_half_day=True)
    req = LeaveRequest.objects.create(
        user_id=101,
        leave_type=lt,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 3),
        duration_days=Decimal("3.0"),
        reason="Attending academic conference in Delhi",
        is_station_leave=True,
        station_start_date=date(2026, 11, 1),
        station_end_date=date(2026, 11, 3),
        station_address="Hotel Taj Palace, New Delhi",
        emergency_contact_no="9876543210",
        status="PENDING_APPROVAL",
    )
    assert req.is_station_leave is True
    assert req.duration_days == Decimal("3.0")
    assert req.status == "PENDING_APPROVAL"


@pytest.mark.django_db
def test_leave_request_workflow_transitions():
    lt = LeaveType.objects.create(code="RH", name="Restricted Holiday", max_days_per_year=2)
    req = LeaveRequest.objects.create(
        user_id=102,
        leave_type=lt,
        start_date=date(2026, 11, 5),
        end_date=date(2026, 11, 5),
        duration_days=Decimal("1.0"),
        reason="Festival observance",
        status="PENDING_APPROVAL",
    )

    # Recommender step
    req.status = "RECOMMENDED"
    req.recommender_user_id = 201
    req.recommendation_remarks = "Recommended by HOD"
    req.save()
    assert req.status == "RECOMMENDED"

    # Approver step
    req.status = "APPROVED"
    req.approver_user_id = 301
    req.approval_remarks = "Sanctioned by Dean"
    req.save()
    assert req.status == "APPROVED"


@pytest.mark.django_db
def test_leave_ledger_audit_entry():
    lt = LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)
    req = LeaveRequest.objects.create(
        user_id=103,
        leave_type=lt,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        duration_days=Decimal("2.0"),
        reason="Personal work",
        status="APPROVED",
    )
    ledger = LeaveLedger.objects.create(
        user_id=103,
        leave_type=lt,
        transaction_type="DEBIT",
        days=Decimal("2.0"),
        balance_after=Decimal("6.0"),
        reference_request=req,
        remarks="Approved leave #1",
    )
    assert ledger.transaction_type == "DEBIT"
    assert ledger.days == Decimal("2.0")
    assert ledger.balance_after == Decimal("6.0")


@pytest.mark.django_db
def test_serializer_date_validation():
    lt = LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)
    data = {
        "leave_type": lt.id,
        "start_date": "2026-11-15",
        "end_date": "2026-11-10",  # invalid: end before start
        "duration_days": 1,
        "reason": "Test",
    }
    serializer = LeaveRequestSerializer(data=data)
    assert serializer.is_valid() is False
    assert "end_date" in serializer.errors
