"""Core workflow operations for VMS."""
import hashlib
import uuid
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from modules.vms.models import (
    Visitor,
    Host,
    VisitRequest,
    HostDecision,
    VisitorPass,
    VisitLog,
    CampusGate,
    RequestStatus,
    PassStatus,
    PassType,
    VisitStatus,
)
from modules.vms.domain.rules import (
    validate_time_window,
    check_blacklist_guard,
    validate_pass_gate_access,
    validate_checkout_transition,
)
from modules.vms.domain.errors import (
    InvalidStateTransitionError,
    VMSDomainError,
)
from modules.vms.selectors.queries import check_is_blacklisted
from modules.vms.contracts import (
    PreRegisterDTO,
    HostDecisionDTO,
    GateValidationDTO,
    GateCheckoutDTO,
    ValidationVerdictDTO,
)


def generate_credential_token(pass_id: str, secret: str = "vms_secret") -> str:
    raw = f"{pass_id}:{secret}:{uuid.uuid4().hex}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@transaction.atomic
def submit_pre_registration(dto: PreRegisterDTO) -> VisitRequest:
    """VMS-C-01: PreRegisterVisitControl realizing VMS-UC-010."""
    validate_time_window(dto.scheduled_start, dto.scheduled_end)
    
    is_blocked, reason = check_is_blacklisted(dto.visitor_phone, dto.id_doc_number)
    check_blacklist_guard(is_blocked, reason)

    visitor, _ = Visitor.objects.get_or_create(
        phone=dto.visitor_phone,
        defaults={
            "full_name": dto.visitor_name,
            "email": dto.visitor_email,
            "id_document_type": dto.id_doc_type,
            "id_document_number": dto.id_doc_number,
            "organization": dto.organization,
        },
    )

    host = Host.objects.filter(user_id=dto.host_id).first()
    if not host:
        host = Host.objects.create(
            user_id=dto.host_id,
            full_name="Assigned Host",
            email="host@iiitdmj.ac.in",
            department="General",
        )

    req = VisitRequest.objects.create(
        visitor=visitor,
        host=host,
        purpose=dto.purpose,
        scheduled_start_time=dto.scheduled_start,
        scheduled_end_time=dto.scheduled_end,
        status=RequestStatus.PENDING_HOST_APPROVAL,
        remarks=dto.remarks,
    )
    return req


@transaction.atomic
def record_host_decision(dto: HostDecisionDTO) -> tuple[HostDecision, VisitorPass | None]:
    """VMS-C-02: DecideVisitRequestControl realizing VMS-UC-013."""
    req = VisitRequest.objects.select_for_update().get(request_id=dto.request_id)
    if req.status != RequestStatus.PENDING_HOST_APPROVAL:
        raise InvalidStateTransitionError(f"Request status is '{req.status}', expected 'PENDING_HOST_APPROVAL'.")

    host = req.host
    decision = HostDecision.objects.create(
        request=req,
        host=host,
        outcome=dto.outcome,
        decided_at=timezone.now(),
        allowed_start_time=dto.allowed_start or req.scheduled_start_time,
        allowed_end_time=dto.allowed_end or req.scheduled_end_time,
        permitted_zones=dto.permitted_zones or ["MAIN_CAMPUS"],
        special_instructions=dto.special_instructions,
    )

    pass_obj = None
    if dto.outcome == "APPROVE":
        req.status = RequestStatus.APPROVED
        req.save(update_fields=["status", "updated_at"])

        pass_id = uuid.uuid4().hex[:12].upper()
        cred_token = generate_credential_token(pass_id)

        pass_obj = VisitorPass.objects.create(
            pass_id=pass_id,
            request=req,
            pass_type=PassType.PRE_REGISTERED,
            credential_data=cred_token,
            valid_from=decision.allowed_start_time,
            valid_until=decision.allowed_end_time,
            status=PassStatus.ACTIVE,
            permitted_zones=decision.permitted_zones,
        )
    else:
        req.status = RequestStatus.REJECTED
        req.save(update_fields=["status", "updated_at"])

    return decision, pass_obj


@transaction.atomic
def validate_and_check_in_at_gate(dto: GateValidationDTO) -> ValidationVerdictDTO:
    """VMS-C-03: GateValidationControl realizing VMS-UC-018."""
    pass_obj = VisitorPass.objects.select_for_update().filter(credential_data=dto.credential_data).first()
    if not pass_obj:
        return ValidationVerdictDTO(allowed=False, reason="Invalid credential token: pass not found.")

    is_blocked, bl_reason = check_is_blacklisted(
        pass_obj.request.visitor.phone,
        pass_obj.request.visitor.id_document_number,
    )
    if is_blocked:
        pass_obj.status = PassStatus.DEACTIVATED
        pass_obj.save(update_fields=["status", "updated_at"])
        return ValidationVerdictDTO(
            allowed=False,
            reason=f"Security alert: Visitor flagged in blacklist ({bl_reason}). Pass deactivated.",
            pass_id=pass_obj.pass_id,
        )

    gate = CampusGate.objects.filter(gate_id=dto.gate_id).first()
    if not gate:
        gate = CampusGate.objects.create(
            gate_id=dto.gate_id,
            gate_name=f"Gate {dto.gate_id}",
            location_zone="MAIN_CAMPUS",
            is_operational=True,
        )

    now = timezone.now()
    try:
        validate_pass_gate_access(
            pass_status=pass_obj.status,
            valid_from=pass_obj.valid_from,
            valid_until=pass_obj.valid_until,
            permitted_zones=pass_obj.permitted_zones,
            gate_zone=gate.location_zone,
            now=now,
        )
    except VMSDomainError as e:
        return ValidationVerdictDTO(
            allowed=False,
            reason=e.message,
            pass_id=pass_obj.pass_id,
            pass_status=pass_obj.status,
        )

    visit_log = VisitLog.objects.create(
        visitor_pass=pass_obj,
        entry_gate=gate,
        check_in_time=now,
        status=VisitStatus.ON_SITE,
        verifier_notes=dto.verifier_notes,
    )

    return ValidationVerdictDTO(
        allowed=True,
        reason="Gate validation successful. Entry granted.",
        visitor_name=pass_obj.request.visitor.full_name,
        pass_id=pass_obj.pass_id,
        pass_status=pass_obj.status,
        permitted_zones=pass_obj.permitted_zones,
        visit_id=visit_log.log_id,
    )


@transaction.atomic
def check_out_at_gate(dto: GateCheckoutDTO) -> VisitLog:
    """VMS-C-04: GateCheckoutControl realizing VMS-UC-021."""
    visit_log = VisitLog.objects.select_for_update().filter(
        visitor_pass__pass_id=dto.pass_id,
        status=VisitStatus.ON_SITE,
    ).first()

    if not visit_log:
        raise InvalidStateTransitionError(f"No active on-site visit session found for Pass {dto.pass_id}.")

    validate_checkout_transition(visit_log.status)

    gate = CampusGate.objects.filter(gate_id=dto.gate_id).first()
    if not gate:
        gate = CampusGate.objects.create(
            gate_id=dto.gate_id,
            gate_name=f"Gate {dto.gate_id}",
            location_zone="MAIN_CAMPUS",
            is_operational=True,
        )

    now = timezone.now()
    visit_log.check_out_time = now
    visit_log.exit_gate = gate
    visit_log.status = VisitStatus.COMPLETED
    if dto.verifier_notes:
        visit_log.verifier_notes = (visit_log.verifier_notes + "\n" + dto.verifier_notes).strip()
    visit_log.save(update_fields=["check_out_time", "exit_gate", "status", "verifier_notes", "updated_at"])

    # Deactivate / mark completed the visitor pass
    pass_obj = visit_log.visitor_pass
    pass_obj.status = PassStatus.COMPLETED
    pass_obj.save(update_fields=["status", "updated_at"])

    # Mark request as completed
    req = pass_obj.request
    req.status = RequestStatus.COMPLETED
    req.save(update_fields=["status", "updated_at"])

    return visit_log
