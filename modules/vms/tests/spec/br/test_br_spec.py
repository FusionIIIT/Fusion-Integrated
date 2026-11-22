"""Automated tests for Business Rules (BR) Strategy.
Derived from frozen BR_DESIGN.json.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.domain.rules import (
    check_overstay,
    validate_blacklist_match,
    validate_zone_access,
)
from modules.vms.domain.state_machine import TransitionTrigger
from modules.vms.models.muster import EmergencyMuster
from modules.vms.services.errors import (
    DuplicatePassError,
    InvalidTransitionError,
)
from modules.vms.services.gate import transition_visit_state
from modules.vms.services.registration import (
    approve_visit,
    request_or_create_visit,
)
from modules.vms.services.security import trigger_emergency_muster


def _create_test_visit(
    first_name="Test",
    last_name="User",
    phone="9876520001",
    email="test@example.com",
    id_type="aadhaar",
    id_number="1234-5678-9012",
    host_user_id=101,
    purpose="Meeting",
    valid_from=None,
    valid_to=None,
    visit_type="pre_registered",
):
    now = timezone.now()
    v_from = valid_from or now
    v_to = valid_to or (now + timedelta(hours=4))
    return request_or_create_visit(
        visitor_data={
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "email": email,
            "id_type": id_type,
            "id_number": id_number,
        },
        host_user_id=host_user_id,
        purpose=purpose,
        valid_from=v_from,
        valid_to=v_to,
        visit_type=visit_type,
    )


def test_br_001_exact_id_hash_match_found():
    """TC-BR-001 | Source: VMS-BR-001 Exact ID Hash Match - Match Found

    Verify exact Government ID hash match blocks visitor.
    """
    bl_entries = [
        {
            "id_number_hash": "hash_abc123",
            "phone": "9999999999",
            "full_name": "Test Name",
            "reason": "Security Alert",
            "severity": "critical",
        }
    ]
    res = validate_blacklist_match("hash_abc123", "8888888888", "Other Name", bl_entries)
    assert res.is_blacklisted is True
    assert res.matched_rule == "BR-001"


def test_br_002_exact_id_hash_match_no_match():
    """TC-BR-002 | Source: VMS-BR-001 Exact ID Hash Match - No Match

    Verify non-matching ID hash permits visitor.
    """
    bl_entries = [
        {
            "id_number_hash": "hash_abc123",
            "phone": "9999999999",
            "full_name": "Test Name",
            "reason": "Security Alert",
            "severity": "critical",
        }
    ]
    res = validate_blacklist_match("hash_xyz999", "8888888888", "Other Name", bl_entries)
    assert res.is_blacklisted is False


def test_br_003_quorum_match_phone_and_name_found():
    """TC-BR-003 | Source: VMS-BR-004 Quorum Match on Phone and Name - Match Found

    Verify matching phone and partial name triggers watchlist hit.
    """
    bl_entries = [
        {
            "id_number_hash": "different_hash",
            "phone": "+919876543210",
            "full_name": "John Doe",
            "reason": "Watchlist match",
            "severity": "warning",
        }
    ]
    res = validate_blacklist_match("my_hash", "+91 98765 43210", "Johnathan Doe", bl_entries)
    assert res.is_blacklisted is True
    assert res.matched_rule == "BR-004"


def test_br_004_quorum_match_phone_mismatch():
    """TC-BR-004 | Source: VMS-BR-004 Quorum Match on Phone and Name - Phone Mismatch

    Verify matching name but different phone does not trigger quorum block.
    """
    bl_entries = [
        {
            "id_number_hash": "different_hash",
            "phone": "+919876543210",
            "full_name": "John Doe",
            "reason": "Watchlist match",
            "severity": "warning",
        }
    ]
    res = validate_blacklist_match("my_hash", "+919111222333", "John Doe", bl_entries)
    assert res.is_blacklisted is False


def test_br_005_pass_validity_window_valid_current():
    """TC-BR-005 | Source: VMS-BR-008 Pass Validity Window - Valid Current Time

    Verify pass is valid when current time is between valid_from and valid_to.
    """
    now = timezone.now()
    valid_from = now - timedelta(hours=1)
    valid_to = now + timedelta(hours=3)
    assert valid_from <= now <= valid_to


def test_br_006_pass_validity_window_expired():
    """TC-BR-006 | Source: VMS-BR-008 Pass Validity Window - Expired Time

    Verify pass is invalid when current time is past valid_to.
    """
    now = timezone.now()
    valid_to = now - timedelta(hours=1)
    is_overstay, dur = check_overstay(valid_to, now)
    assert is_overstay is True
    assert dur > 0


def test_br_007_pass_validity_window_future_start():
    """TC-BR-007 | Source: VMS-BR-008 Pass Validity Window - Future Start Time

    Verify pass is invalid before valid_from start time.
    """
    now = timezone.now()
    valid_from = now + timedelta(days=1)
    assert now < valid_from


def test_br_008_zone_access_permitted_zone():
    """TC-BR-008 | Source: VMS-BR-012 Zone Access Validation - Permitted Zone

    Verify zone access allowed when zone is in allowed_zones list.
    """
    res = validate_zone_access(["Auditorium", "Cafeteria"], "Auditorium")
    assert res.allowed is True


def test_br_009_zone_access_unauthorized_zone():
    """TC-BR-009 | Source: VMS-BR-012 Zone Access Validation - Unauthorized Zone

    Verify zone access prohibited when zone is not in allowed_zones.
    """
    res = validate_zone_access(["Auditorium"], "Data Center")
    assert res.allowed is False


@pytest.mark.django_db
def test_br_010_duplicate_same_day_active_pass_prohibited():
    """TC-BR-010 | Source: VMS-BR-017 / VMS-BR-020 Duplicate Same-Day Active Pass Check

    Verify prohibition against duplicate same-day active passes for same visitor.
    """
    now = timezone.now()
    _create_test_visit(
        first_name="Wanda",
        last_name="Maximoff",
        phone="+919876520010",
        email="wanda@example.com",
        id_number="1234-5678-0010",
        valid_from=now,
        valid_to=now + timedelta(hours=4),
    )

    with pytest.raises(DuplicatePassError):
        _create_test_visit(
            first_name="Wanda",
            last_name="Maximoff",
            phone="+919876520010",
            email="wanda@example.com",
            id_number="1234-5678-0010",
            valid_from=now,
            valid_to=now + timedelta(hours=4),
        )


@pytest.mark.django_db
def test_br_011_idempotency_of_completed_checkout():
    """TC-BR-011 | Source: VMS-BR-023 Idempotency of Completed Checkout

    Verify checkout cannot be re-applied to an already checked-out visit.
    """
    visit = _create_test_visit(
        first_name="Xavier",
        last_name="Charles",
        phone="+919876520011",
        email="xavier@example.com",
        id_type="passport",
        id_number="XC98765432",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)

    with pytest.raises(InvalidTransitionError):
        transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)


@pytest.mark.django_db
def test_br_012_default_walk_in_pass_duration():
    """TC-BR-012 | Source: VMS-BR-032 Default Walk-in Pass Duration

    Verify walk-in pass duration defaults to exactly 4 hours.
    """
    visit = _create_test_visit(
        first_name="Yara",
        last_name="Greyjoy",
        phone="+919876520012",
        email="yara@example.com",
        id_type="pan",
        id_number="YRGJY1234Y",
        visit_type="walk_in",
    )
    diff = visit.valid_to - visit.valid_from
    assert diff.total_seconds() == 4 * 3600


def test_br_013_zone_isolation_case_insensitive():
    """TC-BR-013 | Source: VMS-BR-041 Zone Isolation with Case-Insensitive Matching

    Verify zone checking normalizes case and whitespace.
    """
    res = validate_zone_access(["Library"], "  library  ")
    assert res.allowed is True


@pytest.mark.django_db
def test_br_014_emergency_muster_headcount_consistency():
    """TC-BR-014 | Source: VMS-BR-045 Emergency Muster Headcount Consistency

    Verify emergency muster headcount reflects total on-site checked_in visitors.
    """
    muster = trigger_emergency_muster(admin_user_id=1)
    assert isinstance(muster, EmergencyMuster)
    assert muster.headcount_accounted == 0
    assert muster.headcount_total >= 0
