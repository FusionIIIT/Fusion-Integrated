"""User lifecycle service for System Admin module.

Implements UC-SA-001 through UC-SA-007 and BW-SA-06:
- Create basic user account (Student, Faculty, Staff)
- View and update user profile (preserving immutable Institute ID)
- Manage activation status (deactivate, reactivate)
- Bulk operations (CSV batch creation, bulk deactivation, status updates)
- Full immutable audit logging and notifications.
"""
from datetime import date
import uuid
from typing import Any
from django.db import transaction
from django.utils import timezone

from modules.system_admin.domain import (
    BasicUserType,
    UserStatus,
    validate_bulk_operation_limit,
    validate_institute_email,
    validate_institute_id_immutability,
    validate_institute_id_uniqueness,
    validate_user_transition,
    validate_user_type_required_data,
)
from modules.system_admin.models import (
    BasicUser,
    BulkOperationLog,
    RoleAssignment,
)
from modules.system_admin.services.audit_service import record_audit_event
from modules.system_admin.services.notification_service import (
    notify_super_admin,
    notify_user,
)


def create_basic_user(
    *,
    institute_id: str,
    user_type: BasicUserType | str,
    email: str,
    first_name: str,
    last_name: str,
    contact_number: str = "",
    department: str = "",
    programme: str = "",
    discipline: str = "",
    batch_year: int | None = None,
    employee_id: str = "",
    date_of_joining: date | None = None,
    expected_completion_date: date | None = None,
    actor_user_id: int = 0,
    actor_username: str = "system",
    ip_address: str | None = None,
) -> BasicUser:
    """UC-SA-001: Create Basic User Account (AFR-SA-001..009)."""
    u_type = BasicUserType(user_type) if isinstance(user_type, str) else user_type

    # 1. Validate BR-SA-003: user type required data
    profile_data = {
        "institute_id": institute_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "department": department,
        "programme": programme,
        "discipline": discipline,
        "batch_year": batch_year,
        "employee_id": employee_id,
    }
    validate_user_type_required_data(u_type, profile_data)

    # 2. Validate BR-SA-001: Institute ID uniqueness
    existing_ids = set(
        BasicUser.objects.filter(institute_id__iexact=institute_id.strip()).values_list(
            "institute_id", flat=True
        )
    )
    validate_institute_id_uniqueness(institute_id, existing_ids)

    # 3. Validate BR-SA-002: Institute Email
    validate_institute_email(email)

    with transaction.atomic():
        user = BasicUser.objects.create(
            institute_id=institute_id.strip(),
            user_type=u_type.value,
            email=email.strip().lower(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            contact_number=contact_number.strip(),
            department=department.strip(),
            programme=programme.strip(),
            discipline=discipline.strip(),
            batch_year=batch_year,
            employee_id=employee_id.strip(),
            date_of_joining=date_of_joining,
            expected_completion_date=expected_completion_date,
            status=UserStatus.ACTIVE.value,
            dashboard_access_enabled=True,
        )

        # 4. Generate initial welcome notification with credentials guidance (AFR-SA-009)
        notify_user(
            user_id=user.user_id,
            event="user.account_created",
            title="Welcome to Fusion ERP — Account Created",
            message=(
                f"Hello {user.first_name}, your basic user account ({user.institute_id}) has been created. "
                "Please follow the first-login instructions to set your initial password and complete your profile."
            ),
            email=user.email,
        )

        # 5. Record immutable audit entry (AFR-SA-014, BR-SA-025, BR-SA-033)
        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="user.create",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            ip_address=ip_address,
            reason="Basic user account creation",
            details={
                "institute_id": user.institute_id,
                "user_type": user.user_type,
                "email": user.email,
            },
        )

    return user


def update_user_profile(
    *,
    user_id: int,
    actor_user_id: int,
    actor_username: str,
    fields_to_update: dict[str, Any],
    reason: str = "",
    ip_address: str | None = None,
) -> BasicUser:
    """UC-SA-003: Update User Profile (AFR-SA-011).

    Enforces BR-SA-001: Institute ID cannot be changed after creation.
    """
    with transaction.atomic():
        user = BasicUser.objects.select_for_update().get(user_id=user_id)

        # Enforce BR-SA-001: Institute ID immutability
        if "institute_id" in fields_to_update:
            validate_institute_id_immutability(
                user.institute_id, fields_to_update["institute_id"]
            )

        # Enforce BR-SA-002: Email validation if updated
        if "email" in fields_to_update:
            validate_institute_email(fields_to_update["email"])
            user.email = fields_to_update["email"].strip().lower()

        # Update permitted fields
        changed_fields = {}
        for f in [
            "first_name",
            "last_name",
            "contact_number",
            "department",
            "programme",
            "discipline",
            "batch_year",
            "employee_id",
            "date_of_joining",
            "expected_completion_date",
        ]:
            if f in fields_to_update and fields_to_update[f] != getattr(user, f):
                changed_fields[f] = {
                    "old": getattr(user, f),
                    "new": fields_to_update[f],
                }
                setattr(user, f, fields_to_update[f])

        user.save()

        # Record immutable audit entry
        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="user.update_profile",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            ip_address=ip_address,
            reason=reason or "Profile update",
            details={"changed_fields": changed_fields},
        )

    return user


def deactivate_user(
    *,
    user_id: int,
    actor_user_id: int,
    actor_username: str,
    reason: str,
    ip_address: str | None = None,
) -> BasicUser:
    """UC-SA-004: Deactivate User (AFR-SA-012).

    Automatically revokes assigned roles per BR-SA-015 / AFR-SA-040B.
    """
    with transaction.atomic():
        user = BasicUser.objects.select_for_update().get(user_id=user_id)
        validate_user_transition(UserStatus(user.status), UserStatus.DEACTIVATED)

        user.status = UserStatus.DEACTIVATED.value
        user.deactivated_at = timezone.now()
        user.deactivation_reason = reason
        user.dashboard_access_enabled = False
        user.save(
            update_fields=[
                "status",
                "deactivated_at",
                "deactivation_reason",
                "dashboard_access_enabled",
                "updated_at",
            ]
        )

        # Automatic revocation of active/scheduled roles (BR-SA-015, AFR-SA-040B)
        revoked_count = RoleAssignment.objects.filter(
            user_id=user.user_id, status__in=["scheduled", "active"]
        ).update(
            status="revoked",
            effective_revoked_at=timezone.now(),
            revocation_reason=f"Account deactivated: {reason}",
        )

        # Send deactivation notice (AFR-SA-068)
        notify_user(
            user_id=user.user_id,
            event="user.deactivated",
            title="Account Deactivated",
            message=f"Your account has been deactivated. Reason: {reason}.",
            email=user.email,
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="user.deactivate",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            ip_address=ip_address,
            reason=reason,
            details={"revoked_roles_count": revoked_count},
        )

    return user


def reactivate_user(
    *,
    user_id: int,
    actor_user_id: int,
    actor_username: str,
    reason: str = "",
    ip_address: str | None = None,
) -> BasicUser:
    """UC-SA-005: Reactivate User (AFR-SA-013, BW-SA-06).

    Restores baseline dashboard access. Previously expired/revoked additional roles
    are NOT silently recreated.
    """
    with transaction.atomic():
        user = BasicUser.objects.select_for_update().get(user_id=user_id)
        validate_user_transition(UserStatus(user.status), UserStatus.ACTIVE)

        user.status = UserStatus.ACTIVE.value
        user.deactivated_at = None
        user.deactivation_reason = ""
        user.dashboard_access_enabled = True
        user.save(
            update_fields=[
                "status",
                "deactivated_at",
                "deactivation_reason",
                "dashboard_access_enabled",
                "updated_at",
            ]
        )

        notify_user(
            user_id=user.user_id,
            event="user.reactivated",
            title="Account Reactivated",
            message="Your Fusion account has been reactivated. Baseline dashboard access is restored.",
            email=user.email,
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="user.reactivate",
            result="success",
            target_type="basic_user",
            target_id=str(user.user_id),
            ip_address=ip_address,
            reason=reason or "Account reactivation",
        )

    return user


def bulk_create_users(
    *,
    records: list[dict[str, Any]],
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
) -> BulkOperationLog:
    """UC-SA-006: Bulk Create Users (AFR-SA-015, AFR-SA-018..020).

    Enforces BR-SA-030: maximum 1000 records.
    Pre-validates template structure and record-by-record errors.
    """
    validate_bulk_operation_limit(len(records), limit=1000)

    batch_id = f"batch_create_{uuid.uuid4().hex[:12]}"
    detailed_log: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    existing_institute_ids = set(
        BasicUser.objects.values_list("institute_id", flat=True)
    )
    existing_emails = set(BasicUser.objects.values_list("email", flat=True))

    for idx, row in enumerate(records, start=1):
        row_id = row.get("institute_id", f"row_{idx}")
        try:
            u_type = BasicUserType(row.get("user_type", "student"))
            validate_user_type_required_data(u_type, row)
            validate_institute_id_uniqueness(row["institute_id"], existing_institute_ids)
            validate_institute_email(row["email"])

            if row["email"].lower() in existing_emails:
                raise ValueError(f"Email {row['email']} is already registered.")

            user = BasicUser.objects.create(
                institute_id=row["institute_id"].strip(),
                user_type=u_type.value,
                email=row["email"].strip().lower(),
                first_name=row["first_name"].strip(),
                last_name=row["last_name"].strip(),
                contact_number=row.get("contact_number", "").strip(),
                department=row.get("department", "").strip(),
                programme=row.get("programme", "").strip(),
                discipline=row.get("discipline", "").strip(),
                batch_year=row.get("batch_year"),
                employee_id=row.get("employee_id", "").strip(),
                status=UserStatus.ACTIVE.value,
                dashboard_access_enabled=True,
            )

            existing_institute_ids.add(user.institute_id)
            existing_emails.add(user.email)
            success_count += 1
            detailed_log.append({
                "row": idx,
                "institute_id": row["institute_id"],
                "status": "success",
                "user_id": user.user_id,
            })
        except Exception as e:
            fail_count += 1
            detailed_log.append({
                "row": idx,
                "institute_id": row_id,
                "status": "failed",
                "error": str(e),
            })

    summary = {
        "batch_id": batch_id,
        "total": len(records),
        "success": success_count,
        "failed": fail_count,
    }

    log_entry = BulkOperationLog.objects.create(
        batch_id=batch_id,
        operation_type="bulk_user_creation",
        total_records=len(records),
        successful_records=success_count,
        failed_records=fail_count,
        initiated_by_user_id=actor_user_id,
        summary=summary,
        detailed_log=detailed_log,
    )

    # Super Admin notification (AFR-SA-020)
    notify_super_admin(
        event="bulk_operation.completed",
        title="Bulk User Creation Complete",
        message=f"Batch {batch_id} processed: {success_count} succeeded, {fail_count} failed out of {len(records)}.",
    )

    record_audit_event(
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        action="user.bulk_create",
        result="success" if fail_count == 0 else "partial",
        target_type="bulk_operation",
        target_id=batch_id,
        ip_address=ip_address,
        reason="Bulk user creation batch",
        details=summary,
    )

    return log_entry


def bulk_status_update(
    *,
    user_ids: list[int],
    target_status: str,  # "deactivated"
    reason: str,
    actor_user_id: int,
    actor_username: str,
    ip_address: str | None = None,
) -> BulkOperationLog:
    """UC-SA-007: Bulk User Status Update / Deactivation (AFR-SA-016, AFR-SA-017)."""
    validate_bulk_operation_limit(len(user_ids), limit=1000)

    batch_id = f"batch_status_{uuid.uuid4().hex[:12]}"
    detailed_log: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    for uid in user_ids:
        try:
            if target_status == "deactivated":
                deactivate_user(
                    user_id=uid,
                    actor_user_id=actor_user_id,
                    actor_username=actor_username,
                    reason=reason,
                    ip_address=ip_address,
                )
            elif target_status == "active":
                reactivate_user(
                    user_id=uid,
                    actor_user_id=actor_user_id,
                    actor_username=actor_username,
                    reason=reason,
                    ip_address=ip_address,
                )
            else:
                raise ValueError(f"Unsupported bulk target status: {target_status}")

            success_count += 1
            detailed_log.append({"user_id": uid, "status": "success"})
        except Exception as e:
            fail_count += 1
            detailed_log.append({"user_id": uid, "status": "failed", "error": str(e)})

    summary = {
        "batch_id": batch_id,
        "target_status": target_status,
        "total": len(user_ids),
        "success": success_count,
        "failed": fail_count,
    }

    log_entry = BulkOperationLog.objects.create(
        batch_id=batch_id,
        operation_type=f"bulk_status_{target_status}",
        total_records=len(user_ids),
        successful_records=success_count,
        failed_records=fail_count,
        initiated_by_user_id=actor_user_id,
        summary=summary,
        detailed_log=detailed_log,
    )

    notify_super_admin(
        event="bulk_status_update.completed",
        title=f"Bulk Status Update ({target_status}) Complete",
        message=f"Batch {batch_id} complete: {success_count} succeeded, {fail_count} failed.",
    )

    return log_entry
