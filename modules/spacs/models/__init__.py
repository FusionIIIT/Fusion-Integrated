"""SPACS Django ORM models."""

from django.db import models
from core.db.mixins import TimeStampedModel
from ..domain.errors import AuditProtectionError


class SpacsCatalogueEntry(TimeStampedModel):
    SCHEME_TYPES = [
        ("scholarship", "Scholarship"),
        ("award", "Award"),
    ]
    STATUSES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("retired", "Retired"),
    ]

    scheme_code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    scheme_type = models.CharField(max_length=32, choices=SCHEME_TYPES, default="scholarship")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=32, choices=STATUSES, default="draft", db_index=True)

    policy_approval_ref = models.CharField(max_length=255, blank=True, default="")
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    application_window_start = models.DateTimeField(null=True, blank=True)
    application_window_end = models.DateTimeField(null=True, blank=True)
    academic_cycle = models.CharField(max_length=32, default="2026-27")
    version = models.IntegerField(default=1)

    min_cpi = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    max_family_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    required_documents = models.JSONField(default=list, blank=True)

    renewal_allowed = models.BooleanField(default=False)
    renewal_window_start = models.DateTimeField(null=True, blank=True)
    renewal_window_end = models.DateTimeField(null=True, blank=True)

    candidate_source_method = models.CharField(
        max_length=32,
        choices=[("application", "Application"), ("system_pool", "System Pool"), ("nomination", "Nomination")],
        default="application",
    )
    created_by_user_id = models.IntegerField(default=1)

    class Meta:
        db_table = "spacs_catalogue_entry"


class SpacsCatalogueVersion(models.Model):
    catalogue_entry = models.ForeignKey(
        SpacsCatalogueEntry,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version = models.IntegerField()
    criteria_snapshot = models.JSONField(default=dict)
    policy_approval_ref = models.CharField(max_length=255)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_catalogue_version"
        unique_together = ("catalogue_entry", "version")


class SpacsApplication(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_verification", "Under Verification"),
        ("correction_required", "Correction Required"),
        ("resubmitted", "Resubmitted"),
        ("verified", "Verified / Routed for Decision"),
        ("verification_concern", "Verification Concern"),
        ("under_convener_review", "Under Convener Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("renewal_submitted", "Renewal Submitted"),
        ("renewal_under_verification", "Renewal Under Verification"),
        ("renewal_verified", "Renewal Verified / Routed"),
        ("renewal_under_decision", "Renewal Under Decision"),
        ("renewed", "Renewed / Approved"),
        ("renewal_rejected", "Renewal Rejected"),
    ]

    application_id = models.CharField(max_length=64, unique=True, db_index=True)
    catalogue_entry = models.ForeignKey(SpacsCatalogueEntry, on_delete=models.PROTECT, related_name="applications")
    catalogue_version = models.IntegerField(default=1)
    applicant_user_id = models.IntegerField(db_index=True)
    academic_cycle = models.CharField(max_length=32)
    is_renewal = models.BooleanField(default=False)
    parent_application = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="renewals"
    )

    state = models.CharField(max_length=40, choices=STATUS_CHOICES, default="draft", db_index=True)
    cpi = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    family_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    application_data = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    verification_assigned_to_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    verification_findings = models.TextField(blank=True, default="")
    verification_authenticity_confirmed = models.BooleanField(default=False)
    correction_reason = models.TextField(blank=True, default="")

    decision_actor_user_id = models.IntegerField(null=True, blank=True)
    decision_reason = models.TextField(blank=True, default="")
    decision_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_application"


class SpacsDocument(models.Model):
    application = models.ForeignKey(
        SpacsApplication, null=True, blank=True, on_delete=models.CASCADE, related_name="documents"
    )
    user_id = models.IntegerField(db_index=True)
    document_type = models.CharField(max_length=64)
    file_path = models.CharField(max_length=512)
    valid_until = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_document"


class SpacsAwardCycle(TimeStampedModel):
    STATES = [
        ("open", "Award Cycle Open"),
        ("pool_prepared", "Candidate Pool Prepared"),
        ("under_committee_evaluation", "Under Committee Evaluation"),
        ("committee_result_recorded", "Committee Result Recorded"),
        ("awaiting_approval", "Awaiting Institutional Approval"),
        ("ready_for_publication", "Ready for Publication"),
        ("published", "Published"),
    ]

    catalogue_entry = models.ForeignKey(SpacsCatalogueEntry, on_delete=models.PROTECT, related_name="award_cycles")
    academic_cycle = models.CharField(max_length=32)
    state = models.CharField(max_length=40, choices=STATES, default="open", db_index=True)
    criteria_version = models.IntegerField(default=1)
    approval_evidence = models.CharField(max_length=255, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    prepared_by_user_id = models.IntegerField(default=1)

    class Meta:
        db_table = "spacs_award_cycle"


class SpacsAwardCandidate(models.Model):
    award_cycle = models.ForeignKey(SpacsAwardCycle, on_delete=models.CASCADE, related_name="candidates")
    student_user_id = models.IntegerField(db_index=True)
    cpi = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    academic_standing = models.CharField(max_length=64, blank=True, default="good")
    shortlisted = models.BooleanField(default=False)
    evaluation_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    committee_recommendation = models.CharField(max_length=64, blank=True, default="")
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "spacs_award_candidate"
        unique_together = ("award_cycle", "student_user_id")


class SpacsAuditLog(models.Model):
    event_type = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    actor_user_id = models.IntegerField(db_index=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_audit_log"

    def delete(self, *args, **kwargs):
        raise AuditProtectionError("Audit records are immutable and cannot be deleted (BR-SPACS-021).")

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise AuditProtectionError("Audit records are immutable and cannot be modified (BR-SPACS-021).")
        super().save(*args, **kwargs)


class SpacsNotification(models.Model):
    recipient_user_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_notification"


class SpacsTask(models.Model):
    task_type = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64)
    entity_id = models.CharField(max_length=64)
    assigned_role = models.CharField(max_length=64)
    assigned_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, default="pending")
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_task"
