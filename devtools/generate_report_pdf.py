import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#666666"))
        
        # Header (on pages after cover/first page)
        if self._pageNumber > 1:
            self.drawString(2 * cm, 28.5 * cm, "Fusion ERP Lab — Assignment 6B: ELM Module Engineering Report")
            self.setStrokeColor(colors.HexColor("#D0D7DE"))
            self.setLineWidth(0.5)
            self.line(2 * cm, 28.3 * cm, 19 * cm, 28.3 * cm)

        # Footer
        self.setStrokeColor(colors.HexColor("#D0D7DE"))
        self.setLineWidth(0.5)
        self.line(2 * cm, 1.8 * cm, 19 * cm, 1.8 * cm)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(19 * cm, 1.3 * cm, page_text)
        self.drawString(2 * cm, 1.3 * cm, "Roll No: 24BCS170 & 24BCS182 | IIITDM Jabalpur")
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm
    )

    PRIMARY = colors.HexColor("#0969DA")    # GitHub/Tech Blue
    NAVY = colors.HexColor("#1A2B4C")       # Deep Navy Header
    TEXT = colors.HexColor("#24292F")       # Charcoal Body
    MUTED = colors.HexColor("#57606A")      # Muted Grey
    LIGHT_BG = colors.HexColor("#F6F8FA")   # Light Box BG
    BORDER = colors.HexColor("#D0D7DE")     # Border color
    GREEN = colors.HexColor("#1A7F37")      # Success Green

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY,
        spaceAfter=4,
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=PRIMARY,
        spaceAfter=12,
        alignment=TA_CENTER
    )

    meta_style = ParagraphStyle(
        "MetaText",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=TEXT
    )

    meta_bold = ParagraphStyle(
        "MetaTextBold",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=14,
        textColor=NAVY
    )

    h1_style = ParagraphStyle(
        "Header1",
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Header2",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "BodyDark",
        fontName="Helvetica",
        fontSize=9.3,
        leading=13.5,
        textColor=TEXT,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        textColor=TEXT,
        spaceAfter=3,
        leftIndent=12
    )

    code_style = ParagraphStyle(
        "CodeText",
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0550AE")
    )

    table_cell = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT
    )

    table_header = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.white
    )

    story = []

    # Title Banner
    story.append(Paragraph("FUSION ERP SYSTEM — LAB ASSIGNMENT 6B", subtitle_style))
    story.append(Paragraph("Phase 2: Review, Test, and Improvement of the AI-Generated ELM Module", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceBefore=4, spaceAfter=12))

    # Meta Table Box
    meta_data = [
        [
            Paragraph("<b>Candidate Name:</b> Nikhil Jain", meta_style),
            Paragraph("<b>Primary Roll No:</b> 24BCS170", meta_style)
        ],
        [
            Paragraph("<b>Partner Roll No:</b> 24BCS182", meta_style),
            Paragraph("<b>Assigned Module:</b> Employee Leave Management (ELM)", meta_style)
        ],
        [
            Paragraph("<b>Pull Request:</b> <font color='#0969DA'>PR #255 (FusionIIIT/Fusion-Integrated)</font>", meta_style),
            Paragraph("<b>Branch:</b> elm-nikhiljain10905", meta_style)
        ],
        [
            Paragraph("<b>Selected Code LLM:</b> Qwen2.5-Coder-7B-Instruct (Q4_K_M)", meta_style),
            Paragraph("<b>Inference Runtime:</b> Ollama (Continue IDE Extension)", meta_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[8.5 * cm, 8.5 * cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Section 1: Executive Summary & Objective
    story.append(Paragraph("1. Executive Summary & Objective", h1_style))
    story.append(Paragraph(
        "In Phase 1, an initial baseline implementation of the Employee Leave Management (ELM) module was scaffolded using "
        "locally deployed code LLMs. Under <b>Assignment 6B (Phase 2)</b>, our objective was to treat this generated artifact as "
        "inherited legacy software, rigorously identify architectural and functional gaps against the official ELM Specification Bundle v1.4, "
        "and progressively elevate it into a reliable, robust, deployment-ready module fully integrated with the supplied Fusion Base.",
        body_style
    ))
    story.append(Paragraph(
        "The Phase-1 baseline was preserved intact under <font name='Courier'>pilot/ELM_MODEL_1/</font> per instructions. Over Phase 2, "
        "systematic human-in-the-loop review and iterative LLM prompting were utilized to establish pure-Python domain business rules, "
        "atomic transactional services with row locking, schema migrations, complete REST API endpoints, automated pytest test suites, "
        "and live React frontend workflows.",
        body_style
    ))

    # Section 2: Environment & Hardware Configuration
    story.append(Paragraph("2. Technical & Hardware Environment", h1_style))
    story.append(Paragraph(
        "The entire development, local inference, and verification pipeline was executed locally on the developer machine without reliance on "
        "cloud-hosted black-box APIs:",
        body_style
    ))
    story.append(Paragraph("• <b>Processor:</b> 13th Gen Intel® Core™ i5-13450HX (10 Cores / 16 Threads, up to 4.60 GHz)", bullet_style))
    story.append(Paragraph("• <b>System Memory (RAM):</b> 24 GB DDR5 high-bandwidth memory", bullet_style))
    story.append(Paragraph("• <b>Graphics Hardware:</b> NVIDIA® GeForce RTX™ 3050 Laptop GPU (6 GB Dedicated GDDR6 VRAM)", bullet_style))
    story.append(Paragraph("• <b>Inference Engine:</b> Ollama runtime serving Qwen2.5-Coder-7B-Instruct quantized to 4-bit (Q4_K_M)", bullet_style))
    story.append(Paragraph("• <b>Developer Interface:</b> VS Code with Continue Extension (@file context-aware prompting)", bullet_style))

    # Section 3: Inherited Phase-1 Baseline Audit
    story.append(Paragraph("3. Inherited Phase-1 Baseline Audit & Problem Identification", h1_style))
    story.append(Paragraph(
        "Prior to writing code modifications, a comprehensive inspection of the Phase-1 baseline was conducted against the ELM problem statement, "
        "use case specifications, and Fusion's Architectural Decision Records (ADRs). The following critical defects and omissions were uncovered:",
        body_style
    ))

    audit_data = [
        [Paragraph("Category", table_header), Paragraph("Defect Identified in Phase-1 Baseline", table_header), Paragraph("Architectural / Operational Impact", table_header)],
        [
            Paragraph("<b>Database Schema</b>", table_cell),
            Paragraph("Character truncation bug: <font name='Courier'>LeaveApplication.status</font> was capped at <font name='Courier'>max_length=10</font>.", table_cell),
            Paragraph("Workflow states like <font name='Courier'>'AWAITING_SUBSTITUTE'</font> (19 chars) triggered fatal runtime <font name='Courier'>DataError</font> crashes.", table_cell)
        ],
        [
            Paragraph("<b>Data Models</b>", table_cell),
            Paragraph("Missing fields: <font name='Courier'>LeaveApplication</font> lacked <font name='Courier'>reason</font>; <font name='Courier'>SubstituteNomination</font> lacked <font name='Courier'>status</font> and <font name='Courier'>decline_reason</font>.", table_cell),
            Paragraph("User application motivations were discarded; substitute consent tracking (BR-EL-015) could not be recorded.", table_cell)
        ],
        [
            Paragraph("<b>Business Rules</b>", table_cell),
            Paragraph("Zero domain validation: missing date overlap checks, self-substitute validation, and balance sufficiency checks.", table_cell),
            Paragraph("Employees could submit overlapping leave dates (violating BR-EL-012), nominate themselves (BR-EL-014), or overdraft balances.", table_cell)
        ],
        [
            Paragraph("<b>Platform Rules</b>", table_cell),
            Paragraph("Cross-module Foreign Key: Phase-1 generated models with direct foreign keys to Django's <font name='Courier'>User</font> model.", table_cell),
            Paragraph("Violated Fusion ADR-0013 and failed repository CI check <font name='Courier'>no_cross_module_fk.py</font>.", table_cell)
        ],
        [
            Paragraph("<b>Frontend & API</b>", table_cell),
            Paragraph("Client components were empty mock stubs logging to <font name='Courier'>console.log</font> without backend HTTP calls.", table_cell),
            Paragraph("Users could not view live leave balances, submit real requests, or manage pending applications from the UI.", table_cell)
        ],
        [
            Paragraph("<b>Test Coverage</b>", table_cell),
            Paragraph("Total absence of automated unit tests in the entire <font name='Courier'>modules/elm/</font> directory.", table_cell),
            Paragraph("Zero regression safety or validation evidence existed for leave policy edge cases.", table_cell)
        ]
    ]
    audit_table = Table(audit_data, colWidths=[3.2 * cm, 6.8 * cm, 7.0 * cm])
    audit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 10))

    # Section 4: Phase-2 Engineering Improvements
    story.append(Paragraph("4. Phase-2 Engineering Improvements & Architecture", h1_style))
    story.append(Paragraph(
        "To address the audit findings, code improvements were implemented across multiple layers adhering strictly to Fusion's modular standards:",
        body_style
    ))

    story.append(Paragraph("A. Pure-Python Domain Business Rules (modules/elm/domain/policy.py)", h2_style))
    story.append(Paragraph(
        "To satisfy Fusion's <font name='Courier'>.importlinter</font> architecture (forbidding Django, DRF, or Celery inside domain layers), "
        "all business logic was encapsulated as pure-Python functions: "
        "<font name='Courier'>requested_days()</font> enforces valid calendar intervals; "
        "<font name='Courier'>check_date_overlap()</font> enforces <b>BR-EL-012</b>; "
        "<font name='Courier'>validate_substitute_eligibility()</font> prevents self-substitution (<b>BR-EL-014</b>); "
        "<font name='Courier'>validate_balance_sufficiency()</font> protects quotas; and "
        "<font name='Courier'>is_valid_transition()</font> strictly bounds allowed state transitions.",
        body_style
    ))

    story.append(Paragraph("B. Database Schema & Migration Alignment (modules/elm/models.py & migrations/)", h2_style))
    story.append(Paragraph(
        "Models were aligned with ADR-0013: integer keys (<font name='Courier'>applicant_id</font>, <font name='Courier'>employee_id</font>, "
        "<font name='Courier'>substitute_id</font>) are used instead of cross-module foreign keys. "
        "<font name='Courier'>LeaveApplication.status</font> was expanded to <font name='Courier'>max_length=30</font> accommodating "
        "<font name='Courier'>AWAITING_SUBSTITUTE</font>, <font name='Courier'>AWAITING_APPROVAL</font>, <font name='Courier'>APPROVED</font>, "
        "<font name='Courier'>REJECTED</font>, <font name='Courier'>WITHDRAWN</font>, and <font name='Courier'>CANCELLED</font>. "
        "Migrations <font name='Courier'>0001_initial.py</font> and <font name='Courier'>0002_add_workflow_and_reason_fields.py</font> were generated.",
        body_style
    ))

    story.append(Paragraph("C. Service Layer & Concurrency Control (modules/elm/services/applications.py)", h2_style))
    story.append(Paragraph(
        "All state mutations are encapsulated in atomic database transactions (<font name='Courier'>@transaction.atomic</font>). "
        "During leave application review and approval, row-level database locking (<font name='Courier'>select_for_update()</font>) is held on the "
        "<font name='Courier'>LeaveBalance</font> record before deducting days, eliminating double-spending and race condition hazards.",
        body_style
    ))

    story.append(Paragraph("D. Cross-Module Contracts (modules/elm/contracts.py)", h2_style))
    story.append(Paragraph(
        "Per Fusion's contract rules, cross-module consumers must query through <font name='Courier'>contracts.py</font> using plural getters. "
        "Implemented <font name='Courier'>get_active_leaves_for_employees(employee_ids: Sequence[int])</font> taking sequences to eliminate N+1 queries.",
        body_style
    ))

    story.append(Paragraph("E. REST API & RBAC Integration (modules/elm/api/ & registry.py)", h2_style))
    story.append(Paragraph(
        "Endpoints for leave balances, application submission, substitute consent, and supervisor review were implemented with DRF. "
        "Endpoints are guarded by <font name='Courier'>HasModuleGrant('elm')</font> and granular permissions (<font name='Courier'>elm.balance.view</font>, "
        "<font name='Courier'>elm.application.create</font>). Full OpenAPI schemas were decorated with <font name='Courier'>@extend_schema</font>, "
        "and <font name='Courier'>permission_manifest</font> was synchronized.",
        body_style
    ))

    story.append(Paragraph("F. Frontend React Client (client/src/modules/elm/)", h2_style))
    story.append(Paragraph(
        "Replaced stubs with responsive React components built on Fusion's shared HTTP client: "
        "<font name='Courier'>LeaveBalance.tsx</font> provides live balance cards; "
        "<font name='Courier'>LeaveApplication.tsx</font> provides a validated multi-type leave submission form; "
        "<font name='Courier'>LeaveHistory.tsx</font> provides a tabular audit history with inline application withdrawal (<font name='Courier'>BR-EL-022</font>). "
        "Mounted lazily in <font name='Courier'>routes.tsx</font> and registered in <font name='Courier'>client/src/app/registry.ts</font>.",
        body_style
    ))

    # Section 5: Verification & Quality Assurance Evidence
    story.append(Paragraph("5. Verification Results & Quality Assurance Checks", h1_style))
    story.append(Paragraph(
        "All changes were subjected to the platform's automated quality gates and passed with zero errors or warnings:",
        body_style
    ))

    verify_data = [
        [Paragraph("Quality Check Script / Tool", table_header), Paragraph("Command Executed", table_header), Paragraph("Observed Result", table_header), Paragraph("Status", table_header)],
        [
            Paragraph("<b>Cross-Module Foreign Keys</b>", table_cell),
            Paragraph("<font name='Courier'>python ops/checks/no_cross_module_fk.py</font>", table_cell),
            Paragraph("No cross-module foreign keys detected", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Plural Contract Getters</b>", table_cell),
            Paragraph("<font name='Courier'>python ops/checks/contracts_are_plural.py</font>", table_cell),
            Paragraph("All contract getters accept sequences of IDs", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Nav & Route Parity</b>", table_cell),
            Paragraph("<font name='Courier'>python ops/checks/nav_matches_routes.py</font>", table_cell),
            Paragraph("Nav items and client routes agree 1-to-1", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ],
        [
            Paragraph("<b>IAM Permission Manifest</b>", table_cell),
            Paragraph("<font name='Courier'>python manage.py permission_manifest --check</font>", table_cell),
            Paragraph("Manifest matches registries and views perfectly", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Architectural Import Boundaries</b>", table_cell),
            Paragraph("<font name='Courier'>lint-imports</font>", table_cell),
            Paragraph("4/4 contracts kept (domain pure python)", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Code Linting & Formatting</b>", table_cell),
            Paragraph("<font name='Courier'>ruff check config core fusion_auth ops modules</font>", table_cell),
            Paragraph("All checks passed (0 linting or style errors)", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Automated Unit Tests</b>", table_cell),
            Paragraph("<font name='Courier'>pytest modules/elm/tests/test_policy.py</font>", table_cell),
            Paragraph("5 passed in 0.15s (100% test pass rate)", table_cell),
            Paragraph("<font color='#1A7F37'><b>PASSED</b></font>", table_cell)
        ]
    ]
    verify_table = Table(verify_data, colWidths=[4.2 * cm, 6.2 * cm, 4.6 * cm, 2.0 * cm])
    verify_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('BOX', (0, 0), (-1, -1), 0.8, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
    ]))
    story.append(verify_table)
    story.append(Spacer(1, 10))

    # Section 6: Human-in-the-Loop & Prompting Engineering Insights
    story.append(Paragraph("6. Human-in-the-Loop Engineering & Prompting Insights", h1_style))
    story.append(Paragraph(
        "A critical lesson from Phase 2 is that raw AI output cannot be accepted without thorough human review. Two notable examples "
        "illustrate where human judgment caught subtle defects before they reached integration:",
        body_style
    ))
    story.append(Paragraph(
        "1. <b>Method Signature Mismatch in DRF Views:</b> The LLM generated <font name='Courier'>post(self, request)</font> on a view mounted "
        "with an ID parameter (<font name='Courier'>applications/&lt;int:pk&gt;/review</font>). At runtime, DRF threw a <font name='Courier'>TypeError</font>. "
        "During review, we corrected the method signature to <font name='Courier'>post(self, request, pk: int)</font> and fetched model instances using "
        "<font name='Courier'>get_object_or_404</font>.",
        bullet_style
    ))
    story.append(Paragraph(
        "2. <b>Hallucinated Frontend Dependencies:</b> When prompted to style notifications, the LLM hallucinated an import for "
        "<font name='Courier'>react-toastify</font>. Because Fusion does not have this package installed (it uses Mantine UI), this broke client compilation. "
        "Human review replaced the hallucinated library with self-contained, lightweight alert banners, preserving zero-dependency client health.",
        bullet_style
    ))
    story.append(Paragraph(
        "3. <b>Prompting Evolution:</b> Prompts shifted from broad, multi-file requests to atomic, highly constrained single-file directives with explicit negative "
        "instructions (e.g., 'no Django imports in domain/policy.py') and typed signatures, which eliminated hallucinations entirely.",
        bullet_style
    ))

    # Section 7: Conclusion & Deliverables
    story.append(Paragraph("7. Conclusion & Deliverables", h1_style))
    story.append(Paragraph(
        "Through systematic human–AI software engineering, the Phase-1 scaffold was elevated into a secure, thoroughly tested, and deployment-ready "
        "core ELM module. The submission has been officially raised as a Pull Request on the upstream repository.",
        body_style
    ))
    story.append(Paragraph("• <b>Upstream Pull Request:</b> https://github.com/FusionIIIT/Fusion-Integrated/pull/255", bullet_style))
    story.append(Paragraph("• <b>Developer Fork:</b> https://github.com/nikhiljain10905/Fusion-Integrated/tree/elm-nikhiljain10905", bullet_style))
    story.append(Paragraph("• <b>Engineering Log:</b> docs/changes_made_by_24bcs170.md", bullet_style))
    story.append(Paragraph("• <b>Phase-1 Baseline Preservation:</b> pilot/ELM_MODEL_1/prompts.md", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report PDF generated successfully at: {filename}")

if __name__ == "__main__":
    import sys
    out_path = sys.argv[1] if len(sys.argv) > 1 else "Fusion_ERP_Assignment_6B_Report_24BCS170_24BCS182.pdf"
    build_pdf(out_path)
