# Generate and verify docs/09-psm/psm-reference.md with live file:line traceability links.
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS_OUT = ROOT / "docs" / "09-psm" / "psm-reference.md"
BACKEND_DIRS = [ROOT / "modules" / "psm"]
TEST_DIR = ROOT / "modules" / "psm" / "tests"
CLIENT_DIR = ROOT / "client" / "src" / "modules" / "psm"

RETIRED_IDS = frozenset(
    {
        "BR-PSM-002",
        "BR-PSM-011",
        "BR-PSM-016",
        "PSM-UC-004",
        "PSM-UC-006",
        "PSM-UC-018",
    }
)
SPEC_ID_RE = re.compile(
    r"\b(?:CFR-PSM-\d{3}|AFR-PSM-\d{3}|BR-PSM-\d{3}|PSM-UC-\d{3}|BW-PSM-\d{2}|CW-PSM-\d{2})\b"
)

EXACT_IMPL_SYMBOLS: dict[str, tuple[str, str]] = {
    "CFR-PSM-002": ("modules/psm/services/indents.py", "def modify_indent"),
    "CFR-PSM-003": ("modules/psm/services/stock.py", "def check_and_reserve"),
    "CFR-PSM-004": ("modules/psm/services/stock.py", "def dispatch_internal_issue"),
    "CFR-PSM-005": ("modules/psm/services/approvals.py", "def dept_admin_review"),
    "CFR-PSM-006": ("modules/psm/services/procurement.py", "def review_and_select_method"),
    "CFR-PSM-009": ("modules/psm/services/procurement.py", "def update_po_schedule"),
    "CFR-PSM-010": ("modules/psm/services/receipts.py", "def record_grn"),
    "CFR-PSM-011": ("modules/psm/services/discrepancies.py", "def report_discrepancy"),
    "CFR-PSM-012": ("modules/psm/services/discrepancies.py", "def resolve_case"),
    "CFR-PSM-014": ("modules/psm/services/vendors.py", "def onboard_vendor"),
    "CFR-PSM-015": ("modules/psm/services/transfers.py", "def request_transfer"),
    "CFR-PSM-017": ("modules/psm/services/common.py", "def enqueue_notification"),
    "CFR-PSM-018": ("modules/psm/services/common.py", "def audit_record"),
    "CFR-PSM-019": ("modules/psm/selectors/scoping.py", "def indents_for"),
    "CFR-PSM-020": ("modules/psm/services/policy.py", "def publish_policy"),
    "AFR-PSM-001": ("modules/psm/services/indents.py", "def create_indent"),
    "AFR-PSM-002": ("modules/psm/domain/indent_rules.py", "def validate_indent_completeness"),
    "AFR-PSM-003": ("modules/psm/services/indents.py", "def _submit_created_indent"),
    "AFR-PSM-004": ("modules/psm/domain/indent_rules.py", "def find_potential_duplicate"),
    "AFR-PSM-006": ("modules/psm/api/views_indents.py", "class IndentDetailView"),
    "AFR-PSM-007": ("modules/psm/models/indent.py", "class IndentTransition"),
    "AFR-PSM-008": ("modules/psm/services/indents.py", "def modify_indent"),
    "AFR-PSM-009": ("modules/psm/services/indents.py", "def withdraw_indent"),
    "AFR-PSM-012": ("modules/psm/api/views_indents.py", "class IndentDetailView"),
    "AFR-PSM-013": ("modules/psm/services/stock.py", "def check_and_reserve"),
    "AFR-PSM-014": ("modules/psm/services/stock.py", "def check_and_reserve"),
    "AFR-PSM-015": ("modules/psm/models/stock.py", "class StockReservation"),
    "AFR-PSM-016": ("modules/psm/domain/stock_rules.py", "def allocable_quantity"),
    "AFR-PSM-018": ("modules/psm/services/stock.py", "def dispatch_internal_issue"),
    "AFR-PSM-019": ("modules/psm/services/receipts.py", "def confirm_receipt"),
    "AFR-PSM-020": ("modules/psm/domain/receipt_rules.py", "def ensure_can_post_stock"),
    "AFR-PSM-021": ("modules/psm/domain/receipt_rules.py", "def ensure_can_post_stock"),
    "AFR-PSM-022": ("modules/psm/services/approvals.py", "def dept_admin_review"),
    "AFR-PSM-023": (
        "modules/psm/domain/approval_policy.py",
        "def allows_high_priority_direct_path",
    ),
    "AFR-PSM-024": ("modules/psm/services/approvals.py", "def dept_admin_review"),
    "AFR-PSM-026": ("modules/psm/domain/approval_policy.py", "def ensure_rejection_reason"),
    "AFR-PSM-027": ("modules/psm/services/approvals.py", "def sweep_slas"),
    "AFR-PSM-028": ("modules/psm/services/approvals.py", "def sweep_slas"),
    "AFR-PSM-029": ("modules/psm/services/indents.py", "def transition_indent"),
    "AFR-PSM-030": ("modules/psm/services/stock.py", "def _route_to_external"),
    "AFR-PSM-031": ("modules/psm/domain/approval_policy.py", "def select_procurement_method"),
    "AFR-PSM-036": ("modules/psm/services/tenders.py", "def award_tender"),
    "AFR-PSM-037": ("modules/psm/services/procurement.py", "def _resolve_po_authorization"),
    "AFR-PSM-038": ("modules/psm/models/procurement.py", "class PurchaseOrder"),
    "AFR-PSM-039": ("modules/psm/models/procurement.py", "class PurchaseOrder"),
    "AFR-PSM-040": ("modules/psm/domain/vendor_rules.py", "def ensure_vendor_verified"),
    "AFR-PSM-043": ("modules/psm/services/receipts.py", "def record_grn"),
    "AFR-PSM-044": ("modules/psm/models/procurement.py", "class GoodsReceiptNote"),
    "AFR-PSM-045": ("modules/psm/domain/receipt_rules.py", "def validate_grn_quantities"),
    "AFR-PSM-046": ("modules/psm/domain/receipt_rules.py", "def validate_grn_quantities"),
    "AFR-PSM-047": ("modules/psm/services/receipts.py", "def _post_po_receipt_stock"),
    "AFR-PSM-048": ("modules/psm/services/discrepancies.py", "def report_discrepancy"),
    "AFR-PSM-050": ("modules/psm/services/discrepancies.py", "def report_discrepancy"),
    "AFR-PSM-051": ("modules/psm/services/discrepancies.py", "def _transition_case"),
    "AFR-PSM-053": ("modules/psm/models/procurement.py", "class DiscrepancyCase"),
    "AFR-PSM-056": ("modules/psm/domain/finance_rules.py", "def three_way_match"),
    "AFR-PSM-057": ("modules/psm/domain/finance_rules.py", "def validate_payment_release"),
    "AFR-PSM-058": ("modules/psm/services/finance.py", "def _apply_match_outcome"),
    "AFR-PSM-059": ("modules/psm/services/finance.py", "def process_payment"),
    "AFR-PSM-060": ("modules/psm/services/vendors.py", "def onboard_vendor"),
    "AFR-PSM-061": ("modules/psm/services/vendors.py", "def update_vendor"),
    "AFR-PSM-062": ("modules/psm/domain/vendor_rules.py", "def validate_vendor_master"),
    "AFR-PSM-063": ("modules/psm/services/procurement.py", "def create_and_issue_po"),
    "AFR-PSM-064": ("modules/psm/services/finance.py", "def process_payment"),
    "AFR-PSM-065": ("modules/psm/models/vendor.py", "class VendorVersion"),
    "AFR-PSM-066": ("modules/psm/services/vendors.py", "def update_vendor"),
    "AFR-PSM-068": ("modules/psm/services/transfers.py", "def _reserve_source_stock"),
    "AFR-PSM-069": ("modules/psm/services/transfers.py", "def dispatch_transfer"),
    "AFR-PSM-070": ("modules/psm/services/transfers.py", "def confirm_transfer"),
    "AFR-PSM-071": ("modules/psm/services/transfers.py", "def _post_transfer_ledgers"),
    "AFR-PSM-072": ("modules/psm/services/transfers.py", "def _post_transfer_ledgers"),
    "AFR-PSM-073": ("modules/psm/services/transfers.py", "def confirm_transfer"),
    "AFR-PSM-074": ("modules/psm/selectors/reports.py", "def _operational_rows"),
    "AFR-PSM-075": ("modules/psm/selectors/reports.py", "def _procurement_rows"),
    "AFR-PSM-076": ("modules/psm/selectors/reports.py", "def _stock_rows"),
    "AFR-PSM-077": ("modules/psm/selectors/reports.py", "def _financial_rows"),
    "AFR-PSM-078": ("modules/psm/selectors/reports.py", "def build_report_rows"),
    "AFR-PSM-083": ("modules/psm/services/indents.py", "def _submit_created_indent"),
    "AFR-PSM-084": ("modules/psm/services/finance.py", "def _notify_payment_released"),
    "AFR-PSM-088": ("modules/psm/selectors/scoping.py", "def audit_logs_for"),
    "AFR-PSM-089": ("modules/psm/api/views_finance_reports.py", "class AuditLogListView"),
    "AFR-PSM-090": ("modules/psm/registry.py", "ROLE_GRANTS ="),
    "AFR-PSM-091": ("modules/psm/services/policy.py", "def publish_policy"),
    "AFR-PSM-092": ("modules/psm/services/policy.py", "def publish_policy"),
    "BR-PSM-019": ("modules/psm/services/discrepancies.py", "def resolve_case"),
    "PSM-UC-015": ("modules/psm/selectors/reports.py", "def _financial_rows"),
    "BW-PSM-02": ("modules/psm/services/procurement.py", "def review_and_select_method"),
    "BW-PSM-03": ("modules/psm/services/approvals.py", "def final_decision"),
    "BW-PSM-04": ("modules/psm/services/procurement.py", "def create_and_issue_po"),
}


def _all_live_ids() -> list[tuple[str, str]]:
    ids: list[tuple[str, str]] = [("CFR", f"CFR-PSM-{i:03d}") for i in range(1, 21)]
    ids.extend(("AFR", f"AFR-PSM-{i:03d}") for i in range(1, 93))
    ids.extend(
        ("BR", f"BR-PSM-{i:03d}") for i in range(1, 29) if f"BR-PSM-{i:03d}" not in RETIRED_IDS
    )
    ids.extend(
        ("UC", f"PSM-UC-{i:03d}") for i in range(1, 36) if f"PSM-UC-{i:03d}" not in RETIRED_IDS
    )
    ids.extend(("BW", f"BW-PSM-{i:02d}") for i in (1, 2, 3, 4, 5, 6, 7, 8, 10))
    ids.extend(("CW", f"CW-PSM-{i:02d}") for i in (1, 2))
    return ids


def _scan_files(
    paths: list[pathlib.Path], *, exclude_tests: bool = False, include_lines: bool = True
) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for base in paths:
        for file_path in sorted(base.rglob("*")):
            if not file_path.is_file() or file_path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if exclude_tests and "tests" in file_path.parts:
                continue
            rel = file_path.relative_to(ROOT).as_posix()
            for lineno, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
                for match in SPEC_ID_RE.findall(line):
                    ref = f"{rel}:{lineno}" if include_lines else rel
                    bucket = hits.setdefault(match, [])
                    if ref not in bucket:
                        bucket.append(ref)
    return hits


def _resolve_symbol_ref(spec_id: str) -> str:
    """Resolve an exact file:line reference for a spec ID via its enforcing function or class."""
    entry = EXACT_IMPL_SYMBOLS.get(spec_id)
    if entry is None:
        raise RuntimeError(f"Missing implementation mapping for {spec_id}")
    rel_path, pattern = entry
    target = ROOT / rel_path
    if not target.is_file():
        raise RuntimeError(f"Missing implementation file {rel_path} for {spec_id}")
    for lineno, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if pattern in line:
            return f"{rel_path}:{lineno}"
    raise RuntimeError(f"Symbol '{pattern}' not found in {rel_path} for {spec_id}")


def _verify_ref(ref: str) -> None:
    if ":" not in ref:
        target = ROOT / ref
        if not target.is_file():
            raise RuntimeError(f"Missing linked file: {ref}")
        return
    rel_path, line_str = ref.rsplit(":", 1)
    lineno = int(line_str)
    target = ROOT / rel_path
    if not target.is_file():
        raise RuntimeError(f"Missing linked file: {rel_path}")
    total_lines = len(target.read_text(encoding="utf-8").splitlines())
    if lineno < 1 or lineno > total_lines:
        raise RuntimeError(f"Invalid line {lineno} in {rel_path} (max {total_lines})")


def main() -> int:
    code_hits = _scan_files([*BACKEND_DIRS, CLIENT_DIR], exclude_tests=True, include_lines=True)
    test_hits = _scan_files([TEST_DIR], exclude_tests=False, include_lines=True)

    for retired in sorted(RETIRED_IDS):
        if retired in code_hits or retired in test_hits:
            sys.stderr.write(f"Retired ID {retired} found in codebase or tests.\n")
            return 1

    live_ids = _all_live_ids()
    missing_tests: list[str] = []
    intro = (
        "Reference index from `ops/docs/psm_reference.py`. Every live specification ID links to "
        "verified implementation and test locations. Retired IDs are absent from code and tests."
    )
    lines = [
        "# PSM Specification Traceability Reference",
        "",
        intro,
        "",
        "| Group | Spec ID | Implementation | Tests |",
        "| --- | --- | --- | --- |",
    ]
    for group, spec_id in live_ids:
        c_refs = code_hits.get(spec_id, [])[:3] or [_resolve_symbol_ref(spec_id)]
        t_refs = test_hits.get(spec_id, [])[:3]
        if not t_refs:
            missing_tests.append(spec_id)
        for ref in (*c_refs, *t_refs):
            _verify_ref(ref)
        c_cell = ", ".join(f"`{r}`" for r in c_refs)
        t_cell = ", ".join(f"`{r}`" for r in t_refs)
        lines.append(f"| {group} | `{spec_id}` | {c_cell} | {t_cell} |")

    if missing_tests:
        sys.stderr.write(f"Missing test traceability for {len(missing_tests)} IDs.\n")
        return 1

    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rel_out = DOCS_OUT.relative_to(ROOT).as_posix()
    sys.stdout.write(f"Verified {len(live_ids)} live spec IDs -> {rel_out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
