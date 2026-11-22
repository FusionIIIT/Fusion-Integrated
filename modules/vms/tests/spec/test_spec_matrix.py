"""
Cross-cutting end-to-end integration test matrix for Visitor Management System (VMS).

Verifies multi-workflow operational journeys spanning registration, approval,
gate operations, zone access, emergency muster, policy transitions, and auto-checkout sweeps.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import EmergencyMusterRoster
from modules.vms.selectors.emergency import get_muster_summary
from modules.vms.selectors.visitors import get_live_onsite_visitors
from modules.vms.services.approval import contingency_approve, decide_visit_request
from modules.vms.services.blacklist import add_to_blacklist, safe_list_entry
from modules.vms.services.emergency import record_roll_call, trigger_emergency_muster
from modules.vms.services.gate import check_in_visitor, check_out_visitor, validate_pass_at_gate
from modules.vms.services.policy import create_access_policy, publish_access_policy
from modules.vms.services.registration import pre_register_visit, walk_in_register
from modules.vms.services.scheduled import auto_checkout_overstays
from modules.vms.services.zone import grant_zone_elevation, validate_zone_access

pytestmark = pytest.mark.django_db


def test_spec_matrix_full_visitor_journey():
    """
    Scenario 1: Pre-registration -> Host Approval -> Gate Check-in ->
    Zone Elevation -> Zone Verification -> Normal Checkout.
    """
    now = timezone.now()
    # 1. Pre-registration (submitted with urgent exception so valid_from covers now)
    vr = pre_register_visit(
        name="Matrix Explorer",
        email="matrix.explorer@vms.org",
        phone="+919811122233",
        id_document_type="PASSPORT",
        id_document_number="MTRX-EXP-001",
        host_id=42,
        purpose="Comprehensive System Evaluation",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=4),
        access_zones=["Main Lobby", "Conference Room A"],
        is_urgent_exception=True,
    )
    assert vr.status == "PENDING_APPROVAL"

    # 2. Host Approval
    decide_visit_request(vr.id, host_id=42, decision="APPROVE", reason="Welcome to facility")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    assert hasattr(vr, "digital_pass")
    pass_record = vr.digital_pass
    assert pass_record.status == "ACTIVE"
    assert pass_record.qr_token.startswith("VMS-")

    # 3. Security Gate Check-in
    valid, _reason, _p = validate_pass_at_gate(pass_record.qr_token, "Main Gate East")
    assert valid is True
    check_in = check_in_visitor(pass_record.id, "Main Gate East", operator_id=10)
    assert check_in.action == "CHECK_IN"
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"
    assert vr.actual_check_in is not None

    # 4. Zone Access: Authorized vs Restricted
    allowed, _msg = validate_zone_access(pass_record.id, "Conference Room A")
    assert allowed is True
    denied, _reason = validate_zone_access(pass_record.id, "Secure Server Vault")
    assert denied is False

    # 5. Zone Elevation Grant
    elevation = grant_zone_elevation(
        pass_record.id,
        zone_name="Secure Server Vault",
        hours=2,
        admin_id=1,
        reason="Server inspection permit approved",
    )
    assert elevation.zone_name == "Secure Server Vault"
    elevated_allowed, _ = validate_zone_access(pass_record.id, "Secure Server Vault")
    assert elevated_allowed is True

    # 6. Check-out
    check_out = check_out_visitor(pass_record.id, "Main Gate East", operator_id=10)
    assert check_out.action == "CHECK_OUT"
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"
    assert vr.actual_check_out is not None


def test_spec_matrix_walk_in_contingency_and_blacklist_safelist():
    """
    Scenario 2: Walk-in registration -> Admin contingency approval ->
    Blacklist enforcement -> Watchlist safe-listing review.
    """
    timezone.now()
    # 1. Walk-in Registration
    vr = walk_in_register(
        name="Urgent Contractor",
        email="contractor@vms.org",
        phone="+919877766554",
        id_document_type="DRIVING_LICENSE",
        id_document_number="DL-MTRX-4455",
        host_id=88,
        purpose="Emergency AC repair",
    )
    assert vr.status == "PENDING_APPROVAL"

    # 2. Host uncontactable -> Contingency Approval by Admin
    contingency_approve(vr.id, admin_id=1, reason="Urgent facility maintenance, host unreachable")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    assert vr.digital_pass is not None

    # 3. Add visitor to blacklist
    bl = add_to_blacklist(
        name="Urgent Contractor",
        id_document_type="DRIVING_LICENSE",
        id_document_number="DL-MTRX-4455",
        phone="+919877766554",
        reason="Flagged for security review",
    )
    assert bl.status == "ACTIVE"

    # 4. Attempt to validate at gate - must be blocked
    valid, reason, _ = validate_pass_at_gate(vr.digital_pass.qr_token, "North Gate")
    assert valid is False
    assert "blacklist" in reason.lower()

    # 5. Security review safe-lists the contractor
    safe_list_entry(bl.id, hours=12, admin_id=1, reason="Identity verified and cleared by Chief Security Officer")
    bl.refresh_from_db()
    assert bl.status == "SAFE_LISTED"

    # 6. Retry gate validation - now allowed
    valid_after, _, _ = validate_pass_at_gate(vr.digital_pass.qr_token, "North Gate")
    assert valid_after is True


def test_spec_matrix_emergency_evacuation_and_muster_reconciliation():
    """
    Scenario 3: Active on-site visitors -> Emergency evacuation muster trigger ->
    Roll call accounting -> Real-time muster summary verification.
    """
    now = timezone.now()
    # 1. Create two on-site visitors
    vr1 = pre_register_visit(
        name="Staff Trainee 1",
        email="trainee1@vms.org",
        phone="+919822233344",
        id_document_type="AADHAAR",
        id_document_number="MTRX-EMG-01",
        host_id=5,
        purpose="Training Session",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=3),
        is_urgent_exception=True,
    )
    decide_visit_request(vr1.id, host_id=5, decision="APPROVE")
    vr1.refresh_from_db()
    check_in_visitor(vr1.digital_pass.id, "West Gate")

    vr2 = pre_register_visit(
        name="Staff Trainee 2",
        email="trainee2@vms.org",
        phone="+919822233345",
        id_document_type="AADHAAR",
        id_document_number="MTRX-EMG-02",
        host_id=5,
        purpose="Training Session",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=3),
        is_urgent_exception=True,
    )
    decide_visit_request(vr2.id, host_id=5, decision="APPROVE")
    vr2.refresh_from_db()
    check_in_visitor(vr2.digital_pass.id, "West Gate")

    on_site = get_live_onsite_visitors()
    assert on_site.count() >= 2

    # 2. Trigger Emergency Muster
    muster_id = trigger_emergency_muster(initiated_by_id=99, assembly_point="South Lawn Muster Point")
    assert muster_id.startswith("MUSTER-")

    # Verify muster roster entries
    roster_qs = EmergencyMusterRoster.objects.filter(muster_id=muster_id)
    assert roster_qs.filter(visitor=vr1.visitor).exists()
    assert roster_qs.filter(visitor=vr2.visitor).exists()

    summary_initial = get_muster_summary(muster_id)
    assert summary_initial["total"] >= 2
    assert summary_initial["accounted"] == 0
    assert summary_initial["unaccounted"] >= 2

    # 3. Roll call: Account for Trainee 1
    item1 = roster_qs.get(visitor=vr1.visitor)
    record_roll_call(item1.id, accounted_by_id=99, status="ACCOUNTED")

    summary_updated = get_muster_summary(muster_id)
    assert summary_updated["accounted"] >= 1
    assert summary_updated["unaccounted"] == summary_initial["unaccounted"] - 1


def test_spec_matrix_policy_publication_and_version_tracking():
    """
    Scenario 4: Policy definition, publication lifecycle, and version tracking.
    """
    p1 = create_access_policy(
        version=201,
        max_duration_hours=8,
        policy_notes="Standard visitor policy",
    )
    assert p1.version == 201
    assert p1.is_published is False

    published = publish_access_policy(version=201)
    assert published.is_published is True
    assert published.version == 201


def test_spec_matrix_overstay_sweep():
    """
    Scenario 5: Visitor on-site past departure time ->
    Automated background overstay sweep transitions status to AUTO_CHECKED_OUT.
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Overstay Guest",
        email="overstay.guest@vms.org",
        phone="+919833344455",
        id_document_type="PASSPORT",
        id_document_number="MTRX-OVR-99",
        host_id=12,
        purpose="Brief consultation",
        scheduled_start=now - timedelta(hours=6),
        scheduled_end=now - timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=12, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"

    # Run auto-checkout sweep
    swept = auto_checkout_overstays(buffer_hours=0)
    assert swept >= 1
    vr.refresh_from_db()
    assert vr.status == "AUTO_CHECKED_OUT"
    assert vr.actual_check_out is not None
