"""Use Case (UC) Automated Tests for VMS."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.contracts import (
    GateCheckoutDTO,
    GateValidationDTO,
    HostDecisionDTO,
    PreRegisterDTO,
)
from modules.vms.models import (
    CampusGate,
    Host,
    PassStatus,
    RequestStatus,
    VisitStatus,
)
from modules.vms.services.operations import (
    check_out_at_gate,
    record_host_decision,
    submit_pre_registration,
    validate_and_check_in_at_gate,
)


@pytest.fixture
def host(db):
    return Host.objects.create(
        user_id=102,
        employee_id="EMP-102",
        full_name="Dr. Anita Rao",
        department="ECE",
        email="anita@iiitdmj.ac.in",
    )


@pytest.fixture
def gate(db):
    return CampusGate.objects.create(
        gate_id="GATE-01",
        gate_name="Main Gate",
        location_zone="MAIN_CAMPUS",
        is_operational=True,
    )


@pytest.mark.django_db
class TestVMSUseCases:
    def test_uc_010_pre_register_visit_actor_visitor(self, host):
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Alok Nath",
            visitor_phone="9123456780",
            visitor_email="alok@example.com",
            id_doc_type="AADHAAR",
            id_doc_number="8888-7777-6666",
            organization="Vendor Corp",
            host_id=host.user_id,
            purpose="Maintenance Equipment Delivery",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=6),
        )
        req = submit_pre_registration(dto)
        assert req.request_id is not None
        assert req.status == RequestStatus.PENDING_HOST_APPROVAL

    def test_uc_013_decide_visit_request_actor_host(self, host):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Priya Sharma",
                visitor_phone="9234567890",
                visitor_email="priya@example.com",
                id_doc_type="PASSPORT",
                id_doc_number="Z1234567",
                organization="Research Institute",
                host_id=host.user_id,
                purpose="Joint Project Review",
                scheduled_start=now + timedelta(hours=2),
                scheduled_end=now + timedelta(hours=5),
            )
        )
        decision, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                permitted_zones=["MAIN_CAMPUS"],
            )
        )
        assert decision.outcome == "APPROVE"
        assert pass_obj.status == PassStatus.ACTIVE

    def test_uc_018_validate_visitor_pass_actor_guard(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Vikram Singh",
                visitor_phone="9345678901",
                visitor_email="vikram@example.com",
                id_doc_type="DRIVING_LICENSE",
                id_doc_number="DL-0420110012345",
                organization="Self",
                host_id=host.user_id,
                purpose="Meeting with HOD",
                scheduled_start=now - timedelta(minutes=10),
                scheduled_end=now + timedelta(hours=3),
            )
        )
        _, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                permitted_zones=["MAIN_CAMPUS"],
            )
        )
        verdict = validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate.gate_id,
                verifier_id=601,
            )
        )
        assert verdict.allowed is True
        assert verdict.visit_id is not None

    def test_uc_021_check_out_visitor_actor_guard(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Gaurav Sen",
                visitor_phone="9456789012",
                visitor_email="gaurav@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="4321-8765-2109",
                organization="Tech Consultant",
                host_id=host.user_id,
                purpose="Campus Network Audit",
                scheduled_start=now - timedelta(hours=2),
                scheduled_end=now + timedelta(hours=2),
            )
        )
        _, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                permitted_zones=["MAIN_CAMPUS"],
            )
        )
        validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate.gate_id,
                verifier_id=601,
            )
        )
        log = check_out_at_gate(
            GateCheckoutDTO(
                pass_id=pass_obj.pass_id,
                gate_id=gate.gate_id,
                verifier_id=601,
            )
        )
        assert log.status == VisitStatus.COMPLETED
        assert log.check_out_time is not None
