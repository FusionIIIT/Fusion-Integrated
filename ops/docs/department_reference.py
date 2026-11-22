"""Generate the Department traceability reference from the blueprint and source."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/09-department"
MODULE = ROOT / "modules/department"
DECLARATIONS = {
    "announcements": ("services.py", "publish_announcement"),
    "audience": ("selectors.py", "visible_announcements"),
    "maintenance": ("services.py", "maintain_announcement"),
    "inventory": ("services.py", "insert_stock"),
    "request": ("services.py", "request_stock"),
    "issue": ("services.py", "advance_stock_request"),
    "movement": ("migrations/0003_stock_movement_immutable.py", "Migration"),
    "history": ("selectors.py", "stock_requests_for"),
    "submit": ("services.py", "submit_feedback"),
    "review": ("services.py", "advance_feedback"),
    "confidentiality": ("selectors.py", "feedback_for"),
    "upload": ("administration.py", "upload_timetable"),
    "edit_slot": ("administration.py", "replace_timetable_slot"),
    "overlap": ("administration.py", "_assert_slot_available"),
    "labs": ("administration.py", "save_lab"),
    "lab_view": ("selectors.py", "labs_for"),
    "programme": ("api/administration.py", "AcademicContextView"),
    "timetable": ("selectors.py", "timetable_for"),
    "details": ("administration.py", "update_general_details"),
    "proposal": ("administration.py", "propose_official_details"),
    "decision": ("administration.py", "decide_official_details"),
}

REFERENCES = {
    "CFR": [
        "announcements",
        "audience",
        "maintenance",
        "inventory",
        "issue",
        "history",
        "submit",
        "review",
        "-",
        "-",
        "upload",
        "labs",
        "timetable",
        "details",
        "proposal",
        "-",
    ],
    "AFR": [
        "announcements",
        "audience",
        "audience",
        "maintenance",
        "maintenance",
        "maintenance",
        "inventory",
        "inventory",
        "request",
        "request",
        "issue",
        "issue",
        "issue",
        "movement",
        "movement",
        "history",
        "submit",
        "confidentiality",
        "review",
        "review",
        "review",
        "review",
        "confidentiality",
        "-",
        "-",
        "-",
        "-",
        "-",
        "upload",
        "edit_slot",
        "overlap",
        "-",
        "-",
        "labs",
        "lab_view",
        "programme",
        "timetable",
        "details",
        "proposal",
        "decision",
        "request",
        "request",
        "issue",
        "submit",
        "review",
        "announcements",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
    ],
    "UC": [
        "audience",
        "announcements",
        "maintenance",
        "request",
        "issue",
        "issue",
        "submit",
        "review",
        "upload",
        "details",
        "lab_view",
        "decision",
        "-",
        "review",
        "-",
        "-",
        "labs",
        "timetable",
        "inventory",
        "-",
        "-",
        "-",
    ],
    "BR": [
        "announcements",
        "audience",
        "announcements",
        "maintenance",
        "request",
        "issue",
        "issue",
        "submit",
        "review",
        "overlap",
        "proposal",
        "history",
        "decision",
        "-",
        "request",
        "movement",
        "confidentiality",
        "review",
        "-",
        "-",
        "-",
        "-",
        "-",
        "-",
    ],
    "BW": ["issue", "issue", "review", "review", "decision", "decision", "-", "-"],
    "CW": ["issue", "review", "decision", "-"],
}


def source_link(key):
    if key == "-":
        return "Deferred external dependency"
    filename, decl = DECLARATIONS[key]
    path = MODULE / filename
    nodes = ast.parse(path.read_text()).body
    node = next((entry for entry in nodes if getattr(entry, "name", None) == decl), None)
    if node is None:
        raise ValueError(f"Missing declaration {decl} in {path}")
    relative = path.relative_to(ROOT)
    return f"[`{relative}:{node.lineno}`](../../{relative}#L{node.lineno})"


def main():
    lines = [
        "# Department implementation reference",
        "",
        "| Specification ID | Primary source |",
        "| --- | --- |",
    ]
    blueprint = (DOCS / "department-blueprint.md").read_text()
    for prefix, number in re.findall(r"^\| (CFR|AFR|UC|BR|BW|CW)-DEPT-(\d+) \|", blueprint, re.M):
        key = REFERENCES[prefix][int(number) - 1]
        lines.append(f"| `{prefix}-DEPT-{number}` | {source_link(key)} |")
    (DOCS / "department-reference.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
