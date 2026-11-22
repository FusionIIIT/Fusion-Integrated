"""Emit deterministic HR-EIS teaching reference from declared code surfaces."""

import argparse
import ast
import re
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

workflow = import_module("modules.hreis.domain.workflow")
registry = import_module("modules.hreis.registry")
TRANSITIONS = workflow.TRANSITIONS
MODULE = registry.MODULE
NAV_ITEMS = registry.NAV_ITEMS
PERMISSIONS = registry.PERMISSIONS
ROLE_GRANTS = registry.ROLE_GRANTS
OUTPUT = ROOT / "docs" / "09-hreis" / "hreis-reference.md"
ROUTES = ROOT / "client" / "src" / "modules" / "hreis" / "routes.tsx"

OPEN_IDS = {"HR-CFR-013", "HR-AFR-059", "HR-AFR-090", "HR-AFR-091", "HR-AFR-092", "HR-AFR-093"}
DEFAULT_SYMBOLS = {
    "selectors/scoping.py": ("service_records_for", "requests_for", "notifications_for"),
    "services/records.py": ("create_record", "update_record"),
    "services/requests.py": ("submit_leave", "submit_claim", "submit_appraisal"),
    "services/transitions.py": ("_append",),
    "services/appraisals.py": ("assign_reviewers", "review_appraisal"),
    "services/notifications.py": (
        "create_pending_action_reminders",
        "create_policy_deadline_notifications",
        "deliver_pending_notifications",
    ),
    "domain/leave.py": ("validate_submission",),
    "domain/claims.py": ("validate_ltc", "validate_cpda"),
    "domain/workflow.py": ("resolve",),
    "tasks.py": ("generate_notifications", "deliver_notifications"),
}


def source_link(identifier, filename, symbol):
    path = ROOT / "modules/hreis" / filename
    if not path.is_file():
        raise ValueError(f"Unresolved enforcement file: {identifier}: {filename}")
    source = path.read_text(encoding="utf-8")
    nodes = ast.parse(source).body
    node = next(
        (
            node
            for node in nodes
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == symbol
        ),
        None,
    )
    if node is None or not 1 <= node.lineno <= len(source.splitlines()):
        raise ValueError(f"Unresolved enforcement symbol: {identifier}: {filename}::{symbol}")
    relative = path.relative_to(ROOT).as_posix()
    return f"[{relative}:{node.lineno}](../../{relative}#L{node.lineno})"


def enforcement_links():
    blueprint = (OUTPUT.parent / "hreis-blueprint.md").read_text(encoding="utf-8")
    entries = []
    for line in blueprint.split("## 3.2", 1)[0].splitlines():
        columns = [column.strip().strip("`") for column in line.split("|")[1:-1]]
        if not columns or not re.fullmatch(r"(?:HR-(?:CFR|AFR|UC)|BR-HR|[BC]W-HR)-\d+", columns[0]):
            continue
        identifier, description, _, enforcement, _ = columns
        targets = re.findall(r"([\w/]+\.py)(?:::(\w+)\(\))?", enforcement)
        if not targets:
            targets = (
                [("contracts.py", "get_approved_claim_statuses")]
                if "finance" in enforcement
                else [("registry.py", "readiness")]
            )
        links = []
        for filename, symbol in targets:
            if filename == "scoping.py":
                filename = "selectors/scoping.py"
            symbols = (symbol,) if symbol else DEFAULT_SYMBOLS.get(filename, ())
            if not symbols:
                raise ValueError(f"Declare enforcement functions for {identifier}: {filename}")
            links.extend(source_link(identifier, filename, name) for name in symbols)
        status = (
            "OPEN external contract/definition; linked local boundary only"
            if identifier in OPEN_IDS
            else "Local enforcement entrypoints; acceptance status in quality report"
        )
        entries.append(f"| {identifier} | {description} | {status} | {'; '.join(links)} |")
    identifiers = [entry.split("|")[1].strip() for entry in entries]
    if len(identifiers) != 193 or len(set(identifiers)) != 193:
        raise ValueError("The live inventory must contain exactly 193 distinct specification IDs.")
    return entries


def make_reference() -> str:
    lines = [
        "# HR-EIS implementation reference",
        "",
        "Deterministic generated documentation from the local source registry.",
        "Run python ops/docs/hreis_reference.py after changing HR-EIS routes,",
        "permissions or workflow edges. The script never supplies institutional",
        "policy defaults.",
        "",
        "## Declared permissions",
        "",
        "| Permission | Purpose |",
        "|---|---|",
    ]
    lines.extend(f"| {code} | {label} |" for code, label in PERMISSIONS)
    lines.extend(
        [
            "",
            "## Registered role grants (not proof of live IAM provisioning)",
            "",
            "| Designation | Permissions |",
            "|---|---|",
        ]
    )
    for name, permissions in ROLE_GRANTS.items():
        lines.append(f"| {name} | {', '.join(permissions)} |")
    lines.extend(
        [
            "",
            "The Accounts Admin finance designation is provisionally mapped",
            "from the HR specification's Accountant actor and must be",
            "confirmed by the institution before production grants.",
            "",
            "## Navigation and guarded pages",
            "",
            "| URL | Permission |",
            "|---|---|",
        ]
    )
    found = dict(
        re.findall(
            r'\{\s*path:\s*"([^"]+)"\s*,?\s*element:\s*protectedPage\(\s*"([^"]+)"',
            ROUTES.read_text(encoding="utf-8"),
        )
    )
    for entry in NAV_ITEMS:
        route = entry["to"].removeprefix(MODULE["base_path"] + "/")
        guard = entry["required_permission"]
        if found.get(route) != guard:
            raise ValueError(f"Navigation/route permission mismatch: {route}")
        lines.append(f"| {entry['to']} | {guard} |")
    lines.extend(
        [
            "",
            "## Canonical state transitions",
            "",
            "| Family | Source state | Event | Target state | Actor | Required guards | Spec |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for edge in TRANSITIONS:
        guards = ", ".join(edge.guards) if edge.guards else "(none)"
        lines.append(
            f"| {edge.family} | {edge.source} | {edge.event} | {edge.target} | "
            f"{edge.actor} | {guards} | {edge.specification} |"
        )
    lines.extend(
        [
            "",
            "## Live specification enforcement destinations",
            "",
            "Links resolve against current source declarations. External requirements remain open;",
            "a local boundary link is not evidence of a provider connection or approved exception.",
            "",
            "| ID | Source requirement | Status | Enforcement file:line |",
            "|---|---|---|---|",
            *enforcement_links(),
        ]
    )
    lines.extend(
        [
            "",
            "## Operational constraints",
            "",
            "- Live policy versions are imported only from explicit institutional JSON",
            "  via the authenticated hreis_import_policies management command or HTTP.",
            "- Employee leave credits require a verified evidence reference.",
            "- Payroll/finance payment statuses are recorded locally with",
            "  immutable provenance, not bank or payroll execution.",
            "- External provider synchronization and institutional role mapping",
            "  remain deployment prerequisites.",
            "- The source RTM mentions returned LTC requests but the canonical",
            "  workflow contains no defined return event; no such state is invented.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    generated = make_reference()
    if options.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != generated:
            raise SystemExit("HR-EIS reference is stale; run python ops/docs/hreis_reference.py")
        return
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"HR-EIS reference refreshed: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
