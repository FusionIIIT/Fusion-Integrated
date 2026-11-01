"""Pure Python domain business rules and calculations for BADMS.

Rule specifications: BR-BA-001 through BR-BA-021.
Zero dependencies on Django, DRF, or ORM frameworks.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# Classification Constants
CLASS_ROUTINE = "ROUTINE"
CLASS_SENSITIVE = "SENSITIVE"
CLASS_CRITICAL = "CRITICAL"
CLASS_ARCHIVAL = "ARCHIVAL"

VALID_CLASSIFICATIONS = {CLASS_ROUTINE, CLASS_SENSITIVE, CLASS_CRITICAL, CLASS_ARCHIVAL}

# Retention rules in years per classification (BR-BA-008)
RETENTION_YEARS_POLICY = {
    CLASS_CRITICAL: 30,  # Permanent / institutional master records
    CLASS_ARCHIVAL: 15,  # Long-term preservation
    CLASS_SENSITIVE: 10, # Academic & personnel sensitive records
    CLASS_ROUTINE: 5,    # Operational and transient routine files
}

# Role authorizations
SYSADMIN_ROLES = {"sysadmin", "system_admin", "system administrator"}
SUPERADMIN_ROLES = {"superadmin", "super_admin", "super administrator"}
IT_SECURITY_ROLES = {"it_security", "security_officer", "it security team", "it security"}
BACKUP_TRIGGER_ROLES = SYSADMIN_ROLES | SUPERADMIN_ROLES

# Action Permissions table (enforced by services and API gates)
ACTION_PERMISSIONS = {
    "trigger_manual_backup": "badms.backup.trigger_manual",
    "view_backup_history": "badms.backup.view_history",
    "manage_local_schedule": "badms.schedule.manage_local",
    "manage_global_schedule": "badms.schedule.manage_global",
    "submit_archival": "badms.archival.submit",
    "review_hod": "badms.archival.review_hod",
    "classify_sysadmin": "badms.archival.classify_sysadmin",
    "configure_encryption": "badms.archival.configure_encryption",
    "special_archival_operation": "badms.archival.special_operate",
    "request_storage_extension": "badms.storage.request_extension",
    "review_storage_extension": "badms.storage.review_extension",
    "monitor_storage_threshold": "badms.storage.monitor_threshold",
    "request_restoration": "badms.restoration.request",
    "approve_sensitive_restoration": "badms.restoration.approve_sensitive",
    "execute_restoration": "badms.restoration.execute",
    "view_operational_audit": "badms.audit.view_operational",
    "administer_security": "badms.security.administer",
}


class DomainValidationError(Exception):
    """Raised when a BADMS domain business rule or guard condition is violated."""
    pass


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-001 - Manual Backup Trigger Authorization
# ---------------------------------------------------------------------------
def validate_manual_backup_authority(actor_role: str) -> None:
    """Validate that only SysAdmin or Super Admin may trigger a manual backup.
    
    Ref: BR-BA-001, AFR-BA-001. Enforces permission: badms.backup.trigger_manual.
    """
    if not actor_role or actor_role.strip().lower() not in BACKUP_TRIGGER_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' is not authorized to trigger a manual backup. "
            "Only SysAdmin or Super Admin may execute manual backups (BR-BA-001)."
        )


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-006 - Initial Data Classification and Default
# ---------------------------------------------------------------------------
def get_initial_classification(provided: Optional[str]) -> str:
    """Return provided classification or default to Routine if omitted.
    
    Ref: BR-BA-006, AFR-BA-022.
    """
    if not provided or not provided.strip():
        return CLASS_ROUTINE
    norm = provided.strip().upper()
    if norm not in VALID_CLASSIFICATIONS:
        raise DomainValidationError(
            f"Invalid initial classification '{provided}'. "
            f"Must be one of {sorted(VALID_CLASSIFICATIONS)} (BR-BA-006)."
        )
    return norm


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-002, BR-BA-010 - Respective HoD Approval & Scope
# ---------------------------------------------------------------------------
def validate_hod_department_scope(hod_role: str, hod_department: str, requester_department: str) -> None:
    """Validate that HoD acts only on requests belonging to their own department.
    
    Ref: BR-BA-002, BR-BA-010, AFR-BA-024, AFR-BA-068. Enforces permission: badms.archival.review_hod.
    """
    if not hod_role or "hod" not in hod_role.strip().lower():
        raise DomainValidationError(
            f"Role '{hod_role}' does not have Head of Department (HoD) authority."
        )
    if not hod_department or not requester_department:
        raise DomainValidationError("Both HoD department and requester department must be specified.")
    
    if hod_department.strip().lower() != requester_department.strip().lower():
        raise DomainValidationError(
            f"HoD department '{hod_department}' does not match requester department '{requester_department}'. "
            "A HoD may act only on requests from their own department (BR-BA-002, BR-BA-010)."
        )


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-004 - SysAdmin Authoritative Classification
# ---------------------------------------------------------------------------
def validate_authoritative_classification(actor_role: str, classification: str) -> str:
    """Validate that only SysAdmin can assign authoritative classification.
    
    Ref: BR-BA-004, AFR-BA-028. Enforces permission: badms.archival.classify_sysadmin.
    """
    if not actor_role or actor_role.strip().lower() not in SYSADMIN_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' is not authorized to assign authoritative classification. "
            "Only SysAdmin holds authoritative classification responsibility (BR-BA-004)."
        )
    if not classification or classification.strip().upper() not in VALID_CLASSIFICATIONS:
        raise DomainValidationError(
            f"Invalid authoritative classification '{classification}'. "
            f"Must be one of {sorted(VALID_CLASSIFICATIONS)} (BR-BA-004)."
        )
    return classification.strip().upper()


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-003, BR-BA-007 - IT Security Sensitive Encryption
# ---------------------------------------------------------------------------
def validate_encryption_configuration(actor_role: str, classification: str, algorithm: str) -> None:
    """Validate that only IT Security configures encryption for Sensitive data using AES-256.
    
    Ref: BR-BA-003, BR-BA-007, AFR-BA-032, AFR-BA-033. Enforces permission: badms.archival.configure_encryption.
    """
    if not actor_role or actor_role.strip().lower() not in IT_SECURITY_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' is not authorized to configure encryption. "
            "Only IT Security Team may configure encryption for Sensitive data (BR-BA-003)."
        )
    if classification.strip().upper() != CLASS_SENSITIVE:
        raise DomainValidationError(
            f"Encryption workflow is specifically required for Sensitive data, got '{classification}'."
        )
    if algorithm.strip().upper() != "AES-256":
        raise DomainValidationError(
            f"Unsupported encryption algorithm '{algorithm}'. "
            "Data classified Sensitive must use AES-256 at rest and in transit (BR-BA-007)."
        )


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-008 - Retention Calculation by Classification
# ---------------------------------------------------------------------------
def calculate_retention_policy(classification: str, start_date: Optional[date] = None) -> Tuple[int, date]:
    """Calculate retention period in years and expiry date according to classification.
    
    Ref: BR-BA-008, AFR-BA-030, AFR-BA-056.
    """
    c_norm = classification.strip().upper() if classification else CLASS_ROUTINE
    years = RETENTION_YEARS_POLICY.get(c_norm, 5)
    base_date = start_date or date.today()
    try:
        expiry = base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handle leap day February 29
        expiry = base_date + timedelta(days=years * 365)
    return years, expiry


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-005 - Sensitive Restoration Approval
# ---------------------------------------------------------------------------
def is_sensitive_restoration_approval_required(classification: str) -> bool:
    """Check if restoration requires SysAdmin approval before proceeding.
    
    Ref: BR-BA-005, AFR-BA-042.
    """
    if not classification:
        return False
    return classification.strip().upper() == CLASS_SENSITIVE


def validate_sensitive_restoration_decision(actor_role: str, outcome: str) -> None:
    """Validate SysAdmin decision on Sensitive data restoration.
    
    Ref: BR-BA-005, AFR-BA-042, AFR-BA-043. Enforces permission: badms.restoration.approve_sensitive.
    """
    if not actor_role or actor_role.strip().lower() not in SYSADMIN_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' cannot approve sensitive restoration. "
            "Restoration of data classified Sensitive requires SysAdmin approval (BR-BA-005)."
        )
    norm_outcome = outcome.strip().upper()
    if norm_outcome not in {"APPROVE", "REJECT"}:
        raise DomainValidationError(f"Invalid restoration decision outcome '{outcome}'.")


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-016 - Storage-Extension Usage Validation
# ---------------------------------------------------------------------------
def validate_storage_extension_submission(
    used_storage_mb: float,
    allocated_storage_mb: float,
    requested_additional_mb: float,
    threshold_percent: float = 80.0
) -> None:
    """Validate that storage-extension request meets threshold and positive quantity rules.
    
    Ref: BR-BA-016, AFR-BA-046. Enforces permission: badms.storage.request_extension.
    """
    if requested_additional_mb <= 0:
        raise DomainValidationError("Requested additional storage must be greater than zero.")
    if allocated_storage_mb <= 0:
        raise DomainValidationError("Current allocated storage quota must be positive.")
    
    usage_percent = (used_storage_mb / allocated_storage_mb) * 100.0
    if usage_percent < threshold_percent:
        raise DomainValidationError(
            f"Current storage usage ({usage_percent:.1f}%) has not reached the threshold "
            f"({threshold_percent:.1f}%) required for quota extension (BR-BA-016)."
        )


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-014, BR-BA-015 - Failure Alerting & Consecutive Escalation
# ---------------------------------------------------------------------------
def evaluate_backup_failure_response(consecutive_failure_count: int) -> Tuple[bool, bool, str]:
    """Evaluate alerting SLA and escalation to Director of IT.
    
    Ref: BR-BA-014, BR-BA-015, AFR-BA-057, AFR-BA-058, AFR-BA-059.
    Returns:
        (alert_sysadmin, escalate_director_it, message)
    """
    alert_sysadmin = True  # Every failed backup alerts SysAdmin within 5 minutes SLA
    escalate_director_it = False
    message = "Backup failed: SysAdmin alert dispatched within 5-minute SLA (BR-BA-014)."
    
    if consecutive_failure_count >= 3:
        escalate_director_it = True
        message += (
            f" ESCALATION: {consecutive_failure_count} consecutive backup failures recorded. "
            "Escalated to Director of IT (BR-BA-015)."
        )
    return alert_sysadmin, escalate_director_it, message


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-011, BR-BA-012, BR-BA-019 - Backup Schedule Resolution
# ---------------------------------------------------------------------------
def validate_schedule_parameters(
    frequency: str,
    scheduled_time: str,
    repository_path: str
) -> None:
    """Validate schedule parameters to prevent invalid configurations.
    
    Ref: BR-BA-012, AFR-BA-015.
    """
    valid_freqs = {"HOURLY", "DAILY", "WEEKLY", "MONTHLY"}
    if frequency.strip().upper() not in valid_freqs:
        raise DomainValidationError(
            f"Invalid backup frequency '{frequency}'. Must be one of {valid_freqs} (BR-BA-012)."
        )
    if not scheduled_time or not scheduled_time.strip():
        raise DomainValidationError("Scheduled time cannot be empty (BR-BA-012).")
    if not repository_path or not repository_path.strip():
        raise DomainValidationError("Target repository path cannot be empty (BR-BA-012).")


def resolve_effective_schedule(dataset_name: str, local_schedules: List[Dict[str, Any]], global_schedules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Resolve effective schedule: local schedule overrides global default.
    
    Ref: BR-BA-011, BR-BA-019, AFR-BA-054, AFR-BA-055.
    """
    # Check for active local schedule for this dataset
    for sched in local_schedules:
        if sched.get("dataset_name", "").lower() == dataset_name.lower() and sched.get("is_active", True):
            return {"source": "LOCAL", "schedule": sched}
    
    # Fallback to global schedule
    for sched in global_schedules:
        if sched.get("is_active", True):
            return {"source": "GLOBAL", "schedule": sched}
    
    return None


# ---------------------------------------------------------------------------
# Business Rule: BR-BA-018, BR-BA-019, BR-BA-021 - Governance Authorizations
# ---------------------------------------------------------------------------
def validate_special_archival_authority(actor_role: str) -> None:
    """Validate that only Super Admin can execute special archival operations.
    
    Ref: BR-BA-018, AFR-BA-037. Enforces permission: badms.archival.special_operate.
    """
    if not actor_role or actor_role.strip().lower() not in SUPERADMIN_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' cannot perform special archival operations. "
            "Only Super Admin holds authority for offline-triggered special archival (BR-BA-018)."
        )


def validate_global_backup_policy_authority(actor_role: str) -> None:
    """Validate that only Super Admin defines global schedules and default policies.
    
    Ref: BR-BA-019, AFR-BA-053. Enforces permission: badms.schedule.manage_global.
    """
    if not actor_role or actor_role.strip().lower() not in SUPERADMIN_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' is not authorized to set global backup policy. "
            "Only Super Admin possesses institution-wide global backup authority (BR-BA-019)."
        )


def validate_it_security_policy_authority(actor_role: str) -> None:
    """Validate that only IT Security manages RBAC and security policies.
    
    Ref: BR-BA-021, AFR-BA-066. Enforces permission: badms.security.administer.
    """
    if not actor_role or actor_role.strip().lower() not in IT_SECURITY_ROLES:
        raise DomainValidationError(
            f"Role '{actor_role}' is not authorized to administer security policies. "
            "Only IT Security manages security policies and RBAC configurations (BR-BA-021)."
        )
