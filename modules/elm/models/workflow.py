"""Configured leave routing and user-assigned approval tasks."""
from django.db import models
from django.db.models import Q


class LeaveAuthorityRule(models.Model):
    STAGE_CHOICES = (
        ("UNIT_HEAD", "Unit Head"),
        ("ESTABLISHMENT", "Establishment verification"),
        ("SANCTION", "Final sanction"),
    )
    DECISION_CHOICES = (
        ("RECOMMEND", "Recommendation"),
        ("VERIFY", "Verification"),
        ("FINAL", "Final decision"),
    )

    department = models.CharField(max_length=150)
    leave_type_code = models.CharField(max_length=3, blank=True, default="")
    applicant_role = models.CharField(max_length=64, blank=True, default="")
    for_director = models.BooleanField(default=False)
    step_order = models.PositiveSmallIntegerField()
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    decision_mode = models.CharField(max_length=12, choices=DECISION_CHOICES)
    approver_user_id = models.IntegerField(null=True, blank=True)
    is_self_sanction = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("department", "leave_type_code", "step_order")
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "department",
                    "leave_type_code",
                    "applicant_role",
                    "for_director",
                    "step_order",
                ),
                name="elm_authority_rule_route_step_uniq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_self_sanction=True, approver_user_id__isnull=True)
                    | Q(is_self_sanction=False, approver_user_id__isnull=False)
                ),
                name="elm_authority_rule_assignee_ck",
            ),
        ]

    def __str__(self):
        return (
            f"{self.department} {self.leave_type_code or 'all'} "
            f"{self.stage} step {self.step_order}"
        )


class LeaveApprovalTask(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("BLOCKED", "Waiting for prior step"),
        ("RECOMMENDED", "Recommended"),
        ("NOT_RECOMMENDED", "Not recommended"),
        ("VERIFIED", "Verified"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    request = models.ForeignKey(
        "elm.LeaveRequest", on_delete=models.PROTECT, related_name="approval_tasks"
    )
    rule = models.ForeignKey(
        LeaveAuthorityRule, on_delete=models.PROTECT, related_name="tasks"
    )
    step_order = models.PositiveSmallIntegerField()
    stage = models.CharField(max_length=20, choices=LeaveAuthorityRule.STAGE_CHOICES)
    decision_mode = models.CharField(
        max_length=12, choices=LeaveAuthorityRule.DECISION_CHOICES
    )
    assignee_user_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="BLOCKED"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("request_id", "step_order")
        constraints = [
            models.UniqueConstraint(
                fields=("request", "step_order"),
                name="elm_approval_task_request_step_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=("assignee_user_id", "status", "assigned_at"),
                name="elm_task_assignee_status_idx",
            )
        ]

    def __str__(self):
        return f"Leave #{self.request_id} {self.stage} for {self.assignee_user_id}"
