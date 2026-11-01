"""Employee service record management (BR-HR-004, BR-HR-005, BR-HR-006)."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from modules.directory import contracts as directory
from modules.hreis.domain.leave import DEFAULT_LEAVE_QUOTAS
from modules.hreis.models import EmployeeServiceRecord
from modules.hreis.services.audit import log_hr_action


def get_or_create_service_record(user_id: int) -> EmployeeServiceRecord:
    record = EmployeeServiceRecord.objects.filter(user_id=user_id).first()
    if record:
        return record

    # Attempt to project details from directory
    users = directory.get_users([user_id])
    user_dto = users.get(user_id)

    dept = user_dto.department if user_dto and user_dto.department else "Administration"
    category = "faculty" if (user_dto and user_dto.kind == "faculty") else "staff"
    designation = "Assistant Professor" if category == "faculty" else "Assistant"
    emp_id = user_dto.username if user_dto else f"EMP{user_id:04d}"

    record = EmployeeServiceRecord.objects.create(
        user_id=user_id,
        employee_id=emp_id,
        department=dept,
        designation=designation,
        category=category,
        leave_balances=dict(DEFAULT_LEAVE_QUOTAS),
        retirement_status="active",
        service_history=[
            {
                "event": "Initial Appointment",
                "designation": designation,
                "department": dept,
                "date": "2024-01-01",
            }
        ],
    )
    return record


@transaction.atomic
def update_service_record(
    record_id: int,
    data: dict[str, Any],
    actor_id: int,
    actor_username: str,
    actor_role: str,
) -> EmployeeServiceRecord:
    record = EmployeeServiceRecord.objects.select_for_update().get(id=record_id)

    allowed_fields = [
        "department",
        "designation",
        "category",
        "appointment_date",
        "retirement_date",
        "retirement_status",
        "leave_balances",
        "cpda_balance",
        "ltc_eligible_block",
        "is_active",
    ]

    changed = {}
    for field in allowed_fields:
        if field in data:
            old_val = getattr(record, field)
            new_val = data[field]
            if old_val != new_val:
                changed[field] = {"old": old_val, "new": new_val}
                setattr(record, field, new_val)

    if "history_entry" in data:
        entry = data["history_entry"]
        if isinstance(entry, dict):
            hist = list(record.service_history or [])
            hist.append(entry)
            record.service_history = hist
            changed["history_entry"] = entry

    record.save()

    log_hr_action(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action="update_service_record",
        entity_type="service_record",
        entity_id=record.id,
        details={"changes": changed, "target_user_id": record.user_id},
    )
    return record
