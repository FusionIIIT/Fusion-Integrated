"""Specification tests for Functional Requirements (FR).

Each test explicitly documents:
test_id: FR-NNN
source_id: VMS-CFR-NNN or VMS-AFR-NNN
"""

from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from modules.vms.models import (
    AccessPolicy,
    EmergencyMusterRoster,
    GateCheckLog,
    Pass,
    Visitor,
    VisitRequest,
)
from modules.vms.selectors.audit import list_audit_logs
from modules.vms.selectors.passes import get_pass_by_id
from modules.vms.selectors.policy import get_active_published_policy
from modules.vms.selectors.visitors import get_live_onsite_visitors
from modules.vms.services.approval import (
    contingency_approve,
    create_pre_authorization,
    decide_visit_request,
    extend_visit,
    terminate_visit,
)
from modules.vms.services.blacklist import add_to_blacklist, safe_list_entry
from modules.vms.services.emergency import record_roll_call, trigger_emergency_muster
from modules.vms.services.gate import (
    check_in_visitor,
    check_out_visitor,
    manual_gate_override,
    offline_batch_sync,
    validate_pass_at_gate,
)
from modules.vms.services.policy import create_access_policy, publish_access_policy
from modules.vms.services.registration import (
    pre_register_visit,
    walk_in_register,
)
from modules.vms.services.roles import reassign_vms_work
from modules.vms.services.scheduled import auto_checkout_overstays, expire_pending_requests
from modules.vms.services.zone import grant_zone_elevation, validate_zone_access

pytestmark = pytest.mark.django_db


def test_fr_001_authoritative_record_creation(admin_client):
    """
    test_id: FR-001
    source_id: VMS-CFR-001 authoritative-record-creation
    """
    payload = {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone": "+919876543210",
        "id_document_type": "AADHAAR",
        "id_document_number": "123456789012",
        "host_id": 101,
        "purpose": "Research Collaboration",
        "scheduled_start": (timezone.now() + timedelta(hours=3)).isoformat(),
        "scheduled_end": (timezone.now() + timedelta(hours=5)).isoformat(),
        "access_zones": ["Main Building"],
    }
    resp = admin_client.post("/api/v1/vms/visits/pre-register/", data=payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] in ("PENDING", "PENDING_APPROVAL")
    assert Visitor.objects.filter(email="alice@example.com").exists()
    assert VisitRequest.objects.filter(purpose="Research Collaboration").exists()


def test_fr_002_digital_registry_scoping(host_client):
    """
    test_id: FR-002
    source_id: VMS-AFR-002 digital-registry-scoping
    """
    v = Visitor.objects.create(
        name="Bob Martin",
        email="bob@example.com",
        phone="+919876543211",
        id_document_type="PAN",
        id_document_number="ABCDE1234F",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=3,  # matching host_client user_id
        purpose="Advising",
        scheduled_start=timezone.now() + timedelta(hours=2),
        scheduled_end=timezone.now() + timedelta(hours=4),
        status="PENDING_APPROVAL",
    )
    resp = host_client.get("/api/v1/vms/visits/")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.data]
    assert vr.id in ids


def test_fr_003_role_assignment_duration():
    """
    test_id: FR-003
    source_id: VMS-CFR-002 role-assignment-duration
    """
    policy = AccessPolicy.objects.create(
        version=99,
        visiting_hours_start="06:00",
        visiting_hours_end="22:00",
        max_duration_hours=12,
        is_published=True,
    )
    assert policy.version == 99
    assert policy.max_duration_hours == 12


def test_fr_004_role_reassignment_handoff():
    """
    test_id: FR-004
    source_id: VMS-AFR-003 role-reassignment-handoff
    """
    v = Visitor.objects.create(
        name="Charlie Brown",
        email="charlie@example.com",
        phone="+919876543212",
        id_document_type="PASSPORT",
        id_document_number="Z1234567",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=10,
        purpose="Project Review",
        scheduled_start=timezone.now() + timedelta(hours=2),
        scheduled_end=timezone.now() + timedelta(hours=4),
        status="PENDING_APPROVAL",
    )
    reassigned = reassign_vms_work(from_user_id=10, to_user_id=20)
    assert reassigned == 1
    vr.refresh_from_db()
    assert vr.host_id == 20


def test_fr_005_non_superadmin_denial(host_client):
    """
    test_id: FR-005
    source_id: VMS-CFR-002 non-superadmin-denial
    """
    # Host client lacks policy.manage permission
    resp = host_client.post(
        "/api/v1/vms/policies/",
        data={
            "version": 2,
            "visiting_hours_start": "09:00",
            "visiting_hours_end": "17:00",
            "max_duration_hours": 8,
        },
        format="json",
    )
    assert resp.status_code == 403


def test_fr_006_external_boundary_isolation():
    """
    test_id: FR-006
    source_id: VMS-CFR-003 external-boundary-isolation
    """
    # Verify VisitRequest uses integer/string host_id without Foreign Key to User model
    v = Visitor.objects.create(
        name="David Lee",
        email="david@example.com",
        phone="+919876543213",
        id_document_type="AADHAAR",
        id_document_number="123456789013",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=999999,  # Non-existent DB user ID works cleanly
        purpose="External Audit",
        scheduled_start=timezone.now() + timedelta(hours=2),
        scheduled_end=timezone.now() + timedelta(hours=4),
    )
    assert vr.host_id == 999999


def test_fr_007_event_hostel_coordination():
    """
    test_id: FR-007
    source_id: VMS-AFR-007 event-hostel-coordination
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Event Guest",
        email="guest@event.com",
        phone="+919876543214",
        id_document_type="AADHAAR",
        id_document_number="123456789014",
        host_id=1,
        purpose="Convocation 2026",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=6),
        external_event_ref="EVENT-2026-X",
    )
    assert vr.external_event_ref == "EVENT-2026-X"


def test_fr_008_vip_permission_grant():
    """
    test_id: FR-008
    source_id: VMS-CFR-004 vip-permission-grant
    """
    v = Visitor.objects.create(
        name="Dignitary Chief",
        email="vip@state.gov",
        phone="+919876543215",
        id_document_type="PASSPORT",
        id_document_number="VIP99999",
        is_vip=True,
        vip_reason="Chief Guest",
    )
    assert v.is_vip is True
    assert v.vip_reason == "Chief Guest"


def test_fr_009_vip_override_effect():
    """
    test_id: FR-009
    source_id: VMS-AFR-005 vip-override-effect
    """
    now = timezone.now()
    Visitor.objects.create(
        name="VIP Guest",
        email="vip2@state.gov",
        phone="+919876543216",
        id_document_type="PASSPORT",
        id_document_number="VIP88888",
        is_vip=True,
    )
    vr = pre_register_visit(
        name="VIP Guest",
        email="vip2@state.gov",
        phone="+919876543216",
        id_document_type="PASSPORT",
        id_document_number="VIP88888",
        host_id=1,
        purpose="VIP Inauguration",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=6),
    )
    # VIP visit is immediately approved and pass created
    assert vr.status == "APPROVED"
    assert vr.pass_type == "VIP"
    assert vr.digital_pass is not None


def test_fr_010_audit_trail_logging():
    """
    test_id: FR-010
    source_id: VMS-CFR-005 audit-trail-logging
    """
    now = timezone.now()
    v = Visitor.objects.create(
        name="Test Guest",
        email="audit@example.com",
        phone="+919876543217",
        id_document_type="AADHAAR",
        id_document_number="123456789017",
    )
    vr = VisitRequest.objects.create(
        visitor=v,
        host_id=1,
        purpose="Audit Test",
        scheduled_start=now + timedelta(hours=2),
        scheduled_end=now + timedelta(hours=4),
        status="APPROVED",
    )
    p = Pass.objects.create(
        visit_request=vr,
        pass_number="VMS-PASS-AUDIT-1",
        qr_token="TOKEN-AUDIT-1",
        valid_from=now - timedelta(minutes=10),
        valid_to=now + timedelta(hours=4),
        status="ACTIVE",
    )
    log = GateCheckLog.objects.create(
        pass_record=p,
        action="CHECK_IN",
        gate_name="North Gate",
        operator_id=42,
        timestamp=now,
    )
    assert log.id is not None
    assert log.action == "CHECK_IN"
    assert log.gate_name == "North Gate"


def test_fr_011_audit_trail_retrieval(admin_client):
    """
    test_id: FR-011
    source_id: VMS-AFR-006 audit-trail-retrieval
    """
    logs = list_audit_logs()
    resp = admin_client.get("/api/v1/vms/audit/")
    assert resp.status_code == 200
    assert len(resp.data) >= len(logs)


def test_fr_012_policy_versioning():
    """
    test_id: FR-012
    source_id: VMS-CFR-006 policy-versioning
    """
    p = create_access_policy(
        version=1,
        visiting_hours_start=time(8, 0),
        visiting_hours_end=time(20, 0),
        max_duration_hours=8,
    )
    assert p.version == 1
    assert p.is_published is False


def test_fr_013_policy_runtime_enforcement():
    """
    test_id: FR-013
    source_id: VMS-AFR-008 policy-runtime-enforcement
    """
    create_access_policy(
        version=10,
        visiting_hours_start=time(7, 0),
        visiting_hours_end=time(21, 0),
        max_duration_hours=10,
    )
    publish_access_policy(version=10)
    active = get_active_published_policy()
    assert active is not None
    assert active.version == 10


def test_fr_014_blacklist_addition(admin_client):
    """
    test_id: FR-014
    source_id: VMS-CFR-007 blacklist-addition
    """
    payload = {
        "name": "Banned User",
        "id_document_type": "AADHAAR",
        "id_document_number": "999988887777",
        "phone": "+919999888877",
        "reason": "Security Infraction",
    }
    resp = admin_client.post("/api/v1/vms/blacklist/", data=payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "ACTIVE"


def test_fr_015_blacklist_check_denial():
    """
    test_id: FR-015
    source_id: VMS-AFR-009 blacklist-check-denial
    """
    add_to_blacklist(
        name="Prohibited Person",
        id_document_type="AADHAAR",
        id_document_number="111122223333",
        phone="+919876543299",
        reason="Theft record",
    )
    now = timezone.now()
    with pytest.raises(PermissionError, match="blacklist"):
        pre_register_visit(
            name="Prohibited Person",
            email="denied@example.com",
            phone="+919876543299",
            id_document_type="AADHAAR",
            id_document_number="111122223333",
            host_id=1,
            purpose="Prohibited visit",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )


def test_fr_016_safe_list_override():
    """
    test_id: FR-016
    source_id: VMS-AFR-010 safe-list-override
    """
    entry = add_to_blacklist(
        name="Reformed Person",
        id_document_type="AADHAAR",
        id_document_number="444455556666",
        phone="+919876543298",
        reason="Past violation",
    )
    safe_list_entry(
        entry_id=entry.id,
        hours=24,
        admin_id=1,
        reason="Court cleared temporary exemption",
    )
    now = timezone.now()
    vr = pre_register_visit(
        name="Reformed Person",
        email="reformed@example.com",
        phone="+919876543298",
        id_document_type="AADHAAR",
        id_document_number="444455556666",
        host_id=1,
        purpose="Cleared visit",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.id is not None
    assert vr.status in ("PENDING", "PENDING_APPROVAL")


def test_fr_017_analytics_generation(admin_client):
    """
    test_id: FR-017
    source_id: VMS-CFR-008 analytics-generation
    """
    resp = admin_client.get("/api/v1/vms/analytics/dashboard/")
    assert resp.status_code == 200
    assert "total_today" in resp.data
    assert "onsite_now" in resp.data


def test_fr_018_bulk_visitor_upload(admin_client):
    """
    test_id: FR-018
    source_id: VMS-CFR-009 bulk-visitor-upload
    """
    now = timezone.now()
    records = [
        {
            "name": f"Bulk Attendee {i}",
            "email": f"attendee{i}@conf.org",
            "phone": f"+91987650000{i}",
            "id_document_type": "AADHAAR",
            "id_document_number": f"10002000300{i}",
        }
        for i in range(1, 4)
    ]
    payload = {
        "host_id": 1,
        "purpose": "Tech Conference",
        "scheduled_start": (now + timedelta(hours=3)).isoformat(),
        "scheduled_end": (now + timedelta(hours=6)).isoformat(),
        "records": records,
    }
    resp = admin_client.post("/api/v1/vms/visits/bulk/", data=payload, format="json")
    assert resp.status_code == 201
    assert len(resp.data) == 3


def test_fr_019_pre_registration_mandatory_fields(admin_client):
    """
    test_id: FR-019
    source_id: VMS-CFR-010 pre-registration-mandatory-fields
    """
    # Missing email, phone, purpose
    resp = admin_client.post(
        "/api/v1/vms/visits/pre-register/",
        data={"name": "Incomplete Visitor"},
        format="json",
    )
    assert resp.status_code == 400


def test_fr_020_duplicate_visit_check():
    """
    test_id: FR-020
    source_id: VMS-AFR-011 duplicate-visit-check
    """
    now = timezone.now()
    start = now + timedelta(hours=3)
    end = now + timedelta(hours=5)
    pre_register_visit(
        name="Dup Visitor",
        email="dup@example.com",
        phone="+919876543201",
        id_document_type="AADHAAR",
        id_document_number="555566667777",
        host_id=1,
        purpose="First Consultation",
        scheduled_start=start,
        scheduled_end=end,
    )
    with pytest.raises(ValueError, match="already active or pending"):
        pre_register_visit(
            name="Dup Visitor",
            email="dup@example.com",
            phone="+919876543201",
            id_document_type="AADHAAR",
            id_document_number="555566667777",
            host_id=1,
            purpose="Duplicate Consultation",
            scheduled_start=start + timedelta(minutes=30),
            scheduled_end=end + timedelta(minutes=30),
        )


def test_fr_021_visit_status_tracking(admin_client):
    """
    test_id: FR-021
    source_id: VMS-CFR-011 visit-status-tracking
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Tracked Visitor",
        email="track@example.com",
        phone="+919876543202",
        id_document_type="AADHAAR",
        id_document_number="888899990000",
        host_id=1,
        purpose="Interview",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    pass_obj = get_pass_by_id(vr.digital_pass.id)
    resp = admin_client.get(f"/api/v1/vms/passes/{pass_obj.id}/")
    assert resp.status_code == 200
    assert resp.data["qr_token"] == pass_obj.qr_token


def test_fr_022_host_approval_decision():
    """
    test_id: FR-022
    source_id: VMS-CFR-012 host-approval-decision
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Approval Candidate",
        email="approve@example.com",
        phone="+919876543203",
        id_document_type="AADHAAR",
        id_document_number="222233334444",
        host_id=1,
        purpose="Project Demo",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    approved_vr = decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    assert approved_vr.status == "APPROVED"
    assert approved_vr.digital_pass is not None


def test_fr_023_pre_authorization_creation():
    """
    test_id: FR-023
    source_id: VMS-AFR-012 pre-authorization-creation
    """
    now = timezone.now()
    today = date.today()
    auth = create_pre_authorization(
        host_id=1,
        visitor_email="vendor@services.com",
        valid_from=today - timedelta(days=1),
        valid_to=today + timedelta(days=30),
        visitor_name="Vendor Lead",
    )
    assert auth.id is not None
    vr = pre_register_visit(
        name="Vendor Lead",
        email="vendor@services.com",
        phone="+919876543204",
        id_document_type="PAN",
        id_document_number="VNDOR1234K",
        host_id=1,
        purpose="Vendor Maintenance",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "APPROVED"


def test_fr_024_gate_pass_validation():
    """
    test_id: FR-024
    source_id: VMS-CFR-013 gate-pass-validation
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Gate Guest",
        email="gate@example.com",
        phone="+919876543205",
        id_document_type="AADHAAR",
        id_document_number="333344445555",
        host_id=1,
        purpose="Campus Tour",
        scheduled_start=now - timedelta(minutes=15),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    pass_obj = vr.digital_pass

    is_valid, _msg, _ = validate_pass_at_gate(pass_obj.qr_token, "Main Gate")
    assert is_valid is True
    check_in_visitor(pass_obj.id, "Main Gate", operator_id=1)
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_fr_025_expired_pass_gate_denial():
    """
    test_id: FR-025
    source_id: VMS-AFR-013 expired-pass-gate-denial
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Late Guest",
        email="late@example.com",
        phone="+919876543206",
        id_document_type="AADHAAR",
        id_document_number="444455557777",
        host_id=1,
        purpose="Late arrival",
        scheduled_start=now - timedelta(hours=6),
        scheduled_end=now - timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    p = vr.digital_pass
    p.valid_to = now - timedelta(hours=1)
    p.save(update_fields=["valid_to"])

    is_valid, _msg, _ = validate_pass_at_gate(p.qr_token, "Main Gate")
    assert is_valid is False


def test_fr_026_manual_gate_override():
    """
    test_id: FR-026
    source_id: VMS-CFR-014 manual-gate-override
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Battery Dead Guest",
        email="deadphone@example.com",
        phone="+919876543207",
        id_document_type="AADHAAR",
        id_document_number="666677778888",
        host_id=1,
        purpose="VIP Meeting",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    manual_gate_override(
        vr.digital_pass.id,
        admin_id=1,
        reason="Phone battery depleted; physical passport verified",
    )
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_fr_027_gate_check_out():
    """
    test_id: FR-027
    source_id: VMS-CFR-015 gate-check-out
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Checkout Guest",
        email="checkout@example.com",
        phone="+919876543208",
        id_document_type="AADHAAR",
        id_document_number="777788889999",
        host_id=1,
        purpose="Seminar",
        scheduled_start=now - timedelta(minutes=30),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate", operator_id=1)
    check_out_visitor(vr.digital_pass.id, "Main Exit Gate", operator_id=1)
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"
    assert vr.digital_pass.status == "USED"


def test_fr_028_live_dashboard_roster():
    """
    test_id: FR-028
    source_id: VMS-CFR-016 live-dashboard-roster
    """
    now = timezone.now()
    for i in (1, 2):
        vr = pre_register_visit(
            name=f"Onsite Guest {i}",
            email=f"onsite{i}@campus.edu",
            phone=f"+9198765432{10+i}",
            id_document_type="AADHAAR",
            id_document_number=f"88880000111{i}",
            host_id=1,
            purpose=f"Live Session {i}",
            scheduled_start=now - timedelta(minutes=20),
            scheduled_end=now + timedelta(hours=2),
            is_urgent_exception=True,
        )
        decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
        vr.refresh_from_db()
        check_in_visitor(vr.digital_pass.id, "Gate A", operator_id=1)

    live = get_live_onsite_visitors()
    assert live.count() >= 2


def test_fr_029_zone_permission_check():
    """
    test_id: FR-029
    source_id: VMS-CFR-017 zone-permission-check
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Zone Guest",
        email="zone@example.com",
        phone="+919876543219",
        id_document_type="AADHAAR",
        id_document_number="999911112222",
        host_id=1,
        purpose="Lecture",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Academic Block"],
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    allowed, msg = validate_zone_access(vr.digital_pass.id, "Server Room")
    assert allowed is False
    assert "not authorized" in msg or "violation" in msg


def test_fr_030_temporary_zone_elevation():
    """
    test_id: FR-030
    source_id: VMS-AFR-014 temporary-zone-elevation
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Tech Contractor",
        email="tech@contractor.com",
        phone="+919876543220",
        id_document_type="AADHAAR",
        id_document_number="101020203030",
        host_id=1,
        purpose="Server Maintenance",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Academic Block"],
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    grant_zone_elevation(
        pass_id=vr.digital_pass.id,
        zone_name="Server Room",
        hours=2,
        admin_id=1,
        reason="Emergency Maintenance",
    )
    allowed, _msg = validate_zone_access(vr.digital_pass.id, "Server Room")
    assert allowed is True


def test_fr_031_emergency_muster_trigger():
    """
    test_id: FR-031
    source_id: VMS-CFR-018 emergency-muster-trigger
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Emergency Test Visitor",
        email="evac@example.com",
        phone="+919876543221",
        id_document_type="AADHAAR",
        id_document_number="202030304040",
        host_id=1,
        purpose="Muster check",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    muster_id = trigger_emergency_muster(
        initiated_by_id=1,
        assembly_point="Football Ground",
    )
    assert muster_id is not None
    assert EmergencyMusterRoster.objects.filter(muster_id=muster_id).exists()


def test_fr_032_emergency_roll_call():
    """
    test_id: FR-032
    source_id: VMS-AFR-015 emergency-roll-call
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Roll Call Visitor",
        email="rollcall@example.com",
        phone="+919876543222",
        id_document_type="AADHAAR",
        id_document_number="303040405050",
        host_id=1,
        purpose="Roll Call Test",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    muster_id = trigger_emergency_muster(initiated_by_id=1, assembly_point="Sports Complex")
    roster_item = EmergencyMusterRoster.objects.filter(
        muster_id=muster_id, visitor=vr.visitor
    ).first()
    assert roster_item is not None

    updated = record_roll_call(roster_item.id, accounted_by_id=1, status="ACCOUNTED")
    assert updated.accountability_status == "ACCOUNTED"


def test_fr_033_offline_batch_reconciliation():
    """
    test_id: FR-033
    source_id: VMS-CFR-019 offline-batch-reconciliation
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Offline Sync Guest",
        email="offline@example.com",
        phone="+919876543223",
        id_document_type="AADHAAR",
        id_document_number="404050506060",
        host_id=1,
        purpose="Offline Check",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    p = vr.digital_pass

    events = [
        {
            "pass_id": p.id,
            "action": "CHECK_IN",
            "gate_name": "Gate 2 Offline",
            "timestamp": now.isoformat(),
        }
    ]
    result = offline_batch_sync(events, operator_id=1)
    assert result["synced"] == 1
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_fr_034_walkin_registration():
    """
    test_id: FR-034
    source_id: VMS-CFR-020 walkin-registration
    """
    vr = walk_in_register(
        name="Walkin Person",
        email="walkin@example.com",
        phone="+919876543224",
        host_id=1,
        purpose="In-person Inquiry",
        id_document_type="AADHAAR",
        id_document_number="505060607070",
        auto_approve=False,
    )
    assert vr.pass_type == "WALK_IN"
    assert vr.status in ("PENDING", "PENDING_APPROVAL")


def test_fr_035_walkin_contingency_approval():
    """
    test_id: FR-035
    source_id: VMS-AFR-016 walkin-contingency-approval
    """
    vr = walk_in_register(
        name="Urgent Visitor",
        email="urgent@example.com",
        phone="+919876543225",
        host_id=1,
        purpose="Urgent Dispatch",
        id_document_type="AADHAAR",
        id_document_number="606070708080",
        auto_approve=False,
    )
    app_vr = contingency_approve(
        visit_id=vr.id,
        admin_id=1,
        reason="Host unreachable; VIP parcel delivery verified",
    )
    assert app_vr.status == "APPROVED"
    assert app_vr.digital_pass is not None


def test_fr_036_visit_extension():
    """
    test_id: FR-036
    source_id: VMS-CFR-021 visit-extension
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Extend Guest",
        email="extend@example.com",
        phone="+919876543226",
        id_document_type="AADHAAR",
        id_document_number="707080809090",
        host_id=1,
        purpose="Long Meeting",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=1),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    initial_end = vr.scheduled_end
    ext_vr = extend_visit(
        visit_id=vr.id,
        hours=2,
        operator_id=1,
        reason="Discussion continuing",
    )
    assert ext_vr.scheduled_end > initial_end
    assert ext_vr.status == "CHECKED_IN"


def test_fr_037_early_visit_termination():
    """
    test_id: FR-037
    source_id: VMS-AFR-017 early-visit-termination
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Terminated Guest",
        email="terminate@example.com",
        phone="+919876543227",
        id_document_type="AADHAAR",
        id_document_number="808090900000",
        host_id=1,
        purpose="Short meeting",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=3),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    term_vr = terminate_visit(
        visit_id=vr.id,
        operator_id=1,
        reason="Host called away for emergency",
    )
    assert term_vr.status == "TERMINATED_EARLY"
    assert term_vr.digital_pass.status == "REVOKED"


def test_fr_038_approval_timeout_expiration():
    """
    test_id: FR-038
    source_id: VMS-CFR-022 approval-timeout-expiration
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Timed Out Visitor",
        email="timeout@example.com",
        phone="+919876543228",
        id_document_type="AADHAAR",
        id_document_number="909000001111",
        host_id=1,
        purpose="Stale registration",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    # Manually backdate created_at to 30 hours ago
    VisitRequest.objects.filter(id=vr.id).update(created_at=now - timedelta(hours=30))
    expired_count = expire_pending_requests(timeout_hours=24)
    assert expired_count >= 1
    vr.refresh_from_db()
    assert vr.status == "EXPIRED"


def test_fr_039_automatic_checkout_overstay():
    """
    test_id: FR-039
    source_id: VMS-AFR-018 automatic-checkout-overstay
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="Overstay Visitor",
        email="overstay@example.com",
        phone="+919876543229",
        id_document_type="AADHAAR",
        id_document_number="111100002222",
        host_id=1,
        purpose="Overstay session",
        scheduled_start=now - timedelta(hours=24),
        scheduled_end=now - timedelta(hours=12),
        is_urgent_exception=True,
    )
    decide_visit_request(visit_id=vr.id, decision="APPROVE", host_id=1)
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Gate 1", operator_id=1)

    auto_count = auto_checkout_overstays()
    assert auto_count >= 1
    vr.refresh_from_db()
    assert vr.status == "AUTO_CHECKED_OUT"
