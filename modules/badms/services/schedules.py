from datetime import UTC, datetime

from django.db import models, transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.badms.domain.schedules import (
    InvalidScheduleParametersError,
    ScheduleConflictError,
    validate_cron_expression,
    validate_schedule_conflict,
)
from modules.badms.models import BackupSchedule
from modules.badms.services.audit import log_audit_event


@transaction.atomic
def create_backup_schedule(
    actor,
    name: str,
    scope_type: str,
    dataset_name: str,
    cron_expression: str,
    data_classification_filter: str = "",
) -> BackupSchedule:
    user_id = getattr(actor, "user_id", None) or 0
    try:
        validate_cron_expression(cron_expression)
    except InvalidScheduleParametersError as err:
        raise BadRequestError(str(err)) from err

    if scope_type not in (BackupSchedule.SCOPE_GLOBAL, BackupSchedule.SCOPE_LOCAL):
        raise BadRequestError("Scope type must be either 'global' or 'local'.")

    # Conflict validation: reject if an active schedule already exists for the same
    # dataset and scope (AFR-BA-014)
    now = datetime.now(UTC)
    existing_active = BackupSchedule.objects.select_for_update().filter(
        dataset_name=dataset_name, scope_type=scope_type, is_active=True
    )
    try:
        validate_schedule_conflict(existing_active.exists(), dataset_name, scope_type)
    except ScheduleConflictError as err:
        raise ConflictError(str(err)) from err

    version = (
        BackupSchedule.objects.filter(dataset_name=dataset_name, scope_type=scope_type).aggregate(
            max_v=models.Max("version")
        )["max_v"]
        or 0
    ) + 1

    schedule = BackupSchedule.objects.create(
        name=name,
        scope_type=scope_type,
        dataset_name=dataset_name,
        cron_expression=cron_expression,
        data_classification_filter=data_classification_filter,
        is_active=True,
        created_by_user_id=user_id,
        version=version,
        effective_from=now,
    )
    log_audit_event("backup_schedule_created", actor, "BackupSchedule", schedule.id)
    return schedule


@transaction.atomic
def update_backup_schedule(
    actor,
    schedule_id: int,
    name: str | None = None,
    cron_expression: str | None = None,
    data_classification_filter: str | None = None,
) -> BackupSchedule:
    schedule = (
        BackupSchedule.objects.select_for_update().filter(id=schedule_id, is_active=True).first()
    )
    if not schedule:
        raise NotFoundError("Backup schedule not found.")

    if cron_expression is not None:
        try:
            validate_cron_expression(cron_expression)
        except InvalidScheduleParametersError as err:
            raise BadRequestError(str(err)) from err
        schedule.cron_expression = cron_expression

    if name is not None:
        schedule.name = name
    if data_classification_filter is not None:
        schedule.data_classification_filter = data_classification_filter

    schedule.save()
    log_audit_event("backup_schedule_updated", actor, "BackupSchedule", schedule.id)
    return schedule
