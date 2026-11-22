"""Pure business rule implementations for BADMS (BR-BA-001 through BR-BA-021).

Strictly pure Python: no django, rest_framework, or celery imports.
"""

from __future__ import annotations

import re

from modules.badms.domain.entities import (
    ActorRole,
    DataClassification,
    ScheduleFrequency,
)
from modules.badms.domain.errors import (
    ActorNotAllowed,
    DepartmentScopeViolation,
    QuotaExceededError,
    RepositoryUnreachableError,
    RuleViolation,
    StorageNotFullError,
)


def check_manual_backup_auth(actor_role: ActorRole) -> None:
    """BR-BA-001: Only a SysAdmin or Super Admin may trigger a manual backup."""
    if actor_role not in (ActorRole.SYSADMIN, ActorRole.SUPER_ADMIN):
        raise RuleViolation(
            "BR-BA-001", "Only SysAdmin or Super Admin may trigger a manual backup."
        )


def check_hod_department_scope(
    actor_role: ActorRole, hod_dept_id: int, target_dept_id: int
) -> None:
    """BR-BA-002, BR-BA-010: HoD may act only on requests from their own department."""
    if actor_role != ActorRole.HOD:
        raise ActorNotAllowed(str(actor_role), "hod_action")
    if hod_dept_id != target_dept_id:
        raise DepartmentScopeViolation(hod_dept_id, target_dept_id)


def check_it_security_encryption_auth(actor_role: ActorRole) -> None:
    """BR-BA-003: Only IT Security may configure encryption for Sensitive data."""
    if actor_role != ActorRole.IT_SECURITY:
        raise RuleViolation(
            "BR-BA-003", "Only IT Security Team may configure encryption for Sensitive data."
        )


def check_sysadmin_classification_auth(actor_role: ActorRole) -> None:
    """BR-BA-004: Authoritative classification is assigned by an authorized SysAdmin."""
    if actor_role != ActorRole.SYSADMIN:
        raise RuleViolation("BR-BA-004", "Only SysAdmin may assign authoritative classification.")


def check_sensitive_restoration_approval_requirement(
    classification: DataClassification,
    actor_role: ActorRole,
    is_approved: bool,
) -> None:
    """BR-BA-005: Restoration of Sensitive data requires SysAdmin approval."""
    if classification == DataClassification.SENSITIVE and not is_approved:
        raise RuleViolation(
            "BR-BA-005",
            "Sensitive restoration requires prior SysAdmin approval before technical execution.",
        )


def resolve_initial_classification(initial: str | None) -> DataClassification:
    """BR-BA-006: User provides initial classification; if omitted, defaults to Routine."""
    if not initial or not str(initial).strip():
        return DataClassification.ROUTINE
    try:
        return DataClassification(initial.lower())
    except ValueError:
        return DataClassification.ROUTINE


def validate_sensitive_encryption_algorithm(algorithm: str) -> None:
    """BR-BA-007: Sensitive data must use AES-256 encryption both at rest and in transit."""
    normalized = algorithm.strip().upper()
    if "AES-256" not in normalized:
        raise RuleViolation("BR-BA-007", "Sensitive data must use AES-256 encryption.")


def validate_retention_classification(classification: DataClassification) -> str:
    """BR-BA-008: Enforce institute-defined retention rules according to data classification."""
    # Retention treatment tagging per classification
    mapping = {
        DataClassification.CRITICAL: "RETENTION_PERMANENT_IMMUTABLE",
        DataClassification.SENSITIVE: "RETENTION_RESTRICTED_7_YEARS",
        DataClassification.ROUTINE: "RETENTION_STANDARD_3_YEARS",
        DataClassification.ARCHIVAL: "RETENTION_EXTENDED_INDEFINITE",
    }
    return mapping.get(classification, "RETENTION_STANDARD_3_YEARS")


def check_hod_storage_extension_auth(actor_role: ActorRole) -> None:
    """BR-BA-009: A storage-extension request requires HoD approval."""
    if actor_role != ActorRole.HOD:
        raise RuleViolation("BR-BA-009", "Storage extension request requires HoD approval.")


def resolve_effective_schedule(
    local_schedule: dict | None,
    global_schedule: dict | None,
) -> dict | None:
    """BR-BA-011: Local schedule overrides global schedule; otherwise global applies."""
    if local_schedule and local_schedule.get("is_active", False):
        return local_schedule
    if global_schedule and global_schedule.get("is_active", False):
        return global_schedule
    return None


def validate_schedule_parameters(
    frequency: str,
    execution_time: str,
    dataset: str,
) -> tuple[bool, str]:
    """BR-BA-012: Schedule parameter and conflict validation."""
    if not dataset or not dataset.strip():
        return False, "Target dataset cannot be empty."
    if frequency not in [f.value for f in ScheduleFrequency]:
        valid_freqs = [f.value for f in ScheduleFrequency]
        return (
            False,
            f"Invalid frequency: {frequency}. Must be one of {valid_freqs}.",
        )
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", execution_time.strip()):
        return False, "Execution time must be in HH:MM (24-hour) format."
    return True, ""


def check_repository_reachability(is_reachable: bool, repository_path: str) -> None:
    """BR-BA-013: Backup executes successfully only when repository is reachable."""
    if not is_reachable:
        raise RepositoryUnreachableError(repository_path)


def evaluate_failure_alerts(consecutive_failures: int) -> dict[str, bool]:
    """BR-BA-014, BR-BA-015: Failure alert SLA (SysAdmin) and escalation (Director of IT)."""
    return {
        "alert_sysadmin": True,
        "escalate_director_it": consecutive_failures >= 3,
    }


def validate_storage_extension_eligibility(current_usage_bytes: int, quota_bytes: int) -> None:
    """BR-BA-016: Storage-extension request requires quota to be full (current_usage >= quota)."""
    if current_usage_bytes < quota_bytes:
        raise StorageNotFullError(current_usage_bytes, quota_bytes)


def validate_infrastructure_capacity(requested_bytes: int, available_infra_bytes: int) -> None:
    """BR-BA-017 / AFR-BA-052: Validate requested storage against available infrastructure."""
    if requested_bytes <= 0:
        raise RuleViolation("BR-BA-017", "Requested storage bytes must be positive.")
    if requested_bytes > available_infra_bytes:
        raise QuotaExceededError(requested_bytes, available_infra_bytes)


def check_special_archival_auth(actor_role: ActorRole) -> None:
    """BR-BA-018: Only Super Admin may perform the special archival operation within BADMS."""
    if actor_role != ActorRole.SUPER_ADMIN:
        raise RuleViolation(
            "BR-BA-018", "Only Super Admin may perform special archival operations."
        )


def check_global_backup_auth(actor_role: ActorRole) -> None:
    """BR-BA-019: Only Super Admin may define global backup schedules and default policies."""
    if actor_role != ActorRole.SUPER_ADMIN:
        raise RuleViolation(
            "BR-BA-019", "Only Super Admin may define global backup schedules and default policies."
        )


def can_view_protected_resource(
    actor_role: ActorRole,
    actor_id: int,
    actor_dept_id: int | None,
    resource_owner_id: int,
    resource_dept_id: int | None,
) -> bool:
    """BR-BA-020: Protected information access scope (role, ownership, department)."""
    if actor_role in (ActorRole.SYSADMIN, ActorRole.SUPER_ADMIN, ActorRole.IT_SECURITY):
        return True
    if actor_role == ActorRole.HOD:
        return actor_dept_id is not None and actor_dept_id == resource_dept_id
    # Default user: can view only own records
    return actor_id == resource_owner_id


def check_it_security_rbac_auth(actor_role: ActorRole) -> None:
    """BR-BA-021: Only IT Security Team may manage BADMS RBAC & security policies."""
    if actor_role != ActorRole.IT_SECURITY:
        raise RuleViolation(
            "BR-BA-021", "Only IT Security Team may manage BADMS security and RBAC policies."
        )
