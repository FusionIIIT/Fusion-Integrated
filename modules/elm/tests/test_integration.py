"""Test runner for ELM integration tests using in-memory SQLite."""
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from datetime import date, timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

# Setup Django with SQLite in-memory to test full ORM, Services, and Migrations
from django.conf import settings

settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

django.setup()

from django.core.management import call_command

from modules.elm.models.balances import LeaveAccountTransaction, LeaveBalance
from modules.elm.models.holidays import HolidayCalendar
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory
from modules.elm.services.applications import (
    apply_for_leave,
    request_leave_extension,
    withdraw_leave_application,
)
from modules.elm.services.workflows import (
    make_sanction_decision,
    request_cancellation,
    respond_substitute,
    review_cancellation,
    review_resumption,
    review_unit_head,
    route_establishment,
    submit_resumption,
)
from modules.elm.services.year_end import execute_year_end_processing


def run_integration_suite():
    print("Step 1: Running migrations for elm on in-memory SQLite...")
    call_command("migrate", "contenttypes", verbosity=0)
    call_command("migrate", "auth", verbosity=0)
    call_command("migrate", "elm", verbosity=0)
    print("ELM Migrations applied successfully!")

    # Setup test seed data
    user_id = 1001
    substitute_id = 1002
    unit_head_id = 1003
    establishment_id = 1004
    director_id = 1005

    # Seed Balances for User 1001
    LeaveBalance.objects.create(
        user_id=user_id,
        year=2026,
        category="CL",
        credited_balance=Decimal("8.00"),
        carried_forward=Decimal("0.00"),
        availed_balance=Decimal("0.00"),
    )
    LeaveBalance.objects.create(
        user_id=user_id,
        year=2026,
        category="EL",
        credited_balance=Decimal("30.00"),
        carried_forward=Decimal("5.00"),
        availed_balance=Decimal("0.00"),
    )
    LeaveBalance.objects.create(
        user_id=user_id,
        year=2026,
        category="VL",
        credited_balance=Decimal("30.00"),
        carried_forward=Decimal("0.00"),
        availed_balance=Decimal("0.00"),
    )

    print("Step 2: Testing CW-EL-01: Casual Leave (CL) apply & Unit Head direct approve...")
    cl_req = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=date(2026, 11, 2),  # Monday
        end_date=date(2026, 11, 2),
        reason="Personal urgent appointment",
        is_half_day=True,
        half_day_period="first_half",
        unit_head_user_id=unit_head_id,
    )
    assert cl_req.days_calculated == Decimal("0.5")
    assert cl_req.status == "awaiting_unit_head"

    cl_approved = review_unit_head(
        unit_head_user_id=unit_head_id,
        leave_id=cl_req.id,
        decision="approve",
        remarks="Approved half-day CL",
    )
    assert cl_approved.status == "approved"
    bal_cl = LeaveBalance.objects.get(user_id=user_id, year=2026, category="CL")
    assert bal_cl.availed_balance == Decimal("0.5")
    assert bal_cl.available_balance == Decimal("7.5")
    print("PASS: Casual Leave direct sanction & 0.5-day balance deduction verified.")

    print("Step 3: Testing CW-EL-01: Full Multi-Stage Workflow for Earned Leave (EL)...")
    # Apply EL requiring substitute
    el_req = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=date(2026, 11, 9),  # Monday
        end_date=date(2026, 11, 13),  # Friday = 5 calendar days
        reason="Family vacation outside state",
        substitute_user_id=substitute_id,
        unit_head_user_id=unit_head_id,
        leaving_station=True,
        station_address="Hotel Taj, New Delhi",
        emergency_phone="9876543210",
    )
    assert el_req.days_calculated == Decimal("5.00")
    assert el_req.status == "awaiting_substitute"

    # Substitute accepts
    sub_res = respond_substitute(substitute_id, el_req.id, accepted=True)
    assert sub_res.status == "awaiting_unit_head"
    assert sub_res.substitute_status == "accepted"

    # Unit Head recommends to Establishment
    uh_res = review_unit_head(unit_head_id, el_req.id, decision="recommend", remarks="Recommended")
    assert uh_res.status == "awaiting_establishment"

    # Establishment routes
    est_res = route_establishment(establishment_id, el_req.id, remarks="Records verified")
    assert est_res.status == "awaiting_final_sanction"

    # Sanctioning Authority sanctions
    sanct_res = make_sanction_decision(director_id, el_req.id, approve=True, remarks="Sanctioned by Director")
    assert sanct_res.status == "approved"

    bal_el = LeaveBalance.objects.get(user_id=user_id, year=2026, category="EL")
    assert bal_el.availed_balance == Decimal("5.00")
    assert bal_el.available_balance == Decimal("30.00")  # (30 + 5) - 5 = 30
    print("PASS: Full Multi-Stage EL Hierarchy (Substitute -> Unit Head -> Establishment -> Director) verified.")

    print("Step 4: Testing CW-EL-02: Pre-Start Cancellation with Balance Refund...")
    # Request cancellation
    canc_req = request_cancellation(user_id=user_id, leave_id=el_req.id)
    assert canc_req.status == "cancellation_pending_unit_head"

    # Unit head recommends cancellation -> routes to establishment
    uh_canc = review_cancellation(actor_user_id=unit_head_id, leave_id=el_req.id, approve=True)
    assert uh_canc.status == "cancellation_pending_establishment"

    # Establishment routes cancellation -> routes to final sanction
    est_canc = review_cancellation(actor_user_id=establishment_id, leave_id=el_req.id, approve=True)
    assert est_canc.status == "cancellation_pending_final"

    # Final authority approves cancellation -> balance restored
    canc_final = review_cancellation(actor_user_id=director_id, leave_id=el_req.id, approve=True)
    assert canc_final.status == "cancelled"

    bal_el.refresh_from_db()
    assert bal_el.availed_balance == Decimal("0.00")
    assert bal_el.available_balance == Decimal("35.00")
    print("PASS: Pre-start cancellation properly restored leave balance.")

    print("Step 5: Testing CW-EL-04: Resumption of Duty & Early Return Adjustment...")
    # Create another approved leave
    el_req2 = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 10),  # 10 days
        reason="Conference",
        unit_head_user_id=unit_head_id,
    )
    review_unit_head(unit_head_id, el_req2.id, decision="recommend")
    route_establishment(establishment_id, el_req2.id)
    make_sanction_decision(director_id, el_req2.id, approve=True)

    bal_el.refresh_from_db()
    assert bal_el.availed_balance == Decimal("10.00")

    # Resumes early on 2026-12-07 (3 days earlier than 12-10)
    res_req = submit_resumption(user_id=user_id, leave_id=el_req2.id, actual_date=date(2026, 12, 7), remarks="Returned early")
    assert res_req.status == "resumption_pending"

    review_res = review_resumption(director_id, el_req2.id)
    assert review_res.status == "resumed"

    bal_el.refresh_from_db()
    assert bal_el.availed_balance == Decimal("7.00")  # 10 - 3 = 7
    print("PASS: Resumption with early return accurately refunded excess 3 days.")

    print("Step 6: Testing CW-EL-03: Ongoing Leave Extension... ")
    extension_user_id = 2001
    today = date.today()
    ongoing_start = today - timedelta(days=1)
    ongoing_end = today + timedelta(days=1)
    extension_end = ongoing_end + timedelta(days=2)
    LeaveBalance.objects.create(
        user_id=extension_user_id,
        year=ongoing_start.year,
        category="EL",
        credited_balance=Decimal("10.00"),
        availed_balance=Decimal("3.00"),
    )
    ongoing_leave = LeaveRequest.objects.create(
        user_id=extension_user_id,
        category="EL",
        start_date=ongoing_start,
        end_date=ongoing_end,
        days_calculated=Decimal("3.00"),
        reason="Ongoing conference travel",
        status="approved",
        unit_head_user_id=unit_head_id,
    )
    extension = request_leave_extension(
        user_id=extension_user_id,
        leave_id=ongoing_leave.id,
        end_date=extension_end,
        reason="Conference extended by the host",
    )
    assert extension.status == "extension_pending_unit_head"
    review_unit_head(unit_head_id, extension.id, decision="recommend")
    route_establishment(establishment_id, extension.id)
    extension_result = make_sanction_decision(director_id, extension.id, approve=True)
    assert extension_result.status == "extended"
    ongoing_leave.refresh_from_db()
    assert ongoing_leave.end_date == extension_end
    assert ongoing_leave.days_calculated == Decimal("5.00")
    print("PASS: Approved extension updated the original leave and posted only added days.")

    print("Step 7: Testing Year-End Boundary Processing (EVT-01, BR-EL-007)...")
    stats = execute_year_end_processing(2026)
    print("Year-end stats:", stats)

    # Check that CL lapsed
    # Check that 30 unused VL converted to 15 EL in 2027
    el_2027 = LeaveBalance.objects.get(user_id=user_id, year=2027, category="EL")
    assert el_2027.carried_forward == Decimal("43.00")  # 28 remaining EL + 15 converted VL = 43.00
    print("PASS: Year-end Faculty VL to EL conversion (2:1) & carry-forward verified!")

    print("\n==========================================")
    print("ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("==========================================")


if __name__ == "__main__":
    run_integration_suite()
