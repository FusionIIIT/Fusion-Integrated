#!/usr/bin/env python
"""Generate the RSPC module reference documentation.

Resolves every live requirement, business rule, use case, and workflow ID
to the exact file:line that implements and enforces it.
Exits 0 on success; exits non-zero if any link fails to resolve.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DOC = ROOT / "docs" / "09-rspc" / "rspc-reference.md"

# Format: (Category, ID, Description, RelativePath, SearchSymbolOrAnchor)
REFERENCE_ITEMS = [
    # Coherent & Atomic Functional Requirements
    (
        "Requirements",
        "RSPC-CFR-001",
        "Proposal Creation and Initial Formulation",
        "modules/rspc/services/proposal.py",
        "def create_proposal",
    ),
    (
        "Requirements",
        "RSPC-CFR-002",
        "Department Endorsement by Head of Department",
        "modules/rspc/services/proposal.py",
        "def endorse_proposal",
    ),
    (
        "Requirements",
        "RSPC-CFR-003",
        "Institutional Approval by Dean (RSPC)",
        "modules/rspc/services/proposal.py",
        "def approve_proposal",
    ),
    (
        "Requirements",
        "RSPC-CFR-004",
        "Project Sanction and Registration",
        "modules/rspc/services/project.py",
        "def sanction_and_register_project",
    ),
    (
        "Requirements",
        "RSPC-CFR-005",
        "Financial Ledger and Head Allocation",
        "modules/rspc/models/ledger.py",
        "class ProjectFundTransaction",
    ),
    (
        "Requirements",
        "RSPC-CFR-006",
        "Fund Requisition and Disbursement Verification",
        "modules/rspc/services/finance.py",
        "def disburse_funds",
    ),
    (
        "Requirements",
        "RSPC-CFR-010",
        "Project Extension Lifecycle",
        "modules/rspc/services/extension.py",
        "def request_project_extension",
    ),
    (
        "Requirements",
        "RSPC-CFR-011",
        "Project Closure Protocol",
        "modules/rspc/services/extension.py",
        "def request_project_closure",
    ),
    (
        "Requirements",
        "RSPC-FR-022",
        "Represented Policy Overheads Computation",
        "modules/rspc/domain/invariants.py",
        "def calculate_institutional_overheads",
    ),
    (
        "Requirements",
        "RSPC-FR-035",
        "Budget Head Deficit Prohibition",
        "modules/rspc/domain/invariants.py",
        "def validate_disbursement",
    ),
    (
        "Requirements",
        "RSPC-FR-045",
        "Role-Scoped Proposal Visibility",
        "modules/rspc/selectors/scoping.py",
        "def scope_proposals",
    ),
    # Business Rules
    (
        "Business Rules",
        "BR-RSPC-004",
        "Dean Routing / Forwarding Decision Gate",
        "modules/rspc/domain/state_machine.py",
        "class ProposalStateMachine",
    ),
    (
        "Business Rules",
        "BR-RSPC-013",
        "Mandatory Proposal Completeness on Submission",
        "modules/rspc/services/proposal.py",
        "def submit_proposal",
    ),
    (
        "Business Rules",
        "BR-RSPC-014",
        "Institutional Overhead Policy Validation",
        "modules/rspc/domain/invariants.py",
        "def calculate_institutional_overheads",
    ),
    (
        "Business Rules",
        "BR-RSPC-016",
        "Decision Remarks and Audit Trail Recording",
        "modules/rspc/models/proposal.py",
        "class ProposalReview",
    ),
    (
        "Business Rules",
        "BR-RSPC-027",
        "Disbursement within Sanctioned Budget Limit",
        "modules/rspc/services/finance.py",
        "def disburse_funds",
    ),
    (
        "Business Rules",
        "BR-RSPC-028",
        "Deficit Rejection on Exceeding Budget",
        "modules/rspc/domain/invariants.py",
        "def validate_disbursement",
    ),
    (
        "Business Rules",
        "BR-RSPC-035",
        "Budget Head Non-Negative Balance Invariant",
        "modules/rspc/domain/invariants.py",
        "def validate_budget_head_positive",
    ),
    (
        "Business Rules",
        "BR-RSPC-040",
        "Approved Closure Updates Project Lifecycle",
        "modules/rspc/services/extension.py",
        "def approve_project_closure",
    ),
    (
        "Business Rules",
        "BR-RSPC-041",
        "Pending Closure Retains Active State Unarchived",
        "modules/rspc/services/extension.py",
        "def request_project_closure",
    ),
    (
        "Business Rules",
        "BR-RSPC-045",
        "In-Scope Project Query Narrowing",
        "modules/rspc/selectors/scoping.py",
        "def scope_projects",
    ),
    (
        "Business Rules",
        "BR-RSPC-046",
        "Out-of-Scope Query Returns 404 Not Found",
        "modules/rspc/selectors/scoping.py",
        "def get_project_or_404",
    ),
    (
        "Business Rules",
        "BR-RSPC-069",
        "Director Approval Threshold on Cumulative Extensions",
        "modules/rspc/domain/invariants.py",
        "def validate_extension_request",
    ),
    # Use Cases
    (
        "Use Cases",
        "RSPC-UC-001",
        "View Project Portfolio",
        "modules/rspc/selectors/scoping.py",
        "def scope_projects",
    ),
    (
        "Use Cases",
        "RSPC-UC-002",
        "Submit Research Proposal",
        "modules/rspc/services/proposal.py",
        "def submit_proposal",
    ),
    (
        "Use Cases",
        "RSPC-UC-003",
        "Endorse Proposal as HoD",
        "modules/rspc/services/proposal.py",
        "def endorse_proposal",
    ),
    (
        "Use Cases",
        "RSPC-UC-004",
        "Approve Proposal as Dean (RSPC)",
        "modules/rspc/services/proposal.py",
        "def approve_proposal",
    ),
    (
        "Use Cases",
        "RSPC-UC-005",
        "Manage Project Budget Heads",
        "modules/rspc/services/finance.py",
        "def allocate_budget_head",
    ),
    (
        "Use Cases",
        "RSPC-UC-006",
        "Disburse Project Funds",
        "modules/rspc/services/finance.py",
        "def disburse_funds",
    ),
    (
        "Use Cases",
        "RSPC-UC-011",
        "Request Project Extension",
        "modules/rspc/services/extension.py",
        "def request_project_extension",
    ),
    (
        "Use Cases",
        "RSPC-UC-012",
        "Review Project Extension",
        "modules/rspc/services/extension.py",
        "def review_project_extension",
    ),
    (
        "Use Cases",
        "RSPC-UC-015",
        "Request and Approve Project Closure",
        "modules/rspc/services/extension.py",
        "def request_project_closure",
    ),
    # Workflows
    (
        "Workflows",
        "BW-RSPC-01",
        "Proposal Formulation to Dean Approval",
        "modules/rspc/domain/state_machine.py",
        "class ProposalStateMachine",
    ),
    (
        "Workflows",
        "BW-RSPC-02",
        "Project Sanction and Allocation Lifecycle",
        "modules/rspc/services/project.py",
        "def sanction_and_register_project",
    ),
    (
        "Workflows",
        "BW-RSPC-03",
        "Fund Disbursement Requisition Lifecycle",
        "modules/rspc/services/finance.py",
        "def disburse_funds",
    ),
    (
        "Workflows",
        "BW-RSPC-04",
        "Project Closure Protocol",
        "modules/rspc/services/extension.py",
        "def approve_project_closure",
    ),
    (
        "Workflows",
        "CW-RSPC-01",
        "Composite Multi-Stage Proposal Evaluation",
        "modules/rspc/domain/state_machine.py",
        "TRANSITIONS = {",
    ),
]


def resolve_line(rel_path: str, symbol: str) -> int:
    path = ROOT / rel_path
    if not path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {rel_path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        if symbol in line:
            return idx

    raise ValueError(f"Symbol '{symbol}' not found in {rel_path}")


def generate_reference() -> None:
    errors: list[str] = []
    rows: list[dict[str, str]] = []

    for category, spec_id, desc, rel_path, symbol in REFERENCE_ITEMS:
        try:
            line_no = resolve_line(rel_path, symbol)
            norm_path = rel_path.replace("\\", "/")
            link = f"[{norm_path}:{line_no}](../../{norm_path}#L{line_no})"
            rows.append(
                {
                    "category": category,
                    "id": spec_id,
                    "desc": desc,
                    "enforcement": link,
                }
            )
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"{spec_id} ({rel_path}): {exc}")

    if errors:
        print("ERROR: Failed to resolve RSPC reference links:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    # Build markdown output
    content = [
        "# RSPC Module Teaching Reference",
        "",
        "This document provides verified `file:line` traceability from every active requirement,",
        "business rule, use case, and workflow ID to the code that enforces it.",
        "",
        "Generated by `ops/docs/rspc_reference.py` in compliance with Step 7.6.",
        "",
        "| Category | ID | Description | Enforcement Point |",
        "|:---|:---|:---|:---|",
    ]

    content.extend(
        f"| {r['category']} | **{r['id']}** | {r['desc']} | {r['enforcement']} |"
        for r in rows
    )

    content.append("")
    OUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOC.write_text("\n".join(content), encoding="utf-8")
    print(f"Successfully generated {OUT_DOC.relative_to(ROOT)} ({len(rows)} live IDs verified).")


if __name__ == "__main__":
    generate_reference()
