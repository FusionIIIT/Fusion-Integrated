"""VMS Services Integration Tests.
Tests business rules, state transitions, gate actions, and security operations.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models.access import GateAlert
from modules.vms.services.errors import (
    BlacklistMatchError,
    DuplicatePassError,
    InvalidTransitionError,
    UnauthorizedZoneError,
)
from modules.vms.services.gate import (
    execute_check_out,
    verify_qr_and_check_in,
    verify_zone_access,
)
from modules.vms.services.registration import (
    approve_visit,
    reject_visit,
    request_or_create_visit,
)
from modules.vms.services.security import (
    add_to_blacklist,
    resolve_emergency_muster,
    trigger_emergency_muster,
)

pytestmark = pytest.mark.django_db


def test_request_visit_success():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Kavita",
            "last_name": "Singh",
            "phone": "9811122233",
            "email": "kavita@example.com",
            "id_type": "aadhaar",
            "id_number": "112233445566",
        },
        host_user_id=10,
        purpose="Guest Lecture",
        valid_from=now + timedelta(hours=1),
        valid_to=now + timedelta(hours=5),
        allowed_zones=["MAIN_GATE", "SEMINAR_HALL"],
    )
    assert visit.id is not None
    assert visit.status == "requested"
    assert visit.pass_number.startswith("PASS-")
    assert visit.qr_code_hash is not None


def test_blacklist_blocks_visit_request():
    """Rule BR-004: Blacklisted visitor cannot request pass."""
    add_to_blacklist(
        id_type="aadhaar",
        id_number="999900001111",
        full_name="Banned Person",
        phone="9999888877",
        reason="Campus disciplinary action",
    )
    now = timezone.now()
    with pytest.raises(BlacklistMatchError):
        request_or_create_visit(
            visitor_data={
                "first_name": "Banned",
                "last_name": "Person",
                "phone": "9999888877",
                "email": "banned@example.com",
                "id_type": "aadhaar",
                "id_number": "999900001111",
            },
            host_user_id=10,
            purpose="Meeting",
            valid_from=now,
            valid_to=now + timedelta(hours=2),
        )


def test_duplicate_same_day_pass_refusal():
    """Rule BR-017 & BR-020: Duplicate same-day pass refused."""
    now = timezone.now()
    v_data = {
        "first_name": "Pooja",
        "last_name": "Gupta",
        "phone": "9876500001",
        "email": "pooja@example.com",
        "id_type": "aadhaar",
        "id_number": "555566667777",
    }
    # First pass
    request_or_create_visit(
        visitor_data=v_data,
        host_user_id=12,
        purpose="Interview",
        valid_from=now,
        valid_to=now + timedelta(hours=3),
    )
    # Second pass on the same day raises DuplicatePassError
    with pytest.raises(DuplicatePassError):
        request_or_create_visit(
            visitor_data=v_data,
            host_user_id=14,
            purpose="Lab Visit",
            valid_from=now,
            valid_to=now + timedelta(hours=4),
        )


def test_host_approval_and_rejection():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Alok",
            "last_name": "Mishra",
            "phone": "9111222333",
            "email": "alok@example.com",
            "id_type": "aadhaar",
            "id_number": "777788889999",
        },
        host_user_id=20,
        purpose="Academic Consultation",
        valid_from=now,
        valid_to=now + timedelta(hours=4),
    )
    assert visit.status == "requested"

    # Host approves
    approved = approve_visit(visit.id, host_user_id=20)
    assert approved.status == "approved"

    # Cannot reject after approval
    with pytest.raises(InvalidTransitionError):
        reject_visit(visit.id, host_user_id=20, reason="Too late")


def test_gate_check_in_and_check_out():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Geeta",
            "last_name": "Sen",
            "phone": "9222333444",
            "email": "geeta@example.com",
            "id_type": "aadhaar",
            "id_number": "333344445555",
        },
        host_user_id=25,
        purpose="Library Access",
        valid_from=now - timedelta(minutes=5),
        valid_to=now + timedelta(hours=3),
    )
    approve_visit(visit.id, host_user_id=25)

    # Gate check in
    checked_in = verify_qr_and_check_in(visit.qr_code_hash, guard_user_id=101)
    assert checked_in.status == "on_site"
    assert checked_in.check_in_time is not None

    # Gate check out
    checked_out = execute_check_out(visit.id, guard_user_id=101)
    assert checked_out.status == "completed"
    assert checked_out.check_out_time is not None

    # Rule BR-023: No duplicate checkout
    with pytest.raises(InvalidTransitionError):
        execute_check_out(visit.id, guard_user_id=101)


def test_zone_access_verification():
    """Rule BR-041: Zone access authorization and alert logging."""
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Naveen",
            "last_name": "Kumar",
            "phone": "9333444555",
            "email": "naveen@example.com",
            "id_type": "aadhaar",
            "id_number": "111100002222",
        },
        host_user_id=30,
        purpose="Facility Visit",
        valid_from=now - timedelta(minutes=10),
        valid_to=now + timedelta(hours=2),
        allowed_zones=["MAIN_GATE", "CAFETERIA"],
    )
    approve_visit(visit.id, host_user_id=30)
    verify_qr_and_check_in(visit.qr_code_hash, guard_user_id=101)

    # Allowed zone
    assert verify_zone_access(visit.id, "CAFETERIA", guard_user_id=101) is True

    # Unauthorized zone raises and logs alert
    with pytest.raises(UnauthorizedZoneError):
        verify_zone_access(visit.id, "RESTRICTED_LAB", guard_user_id=101)
    assert GateAlert.objects.filter(alert_type="zone_violation", visit_id=visit.id).exists()


def test_emergency_muster_workflow():
    now = timezone.now()
    visit = request_or_create_visit(
        visitor_data={
            "first_name": "Tanya",
            "last_name": "Chopra",
            "phone": "9444555666",
            "email": "tanya@example.com",
            "id_type": "aadhaar",
            "id_number": "444455556666",
        },
        host_user_id=40,
        purpose="Project Demo",
        valid_from=now - timedelta(minutes=10),
        valid_to=now + timedelta(hours=3),
    )
    approve_visit(visit.id, host_user_id=40)
    verify_qr_and_check_in(visit.qr_code_hash, guard_user_id=101)

    muster = trigger_emergency_muster(admin_user_id=1)
    assert muster.headcount_total >= 1
    assert muster.status == "active"

    resolved = resolve_emergency_muster(muster.id, admin_user_id=1)
    assert resolved.status == "resolved"
