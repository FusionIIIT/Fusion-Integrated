import pytest
from datetime import date
from decimal import Decimal
from core.api.exceptions import BadRequestError
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, LtcRequest
from modules.hreis.services.claims import (
    decide_ltc_request,
    settle_ltc_claim,
    submit_ltc_request,
    verify_ltc_request,
)

pytestmark = pytest.mark.django_db


def test_wf_017_ltc_advance_approved_and_processed():
    """TEST-WF-017 [BW-HR-06 Advance Approval & Settlement Path]: Verify full workflow path for LTC Advance from submission through verification, approval, and settlement."""
    EmployeeServiceRecord.objects.create(
        user_id=530,
        employee_id="EMP0530",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=530,
        username="u530",
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("15000.00"),
    )
    assert ltc.status == "submitted"
    verified = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="Verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.status == "pending_approval"
    approved = decide_ltc_request(
        ltc_id=ltc.id,
        outcome="approved",
        remarks="Approved by HOD",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert approved.status == "approved"
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("15000.00"),
        reference_id="LTC-ADV-SETTLE-530",
        remarks="Settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"


def test_wf_018_ltc_verification_guard():
    """TEST-WF-018 [BW-HR-06 Verification Guard]: Verify unverified LTC Advance cannot enter approval routing."""
    ltc = LtcRequest.objects.create(
        user_id=531,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("15000.00"),
        status="submitted",
    )
    with pytest.raises(BadRequestError):
        decide_ltc_request(
            ltc_id=ltc.id,
            outcome="approved",
            remarks="Premature approval attempt",
            actor_id=301,
            actor_username="hod",
            actor_role="hod",
        )


def test_wf_019_ltc_reimbursement_approved_and_processed():
    """TEST-WF-019 [BW-HR-07 Reimbursement Approval & Settlement Path]: Verify full workflow path for LTC Reimbursement with bills."""
    EmployeeServiceRecord.objects.create(
        user_id=532,
        employee_id="EMP0532",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=532,
        username="u532",
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Goa",
        travel_start_date=date(2026, 11, 1),
        travel_end_date=date(2026, 11, 5),
        estimated_amount=Decimal("20000.00"),
        claimed_amount=Decimal("19500.00"),
        supporting_documents=["ticket.pdf"],
    )
    verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="Tickets verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    decide_ltc_request(
        ltc_id=ltc.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("19500.00"),
        reference_id="LTC-REIM-SETTLE-532",
        remarks="Reimbursement settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"


def test_wf_020_ltc_settlement_role_guard():
    """TEST-WF-020 [BW-HR-07 Settlement Role Guard]: Verify non-accountant cannot record settlement."""
    ltc = LtcRequest.objects.create(
        user_id=533,
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Goa",
        travel_start_date=date(2026, 11, 1),
        travel_end_date=date(2026, 11, 5),
        estimated_amount=Decimal("10000.00"),
        claimed_amount=Decimal("9500.00"),
        status="approved",
        verification_status="verified",
    )
    with pytest.raises(BadRequestError):
        settle_ltc_claim(
            ltc_id=ltc.id,
            passed_amount=Decimal("9500.00"),
            reference_id="REF-533",
            remarks="Unauthorized settlement",
            actor_id=999,
            actor_username="staff_user",
            actor_role="staff",
        )


def test_wf_021_ltc_verification_rejection():
    """TEST-WF-021 [BW-HR-08 Verification Rejection Path]: Verify LTC request rejected during HR verification terminates."""
    ltc = LtcRequest.objects.create(
        user_id=534,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("12000.00"),
        status="submitted",
    )
    verified = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="rejected",
        remarks="Invalid documents",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.status == "rejected"


def test_wf_022_ltc_authority_rejection():
    """TEST-WF-022 [BW-HR-08 Authority Rejection Path]: Verify verified LTC request rejected by Approving Authority terminates workflow."""
    ltc = LtcRequest.objects.create(
        user_id=535,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("12000.00"),
        status="pending_approval",
        verification_status="verified",
    )
    decided = decide_ltc_request(
        ltc_id=ltc.id,
        outcome="rejected",
        remarks="Budget constraint",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "rejected"


def test_wf_023_ltc_forward_one_traversal():
    """TEST-WF-023 [BW-HR-09 Forwarding Traversal Path]: Verify verified LTC request forwarded through one authority traversal to final approval."""
    ltc = LtcRequest.objects.create(
        user_id=536,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Chennai",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("30000.00"),
        status="pending_approval",
        verification_status="verified",
    )
    fwd = decide_ltc_request(
        ltc_id=ltc.id,
        outcome="forwarded",
        remarks="Forward to Director",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert fwd.status == "forwarded"
    approved = decide_ltc_request(
        ltc_id=ltc.id,
        outcome="approved",
        remarks="Approved by Director",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert approved.status == "approved"


def test_wf_024_ltc_forwarding_state_integrity():
    """TEST-WF-024 [BW-HR-09 Forwarding State Integrity]: Verify forwarded LTC request cannot be settled before reaching approved status."""
    ltc = LtcRequest.objects.create(
        user_id=537,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("15000.00"),
        status="forwarded",
        verification_status="verified",
    )
    with pytest.raises(BadRequestError):
        settle_ltc_claim(
            ltc_id=ltc.id,
            passed_amount=Decimal("15000.00"),
            reference_id="REF-537",
            remarks="Premature settlement",
            actor_id=501,
            actor_username="accountant",
            actor_role="accountant",
        )


def test_wf_025_cw_ltc_advance_lifecycle():
    """TEST-WF-025 [CW-HR-03 Advance Lifecycle]: Verify complete composite lifecycle for LTC Advance with audit logging."""
    EmployeeServiceRecord.objects.create(
        user_id=538,
        employee_id="EMP0538",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=538,
        username="u538",
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Mumbai",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("16000.00"),
    )
    verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="Verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    decide_ltc_request(
        ltc_id=ltc.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("16000.00"),
        reference_id="CW-LTC-SETTLE-538",
        remarks="Settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    assert HrAuditLog.objects.filter(entity_type="ltc_request", entity_id=str(ltc.id)).count() >= 3


def test_wf_026_cw_ltc_reimbursement_lifecycle():
    """TEST-WF-026 [CW-HR-03 Reimbursement Lifecycle]: Verify complete composite lifecycle for LTC Reimbursement with bills and settlement."""
    EmployeeServiceRecord.objects.create(
        user_id=539,
        employee_id="EMP0539",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=539,
        username="u539",
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 11, 10),
        travel_end_date=date(2026, 11, 15),
        estimated_amount=Decimal("14000.00"),
        claimed_amount=Decimal("13800.00"),
        supporting_documents=["ticket.pdf"],
    )
    verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="Bills verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    decide_ltc_request(
        ltc_id=ltc.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("13800.00"),
        reference_id="CW-REIM-SETTLE-539",
        remarks="Settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"


def test_wf_027_cw_ltc_rejection_audit_trail():
    """TEST-WF-027 [CW-HR-03 Rejection Audit Trail Lifecycle]: Verify rejected LTC request preserves complete audit trail."""
    ltc = LtcRequest.objects.create(
        user_id=540,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("12000.00"),
        status="pending_approval",
        verification_status="verified",
    )
    decide_ltc_request(
        ltc_id=ltc.id,
        outcome="rejected",
        remarks="Budget cut",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert HrAuditLog.objects.filter(entity_type="ltc_request", entity_id=str(ltc.id), action="decide_ltc_request").exists()
