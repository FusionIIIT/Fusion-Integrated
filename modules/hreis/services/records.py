"""Atomic HR administrator maintenance of official employee service records.

The source of identity stays the directory/IAM. Only HR-owned service fields
are created or updated here; leave balance comes from the separate ledger.
"""

from __future__ import annotations

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory.contracts import get_users
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    ServiceRecordRevision,
)
from modules.hreis.services.authz import require

_ADMIN_ROLES = frozenset({"hradmin"})
_CREATE = "hreis.service_record.create"
_UPDATE = "hreis.service_record.update"
_EDITABLE = frozenset(
    {
        "appointment_details",
        "department",
        "designation_snapshot",
        "service_history",
        "retirement_status",
    }
)


def _validated_fields(fields: dict, *, creating: bool) -> dict:
    if not isinstance(fields, dict) or not fields:
        raise BadRequestError("Provide the official fields to record.", code="empty_service_fields")
    unknown = set(fields) - _EDITABLE
    if unknown:
        raise BadRequestError(
            "Only HR-owned service fields can be modified.", code="unsupported_service_fields"
        )
    if creating and not {
        "appointment_details",
        "department",
        "designation_snapshot",
        "service_history",
    } <= set(fields):
        raise BadRequestError(
            "The official service record is incomplete.", code="missing_service_fields"
        )
    for name, value in fields.items():
        if name in {"department", "designation_snapshot", "retirement_status"}:
            if (
                not isinstance(value, str)
                or (name != "retirement_status" and not value.strip())
                or len(value)
                > (120 if name == "department" else 100 if name == "retirement_status" else 150)
            ):
                raise BadRequestError(
                    f"Enter a valid {name.replace('_', ' ')}.", code="invalid_service_field"
                )
        elif name == "appointment_details" and not isinstance(value, dict):
            raise BadRequestError(
                "Appointment details must be a record.", code="invalid_appointment_details"
            )
        elif name == "service_history" and not isinstance(value, list):
            raise BadRequestError("Service history must be a list.", code="invalid_service_history")
    return fields


def _snapshot(record: EmployeeServiceRecord) -> dict:
    return {
        "appointment_details": record.appointment_details,
        "department": record.department,
        "designation_snapshot": record.designation_snapshot,
        "service_history": record.service_history,
        "retirement_status": record.retirement_status,
    }


def _audit(
    record: EmployeeServiceRecord, actor, action: str, idempotency_key: str, fields: dict
) -> None:
    AuditEvent.objects.create(
        event_key=f"service:{idempotency_key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=record.user_id,
        action=action,
        resource_kind="service_record",
        resource_id=record.pk,
        data={"changed_fields": sorted(fields), "revision": record.revision},
    )
    ServiceRecordRevision.objects.create(
        record=record,
        revision_number=record.revision,
        snapshot=_snapshot(record),
        actor_user_id=actor.user_id,
        actor_designation=actor.active_role,
    )


def _require_employee(user_id: int) -> None:
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise BadRequestError("Select a valid employee.", code="invalid_employee_id")
    employee = get_users([user_id]).get(user_id)
    if employee is None or employee.kind not in {"faculty", "staff"}:
        raise NotFoundError(
            "The employee is not in the authorized directory.", code="employee_not_found"
        )


@transaction.atomic
def create_record(
    actor, *, user_id: int, fields: dict, idempotency_key: str
) -> EmployeeServiceRecord:
    require(actor, _CREATE, allowed_roles=_ADMIN_ROLES)
    if user_id == actor.user_id:
        raise NotFoundError(
            "An HR administrator cannot create their own official record.",
            code="service_record_not_assigned",
        )
    validated = _validated_fields(fields, creating=True)
    _require_employee(user_id)
    if (
        not isinstance(idempotency_key, str)
        or not idempotency_key.strip()
        or len(idempotency_key) > 100
    ):
        raise BadRequestError("Provide an idempotency key.", code="missing_idempotency_key")
    if AuditEvent.objects.filter(event_key=f"service:{idempotency_key}").exists():
        raise ConflictError(
            "That service-record operation was already recorded.", code="operation_replayed"
        )
    if EmployeeServiceRecord.objects.filter(user_id=user_id).exists():
        raise ConflictError("An official service record already exists.", code="record_exists")
    record = EmployeeServiceRecord.objects.create(
        user_id=user_id,
        revision=1,
        **validated,
    )
    _audit(record, actor, "create", idempotency_key, validated)
    return record


@transaction.atomic
def update_record(
    actor, *, record_id: int, fields: dict, expected_revision: int, idempotency_key: str
) -> EmployeeServiceRecord:
    require(actor, _UPDATE, allowed_roles=_ADMIN_ROLES)
    validated = _validated_fields(fields, creating=False)
    if (
        not isinstance(idempotency_key, str)
        or not idempotency_key.strip()
        or len(idempotency_key) > 100
    ):
        raise BadRequestError("Provide an idempotency key.", code="missing_idempotency_key")
    record = (
        EmployeeServiceRecord.objects.select_for_update()
        .filter(
            pk=record_id,
        )
        .first()
    )
    if record is None:
        raise NotFoundError("The service record was not found.", code="record_not_found")
    if record.user_id == actor.user_id:
        raise NotFoundError(
            "An HR administrator cannot change their own official record.",
            code="service_record_not_assigned",
        )
    if record.revision != expected_revision:
        raise ConflictError(
            "This service record changed; refresh before editing.", code="stale_record_revision"
        )
    if AuditEvent.objects.filter(event_key=f"service:{idempotency_key}").exists():
        raise ConflictError(
            "That service-record operation was already recorded.", code="operation_replayed"
        )
    if "service_history" in validated:
        # Finalized appraisals enter this history through the appraisal service,
        # never through a general HR record edit. Preserve their exact snapshots.
        old_archives = [
            item
            for item in record.service_history
            if isinstance(item, dict) and item.get("kind") == "appraisal"
        ]
        new_archives = [
            item
            for item in validated["service_history"]
            if isinstance(item, dict) and item.get("kind") == "appraisal"
        ]
        if old_archives != new_archives:
            raise ConflictError(
                "A finalized appraisal archive cannot be added, modified, or removed here.",
                code="appraisal_archive_immutable",
            )
    for name, value in validated.items():
        setattr(record, name, value)
    record.revision += 1
    record.save(update_fields=[*validated, "revision", "updated_at"])
    _audit(record, actor, "update", idempotency_key, validated)
    return record
