"""Scholarship applications, documents, and state transitions for SPACS.

Enforces:
- CFR-SPACS-003, CFR-SPACS-004, CFR-SPACS-005, CFR-SPACS-006, CFR-SPACS-008
- BR-SPACS-002 (No duplicate active applications)
- BR-SPACS-003 (Document reuse)
- BR-SPACS-006 (Assistant verification is not final sanction)
- BR-SPACS-009 / BR-SPACS-010 (Withdrawal before final decision)
- BR-SPACS-016 (Document authenticity requires authorized verification)
- ADR-0013: Person references are plain integer user_ids, no cross-module foreign keys.
"""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.spacs.domain.state_machines import (
    APPLICATION_STATUSES,
    APP_STATUS_DRAFT,
    ACTIVE_APPLICATION_STATUSES,
)


class ScholarshipApplication(TimeStampedModel, UserScopedModel):
    """A student's scholarship or renewal application for an academic cycle."""

    application_number = models.CharField(max_length=40, unique=True, db_index=True)
    policy_version = models.ForeignKey(
        "CataloguePolicyVersion", on_delete=models.PROTECT, related_name="applications"
    )
    academic_cycle = models.CharField(max_length=20, db_index=True)  # e.g., "2026-27"
    status = models.CharField(
        max_length=32, choices=APPLICATION_STATUSES, default=APP_STATUS_DRAFT, db_index=True
    )

    # Renewal linkage (CFR-SPACS-012, BR-SPACS-017)
    is_renewal = models.BooleanField(default=False, db_index=True)
    prior_award = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="renewals"
    )
    renewal_cycle_number = models.PositiveSmallIntegerField(default=0)

    # Immutable snapshot of student academic/personal data frozen at submission
    applicant_snapshot = models.JSONField(
        default=dict, blank=True,
        help_text="Frozen copy of student CPI, programme, discipline, batch_year at submission"
    )
    submission_data = models.JSONField(
        default=dict, blank=True,
        help_text="Student-entered application responses and declarations"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Assistant Verification Findings (BR-SPACS-006, BR-SPACS-016)
    assigned_assistant_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    verification_findings = models.JSONField(default=dict, blank=True)
    verification_concern_note = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)

    # Convener Decision (BR-SPACS-018)
    decision_outcome = models.CharField(max_length=20, blank=True)  # approved, rejected, returned
    decision_reason = models.TextField(blank=True)
    decision_actor_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)

    # Student Withdrawal (BR-SPACS-009)
    withdrawn_reason = models.CharField(max_length=300, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="spacs_app_user_status_idx"),
            models.Index(fields=["policy_version", "status"], name="spacs_app_policy_status_idx"),
            models.Index(fields=["academic_cycle", "status"], name="spacs_app_cycle_status_idx"),
        ]
        constraints = [
            # BR-SPACS-002: One active/submitted application per student/scheme/cycle
            models.UniqueConstraint(
                fields=["policy_version", "user_id", "academic_cycle"],
                condition=models.Q(status__in=ACTIVE_APPLICATION_STATUSES),
                name="spacs_app_unique_active_per_cycle",
            )
        ]

    def __str__(self) -> str:
        return f"{self.application_number} (u{self.user_id} - {self.status})"


class ApplicationDocument(TimeStampedModel, UserScopedModel):
    """Supporting documentary evidence submitted for a scholarship application.

    Validated Drive links only (core.files.drive.parse).
    """

    VERIFICATION_STATUSES = [
        ("pending", "Pending Verification"),
        ("valid", "Verified Valid"),
        ("invalid", "Invalid Evidence"),
        ("suspicious", "Suspicious / Ineligible"),
    ]

    application = models.ForeignKey(
        ScholarshipApplication, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=60, db_index=True)
    title = models.CharField(max_length=150)
    drive_file_id = models.CharField(max_length=200)
    drive_url = models.URLField(max_length=500)
    declared_validity_date = models.DateField(null=True, blank=True)

    # Document reuse tracking (BR-SPACS-003)
    is_reused = models.BooleanField(default=False)
    reused_from_doc_id = models.IntegerField(null=True, blank=True)

    # Human verification findings (BR-SPACS-016)
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUSES, default="pending"
    )
    verification_comment = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "spacs_application_document"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.doc_type}: {self.title} (app #{self.application_id})"


class ApplicationTransition(models.Model):
    """Append-only audit of application lifecycle state changes (BR-SPACS-021)."""

    application = models.ForeignKey(
        ScholarshipApplication, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role_label = models.CharField(max_length=80)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_application_transition"
        ordering = ["at"]
        indexes = [
            models.Index(fields=["application", "at"], name="spacs_app_trans_idx")
        ]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.from_status} -> {self.to_status} at {self.at}"
