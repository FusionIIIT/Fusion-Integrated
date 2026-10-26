from datetime import date, timedelta
from decimal import Decimal
import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveStatus, LeaveType
from modules.elm.services import (
    cancel_approved_application,
    director_self_sanction,
    execute_year_end_processing,
    extend_leave_application,
    init_employee_balances,
    process_sla_checks,
    record_offline_leave,
    replace_substitute_or_proceed,
    respond_substitute,
    sanctioning_authority_review,
    submit_and_verify_resumption,
    submit_leave_application,
    unit_head_review,
    withdraw_pending_application,
)

pytestmark = pytest.mark.django_db


class TestELMBalanceAndEligibility:
    def test_staff_balance_initialization(self):
        balances = init_employee_balances("staff001", is_faculty=False, year=2026)
        types = {b.leave_type: b.total_allocated for b in balances}
        assert types[LeaveType.CL] == Decimal("8.0")
        assert types[LeaveType.RH] == Decimal("2.0")
        assert types[LeaveType.SCL] == Decimal("15.0")
        assert types[LeaveType.EL] == Decimal("30.0")
        assert types[LeaveType.COL] == Decimal("20.0")
        assert LeaveType.VL not in types

    def test_faculty_balance_initialization(self):
        balances = init_employee_balances("fac001", is_faculty=True, year=2026)
        types = {b.leave_type: b.total_allocated for b in balances}
        assert types[LeaveType.CL] == Decimal("8.0")
        assert types[LeaveType.VL] == Decimal("60.0")
        assert types[LeaveType.EL] == Decimal("0.0")

    def test_staff_cannot_apply_vacation_leave(self):
        data = {
            "leave_type": LeaveType.VL,
            "start_date": date(2026, 6, 1),
            "end_date": date(2026, 6, 10),
            "reason": "Summer break",
        }
        with pytest.raises(BadRequestError, match="Vacation Leave.*only available to Faculty"):
            submit_leave_application("staff001", data, is_faculty=False)

    def test_half_day_cl_rules(self):
        # Half-day only permitted for CL
        with pytest.raises(BadRequestError, match="Half-day leave option is only permitted for Casual Leave"):
            submit_leave_application(
                "fac001",
                {"leave_type": LeaveType.EL, "start_date": date(2026, 5, 1), "end_date": date(2026, 5, 1), "is_half_day": True, "reason": "Doc"},
                is_faculty=True,
            )

        # Half-day must be single day
        with pytest.raises(BadRequestError, match="single day"):
            submit_leave_application(
                "fac001",
                {"leave_type": LeaveType.CL, "start_date": date(2026, 5, 1), "end_date": date(2026, 5, 2), "is_half_day": True, "reason": "Doc"},
                is_faculty=True,
            )

        # Valid half day CL
        app = submit_leave_application(
            "fac001",
            {"leave_type": LeaveType.CL, "start_date": date(2026, 5, 1), "end_date": date(2026, 5, 1), "is_half_day": True, "reason": "Doc appointment"},
            is_faculty=True,
        )
        assert app.total_days == Decimal("0.5")

    def test_overlapping_leave_rejected(self):
        submit_leave_application(
            "emp001",
            {"leave_type": LeaveType.CL, "start_date": date(2026, 4, 10), "end_date": date(2026, 4, 12), "reason": "Trip"},
        )
        with pytest.raises(ConflictError, match="overlap"):
            submit_leave_application(
                "emp001",
                {"leave_type": LeaveType.CL, "start_date": date(2026, 4, 11), "end_date": date(2026, 4, 15), "reason": "Trip 2"},
            )

    def test_station_leave_coupling_rule(self):
        with pytest.raises(BadRequestError, match="Outstation address must be specified"):
            submit_leave_application(
                "emp001",
                {"leave_type": LeaveType.CL, "start_date": date(2026, 7, 1), "end_date": date(2026, 7, 2), "requires_station_leave": True, "reason": "Conference"},
            )


class TestELMWorkflowProgression:
    def test_substitute_consent_gate_and_replacement(self):
        # 1. Submit with substitute
        app = submit_leave_application(
            "emp001",
            {
                "leave_type": LeaveType.CL,
                "start_date": date(2026, 8, 1),
                "end_date": date(2026, 8, 2),
                "reason": "Personal",
                "substitute_id": "sub001",
            },
        )
        assert app.status == LeaveStatus.AWAITING_SUBSTITUTE
        assert app.substitute_status == "PENDING"

        # 2. Substitute declines
        app = respond_substitute(app.id, "sub001", accept=False, remarks="Busy with exams")
        assert app.status == LeaveStatus.SUBSTITUTE_DECLINED
        assert app.substitute_status == "DECLINED"

        # 3. Applicant nominates another substitute
        app = replace_substitute_or_proceed(app.id, "emp001", new_substitute_id="sub002")
        assert app.status == LeaveStatus.AWAITING_SUBSTITUTE
        assert app.substitute_id == "sub002"

        # 4. New substitute accepts
        app = respond_substitute(app.id, "sub002", accept=True, remarks="Sure")
        assert app.status == LeaveStatus.AWAITING_UNIT_HEAD

    def test_unit_head_final_sanction_for_cl_and_rh(self):
        app = submit_leave_application(
            "emp002",
            {"leave_type": LeaveType.CL, "start_date": date(2026, 9, 1), "end_date": date(2026, 9, 2), "reason": "Rest"},
        )
        assert app.status == LeaveStatus.AWAITING_UNIT_HEAD

        # Unit head cannot "recommend" CL
        with pytest.raises(BadRequestError, match="finalized directly"):
            unit_head_review(app.id, "hod001", action="recommend")

        # Unit head final approves
        app = unit_head_review(app.id, "hod001", action="approve", remarks="Approved")
        assert app.status == LeaveStatus.APPROVED
        assert app.unit_head_recommendation == "APPROVED_FINAL"

        bal = LeaveBalance.objects.get(employee_id="emp002", year=2026, leave_type=LeaveType.CL)
        assert bal.used_days == Decimal("2.0")
        assert bal.remaining_days == Decimal("6.0")

    def test_higher_sanction_routing_for_scl_and_el(self):
        init_employee_balances("staff002", is_faculty=False, year=2026)
        app = submit_leave_application(
            "staff002",
            {"leave_type": LeaveType.EL, "start_date": date(2026, 10, 1), "end_date": date(2026, 10, 5), "reason": "Family"},
        )
        assert app.status == LeaveStatus.AWAITING_UNIT_HEAD

        # Unit head cannot directly finalize EL
        with pytest.raises(BadRequestError, match="requires higher sanctioning authority"):
            unit_head_review(app.id, "hod001", action="approve")

        # Unit head recommends
        app = unit_head_review(app.id, "hod001", action="recommend", remarks="Recommended")
        assert app.status == LeaveStatus.AWAITING_SANCTION

        # Higher Sanction approves
        app = sanctioning_authority_review(app.id, "dean001", action="approve", remarks="Sanctioned by Dean")
        assert app.status == LeaveStatus.APPROVED
        assert app.sanction_decision == "APPROVED"

        bal = LeaveBalance.objects.get(employee_id="staff002", year=2026, leave_type=LeaveType.EL)
        assert bal.used_days == Decimal("5.0")
        assert bal.remaining_days == Decimal("25.0")

    def test_director_self_sanction_flow(self):
        app = submit_leave_application(
            "director001",
            {"leave_type": LeaveType.CL, "start_date": date(2026, 11, 1), "end_date": date(2026, 11, 1), "reason": "Off campus"},
            is_director=True,
        )
        assert app.status == LeaveStatus.AWAITING_DIRECTOR_SELF_SANCTION

        app = director_self_sanction(app.id, "director001", action="approve", remarks="Self sanction")
        assert app.status == LeaveStatus.APPROVED


class TestWithdrawalCancellationExtensionResumption:
    def test_withdrawal_of_pending_leave(self):
        app = submit_leave_application(
            "emp003",
            {"leave_type": LeaveType.CL, "start_date": date(2026, 12, 1), "end_date": date(2026, 12, 2), "reason": "Plans"},
        )
        app = withdraw_pending_application(app.id, "emp003", reason="Plans cancelled")
        assert app.status == LeaveStatus.WITHDRAWN

    def test_cancellation_of_approved_leave_restores_balance(self):
        future_date = date.today() + timedelta(days=20)
        app = submit_leave_application(
            "emp004",
            {"leave_type": LeaveType.CL, "start_date": future_date, "end_date": future_date + timedelta(days=1), "reason": "Trip"},
        )
        unit_head_review(app.id, "hod001", action="approve")

        bal = LeaveBalance.objects.get(employee_id="emp004", year=future_date.year, leave_type=LeaveType.CL)
        assert bal.used_days == Decimal("2.0")

        # Cancel approved leave
        app = cancel_approved_application(app.id, "emp004", reason="Trip postponed")
        assert app.status == LeaveStatus.CANCELLED

        bal.refresh_from_db()
        assert bal.used_days == Decimal("0.0")

    def test_leave_extension_flow(self):
        init_employee_balances("emp005", is_faculty=False, year=2026)
        app = submit_leave_application(
            "emp005",
            {"leave_type": LeaveType.EL, "start_date": date(2026, 8, 1), "end_date": date(2026, 8, 5), "reason": "Medical"},
        )
        unit_head_review(app.id, "hod001", action="recommend")
        sanctioning_authority_review(app.id, "dean001", action="approve")

        # Extension for 3 additional days
        ext_app = extend_leave_application(app.id, "emp005", new_end_date=date(2026, 8, 8), reason="Extended medical recovery")
        assert ext_app.is_extension is True
        assert ext_app.parent_leave_id == app.id
        assert ext_app.total_days == Decimal("3.0")
        assert ext_app.status == LeaveStatus.AWAITING_UNIT_HEAD

    def test_resumption_and_early_return_restores_unused_balance(self):
        init_employee_balances("emp006", is_faculty=False, year=2026)
        app = submit_leave_application(
            "emp006",
            {"leave_type": LeaveType.EL, "start_date": date(2026, 9, 10), "end_date": date(2026, 9, 19), "reason": "Long leave"},
        )
        unit_head_review(app.id, "hod001", action="recommend")
        sanctioning_authority_review(app.id, "dean001", action="approve")

        bal = LeaveBalance.objects.get(employee_id="emp006", year=2026, leave_type=LeaveType.EL)
        assert bal.used_days == Decimal("10.0")

        # Resumed early on 9/15 (availed only 5 days, returning 5 days early)
        app = submit_and_verify_resumption(app.id, "emp006", actual_resumption_date=date(2026, 9, 15), verifier_id="admin001")
        assert app.status == LeaveStatus.CLOSED
        assert app.actual_days_availed == Decimal("5.0")

        bal.refresh_from_db()
        assert bal.used_days == Decimal("5.0")
        assert bal.remaining_days == Decimal("25.0")


class TestOfflineYearEndAndSLA:
    def test_offline_sanction_recording(self):
        app = record_offline_leave(
            "admin001",
            {
                "employee_id": "emp007",
                "is_faculty": False,
                "leave_type": LeaveType.EL,
                "start_date": date(2026, 3, 1),
                "end_date": date(2026, 3, 4),
                "offline_sanction_ref": "OFF/2026/042",
            },
        )
        assert app.status == LeaveStatus.APPROVED
        assert app.is_offline_record is True
        assert app.offline_sanction_ref == "OFF/2026/042"

    def test_year_end_processing(self):
        # Set up Faculty with unused VL
        init_employee_balances("fac_ye", is_faculty=True, year=2025)
        # Set up Staff with unused EL
        init_employee_balances("staff_ye", is_faculty=False, year=2025)

        results = execute_year_end_processing(2025)
        assert results["lapsed"] > 0
        assert results["converted_vl"] > 0
        assert results["carried_forward"] > 0

        # Verify faculty VL converted to EL at 1:2 ratio (60 VL -> 30 EL carried forward)
        fac_next_el = LeaveBalance.objects.get(employee_id="fac_ye", year=2026, leave_type=LeaveType.EL)
        assert fac_next_el.carried_forward == Decimal("30.0")

        # Verify staff EL carried forward (30 EL carried forward)
        staff_next_el = LeaveBalance.objects.get(employee_id="staff_ye", year=2026, leave_type=LeaveType.EL)
        assert staff_next_el.carried_forward == Decimal("30.0")

        # Verify 2025 CL lapsed
        staff_cl_2025 = LeaveBalance.objects.get(employee_id="staff_ye", year=2025, leave_type=LeaveType.CL)
        assert staff_cl_2025.lapsed_days == Decimal("8.0")
