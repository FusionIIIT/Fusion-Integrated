"""VMS End-to-End Backend Journey Tests.
Covers BW-VMS-01 (Pre-registered Approved Visit) and BW-VMS-06 (Walk-in Visit).
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models.access import GateLog
from modules.vms.services.gate import execute_check_out, verify_qr_and_check_in
from modules.vms.services.registration import approve_visit, reject_visit, request_or_create_visit

pytestmark = pytest.mark.django_db


def test_complete_preregistered_journey_bw_vms_01():
    """BW-VMS-01: Pre-registration -> Host Approval -> Gate Check-in -> Gate Check-out."""
    now = timezone.now()
    # 1. Visitor requests visit
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Arun",
            "last_name": "Joshi",
            "phone": "9555111222",
            "email": "arun@example.com",
            "id_type": "aadhaar",
            "id_number": "991188227733",
        },
        host_user_id=105,
        purpose="Ph.D. Defense Guest",
        valid_from=now - timedelta(minutes=5),
        valid_to=now + timedelta(hours=4),
        allowed_zones=["MAIN_GATE", "CSE_DEPT"],
    )
    assert visit.status == "requested"

    # 2. Host approves visit
    approved = approve_visit(visit.id, host_user_id=105)
    assert approved.status == "approved"

    # 3. Security checks in visitor at Main Gate
    checked_in = verify_qr_and_check_in(
        visit.qr_code_hash, guard_user_id=201, gate_name="Main Gate"
    )
    assert checked_in.status == "on_site"
    assert GateLog.objects.filter(visit=visit, action="check_in").exists()

    # 4. Security checks out visitor upon departure
    completed = execute_check_out(visit.id, guard_user_id=201, gate_name="Main Gate")
    assert completed.status == "completed"
    assert GateLog.objects.filter(visit=visit, action="check_out").exists()


def test_rejected_visit_journey_bw_vms_02():
    """BW-VMS-02: Pre-registration -> Host Rejection (Terminal)."""
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Suresh",
            "last_name": "Nair",
            "phone": "9555333444",
            "email": "suresh@example.com",
            "id_type": "aadhaar",
            "id_number": "882277336644",
        },
        host_user_id=105,
        purpose="Unscheduled Visit",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )
    rejected = reject_visit(visit.id, host_user_id=105, reason="Host unavailable on campus")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Host unavailable on campus"


def test_walk_in_journey_bw_vms_06():
    """BW-VMS-06: Walk-in visitor registered by security with immediate approval and check-in."""
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Kishore",
            "last_name": "Reddy",
            "phone": "9666777888",
            "email": "kishore@example.com",
            "id_type": "aadhaar",
            "id_number": "114477002255",
        },
        host_user_id=105,
        purpose="Document Delivery",
        valid_from=now,
        valid_to=now + timedelta(hours=4),
        visit_type="walk_in",
    )
    assert visit.status == "approved"
    checked_in = verify_qr_and_check_in(visit.qr_code_hash, guard_user_id=201)
    assert checked_in.status == "on_site"
