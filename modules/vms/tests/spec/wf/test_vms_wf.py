"""Basis Workflow (WF) Automated Tests for VMS."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.contracts import (
    GateCheckoutDTO,
    GateValidationDTO,
    HostDecisionDTO,
    PreRegisterDTO,
)
from modules.vms.domain.errors import InvalidStateTransitionError
from modules.vms.models import (
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
        user_id=104,
        employee_id="EMP-104",
        full_name="Prof. Sengupta",
        department="Design",
        email="sengupta@iiitdmj.ac.in",
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
class TestVMSBasisWorkflow01:
    def test_wf_01_complete_basis_workflow_bw_vms_01(self, host, gate):
        now = timezone.now()
        start = now - timedelta(minutes=15)
        end = now + timedelta(hours=4)

        # Transition 1: Not Submitted -> Pending Host Approval (VMS-UC-010)
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Manish Malhotra",
                visitor_phone="9876501234",
                visitor_email="manish@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="1234-9876-5432",
                organization="Fashion Institute",
                host_id=host.user_id,
                purpose="Design Workshop",
                scheduled_start=start,
                scheduled_end=end,
            )
        )
        assert req.status == RequestStatus.PENDING_HOST_APPROVAL

        # Transition 2: Pending Host Approval -> Approved / Pass Active (VMS-UC-013)
        _decision, pass_obj = record_host_decision(
            HostDecisionDTO(
                request_id=req.request_id,
                host_id=host.user_id,
                outcome="APPROVE",
                allowed_start=start,
                allowed_end=end,
                permitted_zones=["MAIN_CAMPUS"],
            )
        )
        req.refresh_from_db()
        assert req.status == RequestStatus.APPROVED
        assert pass_obj.status == PassStatus.ACTIVE

        # Transition 3: Pass Active -> On-site (VMS-UC-018)
        verdict = validate_and_check_in_at_gate(
            GateValidationDTO(
                credential_data=pass_obj.credential_data,
                gate_id=gate.gate_id,
                verifier_id=701,
            )
        )
        assert verdict.allowed is True
        visit_log = VisitLog.objects.get(log_id=verdict.visit_id)
        assert visit_log.status == VisitStatus.ON_SITE

        # Transition 4: On-site -> Completed (VMS-UC-021)
        completed_log = check_out_at_gate(
            GateCheckoutDTO(
                pass_id=pass_obj.pass_id,
                gate_id=gate.gate_id,
                verifier_id=701,
            )
        )
        assert completed_log.status == VisitStatus.COMPLETED
        assert completed_log.check_out_time is not None

        pass_obj.refresh_from_db()
        req.refresh_from_db()
        assert pass_obj.status == PassStatus.COMPLETED
        assert req.status == RequestStatus.COMPLETED

    def test_wf_02_checkout_before_checkin_fails(self, host, gate):
        now = timezone.now()
        req = submit_pre_registration(
            PreRegisterDTO(
                visitor_name="Out of Order Visitor",
                visitor_phone="9988776655",
                visitor_email="ooo@example.com",
                id_doc_type="AADHAAR",
                id_doc_number="1122-3344-5566",
                organization="Visitor",
                host_id=host.user_id,
                purpose="Visit",
                scheduled_start=now - timedelta(hours=1),
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
        with pytest.raises(InvalidStateTransitionError):
            check_out_at_gate(
                GateCheckoutDTO(
                    pass_id=pass_obj.pass_id,
                    gate_id=gate.gate_id,
                    verifier_id=1,
                )
            )
