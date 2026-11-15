from uuid import uuid4

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class CatalogueEntry(TimeStampedModel):
    KIND = [
        ("scholarship", "Scholarship"),
        ("award", "Award"),
    ]

    kind = models.CharField(max_length=16, choices=KIND)

    class Meta:
        db_table = "spacs_catalogue_entry"
        ordering = ["id"]


class CatalogueVersion(TimeStampedModel):
    STATUS = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("retired", "Retired"),
    ]

    entry = models.ForeignKey(
        CatalogueEntry,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    approval_reference = models.CharField(max_length=255, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    application_opens_at = models.DateTimeField(null=True, blank=True)
    application_closes_at = models.DateTimeField(null=True, blank=True)
    renewal_opens_at = models.DateTimeField(null=True, blank=True)
    renewal_closes_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    retired_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_catalogue_version"
        ordering = ["entry_id", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "version_number"],
                name="spacs_catalogue_version_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(effective_from__isnull=True)
                    | Q(effective_to__isnull=True)
                    | Q(effective_to__gte=models.F("effective_from"))
                ),
                name="spacs_catalogue_effective_dates_ordered",
            ),
            models.CheckConstraint(
                condition=(
                    Q(application_opens_at__isnull=True)
                    | Q(application_closes_at__isnull=True)
                    | Q(application_closes_at__gte=models.F("application_opens_at"))
                ),
                name="spacs_catalogue_application_window_ordered",
            ),
            models.CheckConstraint(
                condition=(
                    Q(renewal_opens_at__isnull=True)
                    | Q(renewal_closes_at__isnull=True)
                    | Q(renewal_closes_at__gte=models.F("renewal_opens_at"))
                ),
                name="spacs_catalogue_renewal_window_ordered",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "effective_from", "effective_to"],
                name="spacs_catalog_status_idx",
            ),
        ]


class Application(TimeStampedModel, UserScopedModel):
    KIND = [
        ("scholarship", "Scholarship"),
        ("renewal", "Renewal"),
    ]

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    catalogue_version = models.ForeignKey(
        CatalogueVersion,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    kind = models.CharField(max_length=16, choices=KIND)
    academic_cycle = models.CharField(max_length=100)
    state = models.CharField(max_length=80)
    application_data = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    previous_application = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="renewals",
    )

    class Meta:
        db_table = "spacs_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user_id", "catalogue_version", "academic_cycle"],
                name="spacs_app_owner_cycle_idx",
            ),
            models.Index(fields=["state", "created_at"], name="spacs_app_state_idx"),
        ]


class ApplicationEvidence(TimeStampedModel):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    requirement_id = models.CharField(max_length=100)
    storage_reference = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    uploaded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_application_evidence"
        indexes = [
            models.Index(
                fields=["application", "requirement_id"],
                name="spacs_evidence_requirement_idx",
            ),
        ]


class ApplicationReview(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer_user_id = models.IntegerField()
    findings = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_application_review"
        ordering = ["at", "id"]
        indexes = [
            models.Index(
                fields=["application", "at"],
                name="spacs_review_application_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Review {self.pk} for {self.application_id}"


class ApplicationTransition(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_state = models.CharField(max_length=80)
    to_state = models.CharField(max_length=80)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_application_transition"
        ordering = ["at", "id"]
        indexes = [
            models.Index(
                fields=["application", "at"],
                name="spacs_transition_app_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_state} -> {self.to_state}"


class AwardCycle(TimeStampedModel):
    SOURCE_METHODS = [
        ("nomination", "Nomination"),
        ("invited", "Invited application"),
        ("manual", "Manual"),
    ]
    STATES = [
        ("Award Cycle Open", "Award Cycle Open"),
        ("Candidate Pool Prepared", "Candidate Pool Prepared"),
        ("Under Committee Evaluation", "Under Committee Evaluation"),
        ("Committee Result Recorded", "Committee Result Recorded"),
        ("Awaiting Institutional Approval", "Awaiting Institutional Approval"),
        ("Ready for Publication", "Ready for Publication"),
        ("Published", "Published"),
    ]
    OUTCOMES = [
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    catalogue_version = models.ForeignKey(
        CatalogueVersion,
        on_delete=models.PROTECT,
        related_name="award_cycles",
    )
    candidate_source = models.CharField(max_length=16, choices=SOURCE_METHODS)
    state = models.CharField(max_length=48, choices=STATES)
    outcome = models.CharField(max_length=16, choices=OUTCOMES, blank=True)
    approval_evidence = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_award_cycle"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["catalogue_version", "state"],
                name="spacs_award_cycle_state_idx",
            ),
        ]


class AwardCandidate(TimeStampedModel):
    cycle = models.ForeignKey(
        AwardCycle,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    user_id = models.IntegerField(db_index=True)
    source = models.CharField(max_length=16, choices=AwardCycle.SOURCE_METHODS)
    source_reference = models.JSONField(default=dict, blank=True)
    added_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_award_candidate"
        indexes = [
            models.Index(
                fields=["cycle", "user_id"],
                name="spacs_award_candidate_idx",
            ),
        ]


class AwardEvaluation(models.Model):
    candidate = models.ForeignKey(
        AwardCandidate,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    evaluator_user_id = models.IntegerField()
    evaluation_data = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_award_evaluation"
        ordering = ["at", "id"]
        indexes = [
            models.Index(
                fields=["candidate", "at"],
                name="spacs_award_evaluation_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Evaluation {self.pk} for candidate {self.candidate_id}"


class AwardCycleTransition(models.Model):
    cycle = models.ForeignKey(
        AwardCycle,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_state = models.CharField(max_length=48)
    to_state = models.CharField(max_length=48)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_award_cycle_transition"
        ordering = ["at", "id"]
        indexes = [
            models.Index(
                fields=["cycle", "at"],
                name="spacs_award_transition_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_state} -> {self.to_state}"


class WorkflowTask(TimeStampedModel):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_tasks",
    )
    award_cycle = models.ForeignKey(
        AwardCycle,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_tasks",
    )
    role_name = models.CharField(max_length=80)
    assigned_user_id = models.IntegerField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    closed_reason = models.TextField(blank=True)

    class Meta:
        db_table = "spacs_workflow_task"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(application__isnull=False, award_cycle__isnull=True)
                    | Q(application__isnull=True, award_cycle__isnull=False)
                ),
                name="spacs_task_one_subject",
            ),
        ]
        indexes = [
            models.Index(
                fields=["role_name", "assigned_user_id", "completed_at"],
                name="spacs_task_assignment_idx",
            ),
        ]


class NotificationOutbox(TimeStampedModel):
    CHANNELS = [
        ("email", "Email"),
        ("in_dashboard", "In dashboard"),
    ]
    STATUS = [
        ("pending", "Pending"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    topic = models.CharField(max_length=80)
    dedupe_key = models.CharField(max_length=200, unique=True)
    channel = models.CharField(max_length=16, choices=CHANNELS)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    recipient_role = models.CharField(max_length=80, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_notification_outbox"
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="spacs_notification_pending_idx",
            ),
            models.Index(
                fields=["recipient_user_id", "created_at"],
                name="spacs_notif_recipient_idx",
            ),
        ]


class AuditEvent(models.Model):
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.CharField(max_length=80)
    event_type = models.CharField(max_length=100)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_audit_event"
        ordering = ["at", "id"]
        indexes = [
            models.Index(
                fields=["aggregate_type", "aggregate_id", "at"],
                name="spacs_audit_aggregate_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.aggregate_type}:{self.aggregate_id})"
