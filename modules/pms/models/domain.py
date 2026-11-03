import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from modules.pms.storage import PmsPrivateStorage


class Application(models.Model):
    """PMS-owned patent application record; IAM identities remain external IDs."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        RESUBMITTED = "resubmitted", "Resubmitted"
        NEEDS_REVISION = "needs_revision", "Needs Revision"
        REJECTED = "rejected", "Rejected"
        APPROVED = "approved", "Approved"
        EXPIRED = "expired", "Expired"
        WITHDRAWN = "withdrawn", "Withdrawn"
        ATTORNEY_ASSIGNED = "attorney_assigned", "Attorney Assigned"
        PENDING_REVIEW = "pending_review", "Pending Review"
        FILED = "filed", "Filed"
        GRANTED = "granted", "Granted"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_number = models.CharField(max_length=40, unique=True, blank=True)
    applicant_user_id = models.PositiveBigIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    detailed_description = models.TextField()
    claims = models.TextField(help_text="Patent claims")
    technical_domain = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    assigned_director_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    assigned_attorney_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    preferred_attorney_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    review_due_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    revision_due_at = models.DateTimeField(null=True, blank=True)
    revision_count = models.PositiveSmallIntegerField(default=0)
    filed_at = models.DateTimeField(null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["applicant_user_id", "status"]),
            models.Index(fields=["assigned_director_user_id", "status"]),
            models.Index(fields=["assigned_attorney_user_id", "status"]),
        ]

    def __str__(self):
        return f"{self.application_number}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = f"PMS-{timezone.now():%Y}-{self.pk.hex[:12].upper()}"
        super().save(*args, **kwargs)


class Inventor(models.Model):
    """Application-local inventor profile; no Fusion/IAM master identity is created."""

    user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    affiliation = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "email", "full_name"], name="pms_inventor_identity_uniq"
            )
        ]

    def __str__(self):
        return self.full_name


class ApplicationInventorAgreement(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="inventor_agreements"
    )
    inventor = models.ForeignKey(
        Inventor, on_delete=models.PROTECT, related_name="application_agreements"
    )
    ownership_percent = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    agreement_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")],
        default="pending",
    )
    consent_recorded_at = models.DateTimeField(null=True, blank=True)
    signature_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "inventor"], name="pms_application_inventor_uniq"
            )
        ]

    def __str__(self):
        return f"ApplicationInventorAgreement #{self.pk}"


class ApplicationTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="transitions"
    )
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=60)
    justification = models.TextField(blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["occurred_at", "id"]

    def __str__(self):
        return f"ApplicationTransition #{self.pk}"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Application history records are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Application history records are immutable.")


class ApplicationDocument(models.Model):
    class Sensitivity(models.TextChoices):
        PUBLIC = "public", "Public"
        INTERNAL = "internal", "Internal"
        CONFIDENTIAL = "confidential", "Confidential"
        RESTRICTED = "restricted", "Restricted"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="documents")
    uploaded_by_user_id = models.PositiveBigIntegerField()
    document_type = models.CharField(max_length=50)
    sensitivity = models.CharField(
        max_length=20, choices=Sensitivity.choices, default=Sensitivity.INTERNAL
    )
    file = models.FileField(upload_to="pms/applications/%Y/%m/", storage=PmsPrivateStorage())
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    version = models.PositiveSmallIntegerField(default=1)
    malware_scan_status = models.CharField(
        max_length=16,
        choices=[
            ("pending", "Pending"),
            ("clean", "Clean"),
            ("infected", "Infected"),
            ("unavailable", "Unavailable"),
        ],
        default="pending",
    )
    previous_version = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="next_versions"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_type", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "document_type", "version"], name="pms_document_version_uniq"
            )
        ]

    def __str__(self):
        return f"ApplicationDocument #{self.pk}"


class DirectorProfile(models.Model):
    user_id = models.PositiveBigIntegerField(unique=True)
    expertise_domains = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    max_open_reviews = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DirectorProfile #{self.pk}"


class AttorneyProfile(models.Model):
    user_id = models.PositiveBigIntegerField(unique=True)
    panel_approved = models.BooleanField(default=False)
    expertise_domains = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    max_open_matters = models.PositiveSmallIntegerField(default=20)
    exception_record = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AttorneyProfile #{self.pk}"


class AttorneyAssignment(models.Model):
    class Status(models.TextChoices):
        OFFERED = "offered", "Assignment Offered"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        PENDING_REVIEW = "pending_review", "Pending Review"

    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="attorney_assignments"
    )
    attorney_user_id = models.PositiveBigIntegerField(db_index=True)
    assigned_by_user_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFERED)
    preference_recorded = models.BooleanField(default=False)
    panel_exception = models.TextField(blank=True)
    conflict_checked_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AttorneyAssignment #{self.pk}"


class PatentabilityOpinion(models.Model):
    class Recommendation(models.TextChoices):
        FILE = "file_patent", "File Patent"
        DO_NOT_FILE = "do_not_file", "Do Not File"
        NEEDS_AMENDMENT = "needs_amendment", "Needs Amendment"

    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="legal_opinions"
    )
    attorney_user_id = models.PositiveBigIntegerField()
    analysis = models.TextField()
    novelty = models.TextField(blank=True)
    non_obviousness = models.TextField(blank=True)
    utility = models.TextField(blank=True)
    recommendation = models.CharField(max_length=24, choices=Recommendation.choices)
    finalized_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"PatentabilityOpinion #{self.pk}"


class BudgetProposal(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ESCALATED = "escalated", "Escalated"

    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="budgets")
    filing_fees = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    attorney_fees = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    administrative_costs = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROPOSED)
    availability_checked = models.BooleanField(default=False)
    decision_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    decision_justification = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    authorization_level = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BudgetProposal #{self.pk}"

    @property
    def total(self):
        return self.filing_fees + self.attorney_fees + self.administrative_costs


class PatentFiling(models.Model):
    application = models.OneToOneField(Application, on_delete=models.PROTECT, related_name="filing")
    filed_by_user_id = models.PositiveBigIntegerField()
    jurisdiction = models.CharField(max_length=80)
    international_justification = models.TextField(blank=True)
    external_filing_id = models.CharField(max_length=120)
    filing_date = models.DateField()
    confirmation_reference = models.CharField(max_length=255, blank=True)
    format_validation_available = models.BooleanField(default=False)
    format_compliant = models.BooleanField(default=False)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PatentFiling #{self.pk}"


class PatentOfficeCommunication(models.Model):
    class Kind(models.TextChoices):
        OFFICE_ACTION = "office_action", "Office Action"
        OTHER = "other", "Other Communication"
        GRANT = "grant", "Patent Granted"

    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="office_communications"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OFFICE_ACTION)
    external_reference = models.CharField(max_length=120, blank=True)
    received_date = models.DateField()
    response_due_date = models.DateField(null=True, blank=True)
    deadline_source = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    recorded_by_user_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PatentOfficeCommunication #{self.pk}"


class OfficeActionResponse(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_APPLICANT = "awaiting_applicant", "Awaiting Applicant Approval"
        READY = "ready", "Ready to Submit"
        SUBMITTED = "submitted", "Submitted"

    communication = models.ForeignKey(
        PatentOfficeCommunication, on_delete=models.PROTECT, related_name="responses"
    )
    prepared_by_user_id = models.PositiveBigIntegerField()
    response_text = models.TextField()
    applicant_review_required = models.BooleanField(default=False)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    applicant_decision_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    applicant_approved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    external_submission_reference = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"OfficeActionResponse #{self.pk}"


class PatentAppeal(models.Model):
    class Outcome(models.TextChoices):
        PENDING = "pending", "Pending"
        UPHOLD = "uphold_rejection", "Uphold Rejection"
        REMAND = "remand_for_amendment", "Remand for Amendment"
        MODIFY = "modify_decision", "Modify Decision"

    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="appeals")
    filed_by_user_id = models.PositiveBigIntegerField()
    grounds = models.TextField()
    justification = models.TextField()
    filed_at = models.DateTimeField(default=timezone.now)
    outcome = models.CharField(max_length=24, choices=Outcome.choices, default=Outcome.PENDING)
    decided_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    decision_justification = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PatentAppeal #{self.pk}"


class Deadline(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="deadlines")
    kind = models.CharField(max_length=40)
    due_at = models.DateTimeField()
    responsible_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    source = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=16,
        choices=[
            ("open", "Open"),
            ("completed", "Completed"),
            ("missed", "Missed"),
            ("escalated", "Escalated"),
        ],
        default="open",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Deadline #{self.pk}"


class PmsConfiguration(models.Model):
    """PMS-only policy configuration; unspecified policy values remain unset."""

    key = models.CharField(max_length=80, unique=True)
    value = models.JSONField()
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PmsConfiguration #{self.pk}"


class PmsNotification(models.Model):
    recipient_user_id = models.PositiveBigIntegerField(db_index=True)
    application = models.ForeignKey(
        Application, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    event = models.CharField(max_length=80)
    dedupe_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=[
            ("queued", "Queued"),
            ("sending", "Sending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        default="queued",
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PmsNotification #{self.pk}"


class PmsAuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    application = models.ForeignKey(
        Application, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events"
    )
    action = models.CharField(max_length=80)
    previous_state = models.CharField(max_length=24, blank=True)
    new_state = models.CharField(max_length=24, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"PmsAuditEvent #{self.pk}"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("PMS audit events are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("PMS audit events are immutable.")


class PriorArtSearchSession(models.Model):
    application = models.ForeignKey(
        Application,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="search_sessions",
    )
    user_id = models.PositiveBigIntegerField()
    query = models.CharField(max_length=500)
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PriorArtSearchSession #{self.pk}"


class PriorArtReference(models.Model):
    session = models.ForeignKey(
        PriorArtSearchSession, on_delete=models.CASCADE, related_name="references"
    )
    title = models.CharField(max_length=500)
    external_reference = models.CharField(max_length=255)
    source_url = models.URLField(max_length=1000, blank=True)
    relevance_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    attached_to_application = models.ForeignKey(
        Application,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prior_art_references",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PriorArtReference #{self.pk}"


class LicensingRequest(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        NEGOTIATING = "negotiating", "Negotiating"
        AGREEMENT_RECORDED = "agreement_recorded", "Agreement Recorded"
        CLOSED = "closed", "Closed"

    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="licensing_requests"
    )
    submitted_by_user_id = models.PositiveBigIntegerField()
    request_details = models.TextField()
    confidentiality = models.CharField(
        max_length=20,
        choices=ApplicationDocument.Sensitivity.choices,
        default=ApplicationDocument.Sensitivity.CONFIDENTIAL,
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.SUBMITTED)
    negotiation_notes = models.TextField(blank=True)
    agreement_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"LicensingRequest #{self.pk}"


class LegalAdviceRecord(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="legal_advice"
    )
    attorney_user_id = models.PositiveBigIntegerField()
    advice = models.TextField()
    lifecycle_stage = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"LegalAdviceRecord #{self.pk}"


class MaintenanceCycle(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DECISION_REQUESTED = "decision_requested", "Renewal Decision Requested"
        RENEWAL_APPROVED = "renewal_approved", "Renewal Approved"
        RENEWED = "renewed", "Renewed"
        DO_NOT_RENEW = "do_not_renew", "Do Not Renew"

    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="maintenance_cycles"
    )
    jurisdiction = models.CharField(max_length=80)
    due_date = models.DateField()
    schedule_source = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    decision_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    transaction_reference = models.CharField(max_length=255, blank=True)
    next_cycle_due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MaintenanceCycle #{self.pk}"
