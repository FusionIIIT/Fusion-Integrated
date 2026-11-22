import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PDF_PATH = "Phase_2_ELM_Improvement_Report.pdf"

NAVY = colors.HexColor("#1A365D")
BLUE = colors.HexColor("#2B6CB0")
DARK = colors.HexColor("#2D3748")
LIGHT_BG = colors.HexColor("#EDF2F7")
LINE_COLOR = colors.HexColor("#CBD5E0")
GREEN = colors.HexColor("#276749")
WHITE = colors.white

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=NAVY,
    spaceAfter=4,
)

subtitle_style = ParagraphStyle(
    "DocSubtitle",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10.5,
    leading=14,
    textColor=BLUE,
    spaceAfter=12,
)

h1_style = ParagraphStyle(
    "Heading1",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=12.5,
    leading=16,
    textColor=NAVY,
    spaceBefore=12,
    spaceAfter=6,
    keepWithNext=True,
)

h2_style = ParagraphStyle(
    "Heading2",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=14,
    textColor=BLUE,
    spaceBefore=8,
    spaceAfter=4,
    keepWithNext=True,
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12.5,
    textColor=DARK,
    spaceAfter=6,
)

bullet_style = ParagraphStyle(
    "Bullet",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8.8,
    leading=12,
    textColor=DARK,
    leftIndent=12,
    spaceAfter=3,
)

code_style = ParagraphStyle(
    "CodeText",
    parent=styles["Normal"],
    fontName="Courier",
    fontSize=8,
    leading=10.5,
    textColor=NAVY,
)

table_header_style = ParagraphStyle(
    "TableHeader",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=8.5,
    leading=11,
    textColor=WHITE,
    alignment=1,
)

table_cell_style = ParagraphStyle(
    "TableCell",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8,
    leading=10.5,
    textColor=DARK,
)

table_cell_bold = ParagraphStyle(
    "TableCellBold",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10.5,
    textColor=DARK,
)


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    story = []

    # Title & Subtitle
    story.append(Paragraph("Fusion ERP Lab Assignment (6B) — Phase 2 Report", title_style))
    story.append(
        Paragraph(
            "Review, Testing, and Hardening of the AI-Generated Employee Leave Management (ELM) Module",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=10))

    # Metadata Card Table
    meta_data = [
        [
            Paragraph("<b>Target System:</b> Fusion ERP (Base Code)", table_cell_style),
            Paragraph("<b>Module:</b> Employee Leave Management (ELM)", table_cell_style),
        ],
        [
            Paragraph("<b>Pull Request:</b> #171 (FusionIIIT/Fusion-Integrated)", table_cell_style),
            Paragraph("<b>Branch:</b> elm-submission-vishnu-20261012", table_cell_style),
        ],
        [
            Paragraph("<b>Author / ID:</b> Vishnu Vardhan (24bcs055)", table_cell_style),
            Paragraph("<b>Selected LLM:</b> Qwen/Qwen2.5-Coder-14B-Instruct", table_cell_style),
        ],
        [
            Paragraph("<b>Phase-1 Preserved Commit:</b> <font name='Courier'>f759468</font>", table_cell_style),
            Paragraph("<b>Phase-2 Final Commit:</b> <font name='Courier'>04e91e6</font>", table_cell_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[9 * cm, 9 * cm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, LINE_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(
        Paragraph(
            "During Phase 1, an initial version of the Employee Leave Management (ELM) module was generated "
            "and submitted under PR #171. In Phase 2, this implementation was systematically preserved, reviewed, "
            "tested, and re-engineered to resolve critical authorization flaws, timezone bugs, and missing operational "
            "components. The final module successfully satisfies all Fusion architectural constraints, eliminates self-approval "
            "vulnerabilities, implements in-app role-scoped task notifications, wires Celery beat periodic SLA schedules, "
            "and establishes a 100% passing automated verification suite across both backend (pytest) and frontend (vitest).",
            body_style,
        )
    )

    # Phase-1 Preservation
    story.append(Paragraph("2. Phase-1 Preservation Strategy", h1_style))
    story.append(
        Paragraph(
            "In strict adherence to assignment guidelines, the baseline Phase-1 code was permanently preserved prior "
            "to executing any modifications. Commit <b>f759468</b> was tagged as <b>phase-1-preserved</b> and pushed to a dedicated "
            "branch <b>phase-1-original</b> on GitHub. Phase-2 changes were then committed progressively on top, maintaining a full "
            "audit trail comparing the initial AI output against the final human-AI engineered module.",
            body_style,
        )
    )

    # Problems Discovered
    story.append(Paragraph("3. Defect Analysis: Problems Identified in Phase-1 Code", h1_style))
    story.append(
        Paragraph(
            "Through manual inspection, negative boundary testing, and specification audits against BR-EL-001..038, "
            "nine material defects were identified in the Phase-1 codebase:",
            body_style,
        )
    )

    problems = [
        "<b>Self-Approval Vulnerability:</b> In <font name='Courier'>services.py::act()</font>, Unit Heads (HODs) could review and approve their own leave applications due to an omitted <font name='Courier'>actor.user_id != request.employee_id</font> restriction.",
        "<b>Department Scope Leakage:</b> Approval queries (<font name='Courier'>visible_requests()</font>) failed to filter by the Unit Head's academic department, allowing reviewers to sanction applications belonging to external departments.",
        "<b>Timezone Date Shift Bug:</b> Frontend DateInputs in <font name='Courier'>MyLeavePage.tsx</font> used <font name='Courier'>.toISOString().slice(0, 10)</font>. In UTC+ offsets (e.g. IST +05:30), dates selected at midnight shifted backwards by 1 full day.",
        "<b>Unconstrained Restricted Holidays (RH):</b> The service permitted multi-day Restricted Holiday requests, violating institutional policy restricting RH to a single calendar day.",
        "<b>Permissive Duty Resumption Scope:</b> Duty resumption reviews were accepted for categories outside the authorized ELM scope (such as Casual Leave), rather than restricting resumption to EL, COL, and VL.",
        "<b>Year-End Ledger Invariant Risks:</b> Year-end processing allowed execution while active leave requests remained unresolved, and rollover arithmetic could calculate negative lapsed days.",
        "<b>Opening Balance Reduction Below Consumed:</b> Administrative balance entries allowed setting opening balances below already consumed leave days.",
        "<b>Absence of In-App Task Notifications:</b> Approvers and employees received no in-app notifications upon task assignment, reminder, or status transition.",
        "<b>Missing Scheduled Work (Celery Beat):</b> SLA reminder and escalation scanning lacked Celery beat periodic automation and runbook documentation.",
    ]
    for p in problems:
        story.append(Paragraph(f"• {p}", bullet_style))

    story.append(Spacer(1, 6))

    # Improvements Implemented
    story.append(Paragraph("4. Phase-2 Engineering Interventions & Improvements", h1_style))
    story.append(
        Paragraph(
            "To resolve these defects, systematic improvements were implemented across both backend and frontend layers:",
            body_style,
        )
    )

    improvements = [
        "<b>Self-Review & Department Guards:</b> Added explicit authorization checks raising <font name='Courier'>PermissionDeniedError('self_review_not_allowed')</font> and scoped Unit Head review queries strictly by employee department via <font name='Courier'>directory.get_users</font>.",
        "<b>Local Date Serialization:</b> Implemented <font name='Courier'>formatLocalDate()</font> in <font name='Courier'>client/.../utils/dates.ts</font> using local date components, validated by dedicated unit tests in <font name='Courier'>dates.test.ts</font>.",
        "<b>Business Rule Enforcement:</b> Added validation checks enforcing single-day RH requests (<font name='Courier'>start_date == end_date</font>) and restricting duty resumption actions to <font name='Courier'>{'EL', 'COL', 'VL'}</font>.",
        "<b>Balance Ledger & Year-End Protection:</b> Guarded year-end runs against unresolved pending requests (<font name='Courier'>pending_leave_workflows</font>) and clamped lapsed days via <font name='Courier'>max(..., Decimal('0'))</font>.",
        "<b>In-App Notification Subsystem:</b> Introduced <font name='Courier'>LeaveTaskNotice</font> model with migrations 0004 & 0005, REST endpoints, and interactive Mantine alert banners with 'Mark read' controls.",
        "<b>Celery Beat Automation:</b> Configured periodic Celery beat runner (every 15 min) in <font name='Courier'>modules/employee_leave/schedule.py</font> and documented operations in <font name='Courier'>enable-scheduled-work.md</font>.",
        "<b>Automated Test Suite & Offline Runner:</b> Authored 11 service and API integration tests in <font name='Courier'>test_services.py</font> and <font name='Courier'>test_api.py</font>, and enabled an in-memory SQLite runner in <font name='Courier'>test.py</font>.",
    ]
    for imp in improvements:
        story.append(Paragraph(f"• {imp}", bullet_style))

    story.append(Spacer(1, 6))

    # Verification Results Table
    story.append(Paragraph("5. Verification and Quality Assurance Results", h1_style))
    story.append(
        Paragraph(
            "The final Phase-2 implementation was validated against all Fusion Base CI gates, architectural linters, "
            "and unit/integration test suites:",
            body_style,
        )
    )

    verif_data = [
        [
            Paragraph("Verification Gate", table_header_style),
            Paragraph("Tool / Command", table_header_style),
            Paragraph("Outcome", table_header_style),
            Paragraph("Status", table_header_style),
        ],
        [
            Paragraph("Python Code Quality", table_cell_bold),
            Paragraph("ruff check .", code_style),
            Paragraph("Zero errors, zero warnings", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Module Boundaries", table_cell_bold),
            Paragraph("lint-imports", code_style),
            Paragraph("4/4 architectural contracts kept", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Foreign Key Isolation", table_cell_bold),
            Paragraph("no_cross_module_fk.py", code_style),
            Paragraph("Zero cross-module FKs", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("API Plural Signatures", table_cell_bold),
            Paragraph("contracts_are_plural.py", code_style),
            Paragraph("All getters conform to plural standard", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Navigation Parity", table_cell_bold),
            Paragraph("nav_matches_routes.py", code_style),
            Paragraph("Sidebar and client routes match", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Migration State", table_cell_bold),
            Paragraph("makemigrations --check", code_style),
            Paragraph("No unapplied model changes", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("OpenAPI Schema Parity", table_cell_bold),
            Paragraph("spectacular --fail-on-warn", code_style),
            Paragraph("Committed schema matches code byte-for-byte", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Frontend Type Safety", table_cell_bold),
            Paragraph("npx tsc --noEmit", code_style),
            Paragraph("Zero TypeScript compiler errors", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Client Test Suite", table_cell_bold),
            Paragraph("npm test (vitest)", code_style),
            Paragraph("5 test suites, 36/36 tests passed", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
        [
            Paragraph("Backend Test Suite", table_cell_bold),
            Paragraph("pytest modules/employee_leave", code_style),
            Paragraph("17/17 tests passed (100%)", table_cell_style),
            Paragraph("<font color='#276749'><b>PASSED</b></font>", table_cell_style),
        ],
    ]
    verif_table = Table(verif_data, colWidths=[4.2 * cm, 4.8 * cm, 6.2 * cm, 2.8 * cm])
    verif_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BOX", (0, 0), (-1, -1), 1, LINE_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(verif_table)
    story.append(Spacer(1, 10))

    # Phase-1 vs Phase-2 Comparison Matrix
    story.append(Paragraph("6. Phase-1 vs Phase-2 Comparison Matrix", h1_style))
    comp_data = [
        [
            Paragraph("Criterion", table_header_style),
            Paragraph("Phase-1 (Initial AI Output)", table_header_style),
            Paragraph("Phase-2 (Hardened Final Version)", table_header_style),
        ],
        [
            Paragraph("Self-Approval Protection", table_cell_bold),
            Paragraph("<font color='#C53030'>Vulnerable</font> (Unit Heads could self-approve)", table_cell_style),
            Paragraph("<font color='#276749'>Guarded</font> (Raises 403 PermissionDeniedError)", table_cell_style),
        ],
        [
            Paragraph("Department Scope Isolation", table_cell_bold),
            Paragraph("<font color='#C53030'>Leaked</font> (All department requests visible)", table_cell_style),
            Paragraph("<font color='#276749'>Isolated</font> (Filtered strictly by reviewer department)", table_cell_style),
        ],
        [
            Paragraph("Date Picker Timezone Handling", table_cell_bold),
            Paragraph("<font color='#C53030'>Buggy</font> (-1 day shift on local UTC+ midnight)", table_cell_style),
            Paragraph("<font color='#276749'>Correct</font> (formatLocalDate preserves exact date)", table_cell_style),
        ],
        [
            Paragraph("Restricted Holiday Constraints", table_cell_bold),
            Paragraph("<font color='#C53030'>Unchecked</font> (Allowed multi-day bookings)", table_cell_style),
            Paragraph("<font color='#276749'>Enforced</font> (Strict single-day validation)", table_cell_style),
        ],
        [
            Paragraph("In-App Task Notifications", table_cell_bold),
            Paragraph("<font color='#C53030'>None</font> (No notification mechanism)", table_cell_style),
            Paragraph("<font color='#276749'>Integrated</font> (LeaveTaskNotice model + UI alerts)", table_cell_style),
        ],
        [
            Paragraph("SLA Scheduled Automation", table_cell_bold),
            Paragraph("<font color='#C53030'>None</font> (No background beat execution)", table_cell_style),
            Paragraph("<font color='#276749'>Configured</font> (Celery beat schedule + ops runbook)", table_cell_style),
        ],
        [
            Paragraph("Automated Test Coverage", table_cell_bold),
            Paragraph("<font color='#C53030'>Minimal</font> (6 basic domain tests only)", table_cell_style),
            Paragraph("<font color='#276749'>Comprehensive</font> (17 backend + 36 client tests)", table_cell_style),
        ],
    ]
    comp_table = Table(comp_data, colWidths=[4.5 * cm, 6.7 * cm, 6.8 * cm])
    comp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BOX", (0, 0), (-1, -1), 1, LINE_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(comp_table)
    story.append(Spacer(1, 10))

    # Conclusion & Recommendation
    story.append(Paragraph("7. Conclusion & Deployment Recommendation", h1_style))
    story.append(
        Paragraph(
            "Through systematic review, testing, and progressive refinement, the Phase-1 prototype has been "
            "successfully elevated into a deployment-ready module that conforms to Fusion ERP standards. All known "
            "security, authorization, data integrity, and operational issues have been resolved. "
            "We recommend deploying this implementation into a controlled staging/test environment for final user "
            "acceptance testing prior to full institutional production release.",
            body_style,
        )
    )

    doc.build(story)
    print(f"Successfully generated PDF report at: {os.path.abspath(PDF_PATH)}")


if __name__ == "__main__":
    build_pdf()
