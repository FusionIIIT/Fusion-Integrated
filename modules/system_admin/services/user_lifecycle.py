"""User lifecycle and bulk operations service for system_admin."""
from __future__ import annotations

import csv
import io
import secrets
from collections.abc import Sequence
from typing import Any, Dict, Optional

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from modules.system_admin.constants import (
    AuditAction,
    AuditResult,
    NotificationChannel,
    RoleAssignmentState,
    RoleRevocationType,
    UserLifecycleStatus,
)
from modules.system_admin.domain import validators
from modules.system_admin.domain.dataclasses import UserCreationSpec
from modules.system_admin.domain.exceptions import (
    BulkLimitExceededError,
    DomainError,
    IdentityValidationError,
    ImmutabilityViolationError,
)
from modules.system_admin.models import (
    BasicUser,
    RoleAssignment,
    SuperAdminAuditLog,
    UserProfile,
    UserStatusHistory,
)
from modules.system_admin.services import notifications


def create_basic_user(
    spec: UserCreationSpec, performed_by_id: int, ip_address: Optional[str] = None
) -> BasicUser:
    """Create a new Student, Faculty, or Staff basic user (UC-SA-001, CFR-SA-001)."""
    validators.validate_user_type_required_data(spec)

    # Validate uniqueness
    if BasicUser.objects.filter(institute_id=spec.institute_id).exists():
        raise IdentityValidationError(f"Institute ID '{spec.institute_id}' already exists (BR-SA-001).")
    if BasicUser.objects.filter(email=spec.institute_email).exists():
        raise IdentityValidationError(f"Email '{spec.institute_email}' already exists (BR-SA-002).")

    username = spec.institute_id.lower()
    if BasicUser.objects.filter(username=username).exists():
        username = f"{username}_{secrets.token_hex(2)}"

    temp_password = secrets.token_urlsafe(12)
    pw_hash = make_password(temp_password)

    with transaction.atomic():
        user = BasicUser.objects.create(
            username=username,
            institute_id=spec.institute_id,
            email=spec.institute_email,
            kind=spec.user_kind,
            is_active=True,
            status=UserLifecycleStatus.ACTIVE,
            password_hash=pw_hash,
            date_of_joining=spec.date_of_joining,
            expected_completion_date=spec.expected_completion_date,
        )

        UserProfile.objects.create(
            user=user,
            display_name=spec.name,
            contact_number=spec.contact_number,
            department=spec.department,
            programme=spec.programme,
            discipline=spec.discipline,
            batch_year=spec.batch_year,
            employee_id=spec.employee_id,
        )

        UserStatusHistory.objects.create(
            user=user,
            from_status=UserLifecycleStatus.ACTIVE,
            to_status=UserLifecycleStatus.ACTIVE,
            changed_by=performed_by_id,
            reason="Account created",
        )

        # Welcome notification with credentials (AFR-SA-006..009)
        notifications.queue_notification(
            recipient_id=user.id,
            email=user.email,
            channel=NotificationChannel.EMAIL,
            template_code="welcome_credentials",
            subject="Welcome to Fusion ERP — Account Created",
            body=(
                f"Hello {spec.name},\n\nYour account has been created.\n"
                f"Username: {user.username}\nTemporary Password: {temp_password}\n"
                "Please log in and change your password."
            ),
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.USER_CREATE,
            target_user_id=user.id,
            ip_address=ip_address,
            result=AuditResult.SUCCESS,
            reason="Created basic user account",
        )

    return user


def update_basic_user_profile(
    user_id: int, updates: Dict[str, Any], performed_by_id: int
) -> BasicUser:
    """Update editable profile data while preserving immutable fields (UC-SA-003, CFR-SA-002, BR-SA-001)."""
    user = BasicUser.objects.select_related("profile").get(id=user_id)

    # Immutability check
    if "institute_id" in updates and updates["institute_id"] != user.institute_id:
        raise ImmutabilityViolationError("institute_id")

    if "email" in updates:
        new_email = updates["email"]
        validators.validate_institute_email(new_email)
        if BasicUser.objects.filter(email=new_email).exclude(id=user.id).exists():
            raise IdentityValidationError(f"Email '{new_email}' already in use.")
        user.email = new_email

    profile = user.profile
    for field in ["display_name", "contact_number", "department", "programme", "discipline", "batch_year", "employee_id"]:
        if field in updates:
            setattr(profile, field, updates[field])

    with transaction.atomic():
        user.save()
        profile.save()
        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.USER_UPDATE,
            target_user_id=user.id,
            result=AuditResult.SUCCESS,
            reason="Updated profile data",
        )

    return user


def deactivate_user(user_id: int, reason: str, performed_by_id: int) -> BasicUser:
    """Deactivate user and automatically revoke all active roles (UC-SA-004, CFR-SA-003, BR-SA-015)."""
    user = BasicUser.objects.get(id=user_id)
    if user.status != UserLifecycleStatus.ACTIVE:
        raise DomainError(f"User is currently '{user.status}' and cannot be deactivated.")

    now = timezone.now()
    with transaction.atomic():
        user.status = UserLifecycleStatus.DEACTIVATED
        user.is_active = False
        user.deactivated_at = now
        user.save(update_fields=["status", "is_active", "deactivated_at"])

        # Automatic role revocation (BR-SA-015, AFR-SA-040B)
        active_assignments = RoleAssignment.objects.filter(
            user=user,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        )
        for assign in active_assignments:
            assign.state = RoleAssignmentState.REVOKED
            assign.revoked_at = now
            assign.revocation_type = RoleRevocationType.AUTOMATIC
            assign.revocation_reason = f"Account deactivated: {reason}"
            assign.save(update_fields=["state", "revoked_at", "revocation_type", "revocation_reason"])

        UserStatusHistory.objects.create(
            user=user,
            from_status=UserLifecycleStatus.ACTIVE,
            to_status=UserLifecycleStatus.DEACTIVATED,
            changed_by=performed_by_id,
            reason=reason,
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.USER_DEACTIVATE,
            target_user_id=user.id,
            result=AuditResult.SUCCESS,
            reason=reason,
        )

    return user


def reactivate_user(user_id: int, reason: str, performed_by_id: int) -> BasicUser:
    """Reactivate a deactivated user account (UC-SA-005, BW-SA-06)."""
    user = BasicUser.objects.get(id=user_id)
    if user.status != UserLifecycleStatus.DEACTIVATED:
        raise DomainError("Only deactivated users can be reactivated via this action.")

    with transaction.atomic():
        user.status = UserLifecycleStatus.ACTIVE
        user.is_active = True
        user.deactivated_at = None
        user.save(update_fields=["status", "is_active", "deactivated_at"])

        UserStatusHistory.objects.create(
            user=user,
            from_status=UserLifecycleStatus.DEACTIVATED,
            to_status=UserLifecycleStatus.ACTIVE,
            changed_by=performed_by_id,
            reason=reason,
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.USER_REACTIVATE,
            target_user_id=user.id,
            result=AuditResult.SUCCESS,
            reason=reason,
        )

    return user


def execute_bulk_user_creation(csv_content: str, performed_by_id: int) -> Dict[str, Any]:
    """Execute bulk user creation with pre-validation and max 1000 records limit (UC-SA-006, CFR-SA-004, BR-SA-030)."""
    f = io.StringIO(csv_content.strip())
    reader = csv.DictReader(f)
    rows = list(reader)

    validators.validate_bulk_size(len(rows), max_limit=1000)

    # Pre-validation phase (AFR-SA-018A)
    errors = []
    specs = []
    seen_ids = set()
    seen_emails = set()

    for idx, row in enumerate(rows, start=2):
        row_id = row.get("institute_id", "").strip()
        row_email = row.get("institute_email", "").strip()

        row_errors = []
        if not row_id:
            row_errors.append("Missing institute_id")
        elif row_id in seen_ids or BasicUser.objects.filter(institute_id=row_id).exists():
            row_errors.append(f"Duplicate institute_id '{row_id}'")

        if not row_email:
            row_errors.append("Missing institute_email")
        elif row_email in seen_emails or BasicUser.objects.filter(email=row_email).exists():
            row_errors.append(f"Duplicate institute_email '{row_email}'")

        try:
            validators.validate_institute_email(row_email)
        except IdentityValidationError as exc:
            row_errors.append(str(exc))

        try:
            validators.validate_institute_id(row_id)
        except IdentityValidationError as exc:
            row_errors.append(str(exc))

        if row_errors:
            errors.append({"line": idx, "institute_id": row_id, "errors": row_errors})
            continue

        seen_ids.add(row_id)
        seen_emails.add(row_email)

        spec = UserCreationSpec(
            user_kind=row.get("user_kind", "student").strip(),
            name=row.get("name", "").strip(),
            institute_email=row_email,
            institute_id=row_id,
            contact_number=row.get("contact_number", "").strip(),
            department=row.get("department", "").strip(),
            programme=row.get("programme", "").strip(),
            discipline=row.get("discipline", "").strip(),
            batch_year=int(row["batch_year"]) if row.get("batch_year") else None,
            employee_id=row.get("employee_id", "").strip(),
        )
        specs.append(spec)

    # Process valid records
    processed = 0
    with transaction.atomic():
        for spec in specs:
            create_basic_user(spec, performed_by_id)
            processed += 1

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.USER_BULK_CREATE,
            result=AuditResult.SUCCESS if not errors else AuditResult.FAILURE,
            reason=f"Bulk user creation: {processed} succeeded, {len(errors)} failed",
            context_metadata={"total": len(rows), "processed": processed, "failed": len(errors)},
        )

    return {
        "total": len(rows),
        "processed": processed,
        "failed": len(errors),
        "error_details": errors,
    }


def execute_bulk_status_update(
    user_ids: Sequence[int], action: str, reason: str, performed_by_id: int
) -> Dict[str, Any]:
    """Execute bulk deactivation or reactivation for up to 1000 users (CFR-SA-004, BR-SA-030)."""
    validators.validate_bulk_size(len(user_ids), max_limit=1000)

    success = 0
    failed = 0
    errors = []

    for uid in user_ids:
        try:
            if action == "deactivate":
                deactivate_user(uid, reason, performed_by_id)
            elif action == "reactivate":
                reactivate_user(uid, reason, performed_by_id)
            else:
                raise DomainError(f"Invalid bulk status action '{action}'.")
            success += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            errors.append({"user_id": uid, "error": str(exc)})

    return {"total": len(user_ids), "succeeded": success, "failed": failed, "errors": errors}
