from django.db import models

from modules.oap.domain import assistantship as rules


class AssistantshipClaim(models.Model):
    student_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=80, choices=rules.STATE_CHOICES, default=rules.INITIAL_STATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    claim_period = models.CharField(max_length=20, blank=True)
    thesis_supervisor_id = models.IntegerField()
    ta_supervisor_id = models.IntegerField()
    department_reviewed_by_id = models.IntegerField(null=True, blank=True)
    decided_by_id = models.IntegerField(null=True, blank=True)
    stipend_processed_by_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_remark = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Assistantship #{self.pk} (student {self.student_id}) - {self.status}"


class SupervisorVerification(models.Model):
    claim = models.ForeignKey(
        AssistantshipClaim, on_delete=models.CASCADE, related_name="verifications"
    )
    role = models.CharField(max_length=30, choices=rules.ROLE_CHOICES)
    verified_by_id = models.IntegerField()
    remark = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "role"],
                name="oap_claim_one_verification_per_role",
            )
        ]

    def __str__(self):
        return f"{self.role} verification (claim {self.claim_id})"
