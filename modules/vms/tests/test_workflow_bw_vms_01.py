"""Test suite for Basis Workflow BW-VMS-01: Pre-registered Approved Visit.

Verifies the 4-step state progression:
1. Not Submitted -> Pending Host Approval (VMS-UC-010)
2. Pending Host Approval -> Approved / Pass Active (VMS-UC-013)
3. Pass Active -> On-site (VMS-UC-018)
4. On-site -> Completed (VMS-UC-021)
"""
from datetime import timedelta
import pytest
from django.utils import timezone

from modules.vms.models import (
    Visitor,
    Host,
    VisitRequest,
    VisitorPass,
    VisitLog,
    CampusGate,
    BlacklistRegistry,
    RequestStatus,
    PassStatus,
    VisitStatus,
)
from modules.vms.contracts import (
    PreRegisterDTO,
    HostDecisionDTO,
    GateValidationDTO,
    GateCheckoutDTO,
)
from modules.vms.services.operations import (
    submit_pre_registration,
    record_host_decision,
    validate_and_check_in_at_gate,
    check_out_at_gate,
)
from modules.vms.domain.errors import (
    BlacklistedVisitorError,
    InvalidTimeWindowError,
    InvalidStateTransitionError,
)


@pytest.fixture
def host(db):
    return Host.objects.create(
        user_id=101,
        employee_id="EMP-101",
        full_name="Prof. Sharma",
        department="Computer Science",
        email="sharma@iiitdmj.ac.in",
    )


@pytest.fixture
def gate(db):
    return CampusGate.objects.create(
        gate_id="GATE-01",
        gate_name="Main Campus Gate",
        location_zone="MAIN_CAMPUS",
        is_operational=True,
    )


@pytest.mark.django_db
class TestBasisWorkflowVMS01:

    def test_full_successful_pre_registered_visit_workflow(self, host, gate):
        now = timezone.now()
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=6)

        # Step 1: Pre-register Visit (VMS-UC-010)
        # Not Submitted -> Pending Host Approval
        pre_dto = PreRegisterDTO(
            visitor_name="John Doe",
            visitor_phone="9876543210",
            visitor_email="john@example.com",
            id_doc_type="AADHAAR",
            id_doc_number="1234-5678-9012",
            organization="IIT Delhi",
            host_id=host.user_id,
            purpose="Research Discussion",
            scheduled_start=start,
            scheduled_end=end,
            remarks="Needs projector access",
        )
        req = submit_pre_registration(pre_dto)
        assert req.status == RequestStatus.PENDING_HOST_APPROVAL
        assert req.visitor.full_name == "John Doe"

        # Step 2: Host Decision (VMS-UC-013)
        # Pending Host Approval -> Approved & Pass Active (PRE_REGISTERED)
        decision_dto = HostDecisionDTO(
            request_id=req.request_id,
            host_id=host.user_id,
            outcome="APPROVE",
            allowed_start=start,
            allowed_end=end,
            permitted_zones=["MAIN_CAMPUS"],
            special_instructions="Allow access to CC building",
        )
        decision, pass_obj = record_host_decision(decision_dto)
        req.refresh_from_db()

        assert req.status == RequestStatus.APPROVED
        assert decision.outcome == "APPROVE"
        assert pass_obj is not None
        assert pass_obj.status == PassStatus.ACTIVE
        assert pass_obj.pass_type == "PRE_REGISTERED"

        # Step 3: Gate Validation Check-in (VMS-UC-018)
        # Pass Active -> On-site
        gate_val_dto = GateValidationDTO(
            credential_data=pass_obj.credential_data,
            gate_id=gate.gate_id,
            verifier_id=501,
            verifier_notes="Identity verified with Aadhaar",
        )
        verdict = validate_and_check_in_at_gate(gate_val_dto)
        assert verdict.allowed is True
        assert verdict.visitor_name == "John Doe"
        assert verdict.visit_id is not None

        visit_log = VisitLog.objects.get(log_id=verdict.visit_id)
        assert visit_log.status == VisitStatus.ON_SITE
        assert visit_log.entry_gate == gate

        # Step 4: Gate Checkout (VMS-UC-021)
        # On-site -> Completed
        checkout_dto = GateCheckoutDTO(
            pass_id=pass_obj.pass_id,
            gate_id=gate.gate_id,
            verifier_id=501,
            verifier_notes="Visitor departed campus",
        )
        completed_log = check_out_at_gate(checkout_dto)

        assert completed_log.status == VisitStatus.COMPLETED
        assert completed_log.check_out_time is not None
        assert completed_log.exit_gate == gate

        pass_obj.refresh_from_db()
        req.refresh_from_db()
        assert pass_obj.status == PassStatus.COMPLETED
        assert req.status == RequestStatus.COMPLETED

    def test_pre_registration_blacklisted_visitor_is_rejected(self, host):
        # Guard check: VMS-BR-051 / VMS-BR-112
        BlacklistRegistry.objects.create(
            phone="9999999999",
            id_document_number="BL-12345",
            full_name="Threat Actor",
            reason="Security incident at hostel gate",
            is_active=True,
            flagged_by=1,
        )

        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Threat Actor",
            visitor_phone="9999999999",
            visitor_email="threat@bad.com",
            id_doc_type="PASSPORT",
            id_doc_number="BL-12345",
            organization="Unknown",
            host_id=host.user_id,
            purpose="Visit",
            scheduled_start=now + timedelta(hours=1),
            scheduled_end=now + timedelta(hours=3),
        )

        with pytest.raises(BlacklistedVisitorError):
            submit_pre_registration(dto)

    def test_invalid_time_window_fails(self, host):
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Time Traveler",
            visitor_phone="9888888888",
            visitor_email="time@test.com",
            id_doc_type="PAN",
            id_doc_number="ABCDE1234F",
            organization="Testing",
            host_id=host.user_id,
            purpose="Testing",
            scheduled_start=now + timedelta(hours=5),
            scheduled_end=now + timedelta(hours=2),  # End before start
        )

        with pytest.raises(InvalidTimeWindowError):
            submit_pre_registration(dto)

    def test_gate_validation_unauthorized_gate_zone_rejected(self, host):
        restricted_gate = CampusGate.objects.create(
            gate_id="RES-GATE",
            gate_name="Restricted Zone Gate",
            location_zone="DATA_CENTER",
            is_operational=True,
        )

        now = timezone.now()
        pre_dto = PreRegisterDTO(
            visitor_name="Zone Visitor",
            visitor_phone="9123456789",
            visitor_email="zone@test.com",
            id_doc_type="AADHAAR",
            id_doc_number="5555-6666-7777",
            organization="Test Org",
            host_id=host.user_id,
            purpose="Meeting",
            scheduled_start=now - timedelta(minutes=10),
            scheduled_end=now + timedelta(hours=2),
        )
        req = submit_pre_registration(pre_dto)
        _, pass_obj = record_host_decision(HostDecisionDTO(
            request_id=req.request_id,
            host_id=host.user_id,
            outcome="APPROVE",
            permitted_zones=["ACADEMIC_ZONE"],
        ))

        verdict = validate_and_check_in_at_gate(GateValidationDTO(
            credential_data=pass_obj.credential_data,
            gate_id=restricted_gate.gate_id,
            verifier_id=1,
        ))
        assert verdict.allowed is False
        assert "not in permitted zones" in verdict.reason
