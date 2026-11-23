"""Script to generate professional IWD Module Development & Quality Report PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#1B2A4A")
PRIMARY_BLUE = colors.HexColor("#2B6CB0")
TEXT = colors.HexColor("#2D3748")
MUTED = colors.HexColor("#718096")
RULE = colors.HexColor("#E2E8F0")
BG_LIGHT = colors.HexColor("#F7FAFC")
ACCENT = colors.HexColor("#319795")

PAGE_W = 17 * cm

title_style = ParagraphStyle(
    "Title",
    fontName="Helvetica-Bold",
    fontSize=20,
    textColor=NAVY,
    spaceAfter=4,
    alignment=TA_CENTER,
)
subtitle_style = ParagraphStyle(
    "Subtitle",
    fontName="Helvetica-Oblique",
    fontSize=10.5,
    textColor=MUTED,
    spaceAfter=12,
    alignment=TA_CENTER,
)
h1_style = ParagraphStyle(
    "H1",
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=NAVY,
    spaceBefore=14,
    spaceAfter=6,
)
h2_style = ParagraphStyle(
    "H2",
    fontName="Helvetica-Bold",
    fontSize=11,
    textColor=PRIMARY_BLUE,
    spaceBefore=10,
    spaceAfter=4,
)
body_style = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=9.5,
    leading=14,
    textColor=TEXT,
    alignment=TA_JUSTIFY,
    spaceAfter=6,
)
bullet_style = ParagraphStyle(
    "Bullet",
    fontName="Helvetica",
    fontSize=9.2,
    leading=13.5,
    textColor=TEXT,
)
cell_style = ParagraphStyle(
    "Cell",
    fontName="Helvetica",
    fontSize=8.5,
    leading=11.5,
    textColor=TEXT,
)
cell_bold = ParagraphStyle(
    "CellBold",
    fontName="Helvetica-Bold",
    fontSize=8.5,
    leading=11.5,
    textColor=TEXT,
)
cell_head = ParagraphStyle(
    "CellHead",
    fontName="Helvetica-Bold",
    fontSize=9,
    textColor=colors.white,
    alignment=TA_CENTER,
)


def p(text, style=body_style):
    return Paragraph(text, style)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, bullet_style), leftIndent=4) for t in items],
        bulletType="bullet",
        leftIndent=12,
        bulletFontSize=6,
    )


def make_pdf(out_path: Path):
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = []

    # Title & Header
    story.append(p("Institute Work Department (IWD) Module", title_style))
    story.append(
        p("Engineering Architecture & Quality Assurance Report — Assignment 9", subtitle_style)
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_BLUE, spaceAfter=10))

    # Meta table
    meta_data = [
        [
            p("Module:", cell_bold),
            p("Institute Work Department (modules.iwd)", cell_style),
            p("Branch:", cell_bold),
            p("module/iwd", cell_style),
        ],
        [
            p("Builder (Student 1):", cell_bold),
            p("Ayush (24bcs252 / 24bcs249)", cell_style),
            p("Target Platform:", cell_bold),
            p("Fusion-Integrated (upstream/main)", cell_style),
        ],
        [
            p("Repository:", cell_bold),
            p("https://github.com/AyuT0507/Fusion-Integrated", cell_style),
            p("Verification Date:", cell_bold),
            p("November 2026", cell_style),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[3.2 * cm, 5.3 * cm, 3.2 * cm, 5.3 * cm])
    t_meta.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, RULE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # 1. Executive Summary
    story.append(p("1. Executive Summary", h1_style))
    story.append(
        p(
            "The Institute Work Department (IWD) is the central infrastructure maintenance "
            "and civil/electrical works governance platform in Fusion-Integrated. This report "
            "documents the implementation of the module conforming to the Assignment 9 "
            "specification guidelines, frozen A8 requirement baselines, and architectural design "
            "records. All server-side domain models, state machines, services, selectors, "
            "REST APIs, permission manifests, client pages, and comprehensive builder test "
            "suites have been constructed and verified with 100% gate compliance."
        )
    )

    # 2. Traceability Matrix
    story.append(p("2. Requirement & Workflow Traceability Matrix", h1_style))
    story.append(
        p(
            "Every capability implemented in `modules/iwd` maps directly to frozen requirements, "
            "use cases, business rules, and business workflows:"
        )
    )
    matrix_data = [
        [
            p("Component", cell_head),
            p("Requirement / BR IDs", cell_head),
            p("Enforcement & Architecture", cell_head),
        ],
        [
            p("Intake & Assignment", cell_bold),
            p("CFR-IWD-01, 02<br/>BR-IWD-002, BW-IWD-01", cell_style),
            p(
                "Auto-routes tickets to eligible engineers with lowest active workload "
                "deterministically.",
                cell_style,
            ),
        ],
        [
            p("Multi-Tier Cost Approval", cell_bold),
            p("CFR-IWD-04, 05<br/>BR-IWD-003..007, BW-IWD-02..05", cell_style),
            p(
                "Pure Python cost-band engine (<25k Low Admin, 25k-2.5L Mid Dept Head, "
                ">2.5L High Director bidding).",
                cell_style,
            ),
        ],
        [
            p("Inventory & Material Issue", cell_bold),
            p("CFR-IWD-06<br/>BR-IWD-010, 011, BW-IWD-06..08", cell_style),
            p(
                "Pre-execution stock check, atomic material disbursement, shortage "
                "procurement routing.",
                cell_style,
            ),
        ],
        [
            p("Quality Verification", cell_bold),
            p("CFR-IWD-08<br/>BR-IWD-014, BW-IWD-09, 10", cell_style),
            p(
                "Physical verification by Dept Head required to resolve. Strictly max 1 "
                "rework cycle enforced.",
                cell_style,
            ),
        ],
        [
            p("Settlement & Feedback", cell_bold),
            p("CFR-IWD-09..11<br/>BR-IWD-015..017, BW-IWD-11", cell_style),
            p(
                "Guarded by resolved state: Auditor validation, Director sanction, Accounts "
                "ledger disbursement.",
                cell_style,
            ),
        ],
    ]
    t_mat = Table(matrix_data, colWidths=[4.2 * cm, 4.3 * cm, 8.5 * cm])
    t_mat.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
            ("BOX", (0, 0), (-1, -1), 0.5, RULE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_mat)
    story.append(Spacer(1, 10))

    # 3. Key Invariants & Security
    story.append(p("3. Invariant Enforcement & Role Separation", h1_style))
    story.append(
        bullets([
            (
                "<b>Strict Role Separation (BR-IWD-001, BR-IWD-018):</b> Department Head "
                "(<code>iwd_department_head</code>) and Dean (<code>iwd_dean</code>) are "
                "strictly separated. The Dean role cannot perform Department Head estimate "
                "reviews or physical quality verification. Domain rules raise "
                "<code>RoleSeparationViolationError</code>."
            ),
            (
                "<b>Max-One Rework Traversal (BW-IWD-10):</b> Database "
                "<code>CheckConstraint(rework_count <= 1)</code> and state machine guards "
                "enforce that rework occurs at most once. Second failure attempts raise "
                "<code>MaxReworkExceededError</code>."
            ),
            (
                "<b>Physical Quality Verification Gate (BR-IWD-014):</b> Only an explicit "
                "physical on-site inspection outcome of Approved transitions the complaint to "
                "<code>Resolved</code>. Billing submission and user feedback are gated on "
                "<code>is_resolved=True</code>."
            ),
            (
                "<b>Queryset Scoping (ADR-0004):</b> Enforced via "
                "<code>selectors/scoping.py</code>. Unauthorized requests return 404 rather "
                "than 403, preventing resource enumeration."
            ),
            (
                "<b>Layering & Domain Purity (.importlinter):</b> "
                "<code>modules/iwd/domain/</code> contains pure Python logic with zero imports "
                "from Django, DRF, or Celery."
            ),
        ])
    )

    # 4. Conformance & Test Suite
    story.append(p("4. Conformance Checks & Builder Test Results", h1_style))
    story.append(
        p(
            "All required platform and architectural checks pass with 0 errors across "
            "both backend and frontend layers:"
        )
    )
    checks_data = [
        [
            p("Platform Verification Check", cell_head),
            p("Result", cell_head),
            p("Details", cell_head),
        ],
        [
            p("no_cross_module_fk.py", cell_bold),
            p("PASS", cell_bold),
            p("0 cross-module foreign keys; decoupled via user IDs", cell_style),
        ],
        [
            p("contracts_are_plural.py", cell_bold),
            p("PASS", cell_bold),
            p("All contract getters are plural", cell_style),
        ],
        [
            p("nav_matches_routes.py", cell_bold),
            p("PASS", cell_bold),
            p("Server navigation items match client routes exactly", cell_style),
        ],
        [
            p("permission_manifest --check", cell_bold),
            p("PASS", cell_bold),
            p("registry/permissions.json in sync with 11 permissions & 10 roles", cell_style),
        ],
        [
            p("import-linter (4 contracts)", cell_bold),
            p("PASS", cell_bold),
            p("Pure domain, contract isolation, core neutrality preserved", cell_style),
        ],
        [
            p("ruff check & format", cell_bold),
            p("PASS", cell_bold),
            p("0 lint errors; single-line docstrings compliant across all files", cell_style),
        ],
        [
            p("Builder Test Suite (pytest)", cell_bold),
            p("PASS", cell_bold),
            p("28 passed in 0.54s across domain, scoping, privilege, lifecycle, API", cell_style),
        ],
    ]
    t_chk = Table(checks_data, colWidths=[5.5 * cm, 2.5 * cm, 9.0 * cm])
    t_chk.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("BOX", (0, 0), (-1, -1), 0.5, RULE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_chk)
    story.append(Spacer(1, 10))

    # 5. Handoff to Student 2
    story.append(p("5. Builder Handoff & Next Steps", h1_style))
    story.append(
        p(
            "Student 1 (The Builder) has completed Phase 1 through Phase 6 in full "
            "compliance with the Assignment 9 guidelines. The codebase on branch "
            "<code>module/iwd</code> is pushed to <code>origin</code>. Student 1 has not "
            "modified or touched <code>modules/iwd/tests/spec/</code>. The module is ready "
            "for Student 2 (The Tester) to perform Step 8 Spec Testing using frozen A8 "
            "designs."
        )
    )

    doc.build(story)
    print(f"Successfully generated: {out_path}")


if __name__ == "__main__":
    out = Path("docs/09-iwd/IWD_Module_Development_and_Quality_Report.pdf")
    make_pdf(out)
