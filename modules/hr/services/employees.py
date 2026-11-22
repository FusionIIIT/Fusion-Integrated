from __future__ import annotations

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.hr.models import APPRAISAL_ARCHIVE_TYPE, EmployeeRecord
from modules.hr.services import authz
from modules.hr.services.common import audit

EDITABLE_FIELDS = {
    "employment_status",
    "department",
    "designation",
    "appointment_type",
    "appointment_start_date",
    "appointment_end_date",
    "appointment_details",
    "service_history",
    "retirement_status",
}


def _audit_snapshot(values: dict) -> dict:
    """Store date-valued employee fields as JSON-compatible ISO strings."""
    return {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in values.items()
    }


def employee_record(*, user_id: int, principal) -> EmployeeRecord:
    from modules.hr.selectors.employees import employee_record_for_user

    record = employee_record_for_user(user_id=user_id, principal=principal)
    if record is None:
        raise NotFoundError("No employee service record is available.")
    return record


@transaction.atomic
def create_employee_record(*, actor, user_id: int, **fields) -> EmployeeRecord:
    authz.require(actor, "hr.employee.create")
    if {
        "appointment_type",
        "appointment_start_date",
        "appointment_end_date",
        "appointment_details",
    } & set(fields):
        authz.require(actor, "hr.employment.manage")
    person = directory.get_users([user_id]).get(user_id)
    if (
        person is None
        or person.kind not in {"faculty", "staff"}
        or user_id not in directory.held_employee_ids()
    ):
        raise NotFoundError("No active faculty or staff identity was found.")
    if EmployeeRecord.objects.filter(user_id=user_id).exists():
        raise ConflictError(
            "An employee service record already exists.", code="employee_record_exists"
        )
    if set(fields) - EDITABLE_FIELDS:
        raise ValueError("Unsupported employee record fields.")

    record = EmployeeRecord.objects.create(
        user_id=user_id,
        employee_category=person.kind,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
        **fields,
    )
    audit(
        actor=actor,
        entity_type="employee",
        entity_id=record.pk,
        action="employee.created",
        details={"user_id": user_id},
    )
    return record


@transaction.atomic
def update_employee_record(*, actor, user_id: int, changes: dict) -> EmployeeRecord:
    authz.require(actor, "hr.employee.update")
    if {
        "appointment_type",
        "appointment_start_date",
        "appointment_end_date",
        "appointment_details",
    } & set(changes):
        authz.require(actor, "hr.employment.manage")
    record = EmployeeRecord.objects.select_for_update().filter(user_id=user_id).first()
    if record is None:
        raise NotFoundError("No employee service record is available.")
    if not changes or set(changes) - EDITABLE_FIELDS:
        raise ConflictError(
            "The submitted employee fields are not editable.", code="invalid_employee_update"
        )
    if "service_history" in changes:
        archived = [
            entry
            for entry in record.service_history
            if isinstance(entry, dict) and entry.get("record_type") == APPRAISAL_ARCHIVE_TYPE
        ]
        requested_archives = [
            entry
            for entry in changes["service_history"]
            if isinstance(entry, dict) and entry.get("record_type") == APPRAISAL_ARCHIVE_TYPE
        ]
        if archived != requested_archives:
            raise ConflictError(
                "Finalized appraisal archive entries cannot be changed.",
                code="appraisal_archive_immutable",
            )

    before = {key: getattr(record, key) for key in changes}
    for key, value in changes.items():
        setattr(record, key, value)
    record.updated_by_user_id = actor.user_id
    record.save(update_fields=[*changes, "updated_by_user_id", "updated_at"])
    audit(
        actor=actor,
        entity_type="employee",
        entity_id=record.pk,
        action="employee.updated",
        details={"before": _audit_snapshot(before), "after": _audit_snapshot(changes)},
    )
    return record
