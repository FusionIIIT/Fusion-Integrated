from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import assistantship as asd
from modules.oap.domain import state_machines as sm


class AssistantshipClaim(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (sm.CLAIM_AWAITING_DUAL, "Awaiting dual supervisor verification"),
        (sm.CLAIM_AWAITING_OTHER, "Awaiting the other supervisor verification"),
        (sm.CLAIM_AWAITING_DEPT_REVIEW, "Awaiting department review"),
        (sm.CLAIM_AWAITING_HOD, "Awaiting HoD decision"),
        (sm.CLAIM_APPROVED, "Approved, awaiting stipend processing"),
        (sm.CLAIM_REJECTED, "Rejected"),
        (sm.CLAIM_STIPEND_PROCESSED, "Stipend processed"),
    ]

    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=sm.CLAIM_AWAITING_DUAL)
    thesis_supervisor_user_id = models.IntegerField()
    ta_supervisor_user_id = models.IntegerField()
    department_forwarded_by_user_id = models.IntegerField(null=True, blank=True)
    department_forwarded_at = models.DateTimeField(null=True, blank=True)
    hod_decided_by_user_id = models.IntegerField(null=True, blank=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    stipend_processed_by_user_id = models.IntegerField(null=True, blank=True)
    stipend_processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "oap_assistantship_claim"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["thesis_supervisor_user_id"]),
            models.Index(fields=["ta_supervisor_user_id"]),
        ]


class SupervisorVerification(TimeStampedModel):
    ROLE_CHOICES = [(r, r) for r in asd.SUPERVISOR_ROLES]

    claim = models.ForeignKey(
        AssistantshipClaim, on_delete=models.CASCADE, related_name="verifications"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    verified_by_user_id = models.IntegerField()
    verified_at = models.DateTimeField()

    class Meta:
        db_table = "oap_supervisor_verification"
        constraints = [
            models.UniqueConstraint(fields=["claim", "role"], name="oap_one_verification_per_role"),
        ]
