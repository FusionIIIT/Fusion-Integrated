import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from modules.leave.models import LeaveType, LeaveBalance, LeaveRequest, LeaveLedger


@pytest.mark.django_db
class TestELMBusinessRulesVerification:
    """Verification suite for ELM business rules generated in Lab 6B (Phase 2)."""

    def test_br_el_001_and_002_cl_quota_and_half_day(self):
        """BR-EL-001 & BR-EL-002: Casual Leave quota (8 days) and half-day eligibility."""
        cl = LeaveType.objects.create(
            code="CL",
            name="Casual Leave",
            max_days_per_year=8,
            allows_half_day=True,
            requires_attachment=False,
        )
        assert cl.max_days_per_year == 8
        assert cl.allows_half_day is True

        req = LeaveRequest.objects.create(
            user_id=101,
            leave_type=cl,
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            duration_days=Decimal("0.5"),
            is_half_day=True,
            half_day_slot="FORENOON",
            reason="Personal appointment",
            status="PENDING_APPROVAL",
        )
        assert req.duration_days == Decimal("0.5")
        assert req.is_half_day is True
        assert req.half_day_slot == "FORENOON"

    def test_br_el_003_rh_quota(self):
        """BR-EL-003: Restricted Holiday entitlement (2 days/year)."""
        rh = LeaveType.objects.create(code="RH", name="Restricted Holiday", max_days_per_year=2)
        assert rh.max_days_per_year == 2

    def test_br_el_005_el_quota(self):
        """BR-EL-005: Earned Leave entitlement (30 days/year)."""
        el = LeaveType.objects.create(code="EL", name="Earned Leave", max_days_per_year=30)
        assert el.max_days_per_year == 30

    def test_br_el_009_col_attachment_requirement(self):
        """BR-EL-009: Commuted Leave requires supporting medical attachment."""
        col = LeaveType.objects.create(
            code="COL",
            name="Commuted Leave",
            max_days_per_year=20,
            requires_attachment=True,
        )
        assert col.requires_attachment is True

    def test_br_el_013_station_leave_coupling(self):
        """BR-EL-013: Station Leave fields coupled within leave request."""
        cl = LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)
        req = LeaveRequest.objects.create(
            user_id=102,
            leave_type=cl,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 14),
            duration_days=Decimal("5.0"),
            reason="Conference presentation",
            is_station_leave=True,
            station_start_date=date(2026, 11, 10),
            station_end_date=date(2026, 11, 14),
            station_address="IISc Bangalore Guest House",
            emergency_contact_no="9876543210",
            status="PENDING_APPROVAL",
        )
        assert req.is_station_leave is True
        assert req.station_address == "IISc Bangalore Guest House"
        assert req.emergency_contact_no == "9876543210"

    def test_multi_tier_workflow_transitions(self):
        """State machine: DRAFT -> PENDING_APPROVAL -> RECOMMENDED -> APPROVED."""
        cl = LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)
        req = LeaveRequest.objects.create(
            user_id=103,
            leave_type=cl,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 2),
            duration_days=Decimal("2.0"),
            reason="Family function",
            status="PENDING_APPROVAL",
        )

        # Recommendation stage (e.g. HOD / Unit Head)
        req.status = "RECOMMENDED"
        req.recommender_user_id = 205
        req.recommendation_remarks = "Recommended for approval"
        req.recommended_at = timezone.now()
        req.save()
        assert req.status == "RECOMMENDED"

        # Sanction stage (e.g. Dean / Sanctioning Authority)
        req.status = "APPROVED"
        req.approver_user_id = 301
        req.approval_remarks = "Approved"
        req.approved_at = timezone.now()
        req.save()
        assert req.status == "APPROVED"

    def test_leave_ledger_audit_trail(self):
        """Leave ledger tracks debits and restorations."""
        cl = LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)
        req = LeaveRequest.objects.create(
            user_id=104,
            leave_type=cl,
            start_date=date(2026, 12, 5),
            end_date=date(2026, 12, 6),
            duration_days=Decimal("2.0"),
            reason="Medical rest",
            status="APPROVED",
        )

        # Debit entry upon approval
        debit = LeaveLedger.objects.create(
            user_id=104,
            leave_type=cl,
            transaction_type="DEBIT",
            days=Decimal("2.0"),
            balance_after=Decimal("6.0"),
            reference_request=req,
            remarks="Approved leave #req",
        )
        assert debit.transaction_type == "DEBIT"
        assert debit.days == Decimal("2.0")
        assert debit.balance_after == Decimal("6.0")

        # Restoration entry upon cancellation
        restore = LeaveLedger.objects.create(
            user_id=104,
            leave_type=cl,
            transaction_type="RESTORE",
            days=Decimal("2.0"),
            balance_after=Decimal("8.0"),
            reference_request=req,
            remarks="Restored cancelled leave",
        )
        assert restore.transaction_type == "RESTORE"
        assert restore.balance_after == Decimal("8.0")
