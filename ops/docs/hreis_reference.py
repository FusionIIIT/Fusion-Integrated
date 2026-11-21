"""Emit deterministic HR-EIS teaching reference from declared code surfaces."""
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
OUTPUT = ROOT / "docs" / "09-hreis" / "hreis-reference.generated.md"
ROUTES = ROOT / "client" / "src" / "modules" / "hreis" / "routes.tsx"


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
    lines.extend([
        "", "## Registered role grants (not proof of live IAM provisioning)",
        "", "| Designation | Permissions |",
        "|---|---|",
    ])
    for name, permissions in ROLE_GRANTS.items():
        lines.append(f"| {name} | {', '.join(permissions)} |")
    lines.extend([
        "", "The Accounts Admin finance designation is provisionally mapped",
        "from the HR specification's Accountant actor and must be",
        "confirmed by the institution before production grants.",
        "",
        "## Navigation and guarded pages",
        "", "| URL | Permission |",
        "|---|---|",
    ])
    found = dict(re.findall(
        r'\{\s*path:\s*"([^"]+)"\s*,?\s*element:\s*protectedPage\(\s*"([^"]+)"',
        ROUTES.read_text(encoding="utf-8"),
    ))
    for entry in NAV_ITEMS:
        route = entry["to"].removeprefix(MODULE["base_path"] + "/")
        guard = entry["required_permission"]
        if found.get(route) != guard:
            raise ValueError(f"Navigation/route permission mismatch: {route}")
        lines.append(f"| {entry['to']} | {guard} |")
    lines.extend([
        "", "## Canonical state transitions",
        "", "| Family | Source state | Event | Target state | Actor | Required guards | Spec |",
        "|---|---|---|---|---|---|---|",
    ])
    for edge in TRANSITIONS:
        guards = ", ".join(edge.guards) if edge.guards else "(none)"
        lines.append(
            f"| {edge.family} | {edge.source} | {edge.event} | {edge.target} | "
            f"{edge.actor} | {guards} | {edge.specification} |"
        )
    lines.extend([
        "", "## Operational constraints",
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
    ])
    return "\n".join(lines)


def main() -> None:
    OUTPUT.write_text(make_reference(), encoding="utf-8")
    print(f"HR-EIS reference refreshed: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
