"""Placement domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


# -- Postings ------------------------------------------------------------------
class JobPosting(TimeStampedModel):
    """An opportunity. PC-BR-003 requires a description, criteria and a
    deadline before publishing, enforced by a database constraint."""

    STATUS = [("draft", "Draft"), ("pending_approval", "Pending TPO approval"),
              ("published", "Published"), ("closed", "Applications closed"),
              ("in_progress", "Selection in progress"),
              ("completed", "Completed"), ("cancelled", "Cancelled")]
    KIND = [("fte", "Full time"), ("internship", "Internship"),
            ("ppo", "Pre-placement offer")]

    company = models.ForeignKey("Company", on_delete=models.PROTECT,
                                related_name="postings")
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=12, choices=KIND, default="fte")
    season = models.CharField(max_length=32)
    tier = models.CharField(max_length=10, choices=[("dream", "Dream"), ("core", "Core"), ("open", "Open")], default="open")
    description = models.TextField(blank=True)          # PC-BR-003 role description
    location = models.CharField(max_length=120, blank=True)
    compensation_ctc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_cpi = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    eligible_batches = models.JSONField(default=list)
    eligible_branches = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    deadline = models.DateTimeField(null=True, blank=True)   # PC-BR-003 deadline

    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_by_recruiter = models.ForeignKey(
        "RecruiterAccount", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="postings_created")

    class Meta:
        db_table = "placement_job_posting"
        indexes = [
            models.Index(fields=["status", "deadline"],
                         name="posting_status_deadline_idx"),
            models.Index(fields=["company", "season"],
                         name="posting_company_season_idx"),
        ]
        constraints = [
            # PC-BR-002: publishing freezes the rule under applicants.
            models.CheckConstraint(
                condition=~Q(status="published")
                | Q(eligibility_rule_locked_at__isnull=False),
                name="posting_published_has_locked_rule",
            ),
            # PC-BR-003.
            models.CheckConstraint(
                condition=~Q(status="published")
                | (~Q(description="") & Q(deadline__isnull=False)),
                name="posting_published_has_required_content",
            ),
            models.CheckConstraint(
                condition=Q(deadline__isnull=True) | Q(deadline__gt=models.F("opens_at")),
                name="posting_window_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} @ {self.company_id}"
