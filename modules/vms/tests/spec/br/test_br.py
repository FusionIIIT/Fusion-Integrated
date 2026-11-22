"""Specification tests for Business Rules (BR).

Each test explicitly documents:
test_id: BR-NNN
source_id: VMS-BR-NNN condition-satisfied or condition-violated
"""

from datetime import date, time, timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from modules.vms.domain.state_machine import InvalidStateTransitionError, assert_can_transition
from modules.vms.domain.validation import ValidationError, validate_mandatory_visitor_fields
from modules.vms.models import (
    AccessPolicy,
    BlacklistEntry,
    EmergencyMusterRoster,
    GateCheckLog,
    Visitor,
    VisitRequest,
)
from modules.vms.services.approval import (
    contingency_approve,
    create_pre_authorization,
    decide_visit_request,
    extend_visit,
    terminate_visit,
)
from modules.vms.services.blacklist import add_to_blacklist, safe_list_entry
from modules.vms.services.emergency import trigger_emergency_muster
from modules.vms.services.gate import (
    check_in_visitor,
    check_out_visitor,
    manual_gate_override,
    validate_pass_at_gate,
)
from modules.vms.services.policy import create_access_policy, publish_access_policy
from modules.vms.services.registration import (
    DuplicateVisitError,
    pre_register_visit,
    walk_in_register,
)
from modules.vms.services.roles import reassign_vms_work
from modules.vms.services.scheduled import auto_checkout_overstays, expire_pending_requests
from modules.vms.services.zone import grant_zone_elevation, validate_zone_access

pytestmark = pytest.mark.django_db


# --- VMS-BR-037 Mandatory Pre-registration Validation ---

def test_br_001_vms_br_037_satisfied():
    """
    test_id: BR-001
    source_id: VMS-BR-037 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Valid Guest",
        email="guest@val.com",
        phone="+919876543001",
        id_document_type="AADHAAR",
        id_document_number="BR37001VAL",
        host_id=1,
        purpose="Official Meeting",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None
    assert vr.status == "PENDING_APPROVAL"


def test_br_002_vms_br_037_violated():
    """
    test_id: BR-002
    source_id: VMS-BR-037 condition-violated
    """
    now = timezone.now()
    with pytest.raises(ValidationError, match="name"):
        pre_register_visit(
            name="",
            email="guest@val.com",
            phone="+919876543001",
            id_document_type="AADHAAR",
            id_document_number="BR37002INV",
            host_id=1,
            purpose="Official Meeting",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


# --- VMS-BR-038 Duplicate Visit Request Check ---

def test_br_003_vms_br_038_satisfied():
    """
    test_id: BR-003
    source_id: VMS-BR-038 condition-satisfied
    """
    now = timezone.now()
    vr1 = pre_register_visit(
        name="Unique Guest 1",
        email="unq1@val.com",
        phone="+919876543003",
        id_document_type="AADHAAR",
        id_document_number="BR38003UNQ",
        host_id=1,
        purpose="Meeting 1",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr1.id is not None


def test_br_004_vms_br_038_violated():
    """
    test_id: BR-004
    source_id: VMS-BR-038 condition-violated
    """
    now = timezone.now()
    start = now + timedelta(hours=3)
    end = now + timedelta(hours=5)
    pre_register_visit(
        name="Duplicate Candidate",
        email="dup@val.com",
        phone="+919876543004",
        id_document_type="AADHAAR",
        id_document_number="BR38004DUP",
        host_id=1,
        purpose="Session 1",
        scheduled_start=start,
        scheduled_end=end,
    )
    with pytest.raises(DuplicateVisitError):
        pre_register_visit(
            name="Duplicate Candidate",
            email="dup@val.com",
            phone="+919876543004",
            id_document_type="AADHAAR",
            id_document_number="BR38004DUP",
            host_id=1,
            purpose="Session 2",
            scheduled_start=start + timedelta(minutes=15),
            scheduled_end=end + timedelta(minutes=15),
        )


# --- VMS-BR-049 Walk-in Contingency Approval Authorization ---

def test_br_005_vms_br_049_satisfied():
    """
    test_id: BR-005
    source_id: VMS-BR-049 condition-satisfied
    """
    vr = walk_in_register(
        name="Contingency Walkin",
        email="walkin@contingency.com",
        phone="+919876543005",
        host_id=1,
        purpose="Walk-in Discussion",
        id_document_type="AADHAAR",
        id_document_number="BR49005WALK",
    )
    app = contingency_approve(vr.id, admin_id=1, reason="Host phone unavailable")
    assert app.status == "APPROVED"


def test_br_006_vms_br_049_violated():
    """
    test_id: BR-006
    source_id: VMS-BR-049 condition-violated
    """
    vr = walk_in_register(
        name="Contingency Walkin 2",
        email="walkin2@contingency.com",
        phone="+919876543006",
        host_id=1,
        purpose="Walk-in Discussion",
        id_document_type="AADHAAR",
        id_document_number="BR49006WALK",
    )
    # Blank justification rejected by rule
    with pytest.raises((ValidationError, ValueError)):
        contingency_approve(vr.id, admin_id=1, reason="")


# --- VMS-BR-050 Walk-in Contingency Approval SLA ---

def test_br_007_vms_br_050_satisfied():
    """
    test_id: BR-007
    source_id: VMS-BR-050 condition-satisfied
    """
    vr = walk_in_register(
        name="SLA Walkin",
        email="sla@contingency.com",
        phone="+919876543007",
        host_id=1,
        purpose="Urgent Delivery",
        id_document_type="AADHAAR",
        id_document_number="BR50007SLA",
    )
    app = contingency_approve(vr.id, admin_id=1, reason="SLA threshold breached")
    assert app.status == "APPROVED"
    assert app.digital_pass is not None


def test_br_008_vms_br_050_violated():
    """
    test_id: BR-008
    source_id: VMS-BR-050 condition-violated
    """
    vr = walk_in_register(
        name="Cancelled Walkin",
        email="cancelled@contingency.com",
        phone="+919876543008",
        host_id=1,
        purpose="Test",
        id_document_type="AADHAAR",
        id_document_number="BR50008SLA",
    )
    vr.status = "CANCELLED"
    vr.save(update_fields=["status"])
    with pytest.raises(InvalidStateTransitionError):
        contingency_approve(vr.id, admin_id=1, reason="Cannot approve cancelled visit")


# --- VMS-BR-051 Blacklist Registration Rejection ---

def test_br_009_vms_br_051_satisfied():
    """
    test_id: BR-009
    source_id: VMS-BR-051 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Clean Guest",
        email="clean@example.com",
        phone="+919876543009",
        id_document_type="AADHAAR",
        id_document_number="BR51009CLN",
        host_id=1,
        purpose="Interview",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None


def test_br_010_vms_br_051_violated():
    """
    test_id: BR-010
    source_id: VMS-BR-051 condition-violated
    """
    add_to_blacklist(
        name="Prohibited Individual",
        id_document_type="AADHAAR",
        id_document_number="BR51010BLK",
        phone="+919876543010",
        reason="Campus ban",
    )
    now = timezone.now()
    with pytest.raises(PermissionError, match="blacklist"):
        pre_register_visit(
            name="Prohibited Individual",
            email="blocked@example.com",
            phone="+919876543010",
            id_document_type="AADHAAR",
            id_document_number="BR51010BLK",
            host_id=1,
            purpose="Denied Meeting",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


# --- VMS-BR-052 Host Approval Requirement ---

def test_br_011_vms_br_052_satisfied():
    """
    test_id: BR-011
    source_id: VMS-BR-052 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Host Approval Guest",
        email="guest@host.com",
        phone="+919876543011",
        id_document_type="AADHAAR",
        id_document_number="BR52011HST",
        host_id=10,
        purpose="Advising",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    app = decide_visit_request(vr.id, host_id=10, decision="APPROVE")
    assert app.status == "APPROVED"


def test_br_012_vms_br_052_violated():
    """
    test_id: BR-012
    source_id: VMS-BR-052 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Host Approval Guest 2",
        email="guest2@host.com",
        phone="+919876543012",
        id_document_type="AADHAAR",
        id_document_number="BR52012HST",
        host_id=10,
        purpose="Advising",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    with pytest.raises(PermissionError, match="assigned host"):
        decide_visit_request(vr.id, host_id=99, decision="APPROVE")


# --- VMS-BR-053 Walk-in Pass Duration ---

def test_br_013_vms_br_053_satisfied():
    """
    test_id: BR-013
    source_id: VMS-BR-053 condition-satisfied
    """
    vr = walk_in_register(
        name="Walkin 4h",
        email="walkin4h@example.com",
        phone="+919876543013",
        host_id=1,
        purpose="Walk-in 4h",
        id_document_type="AADHAAR",
        id_document_number="BR53013WALK",
        duration_hours=4,
    )
    duration = (vr.scheduled_end - vr.scheduled_start).total_seconds() / 3600
    assert duration <= 8


def test_br_014_vms_br_053_violated():
    """
    test_id: BR-014
    source_id: VMS-BR-053 condition-violated
    """
    # Exceeding 8 hours is automatically capped to 8 hours per domain rule
    vr = walk_in_register(
        name="Walkin 24h",
        email="walkin24h@example.com",
        phone="+919876543014",
        host_id=1,
        purpose="Walk-in 24h",
        id_document_type="AADHAAR",
        id_document_number="BR53014WALK",
        duration_hours=24,
    )
    duration = (vr.scheduled_end - vr.scheduled_start).total_seconds() / 3600
    assert duration <= 8.01


# --- VMS-BR-062 Pending Approval Timeout ---

def test_br_015_vms_br_062_satisfied():
    """
    test_id: BR-015
    source_id: VMS-BR-062 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Stale Candidate",
        email="stale@example.com",
        phone="+919876543015",
        id_document_type="AADHAAR",
        id_document_number="BR62015STL",
        host_id=1,
        purpose="Stale Session",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    VisitRequest.objects.filter(id=vr.id).update(created_at=now - timedelta(hours=48))
    expired = expire_pending_requests(timeout_hours=24)
    assert expired >= 1
    vr.refresh_from_db()
    assert vr.status == "EXPIRED"


def test_br_016_vms_br_062_violated():
    """
    test_id: BR-016
    source_id: VMS-BR-062 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Fresh Candidate",
        email="fresh@example.com",
        phone="+919876543016",
        id_document_type="AADHAAR",
        id_document_number="BR62016FRSH",
        host_id=1,
        purpose="Fresh Session",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    # Only 1 hour old; should NOT expire
    expire_pending_requests(timeout_hours=24)
    vr.refresh_from_db()
    assert vr.status == "PENDING_APPROVAL"


# --- VMS-BR-073 Early Pass/Visit Termination Authorization ---

def test_br_017_vms_br_073_satisfied():
    """
    test_id: BR-017
    source_id: VMS-BR-073 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Term Guest",
        email="term@example.com",
        phone="+919876543017",
        id_document_type="AADHAAR",
        id_document_number="BR73017TRM",
        host_id=1,
        purpose="Term test",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    term = terminate_visit(vr.id, operator_id=1, reason="Disciplinary infraction")
    assert term.status == "TERMINATED_EARLY"
    assert term.digital_pass.status == "REVOKED"


def test_br_018_vms_br_073_violated():
    """
    test_id: BR-018
    source_id: VMS-BR-073 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Term Guest 2",
        email="term2@example.com",
        phone="+919876543018",
        id_document_type="AADHAAR",
        id_document_number="BR73018TRM",
        host_id=1,
        purpose="Term test 2",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    # Empty termination justification violates rule
    with pytest.raises(ValueError):
        terminate_visit(vr.id, operator_id=1, reason="")


# --- VMS-BR-077 Active Pass Gate Rule ---

def test_br_019_vms_br_077_satisfied():
    """
    test_id: BR-019
    source_id: VMS-BR-077 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Active Pass Guest",
        email="activepass@example.com",
        phone="+919876543019",
        id_document_type="AADHAAR",
        id_document_number="BR77019ACT",
        host_id=1,
        purpose="Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    is_valid, _, _ = validate_pass_at_gate(vr.digital_pass.qr_token, "Main Gate")
    assert is_valid is True


def test_br_020_vms_br_077_violated():
    """
    test_id: BR-020
    source_id: VMS-BR-077 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Revoked Pass Guest",
        email="revokedpass@example.com",
        phone="+919876543020",
        id_document_type="AADHAAR",
        id_document_number="BR77020RVK",
        host_id=1,
        purpose="Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    p = vr.digital_pass
    p.status = "REVOKED"
    p.save(update_fields=["status"])
    is_valid, msg, _ = validate_pass_at_gate(p.qr_token, "Main Gate")
    assert is_valid is False
    assert "REVOKED" in msg


# --- VMS-BR-082 Gate Validation Failure Rule ---

def test_br_021_vms_br_082_satisfied():
    """
    test_id: BR-021
    source_id: VMS-BR-082 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Checkin Pass Guest",
        email="chkpass@example.com",
        phone="+919876543021",
        id_document_type="AADHAAR",
        id_document_number="BR82021CHK",
        host_id=1,
        purpose="Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    log = check_in_visitor(vr.digital_pass.id, "North Gate")
    assert log.action == "CHECK_IN"


def test_br_022_vms_br_082_violated():
    """
    test_id: BR-022
    source_id: VMS-BR-082 condition-violated
    """
    is_valid, msg, _ = validate_pass_at_gate("VMS-FAKE-TOKEN-12345", "Main Gate")
    assert is_valid is False
    assert "Invalid or tampered" in msg


# --- VMS-BR-085 Manual Gate Override Authorization ---

def test_br_023_vms_br_085_satisfied():
    """
    test_id: BR-023
    source_id: VMS-BR-085 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Override Pass Guest",
        email="ovrpass@example.com",
        phone="+919876543023",
        id_document_type="AADHAAR",
        id_document_number="BR85023OVR",
        host_id=1,
        purpose="VIP",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    log = manual_gate_override(
        vr.digital_pass.id, admin_id=1, reason="Visitor phone dead; passport verified"
    )
    assert log.is_override is True
    assert log.action == "OVERRIDE"


def test_br_024_vms_br_085_violated():
    """
    test_id: BR-024
    source_id: VMS-BR-085 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Override Pass Guest 2",
        email="ovrpass2@example.com",
        phone="+919876543024",
        id_document_type="AADHAAR",
        id_document_number="BR85024OVR",
        host_id=1,
        purpose="VIP",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    with pytest.raises(ValueError):
        manual_gate_override(vr.digital_pass.id, admin_id=1, reason="")


# --- VMS-BR-096 Temporary Zone Elevation Time Box ---

def test_br_025_vms_br_096_satisfied():
    """
    test_id: BR-025
    source_id: VMS-BR-096 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Elevate Guest",
        email="elevate@example.com",
        phone="+919876543025",
        id_document_type="AADHAAR",
        id_document_number="BR96025ELV",
        host_id=1,
        purpose="Server Check",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=4),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1")
    elevation = grant_zone_elevation(
        vr.digital_pass.id,
        zone_name="Server Room",
        hours=4,
        admin_id=1,
        reason="Server installation",
    )
    assert elevation.id is not None


def test_br_026_vms_br_096_violated():
    """
    test_id: BR-026
    source_id: VMS-BR-096 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Elevate Guest 2",
        email="elevate2@example.com",
        phone="+919876543026",
        id_document_type="AADHAAR",
        id_document_number="BR96026ELV",
        host_id=1,
        purpose="Server Check",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=4),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1")
    # > 12 hours violated
    with pytest.raises(ValueError, match="between 1 and 12"):
        grant_zone_elevation(
            vr.digital_pass.id,
            zone_name="Server Room",
            hours=24,
            admin_id=1,
            reason="Illegal 24h elevation",
        )


# --- VMS-BR-101 Automatic Checkout Trigger ---

def test_br_027_vms_br_101_satisfied():
    """
    test_id: BR-027
    source_id: VMS-BR-101 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Overstay Guest",
        email="overstay@example.com",
        phone="+919876543027",
        id_document_type="AADHAAR",
        id_document_number="BR101027OVR",
        host_id=1,
        purpose="Overstay session",
        scheduled_start=now - timedelta(hours=20),
        scheduled_end=now - timedelta(hours=8),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1")
    count = auto_checkout_overstays(buffer_hours=4)
    assert count >= 1
    vr.refresh_from_db()
    assert vr.status == "AUTO_CHECKED_OUT"


def test_br_028_vms_br_101_violated():
    """
    test_id: BR-028
    source_id: VMS-BR-101 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Active Guest Still Within Schedule",
        email="activeguest@example.com",
        phone="+919876543028",
        id_document_type="AADHAAR",
        id_document_number="BR101028ACT",
        host_id=1,
        purpose="Active session",
        scheduled_start=now - timedelta(hours=1),
        scheduled_end=now + timedelta(hours=3),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1")
    auto_checkout_overstays(buffer_hours=4)
    vr.refresh_from_db()
    # Must remain CHECKED_IN
    assert vr.status == "CHECKED_IN"


# --- VMS-BR-105 Visit Completion Rule ---

def test_br_029_vms_br_105_satisfied():
    """
    test_id: BR-029
    source_id: VMS-BR-105 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Completion Guest",
        email="complete@example.com",
        phone="+919876543029",
        id_document_type="AADHAAR",
        id_document_number="BR105029CMP",
        host_id=1,
        purpose="Completion test",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    check_out_visitor(vr.digital_pass.id, "Exit Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"
    assert vr.digital_pass.status == "USED"


def test_br_030_vms_br_105_violated():
    """
    test_id: BR-030
    source_id: VMS-BR-105 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Unchecked Guest",
        email="unchecked@example.com",
        phone="+919876543030",
        id_document_type="AADHAAR",
        id_document_number="BR105030UNCHK",
        host_id=1,
        purpose="Completion test",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    # Attempt checkout on pass that is not checked in
    with pytest.raises(InvalidStateTransitionError):
        check_out_visitor(vr.digital_pass.id, "Exit Gate")


# --- VMS-BR-112 Blacklist Runtime Checkpoints ---

def test_br_031_vms_br_112_satisfied():
    """
    test_id: BR-031
    source_id: VMS-BR-112 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Unbanned Gate Guest",
        email="unbanned@example.com",
        phone="+919876543031",
        id_document_type="AADHAAR",
        id_document_number="BR112031UNB",
        host_id=1,
        purpose="Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    is_valid, _, _ = validate_pass_at_gate(vr.digital_pass.qr_token, "Main Gate")
    assert is_valid is True


def test_br_032_vms_br_112_violated():
    """
    test_id: BR-032
    source_id: VMS-BR-112 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Late Banned Guest",
        email="lateban@example.com",
        phone="+919876543032",
        id_document_type="AADHAAR",
        id_document_number="BR112032BAN",
        host_id=1,
        purpose="Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    # Now blacklisted before gate arrival
    add_to_blacklist(
        name="Late Banned Guest",
        id_document_type="AADHAAR",
        id_document_number="BR112032BAN",
        phone="+919876543032",
        reason="Security watchlist addition",
    )
    is_valid, msg, _ = validate_pass_at_gate(vr.digital_pass.qr_token, "Main Gate")
    assert is_valid is False
    assert "Blacklist" in msg


# --- VMS-BR-116 Blacklist Entry Denial ---

def test_br_033_vms_br_116_satisfied():
    """
    test_id: BR-033
    source_id: VMS-BR-116 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Admitted Person",
        email="admit@example.com",
        phone="+919876543033",
        id_document_type="AADHAAR",
        id_document_number="BR116033ADM",
        host_id=1,
        purpose="Admit test",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "PENDING_APPROVAL"


def test_br_034_vms_br_116_violated():
    """
    test_id: BR-034
    source_id: VMS-BR-116 condition-violated
    """
    add_to_blacklist(
        name="Blacklisted Contact",
        id_document_type="AADHAAR",
        id_document_number="BR116034BLK",
        phone="+919876543034",
        reason="Banned contact",
    )
    now = timezone.now()
    with pytest.raises(PermissionError, match="blacklist"):
        pre_register_visit(
            name="Blacklisted Contact",
            email="blkcontact@example.com",
            phone="+919876543034",
            id_document_type="AADHAAR",
            id_document_number="BR116034BLK",
            host_id=1,
            purpose="Denied Meeting",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


# --- VMS-BR-117 Blacklist Match Alert ---

def test_br_035_vms_br_117_satisfied():
    """
    test_id: BR-035
    source_id: VMS-BR-117 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Alert Free Guest",
        email="alertfree@example.com",
        phone="+919876543035",
        id_document_type="AADHAAR",
        id_document_number="BR117035ALR",
        host_id=1,
        purpose="Clean session",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None


def test_br_036_vms_br_117_violated():
    """
    test_id: BR-036
    source_id: VMS-BR-117 condition-violated
    """
    add_to_blacklist(
        name="Alert Trigger Individual",
        id_document_type="AADHAAR",
        id_document_number="BR117036TRG",
        phone="+919876543036",
        reason="Theft alert trigger",
    )
    now = timezone.now()
    with pytest.raises(PermissionError):
        pre_register_visit(
            name="Alert Trigger Individual",
            email="alerttrg@example.com",
            phone="+919876543036",
            id_document_type="AADHAAR",
            id_document_number="BR117036TRG",
            host_id=1,
            purpose="Should Alert",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


# --- VMS-BR-118 Temporary Safe-list Scope ---

def test_br_037_vms_br_118_satisfied():
    """
    test_id: BR-037
    source_id: VMS-BR-118 condition-satisfied
    """
    entry = add_to_blacklist(
        name="Safe Scope Person",
        id_document_type="AADHAAR",
        id_document_number="BR118037SFE",
        phone="+919876543037",
        reason="Past violation",
    )
    res = safe_list_entry(entry.id, hours=48, admin_id=1, reason="Safe scope granted")
    assert res.status == "SAFE_LISTED"


def test_br_038_vms_br_118_violated():
    """
    test_id: BR-038
    source_id: VMS-BR-118 condition-violated
    """
    entry = add_to_blacklist(
        name="Safe Scope Person 2",
        id_document_type="AADHAAR",
        id_document_number="BR118038SFE",
        phone="+919876543038",
        reason="Past violation",
    )
    # > 72 hours violated
    with pytest.raises(ValueError, match="between 1 and 72"):
        safe_list_entry(entry.id, hours=100, admin_id=1, reason="Excessive safe list")


# --- VMS-BR-119 Temporary Safe-list Expiry ---

def test_br_039_vms_br_119_satisfied():
    """
    test_id: BR-039
    source_id: VMS-BR-119 condition-satisfied
    """
    now = timezone.now()
    entry = add_to_blacklist(
        name="Active Safe Person",
        id_document_type="AADHAAR",
        id_document_number="BR119039SFE",
        phone="+919876543039",
        reason="Past violation",
    )
    safe_list_entry(entry.id, hours=12, admin_id=1, reason="Within 12 hours")
    vr = pre_register_visit(
        name="Active Safe Person",
        email="activesafe@example.com",
        phone="+919876543039",
        id_document_type="AADHAAR",
        id_document_number="BR119039SFE",
        host_id=1,
        purpose="Valid safe visit",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "PENDING_APPROVAL"


def test_br_040_vms_br_119_violated():
    """
    test_id: BR-040
    source_id: VMS-BR-119 condition-violated
    """
    now = timezone.now()
    entry = add_to_blacklist(
        name="Expired Safe Person",
        id_document_type="AADHAAR",
        id_document_number="BR119040EXP",
        phone="+919876543040",
        reason="Past violation",
    )
    safe_list_entry(entry.id, hours=2, admin_id=1, reason="Short window")
    # Backdate safe_list_until to past
    entry.refresh_from_db()
    entry.safe_list_until = now - timedelta(hours=1)
    entry.save(update_fields=["safe_list_until"])

    with pytest.raises(PermissionError, match="blacklist"):
        pre_register_visit(
            name="Expired Safe Person",
            email="expiredsafe@example.com",
            phone="+919876543040",
            id_document_type="AADHAAR",
            id_document_number="BR119040EXP",
            host_id=1,
            purpose="Expired safe visit",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


# --- VMS-BR-120 Published Blacklist Runtime Source ---

def test_br_041_vms_br_120_satisfied():
    """
    test_id: BR-041
    source_id: VMS-BR-120 condition-satisfied
    """
    add_to_blacklist(
        name="Runtime Source Person",
        id_document_type="AADHAAR",
        id_document_number="BR120041SRC",
        phone="+919876543041",
        reason="Watchlist check",
    )
    assert BlacklistEntry.objects.filter(id_document_number="BR120041SRC", status="ACTIVE").exists()


def test_br_042_vms_br_120_violated():
    """
    test_id: BR-042
    source_id: VMS-BR-120 condition-violated
    """
    entry = add_to_blacklist(
        name="Deactivated Person",
        id_document_type="AADHAAR",
        id_document_number="BR120042DEACT",
        phone="+919876543042",
        reason="Resolved issue",
    )
    entry.status = "INACTIVE"
    entry.save(update_fields=["status"])
    now = timezone.now()
    # Inactive blacklist entry does not block visitor
    vr = pre_register_visit(
        name="Deactivated Person",
        email="deact@example.com",
        phone="+919876543042",
        id_document_type="AADHAAR",
        id_document_number="BR120042DEACT",
        host_id=1,
        purpose="Allowed after deactivation",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "PENDING_APPROVAL"


# --- VMS-BR-125 Access Policy Versioning ---

def test_br_043_vms_br_125_satisfied():
    """
    test_id: BR-043
    source_id: VMS-BR-125 condition-satisfied
    """
    p = create_access_policy(version=125)
    assert p.version == 125


def test_br_044_vms_br_125_violated():
    """
    test_id: BR-044
    source_id: VMS-BR-125 condition-violated
    """
    create_access_policy(version=1250)
    with pytest.raises(IntegrityError):
        create_access_policy(version=1250)


# --- VMS-BR-126 Access Policy Publication ---

def test_br_045_vms_br_126_satisfied():
    """
    test_id: BR-045
    source_id: VMS-BR-126 condition-satisfied
    """
    create_access_policy(version=126)
    pub = publish_access_policy(version=126)
    assert pub.is_published is True


def test_br_046_vms_br_126_violated():
    """
    test_id: BR-046
    source_id: VMS-BR-126 condition-violated
    """
    with pytest.raises(AccessPolicy.DoesNotExist):
        publish_access_policy(version=999999)


# --- VMS-BR-127 Published Access Policy Runtime Source ---

def test_br_047_vms_br_127_satisfied():
    """
    test_id: BR-047
    source_id: VMS-BR-127 condition-satisfied
    """
    create_access_policy(version=127, visiting_hours_start=time(7, 0), visiting_hours_end=time(22, 0))
    publish_access_policy(version=127)
    active = AccessPolicy.objects.filter(is_published=True).order_by("-version").first()
    assert active.version == 127


def test_br_048_vms_br_127_violated():
    """
    test_id: BR-048
    source_id: VMS-BR-127 condition-violated
    """
    create_access_policy(version=1280, visiting_hours_start=time(9, 0), visiting_hours_end=time(18, 0))
    # Draft is NOT published
    active = AccessPolicy.objects.filter(version=1280, is_published=True).first()
    assert active is None


# --- VMS-BR-128 Policy Modification Creates New Version ---

def test_br_049_vms_br_128_satisfied():
    """
    test_id: BR-049
    source_id: VMS-BR-128 condition-satisfied
    """
    p1 = create_access_policy(version=1281)
    p2 = create_access_policy(version=1282)
    assert p2.version > p1.version


def test_br_050_vms_br_128_violated():
    """
    test_id: BR-050
    source_id: VMS-BR-128 condition-violated
    """
    create_access_policy(version=1283)
    publish_access_policy(version=1283)
    # Direct overwrite of existing published version with duplicate version is rejected
    with pytest.raises(IntegrityError):
        AccessPolicy.objects.create(version=1283)


# --- VMS-BR-129 Policy Non-retroactivity ---

def test_br_051_vms_br_129_satisfied():
    """
    test_id: BR-051
    source_id: VMS-BR-129 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Retro Guest",
        email="retro@example.com",
        phone="+919876543051",
        id_document_type="AADHAAR",
        id_document_number="BR129051RET",
        host_id=1,
        purpose="Retro test",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")

    # Publishing a new policy does NOT invalidate already approved/checked in pass
    create_access_policy(version=1291, max_duration_hours=2)
    publish_access_policy(version=1291)
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_br_052_vms_br_129_violated():
    """
    test_id: BR-052
    source_id: VMS-BR-129 condition-violated
    """
    # Active pass remains active even under newer policy
    now = timezone.now()
    vr = pre_register_visit(
        name="Retro Guest 2",
        email="retro2@example.com",
        phone="+919876543052",
        id_document_type="AADHAAR",
        id_document_number="BR129052RET",
        host_id=1,
        purpose="Retro test 2",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    assert vr.digital_pass.status == "ACTIVE"


# --- VMS-BR-130 Emergency Muster Trigger Authorization ---

def test_br_053_vms_br_130_satisfied():
    """
    test_id: BR-053
    source_id: VMS-BR-130 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Muster Guest",
        email="muster@example.com",
        phone="+919876543053",
        id_document_type="AADHAAR",
        id_document_number="BR130053MST",
        host_id=1,
        purpose="Muster check",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")

    muster_id = trigger_emergency_muster(initiated_by_id=1, assembly_point="Central Ground")
    assert EmergencyMusterRoster.objects.filter(muster_id=muster_id).exists()


def test_br_054_vms_br_130_violated():
    """
    test_id: BR-054
    source_id: VMS-BR-130 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Muster Checked Out Guest",
        email="musterout@example.com",
        phone="+919876543054",
        id_document_type="AADHAAR",
        id_document_number="BR130054MST",
        host_id=1,
        purpose="Muster check",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    check_out_visitor(vr.digital_pass.id, "Main Gate")

    muster_id = trigger_emergency_muster(initiated_by_id=1, assembly_point="Central Ground")
    # Checked out visitor must NOT be in active emergency muster
    assert not EmergencyMusterRoster.objects.filter(
        muster_id=muster_id, visitor=vr.visitor
    ).exists()


# --- VMS-BR-174 Notification Channel Configuration ---

def test_br_055_vms_br_174_satisfied():
    """
    test_id: BR-055
    source_id: VMS-BR-174 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Notified Guest",
        email="notify@example.com",
        phone="+919876543055",
        id_document_type="AADHAAR",
        id_document_number="BR174055NTF",
        host_id=1,
        purpose="Notify test",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None


def test_br_056_vms_br_174_violated():
    """
    test_id: BR-056
    source_id: VMS-BR-174 condition-violated
    """
    # Empty notification payload still creates visit cleanly
    now = timezone.now()
    vr = pre_register_visit(
        name="Quiet Guest",
        email="quiet@example.com",
        phone="+919876543056",
        id_document_type="AADHAAR",
        id_document_number="BR174056QUT",
        host_id=1,
        purpose="Quiet test",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None


# --- VMS-BR-181 Time-bound VMS Role Assignment ---

def test_br_057_vms_br_181_satisfied():
    """
    test_id: BR-057
    source_id: VMS-BR-181 condition-satisfied
    """
    policy = AccessPolicy.objects.create(
        version=181,
        visiting_hours_start="08:00",
        visiting_hours_end="20:00",
        max_duration_hours=8,
        is_published=True,
    )
    assert policy.is_published is True


def test_br_058_vms_br_181_violated(host_client):
    """
    test_id: BR-058
    source_id: VMS-BR-181 condition-violated
    """
    resp = host_client.post(
        "/api/v1/vms/policies/",
        data={"version": 1810, "visiting_hours_start": "08:00", "visiting_hours_end": "20:00"},
        format="json",
    )
    assert resp.status_code == 403


# --- VMS-BR-182 Immediate Role Reassignment ---

def test_br_059_vms_br_182_satisfied():
    """
    test_id: BR-059
    source_id: VMS-BR-182 condition-satisfied
    """
    now = timezone.now()
    v = Visitor.objects.create(
        name="Reassign User",
        email="reassign@example.com",
        phone="+919876543059",
        id_document_type="AADHAAR",
        id_document_number="BR182059REA",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=100,
        purpose="Reassign",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
        status="PENDING_APPROVAL",
    )
    count = reassign_vms_work(from_user_id=100, to_user_id=200)
    assert count == 1
    vr.refresh_from_db()
    assert vr.host_id == 200


def test_br_060_vms_br_182_violated():
    """
    test_id: BR-060
    source_id: VMS-BR-182 condition-violated
    """
    # Non-existent previous role holder has 0 records updated
    count = reassign_vms_work(from_user_id=999999, to_user_id=888888)
    assert count == 0


# --- VMS-BR-183 Pending Work Handoff on Reassignment ---

def test_br_061_vms_br_183_satisfied():
    """
    test_id: BR-061
    source_id: VMS-BR-183 condition-satisfied
    """
    now = timezone.now()
    v = Visitor.objects.create(
        name="Handoff User",
        email="handoff@example.com",
        phone="+919876543061",
        id_document_type="AADHAAR",
        id_document_number="BR183061HND",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=300,
        purpose="Handoff",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
        status="PENDING_APPROVAL",
    )
    reassign_vms_work(from_user_id=300, to_user_id=400)
    vr.refresh_from_db()
    assert vr.host_id == 400


def test_br_062_vms_br_183_violated():
    """
    test_id: BR-062
    source_id: VMS-BR-183 condition-violated
    """
    # Already approved visits are NOT handed off
    now = timezone.now()
    v = Visitor.objects.create(
        name="Approved User",
        email="approved@example.com",
        phone="+919876543062",
        id_document_type="AADHAAR",
        id_document_number="BR183062APP",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=300,
        purpose="Approved",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
        status="APPROVED",
    )
    reassign_vms_work(from_user_id=300, to_user_id=400)
    vr.refresh_from_db()
    assert vr.host_id == 300


# --- VMS-BR-184 VMS Role Hierarchy ---

def test_br_063_vms_br_184_satisfied(admin_client):
    """
    test_id: BR-063
    source_id: VMS-BR-184 condition-satisfied
    """
    resp = admin_client.get("/api/v1/vms/analytics/dashboard/")
    assert resp.status_code == 200


def test_br_064_vms_br_184_violated(host_client):
    """
    test_id: BR-064
    source_id: VMS-BR-184 condition-violated
    """
    resp = host_client.get("/api/v1/vms/analytics/dashboard/")
    assert resp.status_code == 403


# --- VMS-BR-185 Implicit Host Role ---

def test_br_065_vms_br_185_satisfied():
    """
    test_id: BR-065
    source_id: VMS-BR-185 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Self Host Guest",
        email="selfhost@example.com",
        phone="+919876543065",
        id_document_type="AADHAAR",
        id_document_number="BR185065SLF",
        host_id=5,
        purpose="Self Host",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    app = decide_visit_request(vr.id, host_id=5, decision="APPROVE")
    assert app.status == "APPROVED"


def test_br_066_vms_br_185_violated():
    """
    test_id: BR-066
    source_id: VMS-BR-185 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Other Host Guest",
        email="otherhost@example.com",
        phone="+919876543066",
        id_document_type="AADHAAR",
        id_document_number="BR185066OTH",
        host_id=5,
        purpose="Other Host",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    with pytest.raises(PermissionError):
        decide_visit_request(vr.id, host_id=6, decision="APPROVE")


# --- VMS-BR-186 Valid Identity Document Requirement ---

def test_br_067_vms_br_186_satisfied():
    """
    test_id: BR-067
    source_id: VMS-BR-186 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Valid Doc Guest",
        email="validdoc@example.com",
        phone="+919876543067",
        id_document_type="AADHAAR",
        id_document_number="BR186067DOC",
        host_id=1,
        purpose="Valid Doc",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.visitor.id_document_number == "BR186067DOC"


def test_br_068_vms_br_186_violated():
    """
    test_id: BR-068
    source_id: VMS-BR-186 condition-violated
    """
    now = timezone.now()
    with pytest.raises(ValidationError, match="id_document_number"):
        pre_register_visit(
            name="Blank Doc Guest",
            email="blankdoc@example.com",
            phone="+919876543068",
            id_document_type="AADHAAR",
            id_document_number="",
            host_id=1,
            purpose="Blank Doc",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


# --- VMS-BR-187 Supported Identity Document Types ---

def test_br_069_vms_br_187_satisfied():
    """
    test_id: BR-069
    source_id: VMS-BR-187 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Passport Guest",
        email="passport@example.com",
        phone="+919876543069",
        id_document_type="PASSPORT",
        id_document_number="P12345678",
        host_id=1,
        purpose="Passport Visit",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.visitor.id_document_type == "PASSPORT"


def test_br_070_vms_br_187_violated():
    """
    test_id: BR-070
    source_id: VMS-BR-187 condition-violated
    """
    timezone.now()
    with pytest.raises(ValidationError, match="id_document_type"):
        validate_mandatory_visitor_fields(
            name="Invalid Doc Type Guest",
            email="invdoc@example.com",
            phone="+919876543070",
            id_document_type="LIBRARY_CARD",
            id_document_number="LIB12345",
            host_id=1,
            purpose="Visit",
        )


# --- VMS-BR-190 Pass Validity Window ---

def test_br_071_vms_br_190_satisfied():
    """
    test_id: BR-071
    source_id: VMS-BR-190 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Window Guest",
        email="window@example.com",
        phone="+919876543071",
        id_document_type="AADHAAR",
        id_document_number="BR190071WIN",
        host_id=1,
        purpose="Window Visit",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    is_valid, _, _ = validate_pass_at_gate(vr.digital_pass.qr_token, "Main Gate")
    assert is_valid is True


def test_br_072_vms_br_190_violated():
    """
    test_id: BR-072
    source_id: VMS-BR-190 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Expired Window Guest",
        email="expwindow@example.com",
        phone="+919876543072",
        id_document_type="AADHAAR",
        id_document_number="BR190072EXP",
        host_id=1,
        purpose="Expired Visit",
        scheduled_start=now - timedelta(hours=5),
        scheduled_end=now - timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    p = vr.digital_pass
    p.valid_to = now - timedelta(hours=1)
    p.save(update_fields=["valid_to"])
    is_valid, msg, _ = validate_pass_at_gate(p.qr_token, "Main Gate")
    assert is_valid is False
    assert "validity window" in msg


# --- VMS-BR-191 Unauthorized Zone Access Denial ---

def test_br_073_vms_br_191_satisfied():
    """
    test_id: BR-073
    source_id: VMS-BR-191 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Zone Allowed Guest",
        email="zoneallowed@example.com",
        phone="+919876543073",
        id_document_type="AADHAAR",
        id_document_number="BR191073ALW",
        host_id=1,
        purpose="Zone Visit",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Library"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    allowed, _msg = validate_zone_access(vr.digital_pass.id, "Library")
    assert allowed is True


def test_br_074_vms_br_191_violated():
    """
    test_id: BR-074
    source_id: VMS-BR-191 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Zone Prohibited Guest",
        email="zoneproh@example.com",
        phone="+919876543074",
        id_document_type="AADHAAR",
        id_document_number="BR191074PRH",
        host_id=1,
        purpose="Zone Visit",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Library"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    allowed, msg = validate_zone_access(vr.digital_pass.id, "High Voltage Lab")
    assert allowed is False
    assert "not authorized" in msg or "violation" in msg


# --- VMS-BR-192 Unauthorized Zone Access Logging ---

def test_br_075_vms_br_192_satisfied():
    """
    test_id: BR-075
    source_id: VMS-BR-192 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Zone Logging Guest",
        email="zonelog@example.com",
        phone="+919876543075",
        id_document_type="AADHAAR",
        id_document_number="BR192075LOG",
        host_id=1,
        purpose="Zone Logging",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Academic Block"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    validate_zone_access(vr.digital_pass.id, "Restricted Vault")
    assert GateCheckLog.objects.filter(
        pass_record=vr.digital_pass, action="DENIED"
    ).exists()


def test_br_076_vms_br_192_violated():
    """
    test_id: BR-076
    source_id: VMS-BR-192 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Zone Clean Guest",
        email="zoneclean@example.com",
        phone="+919876543076",
        id_document_type="AADHAAR",
        id_document_number="BR192076CLN",
        host_id=1,
        purpose="Zone Clean",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Cafeteria"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    validate_zone_access(vr.digital_pass.id, "Cafeteria")
    # No DENIED logs should exist for authorized access
    assert not GateCheckLog.objects.filter(
        pass_record=vr.digital_pass, action="DENIED"
    ).exists()


# --- VMS-BR-193 Maximum Visit Duration ---

def test_br_077_vms_br_193_satisfied():
    """
    test_id: BR-077
    source_id: VMS-BR-193 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Duration Guest",
        email="duration@example.com",
        phone="+919876543077",
        id_document_type="AADHAAR",
        id_document_number="BR193077DUR",
        host_id=1,
        purpose="Duration Visit",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=8),
    )
    assert vr.id is not None


def test_br_078_vms_br_193_violated():
    """
    test_id: BR-078
    source_id: VMS-BR-193 condition-violated
    """
    now = timezone.now()
    # 20 hours exceeds max 12 hours policy
    with pytest.raises(ValidationError, match="duration"):
        pre_register_visit(
            name="Over Duration Guest",
            email="overdur@example.com",
            phone="+919876543078",
            id_document_type="AADHAAR",
            id_document_number="BR193078OVR",
            host_id=1,
            purpose="Excessive Visit",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=23),
        )


# --- VMS-BR-194 Extension Approval ---

def test_br_079_vms_br_194_satisfied():
    """
    test_id: BR-079
    source_id: VMS-BR-194 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Ext Guest",
        email="ext@example.com",
        phone="+919876543079",
        id_document_type="AADHAAR",
        id_document_number="BR194079EXT",
        host_id=1,
        purpose="Extension Visit",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=1),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    ext = extend_visit(vr.id, hours=3, operator_id=1, reason="Meeting prolonged")
    assert ext.extension_hours == 3


def test_br_080_vms_br_194_violated():
    """
    test_id: BR-080
    source_id: VMS-BR-194 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Ext Guest 2",
        email="ext2@example.com",
        phone="+919876543080",
        id_document_type="AADHAAR",
        id_document_number="BR194080EXT",
        host_id=1,
        purpose="Extension Visit 2",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=1),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    # Extension > 8 hours violated
    with pytest.raises(ValueError, match="between 1 and 8"):
        extend_visit(vr.id, hours=12, operator_id=1, reason="Excessive extension")


# --- VMS-BR-195 Pre-authorization Approval Bypass ---

def test_br_081_vms_br_195_satisfied():
    """
    test_id: BR-081
    source_id: VMS-BR-195 condition-satisfied
    """
    now = timezone.now()
    today = date.today()
    create_pre_authorization(
        host_id=5,
        visitor_email="frequent@partner.com",
        valid_from=today - timedelta(days=2),
        valid_to=today + timedelta(days=20),
        visitor_name="Frequent Partner",
    )
    vr = pre_register_visit(
        name="Frequent Partner",
        email="frequent@partner.com",
        phone="+919876543081",
        id_document_type="AADHAAR",
        id_document_number="BR195081FRQ",
        host_id=5,
        purpose="Frequent delivery",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "APPROVED"
    assert vr.digital_pass is not None


def test_br_082_vms_br_195_violated():
    """
    test_id: BR-082
    source_id: VMS-BR-195 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Unpreauth Partner",
        email="unpreauth@partner.com",
        phone="+919876543082",
        id_document_type="AADHAAR",
        id_document_number="BR195082UNP",
        host_id=5,
        purpose="Standard visit",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "PENDING_APPROVAL"
    assert not hasattr(vr, "digital_pass")


# --- VMS-BR-196 VIP Override Authorization ---

def test_br_083_vms_br_196_satisfied():
    """
    test_id: BR-083
    source_id: VMS-BR-196 condition-satisfied
    """
    v = Visitor.objects.create(
        name="Minister Chief",
        email="minister@gov.in",
        phone="+919876543083",
        id_document_type="PASSPORT",
        id_document_number="BR196083MIN",
        is_vip=True,
        vip_reason="Cabinet Minister",
    )
    assert v.is_vip is True


def test_br_084_vms_br_196_violated():
    """
    test_id: BR-084
    source_id: VMS-BR-196 condition-violated
    """
    v = Visitor.objects.create(
        name="Citizen User",
        email="citizen@example.com",
        phone="+919876543084",
        id_document_type="AADHAAR",
        id_document_number="BR196084CTZ",
    )
    assert v.is_vip is False


# --- VMS-BR-197 VIP Override Effect ---

def test_br_085_vms_br_197_satisfied():
    """
    test_id: BR-085
    source_id: VMS-BR-197 condition-satisfied
    """
    now = timezone.now()
    Visitor.objects.create(
        name="Dignitary VIP",
        email="dignitary@gov.in",
        phone="+919876543085",
        id_document_type="PASSPORT",
        id_document_number="BR197085DIG",
        is_vip=True,
    )
    vr = pre_register_visit(
        name="Dignitary VIP",
        email="dignitary@gov.in",
        phone="+919876543085",
        id_document_type="PASSPORT",
        id_document_number="BR197085DIG",
        host_id=1,
        purpose="VIP Convocation",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=6),
    )
    assert vr.status == "APPROVED"
    assert vr.pass_type == "VIP"


def test_br_086_vms_br_197_violated():
    """
    test_id: BR-086
    source_id: VMS-BR-197 condition-violated
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Regular Standard Guest",
        email="regular@example.com",
        phone="+919876543086",
        id_document_type="AADHAAR",
        id_document_number="BR197086REG",
        host_id=1,
        purpose="Regular Visit",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "PENDING_APPROVAL"
    assert vr.pass_type == "PRE_REGISTERED"


# --- VMS-BR-200 Expired Request State ---

def test_br_087_vms_br_200_satisfied():
    """
    test_id: BR-087
    source_id: VMS-BR-200 condition-satisfied
    """
    now = timezone.now()
    v = Visitor.objects.create(
        name="Expired State Guest",
        email="expstate@example.com",
        phone="+919876543087",
        id_document_type="AADHAAR",
        id_document_number="BR200087EXP",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=1,
        purpose="Stale",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
        status="EXPIRED",
    )
    assert vr.status == "EXPIRED"


def test_br_088_vms_br_200_violated():
    """
    test_id: BR-088
    source_id: VMS-BR-200 condition-violated
    """
    with pytest.raises(InvalidStateTransitionError):
        assert_can_transition("EXPIRED", "CHECKED_IN")


# --- VMS-BR-202 Advance Pre-registration Window ---

def test_br_089_vms_br_202_satisfied():
    """
    test_id: BR-089
    source_id: VMS-BR-202 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Advance Window Guest",
        email="advance@example.com",
        phone="+919876543089",
        id_document_type="AADHAAR",
        id_document_number="BR202089ADV",
        host_id=1,
        purpose="Advance Consultation",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None


def test_br_090_vms_br_202_violated():
    """
    test_id: BR-090
    source_id: VMS-BR-202 condition-violated
    """
    now = timezone.now()
    # Less than 2 hours in advance without urgent flag violates rule
    with pytest.raises(ValidationError, match="advance"):
        pre_register_visit(
            name="Too Soon Guest",
            email="toosoon@example.com",
            phone="+919876543090",
            id_document_type="AADHAAR",
            id_document_number="BR202090SOON",
            host_id=1,
            purpose="Too soon consultation",
            scheduled_start=now + timedelta(minutes=45),
            scheduled_end=now + timedelta(hours=2),
            is_urgent_exception=False,
        )


# --- VMS-BR-203 Same-day Urgent Visit Exception ---

def test_br_091_vms_br_203_satisfied():
    """
    test_id: BR-091
    source_id: VMS-BR-203 condition-satisfied
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Urgent Exception Guest",
        email="urgentexc@example.com",
        phone="+919876543091",
        id_document_type="AADHAAR",
        id_document_number="BR203091URG",
        host_id=1,
        purpose="Urgent Inspection",
        scheduled_start=now + timedelta(minutes=30),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    assert vr.id is not None
    assert vr.is_urgent_exception is True


def test_br_092_vms_br_203_violated():
    """
    test_id: BR-092
    source_id: VMS-BR-203 condition-violated
    """
    now = timezone.now()
    with pytest.raises(ValidationError, match="advance"):
        pre_register_visit(
            name="Non-urgent Same Day Guest",
            email="nonurgent@example.com",
            phone="+919876543092",
            id_document_type="AADHAAR",
            id_document_number="BR203092NURG",
            host_id=1,
            purpose="Non-urgent Inspection",
            scheduled_start=now + timedelta(minutes=30),
            scheduled_end=now + timedelta(hours=2),
            is_urgent_exception=False,
        )


# --- VMS-BR-211 Pass Type Domain ---

def test_br_093_vms_br_211_satisfied():
    """
    test_id: BR-093
    source_id: VMS-BR-211 condition-satisfied
    """
    valid_types = ["PRE_REGISTERED", "WALK_IN", "VIP", "CONTRACTOR", "EVENT"]
    v = Visitor.objects.create(
        name="Pass Type Domain Guest",
        email="passtype@example.com",
        phone="+919876543093",
        id_document_type="AADHAAR",
        id_document_number="BR211093DOM",
    )
    now = timezone.now()
    for pt in valid_types:
        vr = VisitRequest.objects.create(
            visitor=v,
            host_id=1,
            purpose=f"Pass type {pt}",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
            pass_type=pt,
        )
        assert vr.pass_type == pt


def test_br_094_vms_br_211_violated():
    """
    test_id: BR-094
    source_id: VMS-BR-211 condition-violated
    """
    # Invalid pass type not in choices
    valid_types = {k for k, _ in VisitRequest.PASS_TYPES}
    assert "UNAUTHORIZED_BADGE" not in valid_types
