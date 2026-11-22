"""End-to-end full life-cycle journey tests for HR-EIS core subsystems."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from modules.hreis.domain.appraisal import AppraisalStatus
from modules.hreis.domain.claims import ClaimStatus, PaymentStatus, VerificationStatus
from modules.hreis.domain.leave import LeaveStatus
from modules.hreis.models import (
    EmployeeServiceRecord,
    HrAuditLog,
    HrNotification,
)
from modules.hreis.services.appraisals import (
    assign_appraisal_reviewers,
    finalize_appraisal,
    submit_appraisal,
    submit_appraisal_review,
)
from modules.hreis.services.claims import (
    decide_cpda_request,
    decide_ltc_request,
    settle_cpda_claim,
    settle_ltc_claim,
    submit_cpda_request,
    submit_ltc_request,
    verify_cpda_request,
    verify_ltc_request,
)
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_leave_full_journey():
    """Journey: Submit leave -> Forward by HOD -> Approve by Director -> Verify balance."""
    EmployeeServiceRecord.objects.create(
        user_id=1101,
        employee_id="EMP1101",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 120, "casual": 10},
    )

    leave = submit_leave_request(
        user_id=1101,
        username="prof_jones",
        leave_type="sabbatical",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 30),
        duration_days=30,
        justification="Research sabbatical in robotics",
    )
    assert leave.status == LeaveStatus.PENDING.value
    assert leave.current_authority_role == "hod"

    # Step 1: HOD forwards to Director
    fwd = decide_leave_request(
        leave_id=leave.id,
        outcome="forwarded",
        remarks="Recommended for institute research growth",
        actor_id=301,
        actor_username="hod_cse",
        actor_role="hod",
    )
    assert fwd.status == LeaveStatus.FORWARDED.value
    assert fwd.current_authority_role == "director"

    # Step 2: Director approves
    appr = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved by Director",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert appr.status == LeaveStatus.APPROVED.value

    # Balance check
    rec = EmployeeServiceRecord.objects.get(user_id=1101)
    assert rec.leave_balances["sabbatical"] == 90

    # Notification & audit checks
    assert HrAuditLog.objects.filter(entity_type="leave_request", entity_id=str(leave.id)).count() >= 2
    assert HrNotification.objects.filter(user_id=1101, category="approved").exists()


def test_ltc_full_journey():
    """Journey: Submit LTC -> Verify HR -> Approve HOD -> Settle Accountant."""
    EmployeeServiceRecord.objects.create(
        user_id=1102,
        employee_id="EMP1102",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        ltc_eligible_block="2022-2025",
    )

    ltc = submit_ltc_request(
        user_id=1102,
        username="prof_alice",
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Kochi",
        travel_start_date=date(2026, 8, 1),
        travel_end_date=date(2026, 8, 7),
        estimated_amount=Decimal("25000.00"),
        claimed_amount=Decimal("24500.00"),
        supporting_documents=["ticket.pdf", "boarding_pass.pdf"],
    )
    assert ltc.status == ClaimStatus.SUBMITTED.value
    assert ltc.verification_status == VerificationStatus.PENDING.value

    # HR Verification
    verified = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="All original tickets verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == VerificationStatus.VERIFIED.value
    assert verified.status == "pending_approval"

    # Authority Approval
    approved = decide_ltc_request(
        ltc_id=ltc.id,
        outcome="approved",
        remarks="Approved as per entitlement",
        actor_id=301,
        actor_username="hod_ece",
        actor_role="hod",
    )
    assert approved.status == ClaimStatus.APPROVED.value

    # Financial Settlement
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("24500.00"),
        reference_id="NEFT-LTC-2026-999",
        remarks="Processed via bank voucher",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == ClaimStatus.SETTLED.value
    assert settled.payment_status == PaymentStatus.PAID.value
    assert settled.passed_amount == Decimal("24500.00")
    assert HrAuditLog.objects.filter(entity_type="ltc_request", entity_id=str(ltc.id)).exists()


def test_cpda_full_journey():
    """Journey: Submit CPDA -> Verify HR -> Approve HOD -> Settle Accountant & deduct balance."""
    EmployeeServiceRecord.objects.create(
        user_id=1103,
        employee_id="EMP1103",
        department="ME",
        designation="Associate Professor",
        category="faculty",
        cpda_balance=Decimal("150000.00"),
    )

    cpda = submit_cpda_request(
        user_id=1103,
        username="prof_bob",
        request_type="reimbursement",
        purpose="IEEE Conference Registration Fee",
        amount=Decimal("35000.00"),
        supporting_documents=["receipt.pdf", "conf_certificate.pdf"],
    )
    assert cpda.status == ClaimStatus.SUBMITTED.value

    # Verify
    verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Conference is peer-reviewed and eligible",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )

    # Approve
    decide_cpda_request(
        cpda_id=cpda.id,
        outcome="approved",
        remarks="Approved under CPDA head",
        actor_id=301,
        actor_username="hod_me",
        actor_role="hod",
    )

    # Settle
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("35000.00"),
        voucher_no="VOUCH-CPDA-2026-042",
        remarks="Payment credited to faculty account",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == ClaimStatus.SETTLED.value
    assert settled.disbursement_status == PaymentStatus.PAID.value

    rec = EmployeeServiceRecord.objects.get(user_id=1103)
    assert rec.cpda_balance == Decimal("115000.00")


def test_appraisal_full_journey():
    """Journey: Open Window -> Submit -> Assign Reviewers -> Multi-review -> Finalize."""
    update_workflow_config(
        "appraisal_window",
        {
            "active": True,
            "academic_year": "2025-2026",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )

    EmployeeServiceRecord.objects.create(
        user_id=1104,
        employee_id="EMP1104",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )

    appraisal = submit_appraisal(
        user_id=1104,
        username="prof_charlie",
        academic_year="2025-2026",
        content={"teaching_load": 12, "journal_papers": 3, "sponsored_grants": 1},
    )
    assert appraisal.status == AppraisalStatus.SUBMITTED.value

    # Assign reviewers
    assign_appraisal_reviewers(
        appraisal_id=appraisal.id,
        reviewer_ids=[401, 402],
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )

    # Reviewer 1
    submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=8.5,
        comments="Solid teaching and research performance",
        actor_id=401,
        actor_username="reviewer_hod",
        actor_role="hod",
    )

    # Reviewer 2
    submit_appraisal_review(
        appraisal_id=appraisal.id,
        score=9.0,
        comments="Excellent grant acquisition",
        actor_id=402,
        actor_username="reviewer_dean",
        actor_role="dean",
    )

    # Finalize
    finalized = finalize_appraisal(
        appraisal_id=appraisal.id,
        final_score=8.75,
        final_remarks="Promoted to next grade review list",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert finalized.status == AppraisalStatus.FINALIZED.value
    assert finalized.is_immutable is True
    assert finalized.final_score == Decimal("8.75")

    # Verify service history entry in service record
    rec = EmployeeServiceRecord.objects.get(user_id=1104)
    assert any(h.get("event") == "Annual Appraisal Finalized" for h in rec.service_history)
