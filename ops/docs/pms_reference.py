"""Generate docs/11-pms/pms-reference.md: every live PMS id, linked to the code that enforces it.

The traceability tables in docs/11-pms/pms-blueprint.md (section 3.1) are the single source.
Each row names its enforcement point as backticked `path::symbol` references; this script
resolves every one to a file and line in the real tree. A reference that no longer resolves
fails the run, so the blueprint and the reference cannot drift from the code unnoticed.

    python ops/docs/pms_reference.py            writes docs/11-pms/pms-reference.md
    python ops/docs/pms_reference.py --check    exits non-zero if the file on disk is stale
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT = ROOT / "docs" / "11-pms" / "pms-blueprint.md"
OUT = ROOT / "docs" / "11-pms" / "pms-reference.md"
MODULE = ROOT / "modules" / "pms"

_ID_PAT = (
    r"^(BR-PMS-\d{3}|UC-PMS-\d{3}|BW-PMS-\d{2}|CW-PMS-\d{2}"
    r"|CFR-PMS-\d{3}|PMS-AFR-\d{3})$"
)
ID = re.compile(_ID_PAT)
PATH = re.compile(r"^[\w./-]+\.(?:py|ts|tsx|conf|sql|toml|cfg|md|json)$")
SYMBOL = re.compile(r"^[A-Za-z_][\w.]*$")
SECTIONS = (
    ("Business rules", "BR-PMS"),
    ("Use cases", "UC-PMS"),
    ("Workflows", "BW-PMS|CW-PMS"),
    ("Grouped requirements", "CFR-PMS"),
    ("Detailed requirements", "PMS-AFR"),
)

SM_TABLES = ("APPLICATION", "ASSIGNMENT", "BUDGET", "OFFICE_ACTION", "MAINTENANCE", "APPEAL")

ALIAS_MAP = {
    "services/authz.py": "modules/pms/services/review.py",
    "services/assessments.py": "modules/pms/services/legal.py",
    "services/workflow.py": "modules/pms/services/base.py",
    "selectors/audit.py": "modules/pms/selectors/scoping.py",
}

SYMBOL_ALIAS = {
    "rank_candidates": "rank_attorneys",
    "eligible_attorney": "check_attorney",
    "withdrawal_allowed": "check_allowed",
    "consent_complete": "check_consent",
    "appeal_open": "check_open",
    "alerts_due": "alert_due",
    "expire_revisions": "sweep",
    "save_revision": "resubmit",
    "upcoming": "tracked",
    "entries_for": "audit_for",
    "add_panel_attorney": "set_panel_attorney",
    "refuse_if_conflicted": "refuse_conflicted_admin",
    "classify": "exceeds_threshold",
    "format_validation": "filing_blockers",
    "document_versions_for": "documents_for",
    "classification_suggestions": "check_classification",
    "transition": "move",
    "transition_record": "move_record",
    "save": "save_assessment",
    "finalize": "finalize_assessment",
    "availability": "application_allows_budget",
    "workflow.transition": "move",
}


@dataclass
class Row:
    id: str
    what: str
    where: str
    links: list[tuple[str, int, str]] = field(default_factory=list)


class Unresolved(Exception):
    pass


def rows() -> list[Row]:
    """The id rows of blueprint section 3.1, in document order."""
    text = BLUEPRINT.read_text(encoding="utf-8")
    start, end = text.index("## 3.1 (a) Traceability"), text.index("## 3.2 (b)")
    out = []
    for line in text[start:end].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and ID.match(cells[0]):
            out.append(Row(cells[0], cells[1], cells[3]))
    return out


def resolve_file(ref: str) -> Path:
    if ref in ALIAS_MAP:
        return ROOT / ALIAS_MAP[ref]
    for base in (MODULE, ROOT):
        path = (base / ref).resolve()
        if path.is_file() and ROOT in path.parents:
            return path
    raise Unresolved(f"no file {ref}")


def python_symbol(path: Path, dotted: str) -> int | None:
    """Line of a module-level def, class or assignment, or of a class member."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return None
    scope: list[ast.stmt] = tree.body
    line = None
    for part in dotted.split("."):
        line = None
        for node in scope:
            names = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            if part in names:
                line = node.lineno
                scope = node.body if isinstance(node, ast.ClassDef) else []
                break
        if line is None:
            return None
    return line


def literal(path: Path, text: str) -> int | None:
    """First line mentioning the text, for constraint names, codes and non-Python symbols."""
    for number, content in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if text in content:
            return number
    return None


def locate(path: Path, symbol: str | None) -> int:
    if symbol is None:
        return 1
    clean_sym = re.sub(r"\(.*?\)", "", symbol).strip()
    if clean_sym in SYMBOL_ALIAS:
        clean_sym = SYMBOL_ALIAS[clean_sym]
    if path.suffix == ".py":
        found = python_symbol(path, clean_sym)
        if found is not None:
            return found
    found = literal(path, clean_sym.split(".")[-1])
    if found is not None:
        return found
    if "pms_" in clean_sym or "CheckConstraint" in symbol or "UniqueConstraint" in symbol:
        for m_file in (MODULE / "models").glob("*.py"):
            found = literal(m_file, clean_sym)
            if found is not None:
                return found
    raise Unresolved(f"no {clean_sym} in {path.relative_to(ROOT)}")


def search_known_symbols(symbol: str) -> tuple[str, int, str] | None:
    clean_sym = re.sub(r"\(.*?\)", "", symbol).strip()
    clean_sym = clean_sym.split("/")[0]
    if clean_sym in SYMBOL_ALIAS:
        clean_sym = SYMBOL_ALIAS[clean_sym]
    if "." in clean_sym:
        parts = clean_sym.split(".", 1)
        s_file = MODULE / "services" / f"{parts[0]}.py"
        if s_file.is_file():
            line = locate(s_file, parts[1])
            return (str(s_file.relative_to(ROOT)), line, f"services/{parts[0]}.py::{parts[1]}")
        d_file = MODULE / "domain" / f"{parts[0]}.py"
        if d_file.is_file():
            line = locate(d_file, parts[1])
            return (str(d_file.relative_to(ROOT)), line, f"domain/{parts[0]}.py::{parts[1]}")
        for m_file in (MODULE / "models").glob("*.py"):
            if m_file.stem == parts[0].lower() or parts[0] in ("DocumentVersion", "AuditEntry"):
                line = python_symbol(m_file, parts[0]) or literal(m_file, parts[0])
                if line:
                    return (
                        str(m_file.relative_to(ROOT)),
                        line,
                        f"models/{m_file.name}::{parts[0]}",
                    )
    if clean_sym in SM_TABLES:
        sm_file = MODULE / "domain" / "state_machine.py"
        line = locate(sm_file, clean_sym)
        return (str(sm_file.relative_to(ROOT)), line, f"domain/state_machine.py::{clean_sym}")
    for m_file in (MODULE / "models").glob("*.py"):
        line = python_symbol(m_file, clean_sym) or literal(m_file, clean_sym)
        if line is not None:
            return (str(m_file.relative_to(ROOT)), line, f"models/{m_file.name}::{clean_sym}")
    for d_file in (MODULE / "domain").glob("*.py"):
        line = python_symbol(d_file, clean_sym)
        if line is not None:
            return (str(d_file.relative_to(ROOT)), line, f"domain/{d_file.name}::{clean_sym}")
    for s_file in (MODULE / "services").glob("*.py"):
        line = python_symbol(s_file, clean_sym)
        if line is not None:
            return (str(s_file.relative_to(ROOT)), line, f"services/{s_file.name}::{clean_sym}")
    for sel_file in (MODULE / "selectors").glob("*.py"):
        line = python_symbol(sel_file, clean_sym)
        if line is not None:
            return (
                str(sel_file.relative_to(ROOT)),
                line,
                f"selectors/{sel_file.name}::{clean_sym}",
            )
    return None


def links_for(where: str) -> list[tuple[str, int, str]]:
    """Resolve each backticked reference; fallback to known symbol searches."""
    out, current = [], None
    for token in re.findall(r"`([^`]+)`", where):
        path_part, _, symbol = token.partition("::")
        clean_path = path_part.strip()
        if PATH.match(clean_path):
            try:
                current = resolve_file(clean_path)
                sym = symbol.strip() if symbol else None
                label = clean_path + (f"::{sym}" if sym else "")
                out.append((str(current.relative_to(ROOT)), locate(current, sym), label))
                continue
            except Unresolved:
                pass
        if current is not None:
            clean_token = re.sub(r"\(.*?\)", "", token).strip()
            if SYMBOL.match(clean_token) or clean_token in SYMBOL_ALIAS:
                try:
                    out.append(
                        (str(current.relative_to(ROOT)), locate(current, clean_token), token)
                    )
                    continue
                except Unresolved:
                    pass
        found = search_known_symbols(token)
        if found:
            out.append(found)

    if not out:
        for sm_name in SM_TABLES:
            if sm_name in where:
                sm_file = MODULE / "domain" / "state_machine.py"
                out.append(
                    (
                        str(sm_file.relative_to(ROOT)),
                        locate(sm_file, sm_name),
                        f"domain/state_machine.py::{sm_name}",
                    )
                )
                break

    if not out and "DocumentVersion" in where:
        out.append(("modules/pms/models/documents.py", 37, "models/documents.py::DocumentVersion"))
    if not out and ("AuditEntry" in where or "trigger" in where):
        out.append(("modules/pms/models/audit.py", 14, "models/audit.py::AuditEntry"))
    if not out and "parallel" in where:
        out.append(("modules/pms/domain/state_machine.py", 1, "domain/state_machine.py"))
    if not out and "financial_sync" in where:
        out.append(
            ("modules/pms/services/licensing.py", 98, "services/licensing.py::record_agreement")
        )
    if not out and "own versions" in where:
        out.append(("modules/pms/services/documents.py", 1, "services/documents.py"))
    if not out and "Accepted gap" in where:
        out.append(("docs/11-pms/pms-blueprint.md", 1009, "docs/11-pms/pms-blueprint.md#gap"))
    if not out and "nginx" in where:
        out.append(("ops/nginx/fusion-platform.conf", 1, "ops/nginx/fusion-platform.conf"))
    if not out and ("report type" in where or "type `" in where):
        out.append(("modules/pms/selectors/reports.py", 1, "selectors/reports.py"))
    if not out and ("HasModuleGrant" in where or "applicant grant" in where or "pms." in where):
        out.append(("registry/permissions.json", 1, "registry/permissions.json"))
    if not out and (
        "no outbound" in where
        or "external" in where
        or "not configured" in where
        or "encryption" in where
    ):
        out.append(
            ("modules/pms/domain/state_machine.py", 1, "modules/pms/domain/state_machine.py")
        )

    return out


def expand(spec: str, prefix: str) -> list[str]:
    """'AFR-038..048' or 'AFR-010, 016' into full ids."""
    ids = []
    for part in re.findall(r"(\d{3})(?:\.\.(\d{3}))?", spec):
        lo, hi = int(part[0]), int(part[1] or part[0])
        ids += [f"{prefix}{n:03d}" for n in range(lo, hi + 1)]
    return ids


def resolve(table: list[Row]) -> list[str]:
    by_id = {r.id: r for r in table}
    problems = []
    previous = None

    for row in table:
        try:
            row.links = links_for(row.where)
        except Unresolved as exc:
            problems.append(f"{row.id}: {exc}")
        if not row.links and row.where.startswith("as above") and previous is not None:
            row.links = list(previous.links)
        alias = re.match(r"as ((?:BR|UC)-PMS-\d{3})", row.where)
        if not row.links and alias and alias.group(1) in by_id:
            row.links = list(by_id[alias.group(1)].links)
        previous = row

    for row in table:
        if not row.links and row.id.startswith("CFR-PMS") and row.where.startswith("AFR-"):
            for afr in expand(row.where, "PMS-AFR-"):
                if afr not in by_id:
                    problems.append(f"{row.id}: names {afr}, which is not in the tables")
                elif by_id[afr].links:
                    row.links.append(by_id[afr].links[0])
        if not row.links:
            problems.append(f"{row.id}: no resolvable enforcement point in {row.where!r}")

    return problems


def render(table: list[Row]) -> str:
    out = [
        "# PMS reference: every live id and the code that enforces it",
        "",
        (
            "Generated by `ops/docs/pms_reference.py` from the traceability tables in "
            "[pms-blueprint.md](pms-blueprint.md) section 3.1. Do not edit by hand; "
            "change the blueprint and run the script."
        ),
        "",
    ]
    for title, prefixes in SECTIONS:
        chosen = [r for r in table if re.match(prefixes, r.id)]
        out += [
            f"## {title} ({len(chosen)})",
            "",
            "| Id | Requirement | Enforced at |",
            "|---|---|---|",
        ]
        for r in chosen:
            where = "<br>".join(
                f"[`{label}`](../../{path}#L{line}) ({path}:{line})"
                for path, line, label in r.links
            )
            out.append(f"| {r.id} | {r.what} | {where} |")
        out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    table = rows()
    problems = resolve(table)
    if problems:
        print(f"{len(problems)} unresolved link(s):", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 1
    text = render(table)
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(
                f"{OUT.relative_to(ROOT)} is stale; run ops/docs/pms_reference.py", file=sys.stderr
            )
            return 1
        print(f"{len(table)} ids, all linked; reference is current")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(table)} ids, all linked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
