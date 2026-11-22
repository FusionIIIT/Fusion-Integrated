"""User account creation and update service."""

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.superadmin.domain.exceptions import DomainValidationError
from modules.superadmin.domain.validators import (
    validate_institute_email,
    validate_institute_id,
    validate_user_type_data,
)
from modules.superadmin.models import UserAccountRecord, UserActivationStatus
from modules.superadmin.services.audit import log_audit_event


@transaction.atomic
def create_user_account(
    *,
    actor_user_id: int,
    user_id: int,
    institute_id: str,
    email: str,
    user_type: str,
    department: str = "",
    program: str = "",
    batch: str = "",
    ip_address: str | None = None,
) -> UserAccountRecord:
    # UC-SA-001: Validate and create basic user account.
    try:
        validate_institute_id(institute_id)
        validate_institute_email(email)
        validate_user_type_data(user_type, department, program, batch)
    except DomainValidationError as e:
        raise BadRequestError(str(e), code="validation_error") from e

    if UserAccountRecord.objects.filter(user_id=user_id).exists():
        raise ConflictError(f"User ID {user_id} is already registered.", code="duplicate_user_id")

    if UserAccountRecord.objects.filter(institute_id=institute_id).exists():
        raise ConflictError(
            f"Institute ID {institute_id!r} is already registered across Fusion.",
            code="duplicate_institute_id",
        )

    if UserAccountRecord.objects.filter(email=email).exists():
        raise ConflictError(f"Email {email!r} is already registered.", code="duplicate_email")

    account = UserAccountRecord.objects.create(
        user_id=user_id,
        institute_id=institute_id,
        email=email,
        user_type=user_type.upper(),
        department=department,
        program=program,
        batch=batch,
        activation_status=UserActivationStatus.ACTIVE,
    )

    log_audit_event(
        event_type="USER_CREATED",
        actor_user_id=actor_user_id,
        target_entity="UserAccountRecord",
        target_id=str(user_id),
        ip_address=ip_address,
        action_details={"institute_id": institute_id, "user_type": user_type},
    )
    return account


@transaction.atomic
def update_user_profile(
    *,
    actor_user_id: int,
    user_id: int,
    department: str | None = None,
    program: str | None = None,
    batch: str | None = None,
    ip_address: str | None = None,
) -> UserAccountRecord:
    # UC-SA-003: Update editable profile fields; preserve immutable identity.
    account = UserAccountRecord.objects.select_for_update().filter(user_id=user_id).first()
    if not account:
        raise NotFoundError(f"User with ID {user_id} does not exist.", code="user_not_found")

    changes = {}
    if department is not None and department != account.department:
        changes["department"] = department
        account.department = department
    if program is not None and program != account.program:
        changes["program"] = program
        account.program = program
    if batch is not None and batch != account.batch:
        changes["batch"] = batch
        account.batch = batch

    if changes:
        account.save()
        log_audit_event(
            event_type="USER_PROFILE_UPDATED",
            actor_user_id=actor_user_id,
            target_entity="UserAccountRecord",
            target_id=str(user_id),
            ip_address=ip_address,
            action_details=changes,
        )
    return account
