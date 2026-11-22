"""Audit observation service enforcing IAA-BR-301, IAA-BR-302, IAA-UC-501..503."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.iaa.domain.state_machine import transition_audit_observation
from modules.iaa.models import AuditObservation, AuditObservationStatus
from modules.iaa.services.audit_trail import record_audit_log


def raise_audit_observation(
    auditor_id: int,
    acting_role: str,
    department: str,
    title: str,
    description: str,
    reference_type: str = "",
    reference_id: int | None = None,
) -> AuditObservation:
    if not title or not title.strip():
        raise BadRequestError("Title is mandatory for raising an audit observation.")

    with transaction.atomic():
        obs = AuditObservation.objects.create(
            auditor_id=auditor_id,
            department=department,
            title=title,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            status=AuditObservationStatus.OPEN,
        )
        record_audit_log(
            user_id=auditor_id,
            acting_role=acting_role,
            action="raise_audit_observation",
            target_type="audit_observation",
            target_id=obs.id,
            resulting_status=AuditObservationStatus.OPEN,
            details={"title": title, "department": department},
        )
        return obs


def respond_to_audit_observation(
    observation_id: int,
    user_id: int,
    acting_role: str,
    response_text: str,
) -> AuditObservation:
    if not response_text or not response_text.strip():
        raise BadRequestError("Response text is mandatory.")

    with transaction.atomic():
        obs = AuditObservation.objects.select_for_update().filter(id=observation_id).first()
        if not obs:
            raise NotFoundError("Audit observation not found.")

        new_status = transition_audit_observation(obs.status, "respond", "basic_user")
        obs.status = new_status
        obs.response_text = response_text
        obs.responded_by_id = user_id
        obs.responded_at = timezone.now()
        obs.save()

        record_audit_log(
            user_id=user_id,
            acting_role=acting_role,
            action="respond_audit_observation",
            target_type="audit_observation",
            target_id=obs.id,
            resulting_status=new_status,
        )
        return obs


def review_and_close_observation(
    observation_id: int,
    auditor_id: int,
    acting_role: str,
    is_satisfactory: bool,
    remarks: str,
) -> AuditObservation:
    with transaction.atomic():
        obs = AuditObservation.objects.select_for_update().filter(id=observation_id).first()
        if not obs:
            raise NotFoundError("Audit observation not found.")

        event = "close" if is_satisfactory else "reject_response"
        new_status = transition_audit_observation(obs.status, event, "auditor")
        obs.status = new_status
        obs.closure_remarks = remarks
        if new_status == AuditObservationStatus.CLOSED:
            obs.closed_at = timezone.now()
        obs.save()

        record_audit_log(
            user_id=auditor_id,
            acting_role=acting_role,
            action="close_audit_observation" if is_satisfactory else "reopen_audit_observation",
            target_type="audit_observation",
            target_id=obs.id,
            resulting_status=new_status,
            details={"remarks": remarks, "is_satisfactory": is_satisfactory},
        )
        return obs
