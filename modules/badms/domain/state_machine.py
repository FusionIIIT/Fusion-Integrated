"""Pure Python state machine and rule guards for BADMS (no Django/DRF dependencies)."""

# Archival states (CW-BA-01, BW-BA-01..03)
ARCHIVAL_SUBMITTED = "submitted"
ARCHIVAL_HOD_APPROVED = "hod_approved"
ARCHIVAL_HOD_REJECTED = "hod_rejected"
ARCHIVAL_CLASSIFIED = "classified"
ARCHIVAL_ENCRYPTION_CONFIGURED = "encryption_configured"
ARCHIVAL_COMPLETED = "completed"
ARCHIVAL_SPECIAL_EXECUTED = "special_executed"

# Storage Extension states (CW-BA-02, BW-BA-04..05)
STORAGE_SUBMITTED = "submitted"
STORAGE_APPROVED = "approved"
STORAGE_REJECTED = "rejected"

# Restoration states (CW-BA-03, BW-BA-06..07)
RESTORATION_SUBMITTED = "submitted"
RESTORATION_SYSADMIN_APPROVED = "sysadmin_approved"
RESTORATION_SYSADMIN_REJECTED = "sysadmin_rejected"
RESTORATION_COMPLETED = "completed"

# Classification tiers (BR-BA-004, BR-BA-006)
TIER_ROUTINE = "routine"
TIER_SENSITIVE = "sensitive"
TIER_CRITICAL = "critical"
TIER_ARCHIVAL = "archival"
ALL_TIERS = {TIER_ROUTINE, TIER_SENSITIVE, TIER_CRITICAL, TIER_ARCHIVAL}

# Retention policy by tier in years (BR-BA-008)
RETENTION_YEARS = {
    TIER_ROUTINE: 1,
    TIER_ARCHIVAL: 5,
    TIER_SENSITIVE: 7,
    TIER_CRITICAL: 10,
}


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot transition from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class RuleViolation(Exception):
    def __init__(self, rule_id: str, message: str):
        super().__init__(f"[{rule_id}] {message}")
        self.rule_id = rule_id
        self.message = message


def validate_hod_decision(action: str) -> str:
    """Validates HoD approval or rejection (BR-BA-002, BR-BA-009)."""
    if action == "approve":
        return ARCHIVAL_HOD_APPROVED
    elif action == "reject":
        return ARCHIVAL_HOD_REJECTED
    raise InvalidTransition("submitted", action)


def validate_storage_quota_threshold(current_usage_mb: int, quota_mb: int) -> None:
    """Validates that storage extension is requested when quota is full/reached threshold (BR-BA-016)."""
    if quota_mb > 0 and current_usage_mb < quota_mb:
        raise RuleViolation("BR-BA-016", "Storage extension can only be requested when current quota is reached.")


def calculate_effective_schedule(dataset_code: str, local_schedules: dict, global_schedule: dict | None) -> dict | None:
    """Local backup schedule overrides institution-wide global backup schedule (BR-BA-011)."""
    if dataset_code in local_schedules:
        return local_schedules[dataset_code]
    return global_schedule


def check_repeated_failure_escalation(consecutive_failures: int) -> bool:
    """Escalates to Director of IT when 3 consecutive backup failures occur (BR-BA-015)."""
    return consecutive_failures >= 3
