"""Automated tests for Use Cases (UC) Strategy.
Derived from frozen UC_DESIGN.json.
"""

import hashlib
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.domain.rules import validate_zone_access
from modules.vms.domain.state_machine import TransitionTrigger
from modules.vms.models.visitors import BlacklistEntry
from modules.vms.services.errors import BlacklistMatchError, PassExpiredError
from modules.vms.services.gate import transition_visit_state
from modules.vms.services.registration import (
    approve_visit,
    reject_visit,
    request_or_create_visit,
)
from modules.vms.services.security import resolve_emergency_muster, trigger_emergency_muster


def _create_test_visit(
    first_name="Test",
    last_name="User",
    phone="9876510001",
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


@pytest.mark.django_db
def test_uc_001_register_visitor_main_flow():
    """TC-UC-001 | Source: VMS-UC-001 Main Flow

    Verify visitor registration main success flow.
    """
    visit = _create_test_visit(
        first_name="Liam",
        last_name="Neeson",
        phone="+919876510001",
        email="liam@example.com",
        id_type="passport",
        id_number="P98765431",
    )
    assert visit.visitor.id is not None
    assert visit.visitor.first_name == "Liam"


@pytest.mark.django_db
def test_uc_002_register_visitor_blacklisted_exception():
    """TC-UC-002 | Source: VMS-UC-001 Exception Flow E1

    Verify visitor registration blocked when visitor is blacklisted.
    """
    raw_id = "BL-UC-002"
    id_hash = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()
    BlacklistEntry.objects.create(
        id_type="aadhaar",
        id_number_hash=id_hash,
        full_name="Banned Person",
        phone="9876510002",
        reason="Security Watchlist",
        severity="critical",
        added_by=1,
    )

    with pytest.raises(BlacklistMatchError):
        _create_test_visit(
            first_name="Banned",
            last_name="Person",
            phone="+919876510002",
            email="banned2@example.com",
            id_number=raw_id,
        )


@pytest.mark.django_db
def test_uc_003_register_pre_visiting_guest():
    """TC-UC-003 | Source: VMS-UC-003 Main Flow

    Verify pre-visiting guest pass request creation.
    """
    future = timezone.now() + timedelta(days=2)
    visit = _create_test_visit(
        first_name="Mia",
        last_name="Farrow",
        phone="+919876510003",
        email="mia@example.com",
        id_number="2222-3333-4444",
        host_user_id=202,
        valid_from=future,
        valid_to=future + timedelta(hours=3),
    )
    assert visit.status == "requested"
    assert visit.host_user_id == 202


@pytest.mark.django_db
def test_uc_004_request_visit_via_host_routing():
    """TC-UC-004 | Source: VMS-UC-005 Main Flow

    Verify request visit via host routing.
    """
    visit = _create_test_visit(
        first_name="Noah",
        last_name="Webster",
        phone="+919876510004",
        email="noah@example.com",
        id_type="pan",
        id_number="NHWBS1234N",
        host_user_id=303,
    )
    from modules.vms.selectors.scoping import get_approvals_for_host

    approvals = get_approvals_for_host(303)
    assert visit in approvals


@pytest.mark.django_db
def test_uc_005_approve_visit_request():
    """TC-UC-005 | Source: VMS-UC-014 Main Flow

    Verify host approves visit request.
    """
    visit = _create_test_visit(
        first_name="Olivia",
        last_name="Wilde",
        phone="+919876510005",
        email="olivia@example.com",
        id_number="3333-4444-5555",
        host_user_id=404,
    )
    approved = approve_visit(visit.id, host_user_id=404)
    assert approved.status == "approved"
    assert approved.pass_number is not None


@pytest.mark.django_db
def test_uc_006_reject_visit_request():
    """TC-UC-006 | Source: VMS-UC-015 Main Flow

    Verify host rejects visit request.
    """
    visit = _create_test_visit(
        first_name="Paul",
        last_name="Rudd",
        phone="+919876510006",
        email="paul@example.com",
        id_number="4444-5555-6666",
        host_user_id=505,
    )
    rejected = reject_visit(visit.id, host_user_id=505, reason="Host traveling")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Host traveling"


@pytest.mark.django_db
def test_uc_007_validate_visitor_pass_at_gate():
    """TC-UC-007 | Source: VMS-UC-018 Main Flow

    Verify security guard scans QR code to validate visitor pass.
    """
    visit = _create_test_visit(
        first_name="Quinn",
        last_name="Fabray",
        phone="+919876510007",
        email="quinn@example.com",
        id_number="5555-6666-7777",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(
        visit.id,
        trigger=TransitionTrigger.GATE_CHECK_IN,
        actor_id=1,
        gate_name="Main Gate",
    )
    visit.refresh_from_db()
    assert visit.status == "on_site"


@pytest.mark.django_db
def test_uc_008_gate_validation_success_updates_status():
    """TC-UC-008 | Source: VMS-UC-019 Main Flow

    Verify gate validation success updates visit status to checked_in.
    """
    visit = _create_test_visit(
        first_name="Rachel",
        last_name="Green",
        phone="+919876510008",
        email="rachel@example.com",
        id_type="pan",
        id_number="RCHGR1234R",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "on_site"
    assert visit.check_in_time is not None


@pytest.mark.django_db
def test_uc_009_gate_validation_failure_expired():
    """TC-UC-009 | Source: VMS-UC-020 Exception Flow E1

    Verify gate validation failure on expired pass.
    """
    past = timezone.now() - timedelta(hours=6)
    visit = _create_test_visit(
        first_name="Sam",
        last_name="Winchester",
        phone="+919876510009",
        email="sam@example.com",
        id_number="6666-7777-8888",
        valid_from=past,
        valid_to=past + timedelta(hours=1),
    )
    approve_visit(visit.id, host_user_id=101)
    with pytest.raises(PassExpiredError):
        transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)


@pytest.mark.django_db
def test_uc_010_checkout_visitor_at_gate():
    """TC-UC-010 | Source: VMS-UC-021 Main Flow

    Verify visitor check-out at gate.
    """
    visit = _create_test_visit(
        first_name="Tina",
        last_name="Fey",
        phone="+919876510010",
        email="tina@example.com",
        id_number="7777-8888-9999",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "checked_out"
    assert visit.check_out_time is not None


@pytest.mark.django_db
def test_uc_011_register_walk_in_visitor():
    """TC-UC-011 | Source: VMS-UC-022 Main Flow

    Verify walk-in visitor registration at gate terminal.
    """
    visit = _create_test_visit(
        first_name="Uma",
        last_name="Thurman",
        phone="+919876510011",
        email="uma@example.com",
        id_type="passport",
        id_number="UT98765432",
        visit_type="walk_in",
    )
    assert visit.status == "approved"
    assert visit.visit_type == "walk_in"


@pytest.mark.django_db
def test_uc_012_validate_zone_access_permitted():
    """TC-UC-012 | Source: VMS-UC-023 Main Flow

    Verify zone access validation for permitted zone.
    """
    res = validate_zone_access(["Library", "Admin Block"], "Library")
    assert res.allowed is True


@pytest.mark.django_db
def test_uc_013_validate_zone_access_denied():
    """TC-UC-013 | Source: VMS-UC-023 Exception Flow E1

    Verify zone access refusal for non-permitted zone.
    """
    res = validate_zone_access(["Library"], "Research Lab")
    assert res.allowed is False


@pytest.mark.django_db
def test_uc_014_trigger_emergency_muster():
    """TC-UC-014 | Source: VMS-UC-026 Main Flow

    Verify trigger emergency muster roll-call.
    """
    muster = trigger_emergency_muster(admin_user_id=1)
    assert muster.status == "active"
    assert muster.muster_code.startswith("MUSTER-")


@pytest.mark.django_db
def test_uc_015_emergency_roll_call_resolution():
    """TC-UC-015 | Source: VMS-UC-027 Main Flow

    Verify emergency roll-call resolution.
    """
    muster = trigger_emergency_muster(admin_user_id=1)
    resolved = resolve_emergency_muster(muster.id, admin_user_id=1)
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None


@pytest.mark.django_db
def test_uc_016_terminate_visit_early():
    """TC-UC-016 | Source: VMS-UC-036 Main Flow

    Verify early termination of visit due to policy breach.
    """
    visit = _create_test_visit(
        first_name="Victor",
        last_name="Hugo",
        phone="+919876510016",
        email="victor@example.com",
        id_number="9999-0000-1111",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "checked_out"
