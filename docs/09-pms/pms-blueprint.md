# Patent Management System (PMS) — Architecture and Implementation Blueprint

**Document Version:** 1.0  
**Status:** APPROVED ARCHITECTURAL BLUEPRINT  
**Module Code:** pms  
**Django Module Path:** modules/pms/  
**Frontend Module Path:** client/src/modules/pms/  
**ID Prefix:** PMS  

---

## 1. System Overview & Architectural Principles

The Patent Management System (PMS) is a production-grade module within Fusion ERP responsible for digitizing and managing the complete institutional patent application lifecycle, patent prosecution, attorney interactions, office-action workflows, maintenance fee renewal schedules, licensing requests, and institutional intellectual property governance.

### Architectural Principles
1. **Fusion-Integrated Compliance**: Integrates directly into the existing Fusion ERP repository and architecture. No separate runtime, demo app, or independent authentication.
2. **Strict Module Boundary**: All backend logic resides exclusively in modules/pms/. No foreign keys cross module boundaries (enforced by ops/checks/no_cross_module_fk.py). Inter-module communication occurs strictly via contracts.py with plural interfaces (ops/checks/contracts_are_plural.py).
3. **IAM & Principal Model**: Uses Fusion's immutable Principal built from session identity. No custom User, Role, or IAM tables are created. User references use the plain integer user_id convention with UserScopedModel.
4. **Closed Permission Vocabulary**: Adheres strictly to <module>.<resource>.<action> syntax using the established closed verb vocabulary (iew, create, update, delete, pprove, 
eview, ssign, manage, publish).
5. **Pure Domain Logic**: All business calculations, decision gates, character limits, percentage validations, and deadline arithmetic reside in pure Python classes under modules/pms/domain/ with zero imports of Django, DRF, or Celery (enforced by .importlinter).
6. **Row-Level Security & Failsafe 404s**: Selectors enforce row-level scoping. Out-of-scope or unauthorized object accesses yield 404 Not Found rather than 403 Forbidden to prevent enumeration attacks.
7. **Transactional Integrity & Row-Locking**: State transitions use 	ransaction.atomic() with select_for_update() to prevent race conditions in concurrent reviews or assignment acceptances.
8. **Immutable Audit Trails**: State transitions, reviews, approvals, document modifications, and exceptional handlings generate append-only immutable PatentAuditLog entries.
9. **Realistic External Boundaries**: Acknowledges external system boundaries (Indian/International Patent Offices, accounting/payment gateways, email relays). PMS tracks records, schedules, and statuses without feigning external API processing.

---

## 2. Actors, Roles & Permission Mapping

The authoritative specifications define four primary institutional actors:

| Actor | Institutional Scope | Associated IAM Designations | Primary Permissions |
|---|---|---|---|
| **Applicant** | Faculty, students, and research staff submitting patents, managing co-inventors, responding to revisions, and viewing own records. | student, aculty | pms.application.create, pms.application.view_self, pms.application.update, pms.application.delete, pms.document.upload, pms.document.view, pms.licensing.create, pms.appeal.create, pms.office_action_response.approve, pms.prior_art.search, pms.report.view_self |
| **Director** | Senior academic leaders and technical reviewers evaluating patentability, budgets, renewals, and appeals. | Dean Academic, director, aculty | pms.application.view, pms.application.review, pms.budget.review, pms.budget.approve, pms.maintenance.approve, pms.licensing.review, pms.appeal.review, pms.report.view |
| **PCC_ADMIN** | Patent Cell Coordinator / Admin overseeing system configuration, Director routing, Attorney panel assignments, escalations, and system-wide audits. | cadadmin, pcc_admin, staff | pms.application.view, pms.application.assign, pms.attorney.assign, pms.configuration.manage, pms.attorney_panel.manage, pms.audit.view, pms.report.view, pms.escalation.manage |
| **Attorney** | Legal counsel conducting legal patentability assessments, prior-art validation, external filing, office-action responses, and post-grant maintenance tracking. | patent_attorney, legal_counsel, staff | pms.application.view, pms.attorney_assignment.respond, pms.patentability.assess, pms.filing.record, pms.office_action.record, pms.office_action.respond, pms.maintenance.manage, pms.advice.record, pms.prior_art.manage |

---

## 3. Data Architecture & Relational Models

All models inherit from TimeStampedModel (and UserScopedModel where directly owned by a user):

1. **PatentApplication** (pms_patent_application):
   - id: BigAutoField
   - pplication_no: CharField (e.g., PMS-2026-0001)
   - 	itle: CharField(max_length=255)
   - bstract: TextField
   - description: TextField
   - claims: TextField
   - domain: CharField(max_length=100) (e.g., CSE, ECE, Mechanical, Biotech)
   - iling_type: CharField (e.g., provisional, complete, pct, oreign)
   - status: CharField(max_length=50) (Lifecycle state: draft, submitted, under_review, pproved, 
eeds_revision, 
esubmitted, 
ejected, ppeal_submitted, 
emanded_for_amendment, 
ejection_upheld, decision_modified, ttorney_assigned, udget_approved, iled, office_action_recorded, granted, withdrawn, expired)
   - user_id: IntegerField (Applicant user ID)
   - is_confidential: BooleanField(default=True)
   - 
evision_deadline: DateTimeField(null=True, blank=True)

2. **Inventor** (pms_inventor):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='inventors')
   - user_id: IntegerField(null=True, blank=True)
   - 
ame: CharField(max_length=200)
   - email: EmailField
   - department: CharField(max_length=100)
   - is_lead: BooleanField(default=False)
   - share_percentage: DecimalField(max_digits=5, decimal_places=2) (Sum across inventors must equal 100.00%)
   - consent_status: CharField (pending, granted, 
efused)
   - consent_date: DateTimeField(null=True, blank=True)

3. **InventorAgreement** (pms_inventor_agreement):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='agreements')
   - greement_type: CharField (patent_assignment, co_inventor_agreement, institutional_declaration)
   - status: CharField (draft, circulated, completed)
   - completed_at: DateTimeField(null=True, blank=True)

4. **ApplicationDocument** (pms_application_document):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='documents')
   - document_type: CharField (specification, claims_doc, drawings, prior_art, ormal_submission, office_action, 
esponse_doc)
   - 	itle: CharField(max_length=255)
   - ile: FileField(upload_to='pms/documents/%Y/%m/')
   - ile_size: BigIntegerField
   - mime_type: CharField(default='application/pdf')
   - sensitivity: CharField (standard, confidential, 
estricted)
   - ersion: IntegerField(default=1)
   - uploaded_by_user_id: IntegerField
   - is_malware_scanned: BooleanField(default=False)
   - scan_details: JSONField(default=dict)

5. **DirectorAssignment** (pms_director_assignment):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='director_assignments')
   - director_user_id: IntegerField
   - ssigned_by_user_id: IntegerField
   - due_at: DateTimeField (15 business days from assignment)
   - status: CharField (ssigned, completed, 
eassigned)

6. **DirectorReview** (pms_director_review):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='director_reviews')
   - director_user_id: IntegerField
   - decision: CharField (pprove, 
eject, 
eeds_revision)
   - justification: TextField (Minimum 50 characters required by BR-PMS-030)
   - decided_at: DateTimeField(auto_now_add=True)

7. **AttorneyPanel** (pms_attorney_panel):
   - user_id: IntegerField(unique=True)
   - 
ame: CharField(max_length=200)
   - irm_name: CharField(max_length=200)
   - specialization: CharField(max_length=200)
   - is_active: BooleanField(default=True)
   - max_workload: IntegerField(default=10)
   - current_workload: IntegerField(default=0)

8. **AttorneyAssignment** (pms_attorney_assignment):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='attorney_assignments')
   - ttorney_user_id: IntegerField
   - ssigned_by_user_id: IntegerField
   - status: CharField (offered, ccepted, declined)
   - 
esponded_at: DateTimeField(null=True, blank=True)
   - 
emarks: TextField(blank=True)

9. **PatentabilityAssessment** (pms_patentability_assessment):
   - pplication: ForeignKey(PatentApplication, on_delete=CASCADE, related_name='patentability_assessments')
   - ttorney_user_id: IntegerField
   - 
ecommendation: CharField (ile_patent, do_not_file, 
eeds_amendment)
   - 
ovelty_analysis: TextField
   - inventive_step_analysis: TextField
   - utility_analysis: TextField
   - prior_art_summary: TextField
   - opinion_text: TextField
   - ssessed_at: DateTimeField(auto_now_add=True)

10. **PatentBudget** (pms_patent_budget):
    - pplication: OneToOneField(PatentApplication, on_delete=CASCADE, related_name='budget')
    - iling_fees: DecimalField(max_digits=12, decimal_places=2)
    - ttorney_fees: DecimalField(max_digits=12, decimal_places=2)
    - dministrative_costs: DecimalField(max_digits=12, decimal_places=2)
    - 	otal_cost: DecimalField(max_digits=12, decimal_places=2)
    - status: CharField (draft, pending_approval, pproved, 
ejected, escalated)
    - director_user_id: IntegerField(null=True, blank=True)
    - justification: TextField(blank=True)

11. **ExternalFilingRecord** (pms_external_filing_record):
    - pplication: OneToOneField(PatentApplication, on_delete=CASCADE, related_name='filing_record')
    - jurisdiction: CharField(max_length=50) (e.g. IN, PCT, US, EP)
    - iling_number: CharField(max_length=100)
    - iling_date: DateField
    - patent_office: CharField(max_length=200)
    - confirmation_details: TextField
    - international_justification: TextField(blank=True)
    - 
ecorded_by_user_id: IntegerField

12. **OfficeAction** & **OfficeActionResponse**:
    - Manage post-filing office actions, examination reports, deadlines, and attorney responses with applicant approvals.

13. **PostGrantPatent** & **MaintenanceSchedule**:
    - Track granted patents, 20-year term renewal schedules, and Director renewal decisions.

14. **ApplicationWithdrawal**:
    - Track pre-filing withdrawals, withdrawal reasons, and co-inventor consent verification.

15. **PriorArtSearchRecord** & **PriorArtAttachment**:
    - Record prior-art search queries, database sources, and attached references.

16. **LicensingRequest**:
    - Track licensing proposals, technology-transfer negotiations, and Director review notes.

17. **PatentAppeal** & **AppealDecision**:
    - Track rejection appeals with applicant grounds and Director outcomes (uphold_rejection, 
emand_for_amendment, modify_decision).

18. **PatentAuditLog**:
    - Append-only immutable log recording actor, action, previous/new states, payload, and timestamp.

19. **DeadlineTracking**:
    - Track deadlines for reviews (15 business days), revisions (60 days), office actions, and maintenance renewals, with 30-day, 15-day, and 5-day alert flags.

---

## 4. Layering & Directory Structure

`
modules/pms/
├── __init__.py
├── apps.py                  # AppConfig
├── registry.py              # MODULE, NAV_ITEMS, PERMISSIONS, ROLE_GRANTS
├── contracts.py             # Public plural interface for other modules
├── domain/                  # Pure Python: rules, guards, validators, math
│   ├── __init__.py
│   ├── rules.py             # BR-PMS implementations
│   ├── constants.py         # Enums, limits, deadlines
│   └── exceptions.py        # Domain-specific errors
├── models/                  # Django ORM models
│   ├── __init__.py
│   ├── applications.py
│   ├── reviews.py
│   ├── attorneys.py
│   ├── filings.py
│   ├── documents.py
│   └── maintenance.py
├── selectors/               # Read-only queries with row-level scoping
│   ├── __init__.py
│   ├── applications.py
│   ├── reviews.py
│   ├── attorneys.py
│   └── reports.py
├── services/                # Transactional state transitions & mutations
│   ├── __init__.py
│   ├── applications.py
│   ├── reviews.py
│   ├── attorneys.py
│   ├── filings.py
│   ├── documents.py
│   ├── maintenance.py
│   └── audit.py
├── api/                     # DRF Views & Serializers
│   ├── __init__.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── schedule.py              # Celery beat periodic schedules
├── tasks.py                 # Celery asynchronous tasks for alerts
└── tests/                   # Pytest test suite
    ├── test_domain.py
    ├── test_models.py
    ├── test_services.py
    ├── test_selectors.py
    ├── test_api.py
    └── test_workflows.py
`

---

## 5. Frontend Architecture

Under client/src/modules/pms/:
`
client/src/modules/pms/
├── api/
│   ├── client.ts            # Typed Axios calls using shared http.ts
│   └── types.ts             # TypeScript interfaces for PMS DTOs
├── components/
│   ├── ApplicationCard.tsx
│   ├── StatusBadge.tsx
│   ├── DocumentUploadModal.tsx
│   ├── DirectorReviewModal.tsx
│   ├── AttorneyAssignModal.tsx
│   ├── OfficeActionModal.tsx
│   └── AuditTimeline.tsx
├── pages/
│   ├── ApplicationListPage.tsx
│   ├── ApplicationDetailPage.tsx
│   ├── NewApplicationPage.tsx
│   ├── DirectorReviewsPage.tsx
│   ├── PCCAdminConsolePage.tsx
│   ├── AttorneyConsolePage.tsx
│   ├── OfficeActionsPage.tsx
│   ├── MaintenancePage.tsx
│   ├── ReportsPage.tsx
│   └── AuditLogsPage.tsx
└── routes.tsx               # Route definitions matching NAV_ITEMS
`