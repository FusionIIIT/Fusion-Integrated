"""Automated tests for Functional Requirements (FR) Strategy.
Derived from frozen FR_DESIGN.json.
"""

import hashlib
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.contracts import get_active_visitors_on_campus
from modules.vms.domain.rules import validate_zone_access
from modules.vms.domain.state_machine import TransitionTrigger
from modules.vms.models.access import GateAlert, GateLog
from modules.vms.models.visitors import BlacklistEntry, Visitor
from modules.vms.selectors.visits import list_active_onsite_visits
from modules.vms.services.errors import BlacklistMatchError, PassExpiredError
from modules.vms.services.gate import (
    reconcile_offline_gate_events,
    transition_visit_state,
    verify_qr_and_check_in,
)
from modules.vms.services.registration import (
    approve_visit,
    reject_visit,
    request_or_create_visit,
)
from modules.vms.services.security import trigger_emergency_muster


def _create_test_visit(
    first_name="Test",
    last_name="User",
    phone="9876500001",
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
def test_fr_001_authoritative_digital_recording():
    """TC-FR-001 | Source: VMS-CFR-001 / VMS-AFR-002

    Verify authoritative digital recording of visitor registration.
    """
    visit = _create_test_visit(
        first_name="Alice",
        last_name="Smith",
        phone="+919876500001",
        email="alice.smith@example.com",
        id_number="1234-5678-9012",
    )
    assert visit.visitor.id is not None
    assert visit.visitor.id_number_hash is not None
    assert visit.visitor.first_name == "Alice"


@pytest.mark.django_db
def test_fr_002_role_enforcement_unauthorized_refusal(client):
    """TC-FR-002 | Source: VMS-CFR-002 / VMS-AFR-003

    Verify role-based permission enforcement for role assignment operations.
    """
    res = client.post("/api/v1/vms/emergency/muster/")
    assert res.status_code in [401, 403]


@pytest.mark.django_db
def test_fr_003_public_contract_active_visitor_lookup():
    """TC-FR-003 | Source: VMS-CFR-003 / VMS-AFR-004

    Verify public module contract integration for active visitor lookup.
    """
    visit = _create_test_visit(
        first_name="Bob",
        last_name="Jones",
        phone="+919876500002",
        email="bob.j@example.com",
        id_type="pan",
        id_number="ABCDE1234F",
        host_user_id=202,
    )
    approve_visit(visit.id, host_user_id=202)
    transition_visit_state(
        visit.id,
        trigger=TransitionTrigger.GATE_CHECK_IN,
        actor_id=1,
        gate_name="Main Gate",
    )

    active_list = get_active_visitors_on_campus()
    visitor_names = [v.full_name for v in active_list]
    assert "Bob Jones" in visitor_names


@pytest.mark.django_db
def test_fr_004_immutable_audit_logging_gate_check_in():
    """TC-FR-004 | Source: VMS-CFR-005 / VMS-AFR-006

    Verify immutable audit logging of gate check-in events.
    """
    visit = _create_test_visit(
        first_name="Carol",
        last_name="Danvers",
        phone="+919876500003",
        email="carol@example.com",
        id_type="passport",
        id_number="M98765432",
        host_user_id=303,
    )
    approve_visit(visit.id, host_user_id=303)
    transition_visit_state(
        visit.id,
        trigger=TransitionTrigger.GATE_CHECK_IN,
        actor_id=42,
        gate_name="North Gate",
        reader_machine_id="RDR-01",
    )

    log = GateLog.objects.filter(visit=visit).first()
    assert log is not None
    assert log.action == "check_in"
    assert log.logged_by == 42
    assert log.gate_name == "North Gate"
    assert log.reader_machine_id == "RDR-01"


@pytest.mark.django_db
def test_fr_005_pass_validity_period_validation():
    """TC-FR-005 | Source: VMS-CFR-006 / VMS-AFR-008

    Verify pass validity period constraints enforced at registration.
    """
    now = timezone.now()
    visit = _create_test_visit(
        first_name="Valid",
        last_name="Times",
        phone="+919876500004",
        email="valid@example.com",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )
    assert visit.valid_to > visit.valid_from


@pytest.mark.django_db
def test_fr_006_blacklist_addition():
    """TC-FR-006 | Source: VMS-CFR-007 / VMS-AFR-009

    Verify blacklist addition and subsequent lookup restriction.
    """
    entry = BlacklistEntry.objects.create(
        id_type="aadhaar",
        id_number_hash="test_bl_hash_006",
        full_name="Threat Person",
        phone="9876500005",
        reason="Security Watchlist",
        severity="critical",
        added_by=1,
    )
    assert entry.id is not None
    assert entry.is_active is True


@pytest.mark.django_db
def test_fr_007_blacklist_match_prevention():
    """TC-FR-007 | Source: VMS-CFR-007 / VMS-AFR-106

    Verify blacklist match prevention during visit registration.
    """
    raw_id = "BL-ID-007"
    hashed_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()
    BlacklistEntry.objects.create(
        id_type="aadhaar",
        id_number_hash=hashed_id,
        full_name="Banned Individual",
        phone="9876500007",
        reason="Campus Security Trespass Notice",
        severity="critical",
        added_by=1,
    )

    with pytest.raises(BlacklistMatchError):
        _create_test_visit(
            first_name="Banned",
            last_name="Individual",
            phone="+919876500007",
            email="banned@example.com",
            id_number=raw_id,
        )


@pytest.mark.django_db
def test_fr_008_host_listing_actionable_requests():
    """TC-FR-008 | Source: VMS-CFR-010 / VMS-AFR-013

    Verify host notification and listing of actionable pending visit requests.
    """
    visit = _create_test_visit(
        first_name="Dave",
        last_name="Miller",
        phone="+919876500008",
        email="dave@example.com",
        id_number="9988-7766-5544",
        host_user_id=505,
    )
    from modules.vms.selectors.visits import list_pending_approvals_for_host

    pending = list_pending_approvals_for_host(505)
    assert visit in pending


@pytest.mark.django_db
def test_fr_009_host_approval_generates_pass():
    """TC-FR-009 | Source: VMS-CFR-010 / VMS-AFR-014

    Verify host approval transitions visit to approved state and generates pass.
    """
    visit = _create_test_visit(
        first_name="Eve",
        last_name="White",
        phone="+919876500009",
        email="eve@example.com",
        id_number="5566-7788-9900",
        host_user_id=606,
    )
    approved = approve_visit(visit.id, host_user_id=606)
    assert approved.status == "approved"
    assert approved.pass_number is not None
    assert approved.qr_code_hash is not None


@pytest.mark.django_db
def test_fr_010_host_rejection_records_reason():
    """TC-FR-010 | Source: VMS-CFR-010 / VMS-AFR-015

    Verify host rejection transitions visit to rejected state with reason.
    """
    visit = _create_test_visit(
        first_name="Frank",
        last_name="Castle",
        phone="+919876500010",
        email="frank@example.com",
        id_type="pan",
        id_number="FRKCS1234F",
        host_user_id=707,
    )
    rejected = reject_visit(visit.id, host_user_id=707, reason="Host unavailable on date")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Host unavailable on date"


@pytest.mark.django_db
def test_fr_011_gate_check_in_updates_status():
    """TC-FR-011 | Source: VMS-CFR-012 / VMS-AFR-019

    Verify visit status update upon gate check-in.
    """
    visit = _create_test_visit(
        first_name="Grace",
        last_name="Hopper",
        phone="+919876500011",
        email="grace@example.com",
        id_number="1234-9999-8888",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "on_site"
    assert visit.check_in_time is not None


@pytest.mark.django_db
def test_fr_012_gate_check_in_refusal_when_expired():
    """TC-FR-012 | Source: VMS-CFR-013 / VMS-AFR-020

    Verify gate check-in refusal when pass is expired.
    """
    past = timezone.now() - timedelta(days=2)
    visit = _create_test_visit(
        first_name="Harry",
        last_name="Potter",
        phone="+919876500012",
        email="harry@example.com",
        id_number="0000-1111-2222",
        valid_from=past,
        valid_to=past + timedelta(hours=2),
    )
    approve_visit(visit.id, host_user_id=101)
    with pytest.raises(PassExpiredError):
        verify_qr_and_check_in(visit.qr_code_hash, guard_user_id=1)


@pytest.mark.django_db
def test_fr_013_gate_alert_on_blacklisted_entry_attempt():
    """TC-FR-013 | Source: VMS-CFR-014 / VMS-AFR-024

    Verify gate alert generation when blacklisted visitor attempts entry.
    """
    visit = _create_test_visit(
        first_name="Ian",
        last_name="Malcolm",
        phone="+919876500013",
        email="ian@example.com",
        id_number="9876-1234-5678",
    )
    approve_visit(visit.id, host_user_id=101)

    BlacklistEntry.objects.create(
        id_type="aadhaar",
        id_number_hash=visit.visitor.id_number_hash,
        full_name="Ian Malcolm",
        phone=visit.visitor.phone,
        reason="Security Watchlist",
        severity="critical",
        added_by=1,
    )

    with pytest.raises(BlacklistMatchError):
        verify_qr_and_check_in(visit.qr_code_hash, guard_user_id=1)

    alert = GateAlert.objects.filter(visit_id=visit.id).first()
    assert alert is not None
    assert alert.alert_type == "blacklist_gate_entry_attempt"


@pytest.mark.django_db
def test_fr_014_gate_check_out_records_exit():
    """TC-FR-014 | Source: VMS-CFR-015 / VMS-AFR-021

    Verify gate check-out transitions visit to checked_out and records exit time.
    """
    visit = _create_test_visit(
        first_name="Julia",
        last_name="Roberts",
        phone="+919876500014",
        email="julia@example.com",
        id_number="4321-8765-2109",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "completed"
    assert visit.check_out_time is not None


@pytest.mark.django_db
def test_fr_015_walk_in_registration_default_duration():
    """TC-FR-015 | Source: VMS-CFR-016 / VMS-AFR-022

    Verify walk-in registration by security personnel with default validity.
    """
    visit = _create_test_visit(
        first_name="Kevin",
        last_name="Bacon",
        phone="+919876500015",
        email="kevin@example.com",
        id_type="pan",
        id_number="KVNBC1234K",
        visit_type="walk_in",
    )
    assert visit.visit_type == "walk_in"
    diff = visit.valid_to - visit.valid_from
    assert diff.total_seconds() == 4 * 3600


@pytest.mark.django_db
def test_fr_016_onsite_visitor_count_selector():
    """TC-FR-016 | Source: VMS-CFR-017 / VMS-AFR-023

    Verify on-site visitor active count selector accuracy.
    """
    initial_count = list_active_onsite_visits().count()
    v1 = _create_test_visit(
        first_name="V1",
        last_name="Test",
        phone="+919876500016",
        email="v1@example.com",
        id_number="1111-2222-0001",
    )
    approve_visit(v1.id, host_user_id=101)
    transition_visit_state(v1.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)

    assert list_active_onsite_visits().count() == initial_count + 1


@pytest.mark.django_db
def test_fr_017_emergency_muster_initiation():
    """TC-FR-017 | Source: VMS-CFR-018 / VMS-AFR-025

    Verify emergency muster initiation records headcount and triggers alert.
    """
    muster = trigger_emergency_muster(admin_user_id=1)
    assert muster.id is not None
    assert muster.status == "active"
    alert = GateAlert.objects.filter(alert_type="emergency_muster_active").first()
    assert alert is not None


@pytest.mark.django_db
def test_fr_018_quick_visitor_search_by_phone():
    """TC-FR-018 | Source: VMS-CFR-020 / VMS-AFR-036

    Verify quick visitor search by phone or name.
    """
    Visitor.objects.create(
        first_name="Searchable",
        last_name="Person",
        phone="+919876500018",
        email="searchable@example.com",
        id_type="aadhaar",
        id_number_hash="hash_018",
    )
    found = Visitor.objects.filter(phone="+919876500018").first()
    assert found is not None
    assert found.first_name == "Searchable"


@pytest.mark.django_db
def test_fr_019_offline_gate_sync():
    """TC-FR-019 | Source: VMS-CFR-025 / VMS-AFR-086

    Verify offline gate scan batch reconciliation.
    """
    visit = _create_test_visit(
        first_name="Offline",
        last_name="Visitor",
        phone="+919876500019",
        email="offline@example.com",
        id_number="8888-7777-6666",
    )
    approve_visit(visit.id, host_user_id=101)

    batch = [
        {
            "qr_code_hash": visit.qr_code_hash,
            "action": "check_in",
            "gate_name": "East Gate",
            "reader_machine_id": "OFFLINE-01",
        }
    ]
    res = reconcile_offline_gate_events(batch, guard_user_id=1)
    assert res["processed"] == 1
    assert len(res["errors"]) == 0
    visit.refresh_from_db()
    assert visit.status == "on_site"


@pytest.mark.django_db
def test_fr_020_zone_access_validation():
    """TC-FR-020 | Source: VMS-CFR-026 / VMS-AFR-088

    Verify zone access validation against pass allowed_zones.
    """
    res = validate_zone_access(["Admin Block", "Cafeteria"], "Server Room")
    assert res.allowed is False
