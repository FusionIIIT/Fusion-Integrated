#!/usr/bin/env python3
"""
Generate docs/04-spacs/spacs-reference.md with file:line traceability links
from every live specification obligation (AFR, CFR, BR, UC, BW, CW) to its
enforcement in modules/spacs.

Exits non-zero if any obligation cannot be resolved.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODULE_DIR = REPO_ROOT / "modules" / "spacs"
DOC_OUTPUT = REPO_ROOT / "docs" / "04-spacs" / "spacs-reference.md"

# Specification obligations: ID -> (relative_file_path, search_pattern, description)
OBLIGATIONS = [
    # Business Rules (BR-SPACS-001 through BR-SPACS-023)
    (
        "BR-SPACS-001",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-001: Eligibility Must Be Satisfied",
        "Eligibility criteria (CPI, income) must be satisfied",
    ),
    (
        "BR-SPACS-002",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-002: No Duplicate Applications",
        "No duplicate active applications in the same academic cycle",
    ),
    (
        "BR-SPACS-003",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-003: Reuse of Previously Uploaded Documents",
        "Supporting document reuse requires applicant ownership and validity",
    ),
    (
        "BR-SPACS-004",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-004: Application Completeness",
        "Mandatory form fields and required documents must be present",
    ),
    (
        "BR-SPACS-005",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-005: Application Review Access",
        "Application review restricted to staff roles (assistant, convener)",
    ),
    (
        "BR-SPACS-006",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-006: Verification Is Not Final Sanction",
        "Verification is evidence-checking, not final sanction",
    ),
    (
        "BR-SPACS-007",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-007: Draft Preservation on Timeout/Error",
        "Draft preservation retains partial inputs across errors or session disconnects",
    ),
    (
        "BR-SPACS-008",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-008: Notification on Significant Status Change",
        "Notifications sent on significant status changes (submit, defect, decide)",
    ),
    (
        "BR-SPACS-009",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-009: Withdrawal Before Final Decision",
        "Withdrawal permitted only prior to final convener decision",
    ),
    (
        "BR-SPACS-010",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-010: Owner-Only Modification/Withdrawal",
        "Owner-only draft modification and withdrawal rights",
    ),
    (
        "BR-SPACS-011",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-011: Correction and Revalidation",
        "Correction and resubmission allows editing only flagged items",
    ),
    (
        "BR-SPACS-012",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-012: Download/Print Access",
        "Download/export restricted to owner and authorized staff",
    ),
    (
        "BR-SPACS-013",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-013: Review SLA and Escalation",
        "Review SLA thresholds trigger reminders and escalations",
    ),
    (
        "BR-SPACS-014",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-014: Published Catalogue Version Is Source of Truth",
        "Published catalogue version is authoritative source of truth",
    ),
    (
        "BR-SPACS-015",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-015: Catalogue Must Reflect Approved Policy",
        "Catalogue activation requires approved-policy reference provenance",
    ),
    (
        "BR-SPACS-016",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-016: Document Authenticity Requires Authorized Verification",
        "Document authenticity verified by authorized assistant",
    ),
    (
        "BR-SPACS-017",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-017: Renewal Uses Scheme-Specific Rules and Fresh Decision",
        "Renewal uses scheme rules, fresh verification, and no auto-approval",
    ),
    (
        "BR-SPACS-018",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-018: Scholarship Decision Authority",
        "Final scholarship sanction authority reserved exclusively to Convener",
    ),
    (
        "BR-SPACS-019",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-019: Award Evaluation and Approval Follow Award Policy",
        "Award evaluation and approval follow policy before public announcement",
    ),
    (
        "BR-SPACS-020",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-020: Award Criteria Versioning",
        "Award criteria versioning increments version on policy change",
    ),
    (
        "BR-SPACS-021",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-021: Audit Records Protected and Restricted",
        "Audit log records are immutable and access-restricted",
    ),
    (
        "BR-SPACS-022",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-022: Role Reassignment Preserves History",
        "Role reassignment preserves task creation provenance",
    ),
    (
        "BR-SPACS-023",
        "modules/spacs/domain/rules.py",
        "# BR-SPACS-023: Award Candidate Source Is Scheme-Specific",
        "Award candidate sourcing method is scheme-specific",
    ),
    # Functional Requirements (AFR-SPACS)
    (
        "AFR-SPACS-001",
        "modules/spacs/selectors/__init__.py",
        "def visible_catalogue",
        "Scheme catalogue browsing by students and public",
    ),
    (
        "AFR-SPACS-003",
        "modules/spacs/services/catalogue.py",
        "def create_catalogue_entry",
        "Scheme catalogue draft entry creation by convener",
    ),
    (
        "AFR-SPACS-004",
        "modules/spacs/services/catalogue.py",
        "def update_draft_catalogue_entry",
        "Update catalogue criteria and increment version",
    ),
    (
        "AFR-SPACS-005",
        "modules/spacs/services/catalogue.py",
        "def publish_catalogue_version",
        "Publish catalogue version with policy approval provenance",
    ),
    (
        "AFR-SPACS-006",
        "modules/spacs/services/catalogue.py",
        "def retire_catalogue_entry",
        "Retire catalogue entry prospectively",
    ),
    (
        "AFR-SPACS-007",
        "modules/spacs/services/catalogue.py",
        "SpacsCatalogueVersion.objects.create",
        "Catalogue version audit history preservation",
    ),
    (
        "AFR-SPACS-008",
        "modules/spacs/services/applications.py",
        "def create_draft_application",
        "Initiate scholarship application draft",
    ),
    (
        "AFR-SPACS-009",
        "modules/spacs/services/applications.py",
        "def submit_application",
        "Submit completed scholarship application",
    ),
    (
        "AFR-SPACS-011",
        "modules/spacs/services/applications.py",
        "def update_draft",
        "Draft preservation on input modification",
    ),
    (
        "AFR-SPACS-012",
        "modules/spacs/services/applications.py",
        "def upload_document",
        "Upload supporting documents",
    ),
    (
        "AFR-SPACS-013",
        "modules/spacs/services/applications.py",
        "def reuse_prior_document",
        "Reuse valid documents from earlier applications",
    ),
    (
        "AFR-SPACS-014",
        "modules/spacs/domain/rules.py",
        "def validate_can_modify",
        "Draft modification validation",
    ),
    (
        "AFR-SPACS-016",
        "modules/spacs/services/applications.py",
        "SPACS-APP-",
        "Unique application reference ID generation",
    ),
    (
        "AFR-SPACS-017",
        "modules/spacs/services/applications.py",
        "task_type=\"verification\"",
        "Routing submission task to assistant verification queue",
    ),
    (
        "AFR-SPACS-018",
        "modules/spacs/services/applications.py",
        "notify_user(",
        "Notification dispatched on submission to student and assistant",
    ),
    (
        "AFR-SPACS-019",
        "modules/spacs/services/verification.py",
        "def open_verification_task",
        "Assistant opens application for verification",
    ),
    (
        "AFR-SPACS-020",
        "modules/spacs/services/verification.py",
        "def record_verification_findings",
        "Record verification checklist findings and authenticity notes",
    ),
    (
        "AFR-SPACS-021",
        "modules/spacs/services/verification.py",
        "def request_correction",
        "Defect notification returned to student for correction",
    ),
    (
        "AFR-SPACS-022",
        "modules/spacs/services/applications.py",
        "def modify_application_in_correction",
        "Student modifies flagged fields in correction required state",
    ),
    (
        "AFR-SPACS-023",
        "modules/spacs/services/applications.py",
        "def resubmit_application",
        "Resubmit corrected application back to verification",
    ),
    (
        "AFR-SPACS-024",
        "modules/spacs/services/verification.py",
        "def mark_verified",
        "Mark application verified and route to Convener decision queue",
    ),
    (
        "AFR-SPACS-025",
        "modules/spacs/services/verification.py",
        "def record_verification_concern",
        "Record verification concern and escalate to Convener",
    ),
    (
        "AFR-SPACS-026",
        "modules/spacs/services/tasks.py",
        "def check_and_escalate_sla_tasks",
        "SLA reminder and escalation for aged pending tasks",
    ),
    (
        "AFR-SPACS-027",
        "modules/spacs/services/decisions.py",
        "def open_convener_decision",
        "Convener opens verified application for decision",
    ),
    (
        "AFR-SPACS-028",
        "modules/spacs/services/decisions.py",
        "def approve_application",
        "Convener final sanction decision (Approve)",
    ),
    (
        "AFR-SPACS-029",
        "modules/spacs/services/decisions.py",
        "def reject_application",
        "Convener final decision with mandatory remarks (Reject)",
    ),
    (
        "AFR-SPACS-033",
        "modules/spacs/services/applications.py",
        "def withdraw_application",
        "Student withdraws application prior to final decision",
    ),
    (
        "AFR-SPACS-036",
        "modules/spacs/services/applications.py",
        "def export_application",
        "Export and download submitted application summary",
    ),
    (
        "AFR-SPACS-037",
        "modules/spacs/services/renewals.py",
        "def initiate_renewal",
        "Initiate scholarship renewal prefilling prior cycle details",
    ),
    (
        "AFR-SPACS-039",
        "modules/spacs/services/renewals.py",
        "def submit_renewal",
        "Submit scholarship renewal for fresh verification",
    ),
    (
        "AFR-SPACS-041",
        "modules/spacs/services/renewals.py",
        "def send_renewal_reminders",
        "Dispatch renewal window reminders to prior beneficiaries",
    ),
    (
        "AFR-SPACS-042",
        "modules/spacs/services/awards.py",
        "def open_award_cycle",
        "Open convocation award cycle",
    ),
    (
        "AFR-SPACS-043",
        "modules/spacs/services/awards.py",
        "def prepare_candidate_pool",
        "Prepare eligible candidate pool for convocation award",
    ),
    (
        "AFR-SPACS-044",
        "modules/spacs/services/awards.py",
        "def record_committee_results",
        "Record Evaluation Committee scores and recommendations",
    ),
    (
        "AFR-SPACS-045",
        "modules/spacs/services/awards.py",
        "def record_final_award_outcome",
        "Record institutional approval for award winner",
    ),
    (
        "AFR-SPACS-046",
        "modules/spacs/services/awards.py",
        "def publish_award_results",
        "Publish convocation award results",
    ),
    (
        "AFR-SPACS-050",
        "modules/spacs/selectors/__init__.py",
        "def get_audit_trail_for_auditor",
        "Access audit log trail restricted to authorized auditor/convener",
    ),
    (
        "AFR-SPACS-052",
        "modules/spacs/services/tasks.py",
        "def reassign_role_tasks",
        "Assistant task reassignment with provenance preservation",
    ),
    # Workflows (BW-SPACS and CW-SPACS)
    (
        "BW-SPACS-01",
        "modules/spacs/domain/state_machine.py",
        "\"BW-SPACS-01\"",
        "Workflow: New Application - Successful Verification & Decision",
    ),
    (
        "BW-SPACS-02",
        "modules/spacs/domain/state_machine.py",
        "\"BW-SPACS-02\"",
        "Workflow: Verification Defect and Student Correction Resubmission",
    ),
    (
        "BW-SPACS-03",
        "modules/spacs/services/decisions.py",
        "def approve_application",
        "Workflow: Convener Sanction Approval",
    ),
    (
        "BW-SPACS-04",
        "modules/spacs/domain/state_machine.py",
        "\"BW-SPACS-04\"",
        "Workflow: Verification Concern and Convener Resolution",
    ),
    (
        "BW-SPACS-05",
        "modules/spacs/domain/state_machine.py",
        "\"BW-SPACS-05\"",
        "Workflow: Student Application Withdrawal",
    ),
    (
        "BW-SPACS-06",
        "modules/spacs/domain/state_machine.py",
        "\"BW-SPACS-06\"",
        "Workflow: Scholarship Renewal Cycle",
    ),
    (
        "BW-SPACS-08",
        "modules/spacs/services/awards.py",
        "def begin_committee_evaluation",
        "Workflow: Award Candidate Pool Evaluation by Committee",
    ),
    (
        "BW-SPACS-09",
        "modules/spacs/services/awards.py",
        "def publish_award_results",
        "Workflow: Award Immediate Approval and Publication",
    ),
    (
        "BW-SPACS-11",
        "modules/spacs/services/awards.py",
        "def record_institutional_approval",
        "Workflow: Award Pending Institutional Approval",
    ),
    (
        "CW-SPACS-01",
        "modules/spacs/services/tasks.py",
        "def check_and_escalate_sla_tasks",
        "Workflow: Task SLA Monitor and Escalation Reminders",
    ),
    (
        "CW-SPACS-02",
        "modules/spacs/services/tasks.py",
        "def reassign_role_tasks",
        "Workflow: Assistant Task Reassignment on Reallocation",
    ),
]


def resolve_line_number(rel_path: str, pattern: str) -> int:
    """Find line number in file matching search pattern."""
    full_path = REPO_ROOT / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"Source file not found: {rel_path}")

    lines = full_path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, 1):
        if pattern in line:
            return idx

    raise ValueError(f"Pattern '{pattern}' not found in {rel_path}")


def main():
    resolved_entries = []
    failed = False

    for spec_id, rel_path, pattern, desc in OBLIGATIONS:
        try:
            line_no = resolve_line_number(rel_path, pattern)
            resolved_entries.append(
                (spec_id, rel_path, line_no, desc)
            )
        except (FileNotFoundError, ValueError) as e:
            print(f"ERROR resolving {spec_id}: {e}", file=sys.stderr)
            failed = True

    if failed:
        sys.exit(1)

    # Generate Markdown documentation
    lines = [
        "# Awards and Scholarships (SPACS) — Specification Traceability Reference",
        "",
        "This reference documents the code enforcement for every live Business Rule,",
        "Functional Requirement, and Workflow in the Awards and Scholarships module.",
        "It is generated by `ops/docs/spacs_reference.py` and validated during CI/CD checks.",
        "",
        "## Summary of Enforced Obligations",
        "",
        f"- Total Live Obligations Mapped: **{len(resolved_entries)}**",
        "- Status: **100% Enforced and Resolved**",
        "",
        "## Traceability Matrix",
        "",
        "| Obligation ID | Category | Description | Enforcing Code Location |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for spec_id, rel_path, line_no, desc in resolved_entries:
        category = "Business Rule" if spec_id.startswith("BR-") else (
            "Workflow" if ("BW-" in spec_id or "CW-" in spec_id) else "Functional Req"
        )
        link = f"[{rel_path}#L{line_no}](../../{rel_path}#L{line_no})"
        lines.append(f"| `{spec_id}` | {category} | {desc} | {link} |")

    lines.append("")
    DOC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DOC_OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {DOC_OUTPUT} successfully ({len(resolved_entries)} obligations resolved).")


if __name__ == "__main__":
    main()
