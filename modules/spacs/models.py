"""SPACS (Awards and Scholarships) domain models.

All institute persons are referenced by plain integer user IDs (user_id / student_user_id),
never foreign keys — no cross-module ForeignKeys are permitted.
"""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class SchemeCatalogue(TimeStampedModel):
    """A scholarship or convocation award catalogue item."""

    SCHEME_TYPES = [
        ("scholarship", "Scholarship"),
        ("award", "Convocation Award"),
    ]

    STATUSES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("retired", "Retired"),
    ]

    code = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    scheme_type = models.CharField(max_length=32, choices=SCHEME_TYPES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=STATUSES, default="draft", db_index=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    retired_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "spacs_scheme_catalogue"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "scheme_type"], name="spacs_cat_status_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class SchemePolicyVersion(TimeStampedModel):
    """Auditable, effective-period policy version for a scheme (CFR-SPACS-002, BR-SPACS-014)."""

    STATUSES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("retired", "Retired"),
    ]

    CANDIDATE_SOURCES = [
        ("application", "Student Application"),
        ("academic_pool", "System Academic Pool"),
        ("nomination", "Faculty / Senate Nomination"),
    ]

    scheme = models.ForeignKey(
        SchemeCatalogue,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Machine-checkable eligibility rules (BR-SPACS-001)
    eligibility_criteria = models.JSONField(default=dict, blank=True)

    # Required evidence specifications (BR-SPACS-004, 016)
    required_documents = models.JSONField(default=list, blank=True)

    # Candidate selection method (BR-SPACS-023)
    candidate_source_method = models.CharField(
        max_length=32, choices=CANDIDATE_SOURCES, default="application"
    )

    # Renewal conditions (CFR-SPACS-012, BR-SPACS-017)
    is_renewable = models.BooleanField(default=False)
    renewal_rules = models.JSONField(default=dict, blank=True)

    # Policy provenance (BR-SPACS-015)
    policy_approval_reference = models.CharField(max_length=200, blank=True)
    policy_approved_by = models.CharField(max_length=120, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)

    # Application & Renewal Windows
    application_window_start = models.DateTimeField(null=True, blank=True)
    application_window_end = models.DateTimeField(null=True, blank=True)
    renewal_window_start = models.DateTimeField(null=True, blank=True)
    renewal_window_end = models.DateTimeField(null=True, blank=True)

    # SLA thresholds in days (CFR-SPACS-007, BR-SPACS-013)
    sla_verification_days = models.PositiveIntegerField(default=7)
    sla_decision_days = models.PositiveIntegerField(default=14)

    status = models.CharField(max_length=32, choices=STATUSES, default="draft", db_index=True)

    class Meta:
        db_table = "spacs_policy_version"
        ordering = ["scheme", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "version_number"],
                name="spacs_scheme_version_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["scheme", "status"], name="spacs_pv_scheme_status_idx"),
            models.Index(fields=["effective_from", "effective_to"], name="spacs_pv_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.scheme.code} v{self.version_number} ({self.status})"


class ScholarshipApplication(TimeStampedModel):
    """Scholarship application or renewal lifecycle instance."""

    STATUSES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_verification", "Under Verification"),
        ("correction_required", "Correction Required"),
        ("resubmitted", "Resubmitted"),
        ("verified", "Verified / Routed for Decision"),
        ("verification_concern", "Verification Concern / Routed"),
        ("under_convener_review", "Under Convener Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    ]

    application_number = models.CharField(max_length=64, unique=True, db_index=True)
    student_user_id = models.IntegerField(db_index=True)  # IAM erp_user_id — NO FK

    scheme = models.ForeignKey(
        SchemeCatalogue,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    policy_version = models.ForeignKey(
        SchemePolicyVersion,
        on_delete=models.PROTECT,
        related_name="applications",
    )

    academic_cycle = models.CharField(max_length=32, db_index=True)  # e.g. "2026-27"
    is_renewal = models.BooleanField(default=False)
    prior_application_id = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=32, choices=STATUSES, default="draft", db_index=True)

    # Student submitted form payload
    application_data = models.JSONField(default=dict, blank=True)
    eligibility_snapshot = models.JSONField(default=dict, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    assigned_assistant_user_id = models.IntegerField(null=True, blank=True, db_index=True)

    # Verification stage (SPACS Assistant)
    verification_findings = models.JSONField(default=dict, blank=True)
    verification_concern_details = models.TextField(blank=True)
    correction_requested_reason = models.TextField(blank=True)
    correction_requested_at = models.DateTimeField(null=True, blank=True)
    resubmitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)

    # Decision stage (SPACS Convener)
    decision_outcome = models.CharField(max_length=32, blank=True)
    decision_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    # Withdrawal
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.TextField(blank=True)

    class Meta:
        db_table = "spacs_scholarship_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student_user_id", "status"], name="spacs_app_user_status_idx"),
            models.Index(fields=["scheme", "academic_cycle"], name="spacs_app_scheme_cycle_idx"),
            models.Index(fields=["assigned_assistant_user_id", "status"], name="spacs_app_asst_status_idx"),
            models.Index(fields=["status", "-submitted_at"], name="spacs_app_status_sub_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.application_number} ({self.student_user_id}, {self.status})"


class ApplicationDocument(TimeStampedModel):
    """Document evidence uploaded or reused for an application."""

    DOC_STATUSES = [
        ("pending", "Pending Verification"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    application = models.ForeignKey(
        ScholarshipApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    student_user_id = models.IntegerField(db_index=True)
    doc_type = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=200)
    file_url = models.CharField(max_length=500)
    valid_until = models.DateField(null=True, blank=True)

    is_reused = models.BooleanField(default=False)
    reused_from_doc_id = models.IntegerField(null=True, blank=True)

    verification_status = models.CharField(max_length=32, choices=DOC_STATUSES, default="pending")
    verification_notes = models.TextField(blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_application_document"
        ordering = ["application", "doc_type"]
        indexes = [
            models.Index(fields=["student_user_id", "doc_type"], name="spacs_doc_user_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.doc_type}: {self.title} (App {self.application_id})"


class ApplicationTransition(models.Model):
    """Append-only audit record of scholarship application status changes."""

    application = models.ForeignKey(
        ScholarshipApplication,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True)
    actor_role = models.CharField(max_length=64, blank=True)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_application_transition"
        ordering = ["at"]


class AwardCycle(TimeStampedModel):
    """One annual or convocation cycle of an award scheme (CW-SPACS-03)."""

    STATUSES = [
        ("open", "Award Cycle Open"),
        ("pool_prepared", "Candidate Pool Prepared"),
        ("under_evaluation", "Under Committee Evaluation"),
        ("result_recorded", "Committee Result Recorded"),
        ("awaiting_approval", "Awaiting Institutional Approval"),
        ("ready_for_publication", "Ready for Publication"),
        ("published", "Published"),
    ]

    scheme = models.ForeignKey(
        SchemeCatalogue,
        on_delete=models.PROTECT,
        related_name="award_cycles",
    )
    policy_version = models.ForeignKey(
        SchemePolicyVersion,
        on_delete=models.PROTECT,
        related_name="award_cycles",
    )
    academic_cycle = models.CharField(max_length=32, db_index=True)
    convocation_year = models.PositiveIntegerField(db_index=True)

    status = models.CharField(max_length=32, choices=STATUSES, default="open", db_index=True)

    evaluating_body = models.CharField(max_length=120)
    committee_members = models.JSONField(default=list, blank=True)

    approving_authority = models.CharField(max_length=120, blank=True)
    approval_reference = models.CharField(max_length=200, blank=True)
    approval_recorded_at = models.DateTimeField(null=True, blank=True)
    approval_recorded_by_user_id = models.IntegerField(null=True, blank=True)

    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_award_cycle"
        ordering = ["-convocation_year", "scheme"]
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "convocation_year"],
                name="spacs_award_cycle_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "convocation_year"], name="spacs_award_status_year_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.scheme.name} - Convocation {self.convocation_year} ({self.status})"


class AwardCandidate(TimeStampedModel):
    """Candidate shortlisted or evaluated in an award cycle."""

    RECOMMENDATION_CHOICES = [
        ("pending", "Pending"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]

    FINAL_OUTCOME_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Award Approved"),
        ("rejected", "Award Rejected"),
    ]

    award_cycle = models.ForeignKey(
        AwardCycle,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    student_user_id = models.IntegerField(db_index=True)
    source_method = models.CharField(max_length=32)

    cpi = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    discipline = models.CharField(max_length=32, blank=True)
    merit_data = models.JSONField(default=dict, blank=True)

    is_shortlisted = models.BooleanField(default=False)
    evaluation_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    evaluation_remarks = models.TextField(blank=True)

    recommendation_status = models.CharField(
        max_length=32, choices=RECOMMENDATION_CHOICES, default="pending"
    )
    final_outcome = models.CharField(
        max_length=32, choices=FINAL_OUTCOME_CHOICES, default="pending"
    )

    class Meta:
        db_table = "spacs_award_candidate"
        ordering = ["award_cycle", "-evaluation_score", "-cpi"]
        constraints = [
            models.UniqueConstraint(
                fields=["award_cycle", "student_user_id"],
                name="spacs_candidate_cycle_user_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["award_cycle", "final_outcome"], name="spacs_cand_cycle_outcome_idx"),
        ]

    def __str__(self) -> str:
        return f"Candidate {self.student_user_id} in {self.award_cycle_id}"


class AwardCycleTransition(models.Model):
    """Append-only audit record for award cycle transitions."""

    award_cycle = models.ForeignKey(
        AwardCycle,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True)
    actor_role = models.CharField(max_length=64, blank=True)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_award_cycle_transition"
        ordering = ["at"]


class SpacsNotification(models.Model):
    """In-app and email notifications for significant SPACS lifecycle events (CFR-SPACS-015, BR-SPACS-008)."""

    recipient_user_id = models.IntegerField(db_index=True)
    recipient_role = models.CharField(max_length=64, blank=True)
    event_type = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    reference_id = models.CharField(max_length=64, blank=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient_user_id", "is_read"], name="spacs_notif_user_read_idx"),
        ]


class SpacsAuditLog(models.Model):
    """Audit log for all significant SPACS actions (CFR-SPACS-016, BR-SPACS-021). Protected and restricted."""

    actor_user_id = models.IntegerField(null=True, db_index=True)
    actor_role = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=64, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="spacs_audit_entity_idx"),
            models.Index(fields=["action", "-timestamp"], name="spacs_audit_action_time_idx"),
        ]
