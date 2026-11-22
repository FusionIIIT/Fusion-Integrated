"""Generate a source-linked guide to BADMS specification enforcement."""

import ast
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/09-badms/badms-teaching-reference.md"

AREAS = {
    "CFR-BA-001": (
        "Manual backup",
        [
            "modules/badms/api/views.py:BackupRunCollectionView",
            "modules/badms/services/backups.py:queue_manual",
            "modules/badms/services/backups.py:perform_backup",
        ],
    ),
    "CFR-BA-002": (
        "Scheduled backup",
        [
            "modules/badms/tasks.py:run_due_schedules",
            "modules/badms/services/backups.py:effective_schedules",
            "modules/badms/services/backups.py:perform_backup",
        ],
    ),
    "CFR-BA-003": (
        "Local schedule management",
        [
            "modules/badms/api/views.py:BackupScheduleCollectionView",
            "modules/badms/api/views.py:BackupScheduleDetailView",
        ],
    ),
    "CFR-BA-004": (
        "Backup status and history",
        ["modules/badms/api/views.py:BackupRunCollectionView"],
    ),
    "CFR-BA-005": (
        "Archival intake",
        [
            "modules/badms/api/views.py:ArchiveCollectionView",
            "modules/badms/api/serializers.py:ArchiveCreateSerializer",
        ],
    ),
    "CFR-BA-006": (
        "HoD archival review",
        [
            "modules/badms/api/views.py:ArchiveDecisionView",
            "modules/badms/services/archives.py:decide",
        ],
    ),
    "CFR-BA-007": (
        "Authoritative classification",
        [
            "modules/badms/api/views.py:ArchiveClassificationView",
            "modules/badms/services/archives.py:classify",
            "modules/badms/services/storage.py:retention_deadline",
        ],
    ),
    "CFR-BA-008": (
        "Sensitive encryption and archive",
        [
            "modules/badms/api/views.py:ArchiveEncryptionView",
            "modules/badms/services/archives.py:create_sensitive_archive",
            "modules/badms/services/storage.py:require_secure_storage",
            "modules/badms/services/s3_storage.py:AES256URLLib3Session",
        ],
    ),
    "CFR-BA-009": (
        "Archival tracking and notices",
        [
            "modules/badms/api/views.py:ArchiveDetailView",
            "modules/badms/services/notifications.py:enqueue",
        ],
    ),
    "CFR-BA-010": (
        "Special archival",
        [
            "modules/badms/api/views.py:SpecialArchiveView",
            "modules/badms/services/special_archives.py:perform",
        ],
    ),
    "CFR-BA-011": (
        "Restoration",
        [
            "modules/badms/api/views.py:RestorationCollectionView",
            "modules/badms/api/views.py:RestorationDecisionView",
            "modules/badms/api/views.py:RestorationExecutionView",
            "modules/badms/services/restorations.py:request_restore",
            "modules/badms/services/restorations.py:decide_sensitive",
            "modules/badms/services/restorations.py:execute_restore",
        ],
    ),
    "CFR-BA-012": (
        "Storage extension",
        [
            "modules/badms/api/views.py:StorageExtensionCollectionView",
            "modules/badms/api/views.py:StorageExtensionDecisionView",
            "modules/badms/services/storage_extensions.py:submit",
            "modules/badms/services/storage_extensions.py:decide",
        ],
    ),
    "CFR-BA-013": (
        "Threshold monitoring",
        [
            "modules/badms/tasks.py:monitor_storage_thresholds",
            "modules/badms/api/views.py:MyStorageThresholdView",
        ],
    ),
    "CFR-BA-014": (
        "Global schedules and defaults",
        [
            "modules/badms/api/views.py:BackupScheduleCollectionView",
            "modules/badms/services/backups.py:effective_schedules",
        ],
    ),
    "CFR-BA-015": (
        "Classification retention",
        [
            "modules/badms/api/views.py:SecurityPolicyView",
            "modules/badms/services/storage.py:retention_deadline",
            "modules/badms/tasks.py:enforce_retention",
        ],
    ),
    "CFR-BA-016": (
        "Backup failure escalation",
        [
            "modules/badms/services/backups.py:_record_outcome",
            "modules/badms/services/backups.py:_queue_failure_alerts",
            "modules/badms/services/notifications.py:enqueue",
        ],
    ),
    "CFR-BA-017": (
        "Storage extension notices",
        [
            "modules/badms/services/storage_extensions.py:submit",
            "modules/badms/services/storage_extensions.py:decide",
            "modules/badms/services/notifications.py:enqueue",
        ],
    ),
    "CFR-BA-018": (
        "Audit and operational reports",
        [
            "modules/badms/api/views.py:AuditEventListView",
            "modules/badms/api/views.py:DepartmentReportView",
            "modules/badms/api/views.py:SecurityReportView",
            "modules/badms/models.py:AuditEvent",
        ],
    ),
    "CFR-BA-019": (
        "Security policy and role separation",
        [
            "modules/badms/api/views.py:SecurityPolicyView",
            "modules/badms/registry.py:PERMISSIONS",
            "modules/badms/registry.py:readiness",
            "modules/badms/management/commands/check_badms_readiness.py:Command",
        ],
    ),
}

RULES = {
    "BR-BA-001": (
        "Manual backup authorization",
        [
            "modules/badms/api/views.py:BackupRunCollectionView",
            "modules/badms/services/backups.py:queue_manual",
        ],
    ),
    "BR-BA-002": (
        "Department HoD approval",
        [
            "modules/badms/api/views.py:ArchiveDecisionView",
            "modules/badms/services/archives.py:decide",
        ],
    ),
    "BR-BA-003": (
        "IT Security encryption authority",
        [
            "modules/badms/api/views.py:ArchiveEncryptionView",
            "modules/badms/services/archives.py:create_sensitive_archive",
        ],
    ),
    "BR-BA-004": (
        "SysAdmin authoritative classification",
        [
            "modules/badms/api/views.py:ArchiveClassificationView",
            "modules/badms/services/archives.py:classify",
        ],
    ),
    "BR-BA-005": (
        "Sensitive restoration approval",
        [
            "modules/badms/api/views.py:RestorationDecisionView",
            "modules/badms/services/restorations.py:decide_sensitive",
        ],
    ),
    "BR-BA-006": (
        "Initial classification default",
        ["modules/badms/api/serializers.py:ArchiveCreateSerializer"],
    ),
    "BR-BA-007": (
        "Sensitive AES-256 protection",
        [
            "modules/badms/services/storage.py:require_secure_storage",
            "modules/badms/services/s3_storage.py:AES256URLLib3Session",
        ],
    ),
    "BR-BA-008": (
        "Retention by classification",
        [
            "modules/badms/api/views.py:SecurityPolicyView",
            "modules/badms/services/storage.py:retention_deadline",
        ],
    ),
    "BR-BA-009": (
        "HoD storage-extension decision",
        [
            "modules/badms/api/views.py:StorageExtensionDecisionView",
            "modules/badms/services/storage_extensions.py:decide",
        ],
    ),
    "BR-BA-010": (
        "Department scope",
        [
            "modules/badms/api/views.py:ArchiveDecisionView",
            "modules/badms/api/views.py:StorageExtensionDecisionView",
        ],
    ),
    "BR-BA-011": (
        "Local schedule overrides global",
        ["modules/badms/services/backups.py:effective_schedules"],
    ),
    "BR-BA-012": (
        "Schedule parameter validation",
        ["modules/badms/api/serializers.py:BackupScheduleSerializer"],
    ),
    "BR-BA-013": (
        "Repository reachability",
        [
            "modules/badms/tasks.py:run_due_schedules",
            "modules/badms/services/storage.py:require_secure_storage",
        ],
    ),
    "BR-BA-014": (
        "Failure alert timing",
        ["modules/badms/services/backups.py:_queue_failure_alerts"],
    ),
    "BR-BA-015": (
        "Repeated failure escalation",
        [
            "modules/badms/services/backups.py:_record_outcome",
            "modules/badms/services/backups.py:_queue_failure_alerts",
        ],
    ),
    "BR-BA-016": (
        "Storage usage validation",
        ["modules/badms/services/storage_extensions.py:submit"],
    ),
    "BR-BA-017": (
        "Storage-extension decision criteria",
        ["modules/badms/services/storage_extensions.py:decide"],
    ),
    "BR-BA-018": (
        "Special archive authority",
        [
            "modules/badms/api/views.py:SpecialArchiveView",
            "modules/badms/services/special_archives.py:perform",
        ],
    ),
    "BR-BA-019": (
        "Global schedule authority",
        ["modules/badms/api/views.py:BackupScheduleCollectionView"],
    ),
    "BR-BA-020": (
        "Protected information scope",
        [
            "modules/badms/api/views.py:AuditEventListView",
            "modules/badms/api/views.py:SecurityReportView",
        ],
    ),
    "BR-BA-021": (
        "IT Security RBAC authority",
        ["modules/badms/api/views.py:SecurityPolicyView", "modules/badms/registry.py:PERMISSIONS"],
    ),
}

USE_CASES = {
    "BA-UC-001": [
        "modules/badms/api/views.py:BackupRunCollectionView",
        "modules/badms/services/backups.py:queue_manual",
    ],
    "BA-UC-002": [
        "modules/badms/api/views.py:ArchiveCollectionView",
        "modules/badms/services/storage.py:badms_storage",
    ],
    "BA-UC-003": [
        "modules/badms/api/views.py:ArchiveDecisionView",
        "modules/badms/services/archives.py:decide",
    ],
    "BA-UC-004": [
        "modules/badms/api/views.py:ArchiveClassificationView",
        "modules/badms/services/archives.py:classify",
    ],
    "BA-UC-005": [
        "modules/badms/api/views.py:ArchiveEncryptionView",
        "modules/badms/services/archives.py:create_sensitive_archive",
        "modules/badms/services/s3_storage.py:AES256URLLib3Session",
    ],
    "BA-UC-006": [
        "modules/badms/tasks.py:run_due_schedules",
        "modules/badms/services/backups.py:perform_backup",
    ],
    "BA-UC-007": [
        "modules/badms/api/views.py:StorageExtensionCollectionView",
        "modules/badms/services/storage_extensions.py:submit",
    ],
    "BA-UC-008": [
        "modules/badms/api/views.py:StorageExtensionDecisionView",
        "modules/badms/services/storage_extensions.py:decide",
    ],
    "BA-UC-009": [
        "modules/badms/api/views.py:BackupScheduleCollectionView",
        "modules/badms/api/views.py:BackupScheduleDetailView",
    ],
    "BA-UC-010": [
        "modules/badms/api/views.py:SpecialArchiveView",
        "modules/badms/services/special_archives.py:perform",
    ],
    "BA-UC-011": [
        "modules/badms/api/views.py:BackupScheduleCollectionView",
        "modules/badms/services/backups.py:effective_schedules",
    ],
    "BA-UC-012": ["modules/badms/api/views.py:AuditEventListView"],
    "BA-UC-013": [
        "modules/badms/api/views.py:SecurityReportView",
        "modules/badms/api/views.py:AuditEventListView",
    ],
    "BA-UC-014": ["modules/badms/api/views.py:BackupRunCollectionView"],
    "BA-UC-015": [
        "modules/badms/api/views.py:ArchiveDetailView",
        "modules/badms/api/views.py:RestorationCollectionView",
    ],
    "BA-UC-016": [
        "modules/badms/api/views.py:RestorationCollectionView",
        "modules/badms/services/restorations.py:request_restore",
    ],
    "BA-UC-017": [
        "modules/badms/api/views.py:RestorationDecisionView",
        "modules/badms/services/restorations.py:decide_sensitive",
    ],
    "BA-UC-018": [
        "modules/badms/api/views.py:RestorationExecutionView",
        "modules/badms/services/restorations.py:execute_restore",
    ],
    "BA-UC-019": [
        "../Fusion_System_Administrator/Backend/backend/iam/views/auth.py:RolePermissionAdminView",
        "../Fusion_System_Administrator/Backend/backend/iam/views/auth.py:SecurityAuditView",
    ],
    "BA-UC-020": [
        "modules/badms/api/views.py:SecurityPolicyView",
        "modules/badms/services/storage.py:require_secure_storage",
    ],
    "BA-UC-021": ["modules/badms/api/views.py:DepartmentReportView"],
    "BA-UC-022": [
        "modules/badms/api/views.py:MyStorageThresholdView",
        "modules/badms/tasks.py:monitor_storage_thresholds",
    ],
    "BA-UC-023": [
        "modules/badms/models.py:AuditEvent",
        "modules/badms/services/archives.py:classify",
    ],
}

USE_CASE_NAMES = {
    "BA-UC-001": "Trigger Manual Backup",
    "BA-UC-002": "Submit Secure Archival Request",
    "BA-UC-003": "Decide Secure Archival Request",
    "BA-UC-004": "Classify Secure Archival Data",
    "BA-UC-005": "Configure Sensitive-Data Encryption",
    "BA-UC-006": "Execute Scheduled Automatic Backup",
    "BA-UC-007": "Submit Storage-Extension Request",
    "BA-UC-008": "Decide Storage-Extension Request",
    "BA-UC-009": "Configure Local Backup Schedule",
    "BA-UC-010": "Perform Special Archival Operation",
    "BA-UC-011": "Define Global Backup Schedules and Defaults",
    "BA-UC-012": "View Audit Logs and Activity History",
    "BA-UC-013": "Audit Data Activity and Review Security Reports",
    "BA-UC-014": "View Backup History and Status",
    "BA-UC-015": "Track Request Status",
    "BA-UC-016": "Request Data Restoration",
    "BA-UC-017": "Approve Sensitive Data Restoration",
    "BA-UC-018": "Execute Data Restoration",
    "BA-UC-019": "Manage RBAC Permissions",
    "BA-UC-020": "Define and Enforce Security Policies",
    "BA-UC-021": "View Department Data-Management Reports",
    "BA-UC-022": "Monitor Storage Thresholds",
    "BA-UC-023": "Record Audit Event",
}


def definition_line(target: str) -> tuple[Path, int]:
    path_text, symbol = target.split(":", 1)
    path = (ROOT / path_text).resolve()
    tree = ast.parse(path.read_text())
    parts = symbol.split(".")
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == parts[-1]
        ):
            return path, node.lineno
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            names = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(name, ast.Name) and name.id == parts[-1] for name in names):
                return path, node.lineno
    raise ValueError(f"Definition not found for {target}")


def code_links(targets: list[str]) -> str:
    links = []
    for target in targets:
        path, line = definition_line(target)
        rel = Path(os.path.relpath(path, OUTPUT.parent)).as_posix()
        links.append(f"[`{target.split(':', 1)[1]}`](../../{rel}#L{line})")
    return ", ".join(links)


def main() -> None:
    blueprint = (ROOT / "docs/09-badms/badms-blueprint.md").read_text()
    requirement_rows = re.findall(r"\| (CFR-BA-\d{3}) \| ([^|]+) \| ([^|]+) \|", blueprint)
    if {row[0] for row in requirement_rows} != set(AREAS):
        raise ValueError("Blueprint CFR list and teaching reference mappings differ.")
    lines = [
        "# BADMS teaching reference",
        "",
        "Generated by `ops/docs/badms_teaching_reference.py`.",
        "",
        "## Live consolidated requirements and atomic requirements",
        "",
        "| CFR and name | Live AFRs | Enforcement points |",
        "|---|---|---|",
    ]
    for cfr, name, afrs in requirement_rows:
        lines.append(f"| `{cfr}` {name.strip()} | {afrs.strip()} | {code_links(AREAS[cfr][1])} |")
    lines.extend(
        [
            "",
            "## Business rules",
            "",
            "| Rule | Rule description | Enforcement points |",
            "|---|---|---|",
        ]
    )
    for rule, (description, targets) in RULES.items():
        lines.append(f"| `{rule}` | {description} | {code_links(targets)} |")
    lines.extend(["", "## Use cases", "", "| Use case | Enforcement points |", "|---|---|"])
    for uc, name in USE_CASE_NAMES.items():
        lines.append(f"| `{uc}` {name} | {code_links(USE_CASES[uc])} |")
    lines.extend(
        [
            "",
            "## Workflows",
            "",
            (
                "The archive, storage-extension, and restoration workflow transitions are "
                "defined centrally in [`domain/transitions.py`](../../modules/badms/domain/"
                "transitions.py). Their state tables and role boundaries are described in "
                "[`state-machine.md`](state-machine.md). HTTP endpoints are enumerated in "
                "[`api/urls.py`](../../modules/badms/api/urls.py)."
            ),
            "",
            "## Scope notes",
            "",
            (
                "IAM role permission mapping and the `BA-UC-019` permission-administration "
                "API are implemented in the separately approved `Fusion_System_Administrator` "
                "checkout. No parallel BADMS RBAC tables are created. The BADMS role "
                "administration UI is deferred by user decision. Actual retention durations "
                "and production S3/KMS resources remain institute/deployment inputs; the "
                "implementation does not invent them."
            ),
            "",
        ]
    )
    OUTPUT.write_text("\n".join(lines))
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)}; verified {len(requirement_rows)} CFRs and "
        f"{len(RULES)} business-rule enforcement links."
    )


if __name__ == "__main__":
    main()
