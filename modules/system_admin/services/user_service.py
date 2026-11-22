"""User lifecycle management service."""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from django.db import transaction
from django.db.models import Max

from modules.system_admin.domain.exceptions import (
    DomainValidationError,
    DuplicateUserError,
    UserNotFoundError,
)
from modules.system_admin.domain.models import UserIdentity
from modules.system_admin.domain.rules import (
    validate_institute_email,
    validate_institute_id,
    validate_user_type_data,
)
from modules.system_admin.domain.state_machines import transition_user_state
from modules.system_admin.models.audit import SystemAuditLog
from modules.system_admin.models.user_account import UserAccount


def _next_user_id() -> int:
    max_id = UserAccount.objects.aggregate(m=Max("user_id"))["m"]
    return (max_id or 1000) + 1


@transaction.atomic
def create_basic_user(
    *,
    institute_id: str,
    username: str,
    email: str,
    user_type: str,
    name: str = "",
    contact_number: str = "",
    department: str = "",
    programme: str = "",
    discipline: str = "",
    batch_year: int | None = None,
    user_id: int | None = None,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> UserAccount:
    """Create a basic user account (Student, Faculty, Staff) following BR-SA-001..003."""
    # 1. Domain validations
    validate_institute_id(institute_id)
    validate_institute_email(email)

    clean_u_type = user_type.strip().lower()
    final_dept = department.strip()
    final_prog = programme.strip()
    final_disc = discipline.strip()
    final_year = batch_year

    if clean_u_type == "student":
        if not final_prog:
            final_prog = "B.Tech"
        if not final_disc:
            final_disc = "CSE"
        if final_year is None:
            final_year = date.today().year
    elif clean_u_type in ("faculty", "staff"):
        if not final_dept:
            final_dept = "Computer Science and Engineering"

    identity = UserIdentity(
        institute_id=institute_id.strip(),
        username=username.strip(),
        email=email.strip().lower(),
        user_type=clean_u_type,
        name=name.strip(),
        department=final_dept,
        programme=final_prog,
        discipline=final_disc,
        batch_year=final_year,
    )
    validate_user_type_data(identity)

    # 2. Uniqueness checks
    if UserAccount.objects.filter(institute_id=identity.institute_id).exists():
        raise DuplicateUserError(
            f"User with Institute ID '{identity.institute_id}' already exists."
        )
    if UserAccount.objects.filter(username=identity.username).exists():
        raise DuplicateUserError(
            f"User with username '{identity.username}' already exists."
        )

    assigned_id = user_id if user_id is not None else _next_user_id()

    # 3. Model creation
    user = UserAccount.objects.create(
        user_id=assigned_id,
        institute_id=identity.institute_id,
        username=identity.username,
        email=identity.email,
        user_type=identity.user_type,
        name=identity.name,
        contact_number=contact_number.strip(),
        department=identity.department,
        programme=identity.programme,
        discipline=identity.discipline,
        batch_year=identity.batch_year,
        status="active",
    )

    # 4. Audit trail
    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.user.add",
        target_id=str(user.user_id),
        ip_address=ip_address,
        result="success",
        context={
            "institute_id": user.institute_id,
            "username": user.username,
            "user_type": user.user_type,
        },
    )

    return user


@transaction.atomic
def update_user_profile(
    *,
    user_id: int,
    data: dict[str, Any],
    actor_id: int = 1,
    ip_address: str | None = None,
) -> UserAccount:
    """Update editable user profile fields. Institute ID is immutable (BR-SA-001)."""
    try:
        user = UserAccount.objects.select_for_update().get(user_id=user_id)
    except UserAccount.DoesNotExist as err:
        raise UserNotFoundError(f"User {user_id} does not exist.") from err

    # Immutability check
    if "institute_id" in data and data["institute_id"] != user.institute_id:
        raise DomainValidationError("Institute ID is immutable and cannot be modified.")

    if "email" in data:
        email = data["email"].strip().lower()
        validate_institute_email(email)
        user.email = email

    editable_fields = [
        "name",
        "contact_number",
        "department",
        "programme",
        "discipline",
        "batch_year",
    ]
    for field in editable_fields:
        if field in data:
            setattr(user, field, data[field])

    # Re-validate domain data constraints
    identity = UserIdentity(
        institute_id=user.institute_id,
        username=user.username,
        email=user.email,
        user_type=user.user_type,
        name=user.name,
        department=user.department,
        programme=user.programme,
        discipline=user.discipline,
        batch_year=user.batch_year,
    )
    validate_user_type_data(identity)

    user.save()

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.user.change",
        target_id=str(user.user_id),
        ip_address=ip_address,
        result="success",
        context={"updated_fields": list(data.keys())},
    )

    return user


@transaction.atomic
def deactivate_user(
    *,
    user_id: int,
    reason: str,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> UserAccount:
    """Deactivate an active user account (UC-SA-004, BR-SA-015)."""
    try:
        user = UserAccount.objects.select_for_update().get(user_id=user_id)
    except UserAccount.DoesNotExist as err:
        raise UserNotFoundError(f"User {user_id} does not exist.") from err

    next_state = transition_user_state(user.status, "deactivate", "super_admin")
    user.status = next_state
    user.deactivated_at = datetime.now(UTC)
    user.save(update_fields=["status", "deactivated_at", "updated_at"])

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.user.change",
        target_id=str(user.user_id),
        ip_address=ip_address,
        result="success",
        context={"transition": "deactivate", "reason": reason},
    )

    return user


@transaction.atomic
def reactivate_user(
    *,
    user_id: int,
    reason: str,
    actor_id: int = 1,
    ip_address: str | None = None,
) -> UserAccount:
    """Reactivate a deactivated user account (UC-SA-005, BW-SA-06)."""
    try:
        user = UserAccount.objects.select_for_update().get(user_id=user_id)
    except UserAccount.DoesNotExist as err:
        raise UserNotFoundError(f"User {user_id} does not exist.") from err

    next_state = transition_user_state(user.status, "reactivate", "super_admin")
    user.status = next_state
    user.deactivated_at = None
    user.save(update_fields=["status", "deactivated_at", "updated_at"])

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.user.change",
        target_id=str(user.user_id),
        ip_address=ip_address,
        result="success",
        context={"transition": "reactivate", "reason": reason},
    )

    return user


@transaction.atomic
def bulk_create_users(
    *,
    rows: list[dict[str, Any]],
    actor_id: int = 1,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Bulk create users from parsed CSV records (BR-SA-030). Batch size <= 1000."""
    if not rows:
        raise DomainValidationError("No user records provided for bulk creation.")
    if len(rows) > 1000:
        raise DomainValidationError("Bulk user creation batch cannot exceed 1000 records.")

    created_users: list[UserAccount] = []
    errors: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        try:
            user = create_basic_user(
                institute_id=row.get("institute_id", ""),
                username=row.get("username", ""),
                email=row.get("email", ""),
                user_type=row.get("user_type", ""),
                name=row.get("name", ""),
                contact_number=row.get("contact_number", ""),
                department=row.get("department", ""),
                programme=row.get("programme", ""),
                discipline=row.get("discipline", ""),
                batch_year=row.get("batch_year"),
                user_id=row.get("user_id"),
                actor_id=actor_id,
                ip_address=ip_address,
            )
            created_users.append(user)
        except (DomainValidationError, DuplicateUserError, ValueError, TypeError) as e:
            errors.append({"row": idx, "error": str(e)})

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.user.add",
        target_id=f"bulk_{len(created_users)}",
        ip_address=ip_address,
        result="success" if not errors else "partial",
        context={
            "submitted_count": len(rows),
            "created_count": len(created_users),
            "error_count": len(errors),
        },
    )

    return {
        "created_count": len(created_users),
        "error_count": len(errors),
        "errors": errors,
    }
