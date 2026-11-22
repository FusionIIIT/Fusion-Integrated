"""Comprehensive unit tests for VMS service layer operations."""

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
    RequestStatus,
    VisitStatus,
)
from modules.vms.services.operations import (
    check_out_at_gate,
    record_host_decision,
    submit_pre_registration,
    validate_and_check_in_at_gate,
)


@pytest.mark.django_db
class TestVmsServicesComprehensive:
    """Exhaustive tests for service transactions and edge case validations."""

    @pytest.fixture
    def setup_entities(self):
        host = Host.objects.create(
            user_id=501,
            employee_id="EMP-501",
            full_name="Dr. Host",
            department="CSE",
            designation="Professor",
            email="host501@test.org",
        )
        gate = CampusGate.objects.create(
            gate_id="GATE-01",
            gate_name="Main Gate",
            location_zone="MAIN_CAMPUS",
            is_operational=True,
        )
        return host, gate

    @pytest.mark.parametrize(
        ("org", "purpose"),
        [
            ("IIT Delhi", "PhD Viva Defense"),
            ("ISRO", "Research Project Meeting"),
            ("Microsoft", "Campus Placement Drive"),
            ("Parent/Guardian", "Student Personal Emergency"),
            ("Contractor", "HVAC Maintenance Work"),
            ("Vendor", "Lab Equipment Supply Delivery"),
            ("Alumni", "Department Guest Lecture"),
            ("Auditor", "Annual Institutional Financial Audit"),
            ("Visitor", "Library Archival Access"),
            ("Govt Official", "Accreditation Inspection"),
        ],
    )
    def test_submit_pre_registration_various_purposes(self, setup_entities, org, purpose):
        host, _ = setup_entities
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name=f"Visitor for {purpose[:10]}",
            visitor_phone=f"98110{len(purpose):05d}",
            visitor_email="v@org.test",
            id_doc_type="AADHAAR",
            id_doc_number=f"DOC-{purpose[:5]}",
            organization=org,
            host_id=host.user_id,
            purpose=purpose,
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=3),
        )
        req = submit_pre_registration(dto)
        assert req.request_id is not None
        assert req.status == RequestStatus.PENDING_HOST_APPROVAL
        assert req.purpose == purpose

    @pytest.mark.parametrize(
        "invalid_end_offset",
        [-1, -2, -5, 0, -24],
    )
    def test_submit_pre_registration_time_window_validation(
        self, setup_entities, invalid_end_offset
    ):
        host, _ = setup_entities
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Time Visitor",
            visitor_phone=f"98220{abs(invalid_end_offset):05d}",
            visitor_email="v_time@test.org",
            id_doc_type="AADHAAR",
            id_doc_number=f"DOC-T{abs(invalid_end_offset)}",
            organization="Org",
            host_id=host.user_id,
            purpose="Invalid Window",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=invalid_end_offset),
        )
        with pytest.raises(InvalidTimeWindowError):
            submit_pre_registration(dto)

    @pytest.mark.parametrize(
        ("phone", "id_doc"),
        [
            ("9777777771", "BL-771"),
            ("9777777772", "BL-772"),
            ("9777777773", "BL-773"),
            ("9777777774", "BL-774"),
        ],
    )
    def test_submit_pre_registration_blacklisted(self, setup_entities, phone, id_doc):
        host, _ = setup_entities
        BlacklistRegistry.objects.create(
            phone=phone,
            id_document_number=id_doc,
            reason="Court restraining order",
            is_active=True,
            flagged_by=1,
        )
        now = timezone.now()
        dto = PreRegisterDTO(
            visitor_name="Blocked Person",
            visitor_phone=phone,
            visitor_email="b@test.org",
            id_doc_type="PAN",
            id_doc_number=id_doc,
            organization="None",
            host_id=host.user_id,
            purpose="Visit",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
        )
        with pytest.raises(BlacklistedVisitorError):
            submit_pre_registration(dto)

    @pytest.mark.parametrize(
        "outcome",
        ["APPROVE", "REJECT", "APPROVE", "REJECT", "APPROVE", "REJECT", "APPROVE", "REJECT"],
    )
    def test_record_host_decision_transitions(self, setup_entities, outcome):
        host, _ = setup_entities
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name=f"Outcome Visitor {outcome}",
                visitor_phone=f"95555{len(outcome):05d}",
                visitor_email="o@test.org",
                id_doc_type="AADHAAR",
                id_doc_number=f"DOC-OUT-{outcome}",
                organization="Org",
                host_id=host.user_id,
                purpose="Review",
                scheduled_start=now,
                scheduled_end=now + timedelta(hours=2),
            )
        )
        dec, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome=outcome,
                permitted_zones=["MAIN_CAMPUS"],
            )
        )
        assert dec.outcome == outcome
        req.refresh_from_db()
        if outcome == "APPROVE":
            assert req.status == RequestStatus.APPROVED
            assert pass_obj is not None
            assert pass_obj.status == PassStatus.ACTIVE
        else:
            assert req.status == RequestStatus.REJECTED
            assert pass_obj is None

    @pytest.mark.parametrize(
        ("gate_zone", "permitted_zones", "expected_allowed"),
        [
            ("MAIN_CAMPUS", ["MAIN_CAMPUS"], True),
            ("HOSTEL_ZONE", ["MAIN_CAMPUS"], False),
            ("ACADEMIC_ZONE", ["ACADEMIC_ZONE", "LIBRARY"], True),
            ("VIP_ZONE", ["MAIN_CAMPUS"], False),
            ("LABS", ["LABS"], True),
            ("SPORTS_ZONE", ["ACADEMIC_ZONE"], False),
            ("MAIN_CAMPUS", [], True),
            ("GUEST_HOUSE", ["GUEST_HOUSE"], True),
        ],
    )
    def test_gate_validation_scenarios(
        self, setup_entities, gate_zone, permitted_zones, expected_allowed
    ):
        host, _ = setup_entities
        gate = CampusGate.objects.create(
            gate_id=f"G-VAL-{gate_zone[:6]}",
            gate_name=f"Gate {gate_zone}",
            location_zone=gate_zone,
            is_operational=True,
        )
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Gate Val Visitor",
                visitor_phone=f"93333{abs(hash(gate_zone)) % 100000:05d}",
                visitor_email="gv@test.org",
                id_doc_type="AADHAAR",
                id_doc_number=f"DOC-GV-{gate_zone[:4]}",
                organization="Org",
                host_id=host.user_id,
                purpose="Val",
                scheduled_start=now - timedelta(minutes=10),
                scheduled_end=now + timedelta(hours=2),
            )
        )
        _, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                permitted_zones=permitted_zones,
            )
        )
        verdict = validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate.gate_id,
                verifier_id=1,
            )
        )
        assert verdict.allowed == expected_allowed

    @pytest.mark.parametrize(
        "checkout_gate_id",
        ["GATE-OUT-01", "GATE-OUT-02", "GATE-OUT-03", "GATE-OUT-04", "GATE-OUT-05", "GATE-OUT-06"],
    )
    def test_gate_checkout_scenarios(self, setup_entities, checkout_gate_id):
        host, gate = setup_entities
        out_gate = CampusGate.objects.create(
            gate_id=checkout_gate_id,
            gate_name="Exit Gate",
            location_zone="MAIN_CAMPUS",
            is_operational=True,
        )
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Checkout Visitor",
                visitor_phone=f"92222{abs(hash(checkout_gate_id)) % 100000:05d}",
                visitor_email="co@test.org",
                id_doc_type="AADHAAR",
                id_doc_number=f"DOC-CO-{checkout_gate_id[:5]}",
                organization="Org",
                host_id=host.user_id,
                purpose="Full Flow",
                scheduled_start=now - timedelta(minutes=10),
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
        verdict = validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate.gate_id,
                verifier_id=1,
            )
        )
        assert verdict.allowed is True

        # Now checkout
        vlog = check_out_at_gate(
            GateCheckoutDTO(
                pass_id=pass_obj.pass_id,
                gate_id=out_gate.gate_id,
                verifier_id=1,
            )
        )
        assert vlog.status == VisitStatus.COMPLETED
        assert vlog.check_out_time is not None
        pass_obj.refresh_from_db()
        assert pass_obj.status == PassStatus.COMPLETED
