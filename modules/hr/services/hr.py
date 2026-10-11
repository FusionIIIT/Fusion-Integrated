"""HR services — all writes go through here.

Raises domain exceptions, never DRF exceptions, so they stay callable from
tasks and commands.
"""
from __future__ import annotations

import datetime
import logging

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.hr.models import Department, EmploymentContract
from modules.hr.selectors import hr as selectors

log = logging.getLogger("fusion.hr.services")


@transaction.atomic
def create_department(
    *,
    name: str,
    code: str,
    parent_id: int | None = None,
    head_user_id: int | None = None,
    actor_user_id: int,
) -> Department:
    if Department.objects.filter(code=code).exists():
        raise ConflictError(f"Department code '{code}' is already taken.", code="dept_code_taken")
    if Department.objects.filter(name=name).exists():
        raise ConflictError(f"Department name '{name}' is already taken.", code="dept_name_taken")

    parent = None
    if parent_id is not None:
        parent = selectors.department_by_id(parent_id)
        if parent is None:
            raise NotFoundError("Parent department not found.")

    dept = Department.objects.create(
        name=name,
        code=code,
        parent=parent,
        head_user_id=head_user_id,
    )
    log.info("hr.department.created dept=%d code=%s by=%d", dept.pk, dept.code, actor_user_id)
    return dept


@transaction.atomic
def create_contract(
    *,
    user_id: int,
    department_id: int,
    title: str,
    kind: str,
    starts_on: datetime.date,
    actor_user_id: int,
    ends_on: datetime.date | None = None,
) -> EmploymentContract:
    dept = selectors.department_by_id(department_id)
    if dept is None:
        raise NotFoundError("Department not found.")

    # Guard: only one active contract per person
    active = selectors.active_contract_for_user(user_id)
    if active is not None:
        raise ConflictError(
            f"User {user_id} already has an active contract (#{active.pk}). End it first.",
            code="active_contract_exists",
        )

    if ends_on and ends_on < starts_on:
        raise ConflictError("ends_on cannot be earlier than starts_on.", code="dates_invalid")

    contract = EmploymentContract.objects.create(
        user_id=user_id,
        department=dept,
        title=title,
        kind=kind,
        status="active",
        starts_on=starts_on,
        ends_on=ends_on,
    )
    log.info("hr.contract.created contract=%d user=%d dept=%d by=%d",
             contract.pk, user_id, department_id, actor_user_id)
    return contract


@transaction.atomic
def end_contract(
    *,
    contract_id: int,
    ends_on: datetime.date,
    reason: str,
    actor_user_id: int,
) -> EmploymentContract:
    contract = (
        EmploymentContract.objects.select_for_update()
        .filter(pk=contract_id).first()
    )
    if contract is None:
        raise NotFoundError("Contract not found.")

    if contract.status != "active":
        raise ConflictError(
            f"Cannot end contract #{contract_id} because it is already {contract.status}.",
            code="contract_not_active",
        )

    if ends_on < contract.starts_on:
        raise ConflictError("ends_on cannot be earlier than starts_on.", code="dates_invalid")

    contract.status = "ended"
    contract.ends_on = ends_on
    contract.ended_by_user_id = actor_user_id
    contract.end_reason = reason[:300]
    contract.save(update_fields=["status", "ends_on", "ended_by_user_id", "end_reason", "updated_at"])

    log.info("hr.contract.ended contract=%d user=%d by=%d", contract.pk, contract.user_id, actor_user_id)
    return contract
