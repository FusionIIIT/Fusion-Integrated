"""User Management Service for System Admin Control Plane.

Implements basic user account creation, profile maintenance, status transitions,
and bulk operations conforming to BR-SA-001, BR-SA-002, BR-SA-003, BR-SA-015,
BR-SA-030, and CFR-SA-001 through CFR-SA-004.
"""
import csv
import io
import re
from datetime import date
from typing import Any
from django.db import transaction
from django.utils import timezone

from modules.systemadmin.models.user_mgmt import BasicUserProfile, UserStatusHistory
from modules.systemadmin.models.role_mgmt import RoleAssignment, RoleAssignmentHistory
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.notification_service import NotificationService


class UserManagementError(Exception):
    def __init__(self, message: str, code: str = "user_mgmt_error", details: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


class UserService:
    INSTITUTE_EMAIL_DOMAIN = "@iiitdmj.ac.in"

    @classmethod
    def validate_institute_email(cls, email: str) -> None:
        """Enforce valid institute email (BR-SA-002)."""
        email = (email or "").strip().lower()
        if not email:
            raise UserManagementError("Institute email address is required.", code="missing_email")
        # Standard email format and must end with @iiitdmj.ac.in
        email_regex = r"^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.)*iiitdmj\.ac\.in$"
        if not re.match(email_regex, email):
            raise UserManagementError(
                f"Email '{email}' is not a valid institute email. Must end with '{cls.INSTITUTE_EMAIL_DOMAIN}'.",
                code="invalid_institute_email"
            )

    @classmethod
    def validate_type_required_data(cls, user_type: str, data: dict[str, Any]) -> None:
        """Validate required data fields by user type (BR-SA-003)."""
        user_type = (user_type or "").lower()
        missing = []

        if user_type == "student":
            if not data.get("programme"):
                missing.append("programme")
            if not data.get("batch_year"):
                missing.append("batch_year")
        elif user_type in ("faculty", "staff"):
            if not data.get("employee_id"):
                missing.append("employee_id")
            if not data.get("department"):
                missing.append("department")
        else:
            raise UserManagementError(
                f"Invalid user type '{user_type}'. Must be 'student', 'faculty', or 'staff'.",
                code="invalid_user_type"
            )

        if missing:
            raise UserManagementError(
                f"Missing required fields for user type '{user_type}': {', '.join(missing)}.",
                code="missing_type_data",
                details=missing
            )

    @classmethod
    def _next_internal_user_id(cls) -> int:
        """Generate a unique sequential internal user ID (AFR-SA-006)."""
        max_id = BasicUserProfile.objects.all().order_by("-internal_user_id").values_list(
            "internal_user_id", flat=True
        ).first()
        return (max_id or 10000) + 1

    @classmethod
    @transaction.atomic
    def create_basic_user(
        cls,
        institute_id: str,
        user_type: str,
        full_name: str,
        institute_email: str,
        date_of_joining: date,
        contact_number: str = "",
        department: str = "",
        programme: str = "",
        discipline: str = "",
        batch_year: int | None = None,
        employee_id: str = "",
        expected_completion_date: date | None = None,
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> BasicUserProfile:
        """Create a single basic user account (UC-SA-001)."""
        institute_id = (institute_id or "").strip()
        user_type = (user_type or "").strip().lower()
        full_name = (full_name or "").strip()
        institute_email = (institute_email or "").strip().lower()

        if not institute_id:
            raise UserManagementError("Institute ID is required.", code="missing_institute_id")
        if not full_name:
            raise UserManagementError("Full name is required.", code="missing_full_name")
        if not date_of_joining:
            raise UserManagementError("Date of joining is required.", code="missing_joining_date")

        # Uniqueness checks (BR-SA-001)
        if BasicUserProfile.objects.filter(institute_id=institute_id).exists():
            raise UserManagementError(
                f"User with Institute ID '{institute_id}' already exists.",
                code="duplicate_institute_id"
            )
        if BasicUserProfile.objects.filter(institute_email=institute_email).exists():
            raise UserManagementError(
                f"User with email '{institute_email}' already exists.",
                code="duplicate_institute_email"
            )

        # Email & type data validation (BR-SA-002, BR-SA-003)
        cls.validate_institute_email(institute_email)
        cls.validate_type_required_data(
            user_type,
            {
                "programme": programme,
                "batch_year": batch_year,
                "employee_id": employee_id,
                "department": department,
            }
        )

        internal_id = cls._next_internal_user_id()

        user = BasicUserProfile.objects.create(
            internal_user_id=internal_id,
            institute_id=institute_id,
            user_type=user_type,
            full_name=full_name,
            institute_email=institute_email,
            contact_number=contact_number or "",
            department=department or "",
            programme=programme or "",
            discipline=discipline or "",
            batch_year=batch_year,
            employee_id=employee_id or "",
            date_of_joining=date_of_joining,
            expected_completion_date=expected_completion_date,
            status="active",
            initial_password_issued=True,
            has_dashboard_access=True,
        )

        UserStatusHistory.objects.create(
            user=user,
            from_status="NONE",
            to_status="active",
            reason="Initial account creation",
            actor_username=actor_username,
        )

        # Welcome message & guidance (AFR-SA-009)
        NotificationService.send_notification(
            recipient_username=institute_id,
            title="Welcome to Fusion ERP",
            message=(
                f"Dear {full_name}, your {user_type.capitalize()} account ({institute_id}) has been created. "
                "Your baseline dashboard access is enabled. Please log in using your initial credentials "
                "and update your password."
            ),
            category="account",
            channel="in_system",
            recipient_role=user_type.capitalize(),
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="USER_CREATE",
            result="SUCCESS",
            target_user=institute_id,
            ip_address=ip_address,
            reason_or_context=f"Created {user_type} account for {full_name}",
            metadata={"user_type": user_type, "internal_user_id": internal_id},
        )

        return user

    @classmethod
    @transaction.atomic
    def update_user_profile(
        cls,
        user_id: int,
        data: dict[str, Any] | None = None,
        updates: dict[str, Any] | None = None,
        actor_username: str = "superadmin",
        ip_address: str | None = None,
        reason: str = "Profile update by Super Admin",
    ) -> BasicUserProfile:
        """Update permitted editable fields while protecting Institute ID immutability (UC-SA-003, BR-SA-001)."""
        if data is None and updates is not None:
            data = updates
        if data is None:
            data = {}
        user = BasicUserProfile.objects.filter(id=user_id).first()
        if not user:
            raise UserManagementError(f"User with ID {user_id} does not exist.", code="user_not_found")

        # BR-SA-001 & AFR-SA-003B: Institute ID immutability
        if "institute_id" in data and data["institute_id"] != user.institute_id:
            raise UserManagementError(
                "Institute ID is immutable and cannot be changed after creation.",
                code="institute_id_immutable"
            )

        changed_fields = {}
        editable_fields = [
            "full_name", "contact_number", "department", "programme",
            "discipline", "batch_year", "employee_id", "expected_completion_date"
        ]

        for field in editable_fields:
            if field in data and data[field] != getattr(user, field):
                old_val = getattr(user, field)
                new_val = data[field]
                setattr(user, field, new_val)
                changed_fields[field] = {"old": old_val, "new": new_val}

        if "institute_email" in data and data["institute_email"] != user.institute_email:
            new_email = data["institute_email"].strip().lower()
            cls.validate_institute_email(new_email)
            if BasicUserProfile.objects.exclude(id=user.id).filter(institute_email=new_email).exists():
                raise UserManagementError(
                    f"Email '{new_email}' is already in use by another user.",
                    code="duplicate_institute_email"
                )
            changed_fields["institute_email"] = {"old": user.institute_email, "new": new_email}
            user.institute_email = new_email

        if changed_fields:
            user.save()
            AuditService.log_action(
                actor_username=actor_username,
                action="USER_UPDATE",
                result="SUCCESS",
                target_user=user.institute_id,
                ip_address=ip_address,
                reason_or_context=reason,
                metadata={"changed_fields": changed_fields},
            )

        return user

    @classmethod
    @transaction.atomic
    def deactivate_user(
        cls,
        user_id: int,
        reason: str,
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> BasicUserProfile:
        """Deactivate an active user account and inactivate assigned roles (UC-SA-004, BR-SA-015)."""
        user = BasicUserProfile.objects.filter(id=user_id).first()
        if not user:
            raise UserManagementError(f"User with ID {user_id} does not exist.", code="user_not_found")
        if user.status != "active":
            raise UserManagementError(
                f"User is currently in status '{user.status}'; only active users can be deactivated.",
                code="invalid_status_for_deactivation"
            )

        from_status = user.status
        user.status = "deactivated"
        user.deactivated_at = timezone.now()
        user.deactivation_reason = reason or "Deactivated by Super Admin"
        user.has_dashboard_access = False
        user.save()

        UserStatusHistory.objects.create(
            user=user,
            from_status=from_status,
            to_status="deactivated",
            reason=reason,
            actor_username=actor_username,
        )

        # BR-SA-015: Automatically revoke/inactivate assigned roles
        active_roles = RoleAssignment.objects.filter(user=user, status__in=["active", "scheduled", "extended"])
        revoked_role_codes = []
        for role_assignment in active_roles:
            role_assignment.status = "revoked"
            role_assignment.revoked_at = timezone.now()
            role_assignment.revocation_reason = f"Account deactivation: {reason}"
            role_assignment.revocation_task_disposition = "close"
            role_assignment.save()
            revoked_role_codes.append(role_assignment.role.code)

            RoleAssignmentHistory.objects.create(
                assignment=role_assignment,
                action="revoked",
                actor_username=actor_username,
                details={"reason": "Automatic revocation upon user account deactivation"},
            )

        NotificationService.send_notification(
            recipient_username=user.institute_id,
            title="Account Deactivated",
            message=f"Your account has been deactivated. Reason: {reason}",
            category="account",
            channel="in_system",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="USER_DEACTIVATE",
            result="SUCCESS",
            target_user=user.institute_id,
            ip_address=ip_address,
            reason_or_context=reason,
            metadata={"revoked_roles": revoked_role_codes},
        )

        return user

    @classmethod
    @transaction.atomic
    def reactivate_user(
        cls,
        user_id: int,
        reason: str = "Reactivated by Super Admin",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> BasicUserProfile:
        """Reactivate a previously deactivated user (UC-SA-005, BW-SA-06)."""
        user = BasicUserProfile.objects.filter(id=user_id).first()
        if not user:
            raise UserManagementError(f"User with ID {user_id} does not exist.", code="user_not_found")
        if user.status == "archived":
            raise UserManagementError(
                "Archived user accounts cannot be reactivated via standard reactivation. Use restoration.",
                code="user_is_archived"
            )
        if user.status != "deactivated":
            raise UserManagementError(
                f"User is currently '{user.status}'; only deactivated users may be reactivated.",
                code="user_not_deactivated"
            )

        from_status = user.status
        user.status = "active"
        user.deactivated_at = None
        user.deactivation_reason = ""
        user.has_dashboard_access = True
        user.save()

        UserStatusHistory.objects.create(
            user=user,
            from_status=from_status,
            to_status="active",
            reason=reason,
            actor_username=actor_username,
        )

        NotificationService.send_notification(
            recipient_username=user.institute_id,
            title="Account Reactivated",
            message=f"Your account has been reactivated. Baseline access is restored.",
            category="account",
            channel="in_system",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="USER_REACTIVATE",
            result="SUCCESS",
            target_user=user.institute_id,
            ip_address=ip_address,
            reason_or_context=reason,
        )

        return user

    @classmethod
    def bulk_create_users(
        cls,
        csv_file_or_text: Any = None,
        user_records: list[dict[str, Any]] | None = None,
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Execute bulk user creation with pre-validation and limit of 1000 records (UC-SA-006, BR-SA-030)."""
        if user_records is not None:
            rows = user_records
        elif isinstance(csv_file_or_text, list):
            rows = csv_file_or_text
        elif isinstance(csv_file_or_text, str):
            stream = io.StringIO(csv_file_or_text)
            rows = list(csv.DictReader(stream))
        elif hasattr(csv_file_or_text, "read"):
            rows = list(csv.DictReader(csv_file_or_text))
        else:
            rows = []
        total_records = len(rows)

        # BR-SA-030: Hard limit 1000 records
        if total_records > 1000:
            raise UserManagementError(
                f"Bulk operation exceeds maximum allowable limit of 1000 records (submitted: {total_records}).",
                code="bulk_limit_exceeded"
            )

        if total_records == 0:
            raise UserManagementError("CSV file is empty or missing data rows.", code="empty_csv")

        results = []
        success_count = 0
        failure_count = 0

        for idx, row in enumerate(rows, start=1):
            row_id = row.get("institute_id", "").strip()
            row_type = row.get("user_type", "").strip().lower()
            row_name = row.get("full_name", "").strip()
            row_email = row.get("institute_email", "").strip().lower()
            doj_str = row.get("date_of_joining", "").strip()

            try:
                if not doj_str:
                    doj = date.today()
                else:
                    doj = date.fromisoformat(doj_str)

                batch_val = int(row.get("batch_year")) if row.get("batch_year") else None

                cls.create_basic_user(
                    institute_id=row_id,
                    user_type=row_type,
                    full_name=row_name,
                    institute_email=row_email,
                    date_of_joining=doj,
                    contact_number=row.get("contact_number", "").strip(),
                    department=row.get("department", "").strip(),
                    programme=row.get("programme", "").strip(),
                    discipline=row.get("discipline", "").strip(),
                    batch_year=batch_val,
                    employee_id=row.get("employee_id", "").strip(),
                    actor_username=actor_username,
                    ip_address=ip_address,
                )
                success_count += 1
                results.append({"row": idx, "institute_id": row_id, "status": "SUCCESS", "error": None})
            except Exception as exc:
                failure_count += 1
                results.append({"row": idx, "institute_id": row_id, "status": "FAILED", "error": str(exc)})

        NotificationService.send_notification(
            recipient_username=actor_username,
            title="Bulk User Creation Complete",
            message=f"Processed {total_records} records: {success_count} succeeded, {failure_count} failed.",
            category="bulk_operation",
            channel="in_system",
            recipient_role="Super Admin",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="USER_BULK_CREATE",
            result="SUCCESS" if failure_count == 0 else "PARTIAL",
            ip_address=ip_address,
            reason_or_context=f"Bulk created {success_count}/{total_records} users",
            metadata={"total": total_records, "success": success_count, "failed": failure_count},
        )

        return {
            "total_records": total_records,
            "success_count": success_count,
            "failure_count": failure_count,
            "details": results,
        }

    @classmethod
    def bulk_status_update(
        cls,
        user_ids: list[int],
        action: str,  # "deactivate" or "reactivate"
        reason: str,
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Execute bulk user status updates with limit of 1000 records (UC-SA-007, BR-SA-030)."""
        if len(user_ids) > 1000:
            raise UserManagementError(
                f"Bulk operation exceeds maximum allowable limit of 1000 records (submitted: {len(user_ids)}).",
                code="bulk_limit_exceeded"
            )

        success_count = 0
        failure_count = 0
        logs = []

        for uid in user_ids:
            try:
                if action == "deactivate":
                    cls.deactivate_user(uid, reason, actor_username=actor_username, ip_address=ip_address)
                elif action == "reactivate":
                    cls.reactivate_user(uid, reason, actor_username=actor_username, ip_address=ip_address)
                else:
                    raise UserManagementError(f"Unsupported status action '{action}'.", code="invalid_action")
                success_count += 1
                logs.append({"user_id": uid, "status": "SUCCESS", "error": None})
            except Exception as e:
                failure_count += 1
                logs.append({"user_id": uid, "status": "FAILED", "error": str(e)})

        NotificationService.send_notification(
            recipient_username=actor_username,
            title=f"Bulk {action.capitalize()} Complete",
            message=f"Processed {len(user_ids)} users: {success_count} succeeded, {failure_count} failed.",
            category="bulk_operation",
            channel="in_system",
            recipient_role="Super Admin",
        )

        AuditService.log_action(
            actor_username=actor_username,
            action=f"USER_BULK_{action.upper()}",
            result="SUCCESS" if failure_count == 0 else "PARTIAL",
            ip_address=ip_address,
            reason_or_context=f"Bulk {action} on {len(user_ids)} users",
            metadata={"total": len(user_ids), "success": success_count, "failed": failure_count},
        )

        return {
            "total_records": len(user_ids),
            "success_count": success_count,
            "failure_count": failure_count,
            "details": logs,
        }


create_basic_user = UserService.create_basic_user
update_user_profile = UserService.update_user_profile
deactivate_user = UserService.deactivate_user
reactivate_user = UserService.reactivate_user
bulk_create_users = UserService.bulk_create_users
bulk_status_update = UserService.bulk_status_update
validate_institute_email = UserService.validate_institute_email
validate_type_required_data = UserService.validate_type_required_data
