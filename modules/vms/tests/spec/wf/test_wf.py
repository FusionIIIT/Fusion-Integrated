"""Specification tests for Workflows (WF).

Each test explicitly documents:
test_id: WF-NNN
source_id: BW-VMS-XX or CW-VMS-XX end-to-end-path
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.vms.models import (
    EmergencyMusterRoster,
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
from modules.vms.services.emergency import record_roll_call, trigger_emergency_muster
from modules.vms.services.gate import (
    check_in_visitor,
    check_out_visitor,
    manual_gate_override,
    offline_batch_sync,
    validate_pass_at_gate,
)
from modules.vms.services.registration import (
    bulk_register_visitors,
    pre_register_visit,
    walk_in_register,
)
from modules.vms.services.scheduled import expire_pending_requests
from modules.vms.services.zone import grant_zone_elevation, validate_zone_access

pytestmark = pytest.mark.django_db


def test_wf_001_bw_vms_01_pre_registered_approved_visit():
    """
    test_id: WF-001
    source_id: BW-VMS-01 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF1 Guest",
        email="wf1@example.com",
        phone="+919876541001",
        id_document_type="AADHAAR",
        id_document_number="WF01001APR",
        host_id=1,
        purpose="Official Consultation",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=3),
        is_urgent_exception=True,
    )
    assert vr.status == "PENDING_APPROVAL"

    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    assert hasattr(vr, "digital_pass")

    log_in = check_in_visitor(vr.digital_pass.id, "North Gate")
    assert log_in.action == "CHECK_IN"
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"

    log_out = check_out_visitor(vr.digital_pass.id, "North Gate")
    assert log_out.action == "CHECK_OUT"
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"


def test_wf_002_bw_vms_02_pre_registered_rejected_visit():
    """
    test_id: WF-002
    source_id: BW-VMS-02 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF2 Guest",
        email="wf2@example.com",
        phone="+919876541002",
        id_document_type="AADHAAR",
        id_document_number="WF02002REJ",
        host_id=1,
        purpose="Conference",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    rej = decide_visit_request(vr.id, host_id=1, decision="REJECT", reason="Host out of office")
    assert rej.status == "REJECTED"
    assert not hasattr(rej, "digital_pass")


def test_wf_003_bw_vms_03_pre_registered_approval_timeout():
    """
    test_id: WF-003
    source_id: BW-VMS-03 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF3 Guest",
        email="wf3@example.com",
        phone="+919876541003",
        id_document_type="AADHAAR",
        id_document_number="WF03003TMO",
        host_id=1,
        purpose="Timeout test",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    VisitRequest.objects.filter(id=vr.id).update(created_at=now - timedelta(hours=30))
    expire_pending_requests(timeout_hours=24)
    vr.refresh_from_db()
    assert vr.status == "EXPIRED"


def test_wf_004_bw_vms_04_pre_authorized_visit():
    """
    test_id: WF-004
    source_id: BW-VMS-04 end-to-end-path
    """
    now = timezone.now()
    today = date.today()
    create_pre_authorization(
        host_id=1,
        visitor_email="wf4@preauth.com",
        valid_from=today - timedelta(days=1),
        valid_to=today + timedelta(days=15),
        visitor_name="WF4 Guest",
    )
    vr = pre_register_visit(
        name="WF4 Guest",
        email="wf4@preauth.com",
        phone="+919876541004",
        id_document_type="AADHAAR",
        id_document_number="WF04004PRE",
        host_id=1,
        purpose="Preauth delivery",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    assert vr.status == "APPROVED"
    assert vr.digital_pass is not None


def test_wf_005_bw_vms_05_vip_visit():
    """
    test_id: WF-005
    source_id: BW-VMS-05 end-to-end-path
    """
    now = timezone.now()
    Visitor.objects.create(
        name="WF5 VIP",
        email="wf5@vip.gov",
        phone="+919876541005",
        id_document_type="PASSPORT",
        id_document_number="WF05005VIP",
        is_vip=True,
    )
    vr = pre_register_visit(
        name="WF5 VIP",
        email="wf5@vip.gov",
        phone="+919876541005",
        id_document_type="PASSPORT",
        id_document_number="WF05005VIP",
        host_id=1,
        purpose="VIP Dignitary",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=6),
    )
    assert vr.status == "APPROVED"
    assert vr.pass_type == "VIP"


def test_wf_006_bw_vms_06_walkin_host_approved_visit():
    """
    test_id: WF-006
    source_id: BW-VMS-06 end-to-end-path
    """
    vr = walk_in_register(
        name="WF6 Walkin",
        email="wf6@walkin.com",
        phone="+919876541006",
        host_id=1,
        purpose="In person inquiry",
        id_document_type="AADHAAR",
        id_document_number="WF06006WLK",
        auto_approve=False,
    )
    assert vr.status == "PENDING_APPROVAL"
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"
    check_out_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"


def test_wf_007_bw_vms_07_walkin_contingency_approved_visit():
    """
    test_id: WF-007
    source_id: BW-VMS-07 end-to-end-path
    """
    vr = walk_in_register(
        name="WF7 Walkin",
        email="wf7@contingency.com",
        phone="+919876541007",
        host_id=1,
        purpose="Contingency inquiry",
        id_document_type="AADHAAR",
        id_document_number="WF07007CTG",
        auto_approve=False,
    )
    contingency_approve(vr.id, admin_id=1, reason="Host uncontactable by security")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_wf_008_bw_vms_08_walkin_host_rejected_visit():
    """
    test_id: WF-008
    source_id: BW-VMS-08 end-to-end-path
    """
    vr = walk_in_register(
        name="WF8 Walkin",
        email="wf8@reject.com",
        phone="+919876541008",
        host_id=1,
        purpose="Rejected inquiry",
        id_document_type="AADHAAR",
        id_document_number="WF08008REJ",
        auto_approve=False,
    )
    decide_visit_request(vr.id, host_id=1, decision="REJECT", reason="Not available today")
    vr.refresh_from_db()
    assert vr.status == "REJECTED"


def test_wf_009_bw_vms_09_gate_validation_denied():
    """
    test_id: WF-009
    source_id: BW-VMS-09 end-to-end-path
    """
    is_valid, msg, _ = validate_pass_at_gate("VMS-NON-EXISTENT-TOKEN", "Main Gate")
    assert is_valid is False
    assert "Invalid or tampered" in msg


def test_wf_010_bw_vms_10_gate_denial_with_authorized_override():
    """
    test_id: WF-010
    source_id: BW-VMS-10 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF10 Override",
        email="wf10@override.com",
        phone="+919876541010",
        id_document_type="AADHAAR",
        id_document_number="WF10010OVR",
        host_id=1,
        purpose="Override Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    manual_gate_override(
        vr.digital_pass.id, admin_id=1, reason="Pass QR unreadable; physical ID verified"
    )
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_wf_011_bw_vms_11_offline_gate_entry_and_reconciliation():
    """
    test_id: WF-011
    source_id: BW-VMS-11 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF11 Offline",
        email="wf11@offline.com",
        phone="+919876541011",
        id_document_type="AADHAAR",
        id_document_number="WF11011OFF",
        host_id=1,
        purpose="Offline Sync Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    events = [
        {"pass_id": vr.digital_pass.id, "gate_name": "Gate 3 Offline", "timestamp": now.isoformat()}
    ]
    res = offline_batch_sync(events)
    assert res["synced"] == 1
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_wf_012_bw_vms_12_zone_access_granted():
    """
    test_id: WF-012
    source_id: BW-VMS-12 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF12 Zone",
        email="wf12@zone.com",
        phone="+919876541012",
        id_document_type="AADHAAR",
        id_document_number="WF12012ZON",
        host_id=1,
        purpose="Zone Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Research Lab"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    allowed, _ = validate_zone_access(vr.digital_pass.id, "Research Lab")
    assert allowed is True


def test_wf_013_bw_vms_13_zone_access_denied_and_alert_handled():
    """
    test_id: WF-013
    source_id: BW-VMS-13 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF13 Zone Denied",
        email="wf13@zone.com",
        phone="+919876541013",
        id_document_type="AADHAAR",
        id_document_number="WF13013DEN",
        host_id=1,
        purpose="Zone Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Cafeteria"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    allowed, msg = validate_zone_access(vr.digital_pass.id, "Data Center")
    assert allowed is False
    assert "not authorized" in msg or "violation" in msg


def test_wf_014_bw_vms_14_temporary_zone_elevation_and_one_revalidation():
    """
    test_id: WF-014
    source_id: BW-VMS-14 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF14 Elevate",
        email="wf14@elevate.com",
        phone="+919876541014",
        id_document_type="AADHAAR",
        id_document_number="WF14014ELV",
        host_id=1,
        purpose="Elevate Tour",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["General"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    allowed1, _ = validate_zone_access(vr.digital_pass.id, "Server Room")
    assert allowed1 is False
    grant_zone_elevation(vr.digital_pass.id, "Server Room", hours=2, admin_id=1, reason="Maintenance")
    allowed2, _ = validate_zone_access(vr.digital_pass.id, "Server Room")
    assert allowed2 is True


def test_wf_015_bw_vms_15_host_terminates_pass_before_checkin():
    """
    test_id: WF-015
    source_id: BW-VMS-15 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF15 PreTerm",
        email="wf15@term.com",
        phone="+919876541015",
        id_document_type="AADHAAR",
        id_document_number="WF15015PRT",
        host_id=1,
        purpose="Pre Term",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    terminate_visit(vr.id, operator_id=1, reason="Meeting cancelled by host")
    vr.refresh_from_db()
    assert vr.status == "TERMINATED_EARLY"
    assert vr.digital_pass.status == "REVOKED"


def test_wf_016_bw_vms_16_host_terminates_onsite_visit():
    """
    test_id: WF-016
    source_id: BW-VMS-16 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF16 OnsiteTerm",
        email="wf16@term.com",
        phone="+919876541016",
        id_document_type="AADHAAR",
        id_document_number="WF16016OST",
        host_id=1,
        purpose="Onsite Term",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    terminate_visit(vr.id, operator_id=1, reason="Host emergency departure")
    vr.refresh_from_db()
    assert vr.status == "TERMINATED_EARLY"
    assert vr.digital_pass.status == "REVOKED"


def test_wf_017_bw_vms_17_admin_terminates_pass_before_checkin():
    """
    test_id: WF-017
    source_id: BW-VMS-17 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF17 AdminPreTerm",
        email="wf17@term.com",
        phone="+919876541017",
        id_document_type="AADHAAR",
        id_document_number="WF17017APT",
        host_id=1,
        purpose="Admin Pre Term",
        scheduled_start=now + timedelta(hours=3),
        scheduled_end=now + timedelta(hours=5),
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    terminate_visit(vr.id, operator_id=99, reason="Security administrative order")
    vr.refresh_from_db()
    assert vr.status == "TERMINATED_EARLY"


def test_wf_018_bw_vms_18_admin_terminates_onsite_visit():
    """
    test_id: WF-018
    source_id: BW-VMS-18 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF18 AdminOnsiteTerm",
        email="wf18@term.com",
        phone="+919876541018",
        id_document_type="AADHAAR",
        id_document_number="WF18018AOT",
        host_id=1,
        purpose="Admin Onsite Term",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    terminate_visit(vr.id, operator_id=99, reason="Campus protocol violation")
    vr.refresh_from_db()
    assert vr.status == "TERMINATED_EARLY"


def test_wf_019_bw_vms_19_admin_triggered_emergency_muster():
    """
    test_id: WF-019
    source_id: BW-VMS-19 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF19 Evac",
        email="wf19@evac.com",
        phone="+919876541019",
        id_document_type="AADHAAR",
        id_document_number="WF19019EVC",
        host_id=1,
        purpose="Evac Session",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    muster_id = trigger_emergency_muster(initiated_by_id=1, assembly_point="Ground 1")
    assert EmergencyMusterRoster.objects.filter(muster_id=muster_id).exists()


def test_wf_020_bw_vms_20_security_triggered_emergency_muster():
    """
    test_id: WF-020
    source_id: BW-VMS-20 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF20 Evac",
        email="wf20@evac.com",
        phone="+919876541020",
        id_document_type="AADHAAR",
        id_document_number="WF20020EVC",
        host_id=1,
        purpose="Security Evac Session",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    muster_id = trigger_emergency_muster(initiated_by_id=2, assembly_point="Assembly B")
    item = EmergencyMusterRoster.objects.filter(muster_id=muster_id, visitor=vr.visitor).first()
    assert item is not None
    record_roll_call(item.id, accounted_by_id=2, status="ACCOUNTED")
    item.refresh_from_db()
    assert item.accountability_status == "ACCOUNTED"


def test_wf_021_bw_vms_21_bulk_event_visitor_entry():
    """
    test_id: WF-021
    source_id: BW-VMS-21 end-to-end-path
    """
    now = timezone.now()
    data = [
        {
            "name": "Event Attendee 1",
            "email": "att1@event.org",
            "phone": "+919876541021",
            "id_document_type": "AADHAAR",
            "id_document_number": "WF21021ATT1",
        }
    ]
    created = bulk_register_visitors(
        records=data,
        host_id=1,
        purpose="Symposium",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=4),
        external_event_ref="SYM-2026",
    )
    assert len(created) == 1
    vr = created[0]
    assert vr.external_event_ref == "SYM-2026"
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    assert vr.digital_pass is not None


def test_wf_022_bw_vms_22_same_day_urgent_preregistration():
    """
    test_id: WF-022
    source_id: BW-VMS-22 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF22 Urgent",
        email="wf22@urgent.com",
        phone="+919876541022",
        id_document_type="AADHAAR",
        id_document_number="WF22022URG",
        host_id=1,
        purpose="Same day urgent delivery",
        scheduled_start=now + timedelta(minutes=30),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    assert vr.id is not None
    assert vr.is_urgent_exception is True


def test_wf_023_bw_vms_23_admin_approved_visit_extension():
    """
    test_id: WF-023
    source_id: BW-VMS-23 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="WF23 Ext",
        email="wf23@ext.com",
        phone="+919876541023",
        id_document_type="AADHAAR",
        id_document_number="WF23023EXT",
        host_id=1,
        purpose="Extension workflow",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=1),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    extended = extend_visit(vr.id, hours=2, operator_id=1, reason="Meeting prolonged")
    assert extended.extension_hours == 2


def test_wf_024_cw_vms_01_pre_registered_visit_lifecycle():
    """
    test_id: WF-024
    source_id: CW-VMS-01 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="CW1 Full Journey",
        email="cw1@full.com",
        phone="+919876541024",
        id_document_type="AADHAAR",
        id_document_number="CW01024FUL",
        host_id=1,
        purpose="Complete lifecycle",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    assert vr.status == "PENDING_APPROVAL"
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"
    check_out_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"


def test_wf_025_cw_vms_02_walkin_visit_lifecycle():
    """
    test_id: WF-025
    source_id: CW-VMS-02 end-to-end-path
    """
    vr = walk_in_register(
        name="CW2 Walkin Journey",
        email="cw2@walkin.com",
        phone="+919876541025",
        host_id=1,
        purpose="Walkin lifecycle",
        id_document_type="AADHAAR",
        id_document_number="CW02025WLK",
        auto_approve=True,
    )
    assert vr.status == "APPROVED"
    assert vr.digital_pass is not None
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"
    check_out_visitor(vr.digital_pass.id, "Main Gate")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_OUT"


def test_wf_026_cw_vms_03_gate_entry_validation_and_exception_handling():
    """
    test_id: WF-026
    source_id: CW-VMS-03 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="CW3 Gate Journey",
        email="cw3@gate.com",
        phone="+919876541026",
        id_document_type="AADHAAR",
        id_document_number="CW03026GTE",
        host_id=1,
        purpose="Gate lifecycle",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    manual_gate_override(vr.digital_pass.id, admin_id=1, reason="Pass damaged")
    vr.refresh_from_db()
    assert vr.status == "CHECKED_IN"


def test_wf_027_cw_vms_04_zone_access_and_elevation():
    """
    test_id: WF-027
    source_id: CW-VMS-04 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="CW4 Zone Journey",
        email="cw4@zone.com",
        phone="+919876541027",
        id_document_type="AADHAAR",
        id_document_number="CW04027ZON",
        host_id=1,
        purpose="Zone lifecycle",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        access_zones=["Auditorium"],
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    allowed, _ = validate_zone_access(vr.digital_pass.id, "Auditorium")
    assert allowed is True
    denied, _ = validate_zone_access(vr.digital_pass.id, "VIP Lounge")
    assert denied is False
    grant_zone_elevation(vr.digital_pass.id, "VIP Lounge", hours=2, admin_id=1, reason="Speaker invite")
    elevated, _ = validate_zone_access(vr.digital_pass.id, "VIP Lounge")
    assert elevated is True


def test_wf_028_cw_vms_05_early_termination_and_extension():
    """
    test_id: WF-028
    source_id: CW-VMS-05 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="CW5 Term Journey",
        email="cw5@term.com",
        phone="+919876541028",
        id_document_type="AADHAAR",
        id_document_number="CW05028TRM",
        host_id=1,
        purpose="Term lifecycle",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=1),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    extend_visit(vr.id, hours=1, operator_id=1, reason="Overrun")
    vr.refresh_from_db()
    assert vr.extension_hours == 1
    terminate_visit(vr.id, operator_id=1, reason="Cancelled early")
    vr.refresh_from_db()
    assert vr.status == "TERMINATED_EARLY"


def test_wf_029_cw_vms_06_emergency_muster_and_accountability():
    """
    test_id: WF-029
    source_id: CW-VMS-06 end-to-end-path
    """
    now = timezone.now()
    vr = pre_register_visit(
        name="CW6 Muster Journey",
        email="cw6@muster.com",
        phone="+919876541029",
        id_document_type="AADHAAR",
        id_document_number="CW06029MST",
        host_id=1,
        purpose="Muster lifecycle",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=2),
        is_urgent_exception=True,
    )
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    check_in_visitor(vr.digital_pass.id, "Main Gate")
    muster_id = trigger_emergency_muster(initiated_by_id=1, assembly_point="Ground CW")
    item = EmergencyMusterRoster.objects.filter(muster_id=muster_id, visitor=vr.visitor).first()
    assert item is not None
    record_roll_call(item.id, accounted_by_id=1, status="ACCOUNTED")
    item.refresh_from_db()
    assert item.accountability_status == "ACCOUNTED"


def test_wf_030_cw_vms_07_bulk_event_visitor_handling():
    """
    test_id: WF-030
    source_id: CW-VMS-07 end-to-end-path
    """
    now = timezone.now()
    data = [
        {
            "name": "CW7 Attendee",
            "email": "cw7@event.org",
            "phone": "+919876541030",
            "id_document_type": "AADHAAR",
            "id_document_number": "CW07030ATT",
        }
    ]
    created = bulk_register_visitors(
        records=data,
        host_id=1,
        purpose="Grand Symposium",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(hours=4),
        external_event_ref="GRAND-2026",
    )
    assert len(created) == 1
    vr = created[0]
    decide_visit_request(vr.id, host_id=1, decision="APPROVE")
    vr.refresh_from_db()
    assert vr.status == "APPROVED"
    assert vr.digital_pass is not None
