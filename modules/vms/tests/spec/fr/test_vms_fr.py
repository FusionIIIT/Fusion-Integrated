"""Functional Requirements (FR) Automated Tests for VMS."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.contracts import (
    GateCheckoutDTO,
    GateValidationDTO,
    HostDecisionDTO,
    PreRegisterDTO,
)
from modules.vms.domain.errors import BlacklistedVisitorError
from modules.vms.models import (
    BlacklistRegistry,
    CampusGate,
    Host,
    PassStatus,
    RequestStatus,
    VisitLog,
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
class TestVMSFunctionalRequirements:
    def test_fr_01_pre_registration_submission(self, host):
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Rajesh Kumar",
            visitor_phone="9876543210",
            visitor_email="rajesh@example.com",
            id_doc_type="AADHAAR",
            id_doc_number="1234-5678-9012",
            organization="IIT Bombay",
            host_id=host.user_id,
            purpose="Academic Collaboration",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=7),
            remarks="Needs access to lab",
        )
        req = submit_pre_registration(dto)
        assert req.status == RequestStatus.PENDING_HOST_APPROVAL
        assert req.visitor.full_name == "Rajesh Kumar"
        assert req.visitor.phone == "9876543210"

    def test_fr_02_blacklisted_visitor_rejection(self, host):
        BlacklistRegistry.objects.create(
            phone="9999999999",
            id_document_number="BL-12345",
            full_name="Blocked Person",
            reason="Prior misconduct",
            is_active=True,
            flagged_by=1,
        )
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Blocked Person",
            visitor_phone="9999999999",
            visitor_email="blocked@example.com",
            id_doc_type="PASSPORT",
            id_doc_number="BL-12345",
            organization="None",
            host_id=host.user_id,
            purpose="Meeting",
            scheduled_start=now + timedelta(hours=3),
            scheduled_end=now + timedelta(hours=5),
        )
        with pytest.raises(BlacklistedVisitorError):
            submit_pre_registration(dto)

    def test_fr_03_host_decision_and_pass_generation(self, host):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Sneha Verma",
                visitor_phone="9811122233",
                visitor_email="sneha@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="9988-7766-5544",
                organization="IIITDMJ",
                host_id=host.user_id,
                purpose="Viva Examiner",
                scheduled_start=now + timedelta(hours=2),
                scheduled_end=now + timedelta(hours=6),
            )
        )
        _decision, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                allowed_start=now + timedelta(hours=2),
                allowed_end=now + timedelta(hours=6),
                permitted_zones=["MAIN_CAMPUS"],
            )
        )
        req.refresh_from_db()
        assert req.status == RequestStatus.APPROVED
        assert pass_obj.status == PassStatus.ACTIVE
        assert pass_obj.pass_type == "PRE_REGISTERED"

    def test_fr_04_gate_validation_check_in(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Amit Patel",
                visitor_phone="9777788888",
                visitor_email="amit@example.com",
                id_doc_type="PAN",
                id_doc_number="ABCDE9999Z",
                organization="Industry Partner",
                host_id=host.user_id,
                purpose="Guest Lecture",
                scheduled_start=now - timedelta(minutes=15),
                scheduled_end=now + timedelta(hours=4),
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
                verifier_id=501,
            )
        )
        assert verdict.allowed is True
        visit_log = VisitLog.objects.get(log_id=verdict.visit_id)
        assert visit_log.status == VisitStatus.ON_SITE

    def test_fr_05_gate_checkout(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Karan Johar",
                visitor_phone="9666655555",
                visitor_email="karan@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="1111-2222-3333",
                organization="Media",
                host_id=host.user_id,
                purpose="Interview",
                scheduled_start=now - timedelta(hours=1),
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
                verifier_id=501,
            )
        )
        completed_log = check_out_at_gate(
            GateCheckoutDTO(
                pass_id=pass_obj.pass_id,
                gate_id=gate.gate_id,
                verifier_id=501,
            )
        )
        assert completed_log.status == VisitStatus.COMPLETED
        assert completed_log.check_out_time is not None
