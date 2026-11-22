"""Business Rules (BR) Automated Tests for VMS."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.contracts import (
    GateCheckoutDTO,
    GateValidationDTO,
    HostDecisionDTO,
    PreRegisterDTO,
)
from modules.vms.domain.errors import (
    BlacklistedVisitorError,
    InvalidTimeWindowError,
)
from modules.vms.models import (
    BlacklistRegistry,
    CampusGate,
    Host,
    PassStatus,
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
        user_id=103,
        employee_id="EMP-103",
        full_name="Prof. Verma",
        department="Mechanical",
        email="verma@iiitdmj.ac.in",
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
class TestVMSBusinessRules:
    def test_br_051_blacklist_screening_rejects_immediately(self, host):
        BlacklistRegistry.objects.create(
            phone="9898989898",
            id_document_number="BL-PAN-99",
            full_name="Blacklisted Guy",
            reason="Violation of safety",
            is_active=True,
            flagged_by=1,
        )
        now = timezone.now()
        with pytest.raises(BlacklistedVisitorError):
            submit_pre_registration(
                PreRegisterDTO(
                    visitor_name="Blacklisted Guy",
                    visitor_phone="9898989898",
                    visitor_email="bl@example.com",
                    id_doc_type="PAN",
                    id_doc_number="BL-PAN-99",
                    organization="None",
                    host_id=host.user_id,
                    purpose="Attempted Entry",
                    scheduled_start=now + timedelta(hours=2),
                    scheduled_end=now + timedelta(hours=5),
                )
            )

    def test_br_190_inverted_time_window_rejected(self, host):
        now = timezone.now()
        with pytest.raises(InvalidTimeWindowError):
            submit_pre_registration(
                PreRegisterDTO(
                    visitor_name="Invalid Time",
                    visitor_phone="9111122222",
                    visitor_email="invalid@example.com",
                    id_doc_type="AADHAAR",
                    id_doc_number="1234-1234-1234",
                    organization="None",
                    host_id=host.user_id,
                    purpose="Testing",
                    scheduled_start=now + timedelta(hours=5),
                    scheduled_end=now + timedelta(hours=2),
                )
            )

    def test_br_191_gate_zone_not_permitted_rejected(self, host):
        gate_hostel = CampusGate.objects.create(
            gate_id="HOSTEL-GATE",
            gate_name="Hostel Gate",
            location_zone="HOSTEL_ZONE",
            is_operational=True,
        )
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Campus Visitor",
                visitor_phone="9333344444",
                visitor_email="cv@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="5678-5678-5678",
                organization="Visitor",
                host_id=host.user_id,
                purpose="Visit",
                scheduled_start=now - timedelta(minutes=10),
                scheduled_end=now + timedelta(hours=3),
            )
        )
        _, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                permitted_zones=["ACADEMIC_ZONE"],
            )
        )
        verdict = validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate_hostel.gate_id,
                verifier_id=1,
            )
        )
        assert verdict.allowed is False
        assert "not in permitted zones" in verdict.reason

    def test_br_077_non_active_pass_denied(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Cancelled Visitor",
                visitor_phone="9444455555",
                visitor_email="can@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="9999-0000-1111",
                organization="Visitor",
                host_id=host.user_id,
                purpose="Cancelled Meeting",
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
        pass_obj.status = PassStatus.DEACTIVATED
        pass_obj.save()

        verdict = validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate.gate_id,
                verifier_id=1,
            )
        )
        assert verdict.allowed is False
        assert "DEACTIVATED" in verdict.reason

    def test_br_105_departure_logging_audit(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Audit Visitor",
                visitor_phone="9555566666",
                visitor_email="audit@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="7777-8888-9999",
                organization="Auditor",
                host_id=host.user_id,
                purpose="Audit",
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
                verifier_id=1,
            )
        )
        log = check_out_at_gate(
            GateCheckoutDTO(
                pass_id=pass_obj.pass_id,
                gate_id=gate.gate_id,
                verifier_id=1,
            )
        )
        assert log.check_out_time is not None
        assert log.exit_gate == gate
