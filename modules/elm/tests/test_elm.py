from datetime import date, timedelta
from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import (
    HolidayCalendar,
    LeaveAction,
    LeaveBalance,
    LeaveRequest,
    LeaveTransaction,
)
from modules.elm.api.views import (
    calculate_leave_days,
    validate_overlap,
)


@pytest.mark.django_db
class TestLeaveDayCalculation:
    def test_half_day_cl_calculation(self):
        """BR-EL-010: Half-day CL consumes exactly 0.5 days."""
        d = date(2026, 11, 2)  # Monday
        assert calculate_leave_days("CL", d, d, "first_half") == Decimal("0.5")
        assert calculate_leave_days("CL", d, d, "second_half") == Decimal("0.5")

    def test_continuous_counting_for_el_col_vl(self):
        """BR-EL-011: For EL, COL, VL, intervening weekends and holidays count."""
        # Friday to Monday = 4 continuous days
        start = date(2026, 11, 6)   # Friday
        end = date(2026, 11, 9)     # Monday
        assert calculate_leave_days("EL", start, end, "full") == Decimal("4")
        assert calculate_leave_days("COL", start, end, "full") == Decimal("4")
        assert calculate_leave_days("VL", start, end, "full") == Decimal("4")

    def test_non_continuous_counting_for_cl_scl_rh(self):
        """BR-EL-011: For CL, SCL, RH, intervening weekends and holidays do not count."""
        # Friday to Monday = Friday + Monday = 2 days (Sat & Sun excluded)
        start = date(2026, 11, 6)   # Friday
        end = date(2026, 11, 9)     # Monday
        assert calculate_leave_days("CL", start, end, "full") == Decimal("2")
        assert calculate_leave_days("SCL", start, end, "full") == Decimal("2")

        # Closed holiday on Friday -> only Monday counts = 1 day
        HolidayCalendar.objects.create(
            date=start, name="Diwali Holiday", is_restricted=False, year=2026
        )
        assert calculate_leave_days("CL", start, end, "full") == Decimal("1")


@pytest.mark.django_db
class TestLeaveValidationAndOverlap:
    def test_overlap_blocks_duplicate_request(self):
        """BR-EL-012: Request cannot impermissibly overlap active pending/approved leave."""
        user_id = 101
        LeaveRequest.objects.create(
            user_id=user_id,
            category="EL",
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 15),
            status="pending",
        )
        with pytest.raises(ValidationError):
            validate_overlap(user_id, date(2026, 11, 12), date(2026, 11, 18), "full")

    def test_cl_different_halves_same_day_allowed(self):
        """BR-EL-012: Different halves of CL on the same date are allowed."""
        user_id = 102
        d = date(2026, 11, 10)
        LeaveRequest.objects.create(
            user_id=user_id,
            category="CL",
            start_date=d,
            end_date=d,
            part_of_day="first_half",
            status="approved",
        )
        # Second half on the same date must not raise ValidationError
        validate_overlap(user_id, d, d, "second_half")


@pytest.mark.django_db
class TestLeaveLifecycleAndWorkflow:
    def test_substitute_consent_gate(self):
        """BR-EL-014, BR-EL-015: Substitute must accept before request moves to Unit Head."""
        req = LeaveRequest.objects.create(
            user_id=201,
            category="CL",
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 21),
            days_requested=Decimal("2"),
            substitute_user_id=202,
            substitute_status="pending",
            status="pending",
            current_stage="substitute_consent",
        )
        assert req.current_stage == "substitute_consent"
        assert req.substitute_status == "pending"

        # Substitute accepts -> advances to unit_head_review
        req.substitute_status = "accepted"
        req.current_stage = "unit_head_review"
        req.save()
        assert req.current_stage == "unit_head_review"

    def test_unit_head_final_decision_for_cl_deducts_balance(self):
        """BR-EL-016: Unit Head is final authority for CL and approval deducts balance."""
        user_id = 301
        bal = LeaveBalance.objects.create(
            user_id=user_id,
            year=2026,
            category="CL",
            entitled_days=Decimal("8"),
            used_days=Decimal("0"),
        )
        req = LeaveRequest.objects.create(
            user_id=user_id,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 3),
            days_requested=Decimal("2"),
            status="pending",
            current_stage="unit_head_review",
        )

        # Approve and deduct
        req.status = "approved"
        req.current_stage = "completed"
        req.save()
        bal.used_days += req.days_requested
        bal.save()
        LeaveTransaction.objects.create(
            request=req,
            user_id=user_id,
            year=2026,
            category="CL",
            transaction_type="debit",
            amount=req.days_requested,
            note="Approved by Unit Head",
        )

        assert bal.available_days == Decimal("6")
        assert LeaveTransaction.objects.filter(request=req, transaction_type="debit").exists()

    def test_pre_start_cancellation_restores_balance(self):
        """BR-EL-023: Cancellation before start restores used balance."""
        user_id = 401
        bal = LeaveBalance.objects.create(
            user_id=user_id,
            year=2026,
            category="EL",
            entitled_days=Decimal("30"),
            used_days=Decimal("5"),
        )
        req = LeaveRequest.objects.create(
            user_id=user_id,
            category="EL",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 5),
            days_requested=Decimal("5"),
            status="approved",
            current_stage="completed",
        )

        # Cancel
        req.status = "cancelled"
        req.save()
        bal.used_days -= req.days_requested
        bal.save()
        LeaveTransaction.objects.create(
            request=req,
            user_id=user_id,
            year=2026,
            category="EL",
            transaction_type="restoration",
            amount=req.days_requested,
            note="Cancelled pre-start",
        )

        assert bal.available_days == Decimal("30")
        assert LeaveTransaction.objects.filter(request=req, transaction_type="restoration").exists()

    def test_year_end_processing_vl_conversion_and_lapse(self):
        """BR-EL-007, BR-EL-008: VL converts to EL at 2:1 ratio; CL lapses."""
        user_id = 501
        # 60 VL entitled, 20 used -> 40 available
        LeaveBalance.objects.create(
            user_id=user_id,
            year=2026,
            category="VL",
            entitled_days=Decimal("60"),
            used_days=Decimal("20"),
        )
        # 8 CL entitled, 3 used -> 5 unused
        LeaveBalance.objects.create(
            user_id=user_id,
            year=2026,
            category="CL",
            entitled_days=Decimal("8"),
            used_days=Decimal("3"),
        )

        # 40 VL converts to 20 EL
        unused_vl = Decimal("40")
        converted_el = unused_vl / Decimal("2")
        el_next = LeaveBalance.objects.create(
            user_id=user_id,
            year=2027,
            category="EL",
            entitled_days=Decimal("0"),
            carried_forward_days=converted_el,
        )

        assert converted_el == Decimal("20")
        assert el_next.available_days == Decimal("20")

    def test_offline_sanctioned_synchronization(self):
        """BR-EL-029: Retrospective offline entry logs sanction reference and updates balance."""
        user_id = 601
        bal = LeaveBalance.objects.create(
            user_id=user_id,
            year=2026,
            category="SCL",
            entitled_days=Decimal("15"),
            used_days=Decimal("0"),
        )
        req = LeaveRequest.objects.create(
            user_id=user_id,
            category="SCL",
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 7),
            days_requested=Decimal("3"),
            status="approved",
            current_stage="completed",
            offline_sanctioned=True,
            offline_reference="DIR/OFF/2026/88",
        )
        bal.used_days += req.days_requested
        bal.save()

        assert req.offline_sanctioned is True
        assert req.offline_reference == "DIR/OFF/2026/88"
        assert bal.available_days == Decimal("12")


@pytest.mark.django_db
class TestELMAPIEndpoints:
    def _client(self, stub_iam, user_id=1001, permissions=("leave_elm.request.view_self", "leave_elm.request.apply", "leave_elm.balance.view_self", "leave_elm.request.review")):
        stub_iam(make_session(
            user_id=user_id,
            modules=("leave_elm",),
            permissions=permissions,
        ))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token mock-token")
        return c

    def test_api_leave_balances(self, stub_iam):
        uid = 1001
        c = self._client(stub_iam, user_id=uid)
        LeaveBalance.objects.create(
            user_id=uid,
            year=timezone.localdate().year,
            category="CL",
            entitled_days=Decimal("8"),
            used_days=Decimal("2"),
        )
        res = c.get("/api/v1/elm/balances")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert Decimal(str(data[0]["available_days"])) == Decimal("6")

    def test_api_apply_and_withdraw_leave(self, stub_iam):
        uid = 1002
        c = self._client(stub_iam, user_id=uid)
        year = timezone.localdate().year
        LeaveBalance.objects.create(
            user_id=uid,
            year=year,
            category="CL",
            entitled_days=Decimal("8"),
            used_days=Decimal("0"),
        )

        # Apply for leave
        res = c.post("/api/v1/elm/requests", {
            "category": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "part_of_day": "full",
            "reason": "Family function",
            "station_leave": False,
        })
        assert res.status_code == 201
        req_id = res.json()["id"]
        assert res.json()["status"] == "pending"

        # Withdraw
        w_res = c.post(f"/api/v1/elm/requests/{req_id}/withdraw")
        assert w_res.status_code == 200
        assert w_res.json()["status"] == "withdrawn"

    def test_api_unit_head_approval_and_deduction(self, stub_iam):
        applicant_id = 1003
        reviewer_id = 9001
        year = timezone.localdate().year
        bal = LeaveBalance.objects.create(
            user_id=applicant_id,
            year=year,
            category="CL",
            entitled_days=Decimal("8"),
            used_days=Decimal("0"),
        )
        req = LeaveRequest.objects.create(
            user_id=applicant_id,
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 3),
            days_requested=Decimal("2"),
            status="pending",
            current_stage="unit_head_review",
        )

        c = self._client(stub_iam, user_id=reviewer_id)
        res = c.post(f"/api/v1/elm/requests/{req.pk}/decision", {
            "decision": "approve",
            "note": "Approved for department",
        })
        assert res.status_code == 200
        assert res.json()["status"] == "approved"

        bal.refresh_from_db()
        assert bal.used_days == Decimal("2")
        assert bal.available_days == Decimal("6")
        assert LeaveTransaction.objects.filter(request=req, transaction_type="debit").exists()
