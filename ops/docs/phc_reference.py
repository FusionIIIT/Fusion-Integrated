#!/usr/bin/env python
"""Write docs/09-phc/phc-reference.md: a file:line link per live PHC spec id; exit 1 if dead."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "09-phc" / "phc-reference.md"
M = "modules/phc"

# id -> (file, the text that marks its enforcement point in that file)
LINKS: dict[str, tuple[str, str]] = {
    "CFR-PHC-001": (f"{M}/services/schedules.py", "def create_schedule"),
    "CFR-PHC-002": (f"{M}/services/records.py", "def record_visit"),
    "CFR-PHC-003": (f"{M}/services/reimbursements.py", "def submit_claim"),
    "CFR-PHC-004": (f"{M}/services/reimbursements.py", "def transition_claim"),
    "CFR-PHC-005": (f"{M}/selectors/scoping.py", "def claims_for"),
    "CFR-PHC-006": (f"{M}/services/inventory.py", "def adjust_stock"),
    "CFR-PHC-007": (f"{M}/services/requisitions.py", "def submit"),
    "CFR-PHC-008": (f"{M}/services/operations.py", "def log_ambulance"),
    "CFR-PHC-009": (f"{M}/services/operations.py", "def publish_advisory"),
    "CFR-PHC-010": (f"{M}/selectors/reports.py", "def build"),
    "CFR-PHC-011": (f"{M}/api/views.py", "class _Gates"),
    "CFR-PHC-012": (f"{M}/services/trail.py", "def audit"),
    "AFR-PHC-001": (f"{M}/selectors/scoping.py", "def schedules_for"),
    "AFR-PHC-002": (f"{M}/services/schedules.py", "def update_schedule"),
    "AFR-PHC-003": (f"{M}/services/schedules.py", "def mark_attendance"),
    "AFR-PHC-004": (f"{M}/services/schedules.py", "def create_schedule"),
    "AFR-PHC-005": (f"{M}/services/schedules.py", "def publish_schedule"),
    "AFR-PHC-006": (f"{M}/services/records.py", "def search_patients"),
    "AFR-PHC-007": (f"{M}/services/records.py", "def record_visit"),
    "AFR-PHC-008": (f"{M}/services/records.py", "Prescription.objects.bulk_create"),
    "AFR-PHC-009": (f"{M}/selectors/scoping.py", "def visits_for"),
    "AFR-PHC-010": (f"{M}/selectors/scoping.py", "prefetch_related(\"prescriptions\")"),
    "AFR-PHC-011": (f"{M}/api/views.py", "class RecordsPdfView"),
    "AFR-PHC-012": (f"{M}/selectors/scoping.py", "return qs.filter(patient_user_id=uid)"),
    "AFR-PHC-013": (f"{M}/domain/rules.py", "def require_employee"),
    "AFR-PHC-014": (f"{M}/services/reimbursements.py", "# PHC-BR-05"),
    "AFR-PHC-015": (f"{M}/domain/rules.py", "def check_submission_window"),
    "AFR-PHC-016": (f"{M}/services/reimbursements.py", "def submit_claim"),
    "AFR-PHC-017": (f"{M}/domain/state_machine.py", "CLAIM_TRANSITIONS = ("),
    "AFR-PHC-018": (f"{M}/domain/state_machine.py", '"forward", P_CLAIM_REVIEW'),
    "AFR-PHC-019": (f"{M}/domain/state_machine.py", '"verify", P_CLAIM_UPDATE'),
    "AFR-PHC-020": (f"{M}/domain/state_machine.py", '"approve", P_CLAIM_APPROVE'),
    "AFR-PHC-021": (f"{M}/domain/state_machine.py", '"pay", P_CLAIM_UPDATE'),
    "AFR-PHC-022": (f"{M}/api/serializers.py", "class ClaimSerializer"),
    "AFR-PHC-023": (f"{M}/services/reimbursements.py", "# PHC-BR-13"),
    "AFR-PHC-024": (f"{M}/domain/rules.py", "def apply_stock_change"),
    "AFR-PHC-025": (f"{M}/domain/rules.py", "def is_low_stock"),
    "AFR-PHC-026": (f"{M}/services/inventory.py", "# PHC-BR-07"),
    "AFR-PHC-027": (f"{M}/services/requisitions.py", "def submit"),
    "AFR-PHC-028": (f"{M}/models/requisitions.py", "default=RequisitionStatus.PENDING_APPROVAL"),
    "AFR-PHC-029": (f"{M}/domain/state_machine.py", "REQUISITION_TRANSITIONS = ("),
    "AFR-PHC-030": (f"{M}/services/requisitions.py", "# PHC-BR-11"),
    "AFR-PHC-031": (f"{M}/domain/state_machine.py", '"fulfill", P_REQUISITION_UPDATE'),
    "AFR-PHC-032": (f"{M}/services/operations.py", "def log_ambulance"),
    "AFR-PHC-033": (f"{M}/services/operations.py", "def publish_advisory"),
    "AFR-PHC-034": (f"{M}/selectors/reports.py", "BUILDERS = {"),
    "AFR-PHC-035": (f"{M}/domain/reports.py", "def suppress"),
    "AFR-PHC-036": (f"{M}/api/views.py", "def get_permissions"),
    "AFR-PHC-037": (f"{M}/migrations/0002_append_only_triggers.py", "APPEND_ONLY = ("),
    "AFR-PHC-038": (f"{M}/models/reimbursements.py", "_FROZEN_FIELDS = ("),
    "PHC-UC-01": (f"{M}/api/views.py", "class ScheduleListView"),
    "PHC-UC-02": (f"{M}/api/views.py", "class VisitListView"),
    "PHC-UC-03": (f"{M}/api/views.py", "class RecordsPdfView"),
    "PHC-UC-04": (f"{M}/services/reimbursements.py", "def submit_claim"),
    "PHC-UC-05": (f"{M}/api/views.py", "class ClaimDetailView"),
    "PHC-UC-06": (f"{M}/services/records.py", "def record_visit"),
    "PHC-UC-07": (f"{M}/services/schedules.py", "def update_schedule"),
    "PHC-UC-08": (f"{M}/services/schedules.py", "def mark_attendance"),
    "PHC-UC-09": (f"{M}/services/inventory.py", "def adjust_stock"),
    "PHC-UC-10": (f"{M}/services/requisitions.py", "def submit"),
    "PHC-UC-11": (f"{M}/services/operations.py", "def log_ambulance"),
    "PHC-UC-12": (f"{M}/services/operations.py", "def publish_advisory"),
    "PHC-UC-13": (f"{M}/api/views.py", "class ReportView"),
    "PHC-UC-14": (f"{M}/services/requisitions.py", "fulfilled_by_user_id = actor.user_id"),
    "PHC-UC-15": (f"{M}/domain/state_machine.py", '"forward", P_CLAIM_REVIEW'),
    "PHC-UC-16": (f"{M}/services/requisitions.py", 'if event in ("approve", "reject"):'),
    "PHC-UC-19": (f"{M}/domain/state_machine.py", '"verify", P_CLAIM_UPDATE'),
    "PHC-UC-20": (f"{M}/domain/state_machine.py", '"approve", P_CLAIM_APPROVE'),
    "PHC-UC-21": (f"{M}/domain/state_machine.py", '"pay", P_CLAIM_UPDATE'),
    "PHC-UC-22": (f"{M}/services/schedules.py", "def publish_schedule"),
    "PHC-BR-01": (f"{M}/selectors/scoping.py", "# PHC-BR-01"),
    "PHC-BR-02": (f"{M}/selectors/scoping.py", "# PHC-BR-02"),
    "PHC-BR-03": (f"{M}/api/views.py", "# PHC-BR-03"),
    "PHC-BR-04": (f"{M}/domain/rules.py", "# PHC-BR-04"),
    "PHC-BR-05": (f"{M}/services/reimbursements.py", "# PHC-BR-05"),
    "PHC-BR-06": (f"{M}/domain/rules.py", "# PHC-BR-06"),
    "PHC-BR-07": (f"{M}/domain/rules.py", "# PHC-BR-07"),
    "PHC-BR-08": (f"{M}/domain/state_machine.py", "# PHC-BR-08"),
    "PHC-BR-09": (f"{M}/services/reimbursements.py", "# PHC-BR-09"),
    "PHC-BR-10": (f"{M}/domain/state_machine.py", "# PHC-BR-10"),
    "PHC-BR-11": (f"{M}/services/requisitions.py", "# PHC-BR-11"),
    "PHC-BR-12": (f"{M}/domain/reports.py", "PHC-BR-12"),
    "PHC-BR-13": (f"{M}/services/reimbursements.py", "# PHC-BR-13"),
    "PHC-BR-14": (f"{M}/models/reimbursements.py", "# PHC-BR-14"),
    "BW-PHC-01": (f"{M}/domain/state_machine.py", '"pay", P_CLAIM_UPDATE'),
    "BW-PHC-02": (f"{M}/domain/state_machine.py", '"reject", P_CLAIM_APPROVE'),
    "BW-PHC-03": (f"{M}/domain/state_machine.py", '"fulfill", P_REQUISITION_UPDATE'),
    "BW-PHC-04": (f"{M}/domain/state_machine.py", '"reject", P_REQUISITION_APPROVE'),
    "CW-PHC-01": (f"{M}/services/reimbursements.py", "# CW-PHC-01"),
    "CW-PHC-02": (f"{M}/domain/state_machine.py", "CW-PHC-02"),
}


def resolve(path: str, needle: str) -> int | None:
    file = ROOT / path
    if not file.is_file():
        return None
    for number, line in enumerate(file.read_text().splitlines(), start=1):
        if needle in line:
            return number
    return None


def main() -> int:
    rows, dead = [], []
    for spec_id, (path, needle) in LINKS.items():
        line = resolve(path, needle)
        if line is None:
            dead.append(f"{spec_id}: {needle!r} not found in {path}")
            continue
        rows.append(f"| {spec_id} | [{path}:{line}](../../{path}#L{line}) |")
    if dead:
        print("\n".join(dead), file=sys.stderr)
        return 1
    OUT.write_text("# PHC spec-to-code reference\n\n"
                   "Generated by `ops/docs/phc_reference.py`; do not edit by hand.\n\n"
                   "| Spec id | Enforced at |\n|---|---|\n" + "\n".join(rows) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} ids")
    return 0


if __name__ == "__main__":
    sys.exit(main())
