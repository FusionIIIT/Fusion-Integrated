"""Automated tests for Workflows (WF) Strategy.
Derived from frozen WF_DESIGN.json.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.domain.state_machine import (
    InvalidStateTransitionError,
    TransitionTrigger,
    validate_transition,
)
from modules.vms.services.errors import InvalidTransitionError
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
    phone="9876530001",
    email="test@example.com",
    id_type="aadhaar",
    id_number="1234-9999-0001",
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
def test_wf_001_full_lifecycle_path():
    """TC-WF-001 | Source: BW-VMS-01 Full Pre-registered Visit Lifecycle Path

    Verify sequential state transitions from initial request to gate exit.
    """
    visit = _create_test_visit(
        first_name="Zack",
        last_name="Snyder",
        phone="+919876530001",
        email="zack@example.com",
        id_number="1234-9999-0001",
        purpose="Production Meeting",
    )
    assert visit.status == "requested"

    approve_visit(visit.id, host_user_id=101)
    visit.refresh_from_db()
    assert visit.status == "approved"

    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "on_site"

    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "checked_out"


@pytest.mark.django_db
def test_wf_002_decision_path_approval():
    """TC-WF-002 | Source: BW-VMS-04 Decision Path - Approval

    Verify visit request approval workflow path.
    """
    visit = _create_test_visit(
        first_name="Amy",
        last_name="Adams",
        phone="+919876530002",
        email="amy@example.com",
        id_number="1234-9999-0002",
        host_user_id=202,
        purpose="Interview",
    )
    approved = approve_visit(visit.id, host_user_id=202)
    assert approved.status == "approved"
    assert approved.pass_number is not None


@pytest.mark.django_db
def test_wf_003_decision_path_rejection():
    """TC-WF-003 | Source: BW-VMS-04 Decision Path - Rejection

    Verify visit request rejection workflow path.
    """
    visit = _create_test_visit(
        first_name="Ben",
        last_name="Affleck",
        phone="+919876530003",
        email="ben@example.com",
        id_number="1234-9999-0003",
        host_user_id=303,
        purpose="Meeting",
    )
    rejected = reject_visit(visit.id, host_user_id=303, reason="Scheduling conflict")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Scheduling conflict"


@pytest.mark.django_db
def test_wf_004_walk_in_workflow_path():
    """TC-WF-004 | Source: BW-VMS-01 Walk-in Workflow Path

    Verify walk-in visit creation directly bypasses host approval into approved pass.
    """
    visit = _create_test_visit(
        first_name="Chris",
        last_name="Evans",
        phone="+919876530004",
        email="chris@example.com",
        id_number="1234-9999-0004",
        purpose="Urgent Delivery",
        visit_type="walk_in",
    )
    assert visit.status == "approved"
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "on_site"


@pytest.mark.django_db
def test_wf_005_early_termination_path():
    """TC-WF-005 | Source: BW-VMS-05 Early Termination Workflow Path

    Verify early visit termination while on-site.
    """
    visit = _create_test_visit(
        first_name="Diana",
        last_name="Prince",
        phone="+919876530005",
        email="diana@example.com",
        id_number="1234-9999-0005",
        purpose="Guest",
    )
    approve_visit(visit.id, host_user_id=101)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)
    transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)
    visit.refresh_from_db()
    assert visit.status == "checked_out"


@pytest.mark.django_db
def test_wf_006_emergency_muster_lifecycle():
    """TC-WF-006 | Source: BW-VMS-06 Emergency Muster Lifecycle Path

    Verify emergency muster initiation and resolution lifecycle.
    """
    muster = trigger_emergency_muster(admin_user_id=1)
    assert muster.status == "active"
    resolved = resolve_emergency_muster(muster.id, admin_user_id=1)
    assert resolved.status == "resolved"


@pytest.mark.django_db
def test_wf_007_gate_check_in_state_guard():
    """TC-WF-007 | Source: BW-VMS-19 Gate Check-in State Guard Path

    Verify illegal direct check-in from requested status is rejected.
    """
    visit = _create_test_visit(
        first_name="Ethan",
        last_name="Hunt",
        phone="+919876530007",
        email="ethan@example.com",
        id_number="1234-9999-0007",
        purpose="Visit",
    )
    with pytest.raises(InvalidTransitionError):
        transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_IN, actor_id=1)


@pytest.mark.django_db
def test_wf_008_gate_check_out_state_guard():
    """TC-WF-008 | Source: BW-VMS-23 Gate Check-out State Guard Path

    Verify check-out rejected when visitor has not checked in.
    """
    visit = _create_test_visit(
        first_name="Fiona",
        last_name="Gallagher",
        phone="+919876530008",
        email="fiona@example.com",
        id_number="1234-9999-0008",
        purpose="Visit",
    )
    approve_visit(visit.id, host_user_id=101)
    with pytest.raises(InvalidTransitionError):
        transition_visit_state(visit.id, trigger=TransitionTrigger.GATE_CHECK_OUT, actor_id=1)


def test_wf_009_terminal_rejection_guard():
    """TC-WF-009 | Source: STT-Terminal Rejection Guard Path

    Verify terminal states cannot be re-opened.
    """
    with pytest.raises(InvalidStateTransitionError):
        validate_transition("rejected", TransitionTrigger.HOST_APPROVE)


def test_wf_010_terminal_checkout_guard():
    """TC-WF-010 | Source: STT-Terminal Check-out Guard Path

    Verify checked_out visit cannot transition back to checked_in.
    """
    with pytest.raises(InvalidStateTransitionError):
        validate_transition("checked_out", TransitionTrigger.GATE_CHECK_IN)
