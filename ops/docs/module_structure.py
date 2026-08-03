#!/usr/bin/env python
"""Generate the module-structure reference PDF from the real tree.

Placement is the worked example every other module copies, so this walks the
actual files rather than reproducing them by hand — a drawn tree goes stale the
first time someone adds a service, and a junior then follows a map that is
wrong.

Files without an annotation are reported on stderr rather than marked in the
document — a reference a junior follows should not be covered in gaps, but the
maintainer still needs to see them.

    python ops/docs/module_structure.py            writes docs/module-structure.pdf
    python ops/docs/module_structure.py --html     writes the HTML only
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_PDF = ROOT / "docs" / "module-structure.pdf"
OUT_HTML = ROOT / "docs" / "module-structure.html"

BACKEND = ROOT / "modules" / "placement"
FRONTEND = ROOT / "client" / "src" / "modules" / "placement"

SKIP_DIRS = {"__pycache__", "node_modules"}

#: Listed as a count rather than file by file — they are numbered, sequential
#: and carry no lesson individually.
COLLAPSE = {"migrations"}

#: One line per path, relative to the module root. Directories get an entry too.
BACKEND_NOTES = {
    "domain": "PURE PYTHON. No Django import — CI fails the build on one.",
    "domain/offer_policy.py": "The signed policy as rules. Testable in milliseconds.",
    "domain/state_machine.py":
        "Legal transitions as a table; an illegal one cannot be expressed.",
    "domain/eligibility.py": "The rule AST, evaluated fail-closed.",
    "domain/conduct.py": "The debarment ladder (rules 18/19/21).",
    "domain/registration.py": "Who may register, and on what terms.",
    "domain/clearance.py": "Rules 22 and 24: the no-dues gate and non-joining.",
    "domain/profile_completeness.py": "Weights and the named list of what is missing.",

    "models.py":
        "Django ORM only. No business logic, no cross-module ForeignKey.",
    "migrations": "One per schema change. Never edited after it ships.",

    "selectors": "ALL reads. Every queryset a view uses is built here.",
    "selectors/scoping.py":
        "Who may see what. Narrowing means a foreign row is 404, not 403.",
    "selectors/applications.py": "Read helpers for the application list.",
    "management/commands/send_notifications.py": "Drain or inspect the outbox by hand.",

    "services": "ALL writes. Transaction boundaries live here.",
    "services/authz.py":
        "Write authority. `scope` proves a row is readable, not writable.",
    "services/offers.py": "Accept/issue, with the per-student mutex.",
    "services/applications.py": "The only caller of the state machine.",
    "services/notifications.py": "Outbox writes and the drain.",
    "services/conduct.py": "Records incidents; imposing a sanction is a separate act.",
    "services/registration.py": "Rules 1, 20, 21.",
    "services/announcements.py": "Publish and withdraw; history is kept.",
    "services/companies.py": "Registration and the PC-BR-007 approval gate.",
    "services/documents.py": "Attach, replace, remove a document link.",
    "services/facts.py": "Assembles eligibility facts in a fixed query count.",
    "services/interviews.py": "Rounds, candidates and outcomes.",
    "services/postings.py": "Create, update, publish. Criteria freeze on publish.",
    "services/profiles.py": "Profile and derived completeness.",
    "services/recruiters.py": "Invitation, acceptance, sign-in.",
    "services/stats.py": "Snapshots, with small-cell suppression.",
    "services/clearance.py":
        "Rule 24's no-dues lever, exposed to other modules via contracts.py.",

    "api": "THIN. Parse, scope, delegate, serialise. No business logic.",
    "api/views.py": "Endpoints. Each takes its queryset from selectors/.",
    "api/serializers.py": "Explicit allow-lists. `fields = \"__all__\"` is never used.",
    "api/permissions.py": "Module-specific permission classes.",
    "api/urls.py": "Mounted by config/urls.py under /api/v1/<module>/.",
    "api/exports.py": "CSV. Escaping lives in core.api.csv so no export forgets it.",
    "api/academics.py":
        "The CPI directory. Staff only — the largest disclosure here.",
    "api/conduct.py":
        "Recording an incident and imposing a sanction are separate.",
    "api/documents.py": "Attach a Drive link; reaching one re-checks scope.",
    "api/registration.py": "Self-service registration; fee routes are staff-only.",
    "api/clearance.py":
        "A student sees only their own clearance — no user parameter exists.",
    "api/audit.py":
        "The trail. Staff see reasons and actors; a student sees the timeline.",

    "contracts.py": "THE ONLY module-to-module entry point. Plural by signature.",
    "registry.py": "Module code, nav items and permission catalogue.",
    "tasks.py": "Celery. Ids in arguments, never ORM objects.",
    "schedule.py": "This module's beat entries, merged by config/celery.py.",
    "apps.py": "AppConfig. Registers this module's system checks.",
    "authentication.py": "Only if the module owns a credential pool. Most do not.",

    "tests": "domain/ 90%, services 85%, api 80%.",
    "tests/test_domain.py": "Pure, no database, milliseconds.",
    "tests/test_privilege_escalation.py": "Read scope is not write authority.",
    "management": "Operational commands, not business logic.",
}

FRONTEND_NOTES = {
    "api": "The server contract, in one place.",
    "api/types.ts": "Wire types. Money and CPI stay STRINGS — Decimal, not float.",
    "api/hooks.ts": "TanStack Query. Every mutation invalidates what it can affect.",

    "pages": "One route each. Lazy-loaded, one chunk per page.",
    "components": "Reused within this module only. Anything shared goes to ui/.",
    "components/CpiBadge.tsx":
        "A CPI never renders without its semester. null is not 0.00.",
    "components/EligibilityPanel.tsx": "Why a student may or may not apply, per rule.",
    "components/DocumentsCard.tsx": "Drive links. The raw URL never reaches the list.",
    "components/NewPostingModal.tsx":
        "The eligibility rule from named controls, not raw JSON.",
    "components/IssueOfferModal.tsx": "Issue an offer; the deadline is mandatory.",
    "components/PlacementRecordCard.tsx":
        "The rule 24 hold and the way to release it, side by side.",
    "components/HistoryDrawer.tsx":
        "An application's timeline. Says when reasons were withheld.",
    "routes.tsx": "Relative paths. Must match registry.py — CI compares them.",
}

#: Shared scaffolding a module depends on but must not modify casually.
SHARED = [
    ("core/api/exceptions.py", "The one error envelope. Views never build errors by hand."),
    ("core/api/csv.py", "Formula-injection-safe CSV for every module."),
    ("core/api/throttling.py", "Principal-aware throttle."),
    ("core/api/csrf.py", "CSRF for cookie-borne credentials."),
    ("core/files/", "Upload/download plumbing."),
    ("fusion_auth/", "Identity. Modules read `request.principal`, never a user table."),
    ("client/src/ui/", "Design system. FormModal, FormSection, DataTable, PageHeader."),
    ("client/src/app/registry.ts", "Frontend module manifest. `code` must match the server."),
]

RULES = [
    ("A module may import another ONLY via <code>modules.&lt;other&gt;.contracts</code>",
     "import-linter, 4 contracts"),
    ("No ForeignKey may cross a module boundary — use a plain integer id",
     "ops/checks/no_cross_module_fk.py"),
    (("<code>contracts.py</code> getters are plural: "
      "<code>get_users(ids)</code>, never <code>get_user(id)</code>"),
     "ops/checks/contracts_are_plural.py"),
    ("<code>domain/</code> must not import Django",
     "import-linter"),
    ("Every server nav item needs a client route, and vice versa",
     "ops/checks/nav_matches_routes.py"),
    ("The committed OpenAPI schema must match the code",
     "make schema-check"),
]

CHECKLIST = [
    "Scaffold the directories below and add the app to <code>DOMAIN_MODULES</code>.",
    "Write <code>registry.py</code>: module code, nav items, permission catalogue.",
    "Model the domain in <code>domain/</code> first, in pure Python, with tests.",
    "Add <code>models.py</code> and its migration. No cross-module FK.",
    ("Write selectors (reads) and services (writes). Services call"
     " <code>authz.require</code>."),
    "Add the thin <code>api/</code> layer and mount it in <code>config/urls.py</code>.",
    "Expose <code>contracts.py</code> — plural getters only.",
    "Add the frontend manifest entry, routes and pages.",
    "Run <code>make check</code>. It must be green before review.",
]


@dataclass
class Node:
    name: str
    is_dir: bool
    note: str = ""
    children: list[Node] = field(default_factory=list)


def build(root: Path, notes: dict[str, str], rel: Path | None = None) -> list[Node]:
    """The real tree, annotated. Directories first, then files, both sorted."""
    base = root if rel is None else root / rel
    nodes: list[Node] = []
    for entry in sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name)):
        if entry.name in SKIP_DIRS or entry.name == "__init__.py":
            continue
        key = str((rel / entry.name) if rel else Path(entry.name))
        note = notes.get(key, "") or _derive(entry.name)
        if entry.is_dir():
            children = [] if entry.name in COLLAPSE else build(root, notes,
                                                               Path(key))
            if entry.name in COLLAPSE:
                count = len(list(entry.glob("0*.py")))
                note = f"{note} {count} so far."
            nodes.append(Node(entry.name + "/", True, note, children))
        else:
            nodes.append(Node(entry.name, False, note))
    return nodes


def _routes_by_page() -> dict[str, str]:
    """Component name -> the URL it serves, read from routes.tsx.

    More useful to a newcomer than any sentence about the page: it answers
    "which screen is this?" directly.
    """
    src = (FRONTEND / "routes.tsx").read_text()
    lazy = dict(re.findall(r"const (\w+) = lazy\(\s*\n?\s*\(\) =>"
                           r' import\("\./pages/(\w+)"\)', src))
    paths = dict(re.findall(r'path: "([^"]+)", element: <(\w+) ?/>', src))
    by_component = {comp: path for path, comp in paths.items()}
    return {f"{file}.tsx": f"Route: /placement/{by_component[comp]}"
            for comp, file in lazy.items() if comp in by_component}


PAGE_ROUTES = _routes_by_page()


def _derive(name: str) -> str:
    """A note for files whose name already says it."""
    if name.startswith("test_"):
        subject = name[5:].removesuffix(".py").replace("_", " ")
        return f"Tests: {subject}."
    return PAGE_ROUTES.get(name, "")


def render_tree(nodes: list[Node], prefix: str = "") -> list[str]:
    """Box-drawing tree with the annotation column aligned."""
    lines = []
    for i, node in enumerate(nodes):
        last = i == len(nodes) - 1
        branch = "└── " if last else "├── "
        label = prefix + branch + node.name
        lines.append((label, node.note, node.is_dir))
        if node.children:
            lines += render_tree(node.children, prefix + ("    " if last else "│   "))
    return lines


def tree_html(nodes: list[Node], gaps: list[str]) -> str:
    rows = []
    for label, note, is_dir in render_tree(nodes):
        if not note and not is_dir:
            gaps.append(label.strip(" │├└─"))
        cls = "dir" if is_dir else "file"
        rows.append(
            f'<div class="row"><span class="{cls}">{html.escape(label)}</span>'
            f'<span class="note">{note}</span></div>')
    return "\n".join(rows)


def page(title: str, body: str) -> str:
    return f'<section class="page"><h2>{title}</h2>{body}</section>'


def build_html(gaps: list[str]) -> str:
    backend = tree_html(build(BACKEND, BACKEND_NOTES), gaps)
    frontend = tree_html(build(FRONTEND, FRONTEND_NOTES), gaps)

    shared = "".join(
        f'<div class="row"><span class="file">{html.escape(p)}</span>'
        f'<span class="note">{n}</span></div>' for p, n in SHARED)
    rules = "".join(
        f"<tr><td>{r}</td><td class='mono'>{how}</td></tr>" for r, how in RULES)
    checklist = "".join(f"<li>{c}</li>" for c in CHECKLIST)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Module Structure</title>
<style>
  @page {{ size: A4; margin: 14mm 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font: 10pt/1.45 -apple-system, "Segoe UI", Roboto, sans-serif;
         color: #14202e; margin: 0; }}
  h1 {{ font-size: 19pt; margin: 0 0 2mm; }}
  h2 {{ font-size: 13pt; margin: 0 0 4mm; padding-bottom: 2mm;
        border-bottom: 2px solid #0b1220; }}
  .lede {{ color: #5a6a7a; margin: 0 0 7mm; font-size: 9.5pt; }}
  .page {{ page-break-after: always; }}
  .page:last-child {{ page-break-after: auto; }}
  .row {{ display: flex; gap: 5mm; font-size: 7.6pt; line-height: 1.44; }}
  .row span:first-child {{ flex: 0 0 70mm; font-family: ui-monospace,
        SFMono-Regular, Menlo, monospace; white-space: pre; }}
  .dir {{ color: #0b4f8a; font-weight: 600; }}
  .file {{ color: #14202e; }}
  .note {{ color: #5a6a7a; flex: 1; }}
  .undoc {{ color: #c92a2a; font-style: italic; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
  td, th {{ text-align: left; padding: 2mm 3mm; border-bottom: 1px solid #e4e9ee;
            vertical-align: top; }}
  th {{ background: #f6f8fa; font-size: 8pt; text-transform: uppercase;
        letter-spacing: .04em; color: #5a6a7a; }}
  .mono, code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 8.2pt; }}
  code {{ background: #f2f5f8; padding: 0 1mm; border-radius: 2px; }}
  ol {{ padding-left: 6mm; }} ol li {{ margin-bottom: 1.6mm; }}
  .box {{ background: #f6f8fa; border-left: 3px solid #15abff;
          padding: 3mm 4mm; margin: 5mm 0; font-size: 9pt; }}
  .layers {{ font-size: 9pt; }}
  .layers b {{ display: inline-block; width: 26mm; }}
  .gen {{ margin-top: 7mm; font-size: 8pt; color: #5a6a7a; }}
</style></head><body>

<section class="page">
  <h1>Fusion&#8209;Integrated · Module Structure</h1>
  <p class="lede">Placement Cell as the reference. Every other module keeps this
  shape — the boundaries below are enforced by CI, not by convention.</p>

  <h2>The five layers</h2>
  <div class="layers">
    <p><b>domain/</b> Pure Python. Entities and rules. No Django, so it tests in
       milliseconds with no database.</p>
    <p><b>models.py</b> ORM only. No business logic. No ForeignKey leaving the
       module.</p>
    <p><b>selectors/</b> All reads. Authorisation happens here by narrowing the
       queryset, which is why an out-of-scope row is a 404 and not a 403.</p>
    <p><b>services/</b> All writes. Transaction boundaries. Emits notifications
       and events.</p>
    <p><b>api/</b> Thin: parse, scope, delegate, serialise.</p>
  </div>

  <div class="box"><b>Why the split matters.</b> Read scope and write authority
  are different questions. A student can legitimately <i>see</i> every published
  posting, so passing that queryset into a service proves only that the row is
  reachable — never that the caller may change it. Services therefore call
  <code>authz.require(actor, &lt;permission&gt;)</code> as well.</div>

  <h2>Contracts CI enforces</h2>
  <table><tr><th>Rule</th><th>Checked by</th></tr>{rules}</table>
  <p class="gen">Generated from the real tree by
  <code>make module-structure</code>. Regenerate it rather than editing the
  PDF — a hand-kept copy is wrong the first time someone adds a service.</p>
</section>

{page("Backend — modules/placement/", backend)}
{page("Frontend — client/src/modules/placement/", frontend)}

<section class="page">
  <h2>Shared scaffolding — use, do not fork</h2>
  {shared}

  <h2 style="margin-top:8mm">Adding a module</h2>
  <ol>{checklist}</ol>

  <div class="box">A module granted to nobody is invisible and unroutable in
  production, so shipping half of one is safe. Grant it when it is ready.</div>
</section>

</body></html>"""


def find_chrome() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    return next((c for c in candidates if Path(c).exists()),
                shutil.which("chromium") or shutil.which("google-chrome"))


def main() -> int:
    gaps: list[str] = []
    OUT_HTML.write_text(build_html(gaps))
    if gaps:
        print(f"note: {len(gaps)} file(s) have no annotation: "
              f"{', '.join(gaps)}", file=sys.stderr)
    print(f"wrote {OUT_HTML.relative_to(ROOT)}")
    if "--html" in sys.argv:
        return 0

    chrome = find_chrome()
    if chrome is None:
        print("No Chrome/Chromium found; open the HTML and print to PDF.",
              file=sys.stderr)
        return 1

    # Fixed argv built from an allowlisted browser path; nothing here is
    # user input.
    subprocess.run(  # noqa: S603
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()],
        check=True, capture_output=True)
    OUT_HTML.unlink()
    size = OUT_PDF.stat().st_size // 1024
    print(f"wrote {OUT_PDF.relative_to(ROOT)} ({size} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
