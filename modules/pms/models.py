"""PMS Models.

Encodes persistence for the Patent Management System.
Invariants and integrity rules are enforced via database constraints and domain services.
No cross-module foreign keys (ADR-0013).
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.domain.state_machine import PatentApplicationStatus


class PatentApplication(TimeStampedModel):
    """The central entity of the Patent Management System."""

    STATUS_CHOICES = [(s.value, s.name) for s in PatentApplicationStatus]

    application_no = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    detailed_description = models.TextField()
    claims = models.TextField()
    domain = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=PatentApplicationStatus.SUBMITTED.value,
        db_index=True,
    )

    # Actor user IDs (plain integer IDs from IAM - NO cross-module FK)
    applicant_user_id = models.IntegerField(db_index=True)
    assigned_director_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_attorney_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    preferred_attorney_id = models.IntegerField(null=True, blank=True)

    # Lifecycle tracking & deadlines
    director_assigned_at = models.DateTimeField(null=True, blank=True)
    review_deadline = models.DateTimeField(null=True, blank=True)
    revision_deadline = models.DateTimeField(null=True, blank=True)

    # Jurisdiction & Filing
    jurisdiction = models.CharField(max_length=50, default="IN")
    is_international = models.BooleanField(default=False)
    international_justification = models.TextField(blank=True)
    external_filing_id = models.CharField(max_length=100, blank=True)
    external_filing_date = models.DateField(null=True, blank=True)
    filing_confirmation = models.TextField(blank=True)
    format_validated = models.BooleanField(default=False)

    # Post-grant
    grant_date = models.DateField(null=True, blank=True)
    patent_number = models.CharField(max_length=100, blank=True)

    # Pre-filing withdrawal
    is_withdrawn = models.BooleanField(default=False)
    withdrawal_reason = models.TextField(blank=True)
    withdrawal_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_patent_application"
        indexes = [
            models.Index(fields=["status", "-created_at"], name="pms_app_status_created_idx"),
            models.Index(fields=["applicant_user_id", "status"], name="pms_app_applicant_idx"),
            models.Index(
                fields=["assigned_director_user_id", "status"], name="pms_app_director_idx"
            ),
            models.Index(
                fields=["assigned_attorney_user_id", "status"], name="pms_app_attorney_idx"
            ),
            models.Index(fields=["domain"], name="pms_app_domain_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.application_no}: {self.title} ({self.status})"


class CoInventor(TimeStampedModel):
    """Co-inventor and ownership shares (CFR-PMS-016)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="coinventors"
    )
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    department = models.CharField(max_length=100, blank=True)
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    consent_given = models.BooleanField(default=False)
    agreement_signed = models.BooleanField(default=False)
    electronic_signature = models.CharField(max_length=255, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    withdrawal_consent_given = models.BooleanField(default=False)

    class Meta:
        db_table = "pms_coinventor"
        indexes = [
            models.Index(fields=["application", "user_id"], name="pms_coinv_app_user_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.ownership_percentage}%) - {self.application.application_no}"


class ApplicationDocument(TimeStampedModel):
    """Supporting application document with version control (CFR-PMS-018)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    file_format = models.CharField(max_length=10, default="pdf")
    file_size_bytes = models.BigIntegerField(default=0)
    malware_scanned = models.BooleanField(default=True)
    is_clean = models.BooleanField(default=True)
    sensitivity = models.CharField(max_length=20, default="confidential")
    version = models.IntegerField(default=1)
    is_current = models.BooleanField(default=True)
    uploaded_by_user_id = models.IntegerField(db_index=True)
    file_url = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "pms_application_document"
        indexes = [
            models.Index(
                fields=["application", "doc_type", "version"], name="pms_doc_app_type_ver_idx"
            ),
            models.Index(fields=["application", "is_current"], name="pms_doc_current_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} v{self.version} ({self.doc_type})"


class DirectorReview(TimeStampedModel):
    """Director technical review and justification record (CFR-PMS-007)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="director_reviews"
    )
    director_user_id = models.IntegerField(db_index=True)
    decision = models.CharField(max_length=20)
    justification = models.TextField()
    feedback = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_director_review"
        indexes = [
            models.Index(fields=["application", "-decided_at"], name="pms_review_app_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Review by {self.director_user_id}: {self.decision} on {self.application.application_no}"


class PatentBudget(TimeStampedModel):
    """Patent prosecution and filing budget (CFR-PMS-011)."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("escalated", "Escalated"),
    ]

    application = models.OneToOneField(
        PatentApplication, on_delete=models.CASCADE, related_name="budget"
    )
    filing_fees = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    attorney_fees = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    administrative_costs = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    threshold_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("100000.00")
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    justification = models.TextField(blank=True)
    availability_verified = models.BooleanField(default=True)

    class Meta:
        db_table = "pms_patent_budget"

    def __str__(self) -> str:
        return f"Budget {self.total_cost} ({self.status}) for {self.application.application_no}"


class AttorneyAssignment(TimeStampedModel):
    """Attorney assignment offer and response tracking (CFR-PMS-009)."""

    STATUS_CHOICES = [
        ("offered", "Offered"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="attorney_assignments"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    assigned_by_user_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="offered")
    decline_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "pms_attorney_assignment"
        indexes = [
            models.Index(fields=["attorney_user_id", "status"], name="pms_atty_assign_user_idx"),
        ]

    def __str__(self) -> str:
        return f"Assignment of {self.attorney_user_id}: {self.status}"


class AttorneyPanel(TimeStampedModel):
    """Approved attorney panel with domain expertise and workload tracking (CFR-PMS-009)."""

    attorney_user_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=150)
    firm_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    is_approved = models.BooleanField(default=True)
    expertise_domains = models.JSONField(default=list)
    current_workload = models.IntegerField(default=0)
    max_workload = models.IntegerField(default=10)

    class Meta:
        db_table = "pms_attorney_panel"

    def __str__(self) -> str:
        return f"Attorney {self.name} (Approved: {self.is_approved}, Workload: {self.current_workload}/{self.max_workload})"


class PatentabilityAssessment(TimeStampedModel):
    """Attorney patentability opinion and legal review (CFR-PMS-010)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="patentability_assessments"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    novelty_score = models.IntegerField(default=0)
    non_obviousness_score = models.IntegerField(default=0)
    utility_score = models.IntegerField(default=0)
    recommendation = models.CharField(max_length=20)
    opinion_text = models.TextField()
    is_final = models.BooleanField(default=True)

    class Meta:
        db_table = "pms_patentability_assessment"

    def __str__(self) -> str:
        return f"Assessment for {self.application.application_no}: {self.recommendation}"


class PriorArtReference(TimeStampedModel):
    """Attached prior art references and literature searches (CFR-PMS-017)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="prior_art_references"
    )
    source = models.CharField(max_length=100)
    reference_id = models.CharField(max_length=100)
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=300, blank=True)
    relevance = models.CharField(max_length=20, default="high")
    notes = models.TextField(blank=True)
    attached_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "pms_prior_art_reference"

    def __str__(self) -> str:
        return f"{self.reference_id}: {self.title}"


class OfficeAction(TimeStampedModel):
    """External patent office action and response workflow (CFR-PMS-014)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="office_actions"
    )
    action_type = models.CharField(max_length=100)
    issue_date = models.DateField()
    due_date = models.DateField()
    details = models.TextField()
    status = models.CharField(max_length=32, default="recorded")
    requires_applicant_review = models.BooleanField(default=True)
    draft_response = models.TextField(blank=True)
    applicant_approved = models.BooleanField(default=False)
    extension_months = models.IntegerField(default=0)
    response_submitted_date = models.DateField(null=True, blank=True)
    submission_details = models.TextField(blank=True)

    class Meta:
        db_table = "pms_office_action"
        indexes = [
            models.Index(fields=["application", "due_date"], name="pms_oa_app_due_idx"),
        ]

    def __str__(self) -> str:
        return f"OA {self.action_type} for {self.application.application_no} ({self.status})"


class PostGrantMaintenance(TimeStampedModel):
    """Post-grant renewal fee schedule and decision tracking (CFR-PMS-013)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="maintenance_records"
    )
    cycle_number = models.IntegerField(default=1)
    fee_due_date = models.DateField()
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    decision_requested = models.BooleanField(default=False)
    director_decision = models.CharField(max_length=20, blank=True)
    renewal_decided_at = models.DateTimeField(null=True, blank=True)
    maintenance_status = models.CharField(max_length=32, default="scheduled")
    action_recorded_date = models.DateField(null=True, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "pms_post_grant_maintenance"
        indexes = [
            models.Index(fields=["application", "fee_due_date"], name="pms_maint_app_due_idx"),
        ]

    def __str__(self) -> str:
        return f"Maint Cycle {self.cycle_number} for {self.application.application_no} ({self.maintenance_status})"


class LicensingRequest(TimeStampedModel):
    """Licensing and tech transfer requests (CFR-PMS-019)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="licensing_requests"
    )
    requested_by_user_id = models.IntegerField(db_index=True)
    licensee_name = models.CharField(max_length=200)
    request_type = models.CharField(max_length=50)
    commercial_terms = models.TextField()
    status = models.CharField(max_length=32, default="submitted")
    negotiation_notes = models.TextField(blank=True)
    agreement_reference = models.CharField(max_length=100, blank=True)
    is_confidential = models.BooleanField(default=True)

    class Meta:
        db_table = "pms_licensing_request"

    def __str__(self) -> str:
        return f"License to {self.licensee_name} ({self.status})"


class PatentAppeal(TimeStampedModel):
    """Applicant appeal against rejection (CFR-PMS-020)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="appeals"
    )
    applicant_user_id = models.IntegerField(db_index=True)
    grounds = models.TextField()
    justification = models.TextField()
    status = models.CharField(max_length=32, default="submitted")
    outcome = models.CharField(max_length=32, blank=True)
    director_user_id = models.IntegerField(null=True, blank=True)
    outcome_justification = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_patent_appeal"

    def __str__(self) -> str:
        return f"Appeal on {self.application.application_no}: {self.status}"


class PatentLegalAdvice(TimeStampedModel):
    """Attorney legal advice record (CFR-PMS-004)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="legal_advices"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    stage = models.CharField(max_length=50)
    advice_text = models.TextField()

    class Meta:
        db_table = "pms_patent_legal_advice"

    def __str__(self) -> str:
        return f"Legal Advice by {self.attorney_user_id} on {self.application.application_no}"


class PmsAuditTrail(models.Model):
    """Immutable audit trail for all critical patent actions (CFR-PMS-024)."""

    application = models.ForeignKey(
        PatentApplication,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    action_type = models.CharField(max_length=100, db_index=True)
    from_state = models.CharField(max_length=50, blank=True)
    to_state = models.CharField(max_length=50, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_immutable = models.BooleanField(default=True)

    class Meta:
        db_table = "pms_audit_trail"
        indexes = [
            models.Index(fields=["application", "-timestamp"], name="pms_audit_app_time_idx"),
            models.Index(fields=["actor_user_id", "-timestamp"], name="pms_audit_actor_time_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.action_type} by {self.actor_user_id}"


class PmsNotificationOutbox(TimeStampedModel):
    """System-generated email notification outbox (CFR-PMS-023)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"], name="pms_notify_pending_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.topic} -> {self.recipient_user_id or self.recipient_email} ({self.status})"


class PmsConfiguration(TimeStampedModel):
    """Module-level configuration managed by PCC_ADMIN (CFR-PMS-003)."""

    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "pms_configuration"

    def __str__(self) -> str:
        return f"PMS Config: {self.key}"


class PmsRoleAssignment(TimeStampedModel):
    """Local PMS role assignment and expertise mapping (CFR-PMS-025, CFR-PMS-028)."""

    ROLE_CHOICES = [
        ("Applicant", "Applicant"),
        ("Director", "Director"),
        ("PCC_ADMIN", "PCC_ADMIN"),
        ("Attorney", "Attorney"),
    ]

    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    domain = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "pms_role_assignment"
        constraints = [
            # Enforce exactly one active PCC_ADMIN constraint (BR-PMS-131)
            models.UniqueConstraint(
                fields=["role", "is_active"],
                condition=models.Q(role="PCC_ADMIN", is_active=True),
                name="pms_unique_active_pcc_admin",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "role", "is_active"], name="pms_role_user_act_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id}: {self.role} ({'Active' if self.is_active else 'Inactive'})"
