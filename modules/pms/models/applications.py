"""The application aggregate: the record, its versions, inventors, review cycles and appeals."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import appeals as ap
from modules.pms.domain import state_machine as sm
from modules.pms.models.base import AppendOnly, choices


class ReferenceCounter(models.Model):
    """One row per year, locked while a submission takes the next number (PMS-AFR-044)."""

    year = models.PositiveIntegerField(primary_key=True)
    last = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.year}: {self.last}"


class Application(TimeStampedModel):
    reference = models.CharField(max_length=20, blank=True, default="")
    applicant_user_id = models.IntegerField()
    title = models.CharField(max_length=300, blank=True)
    abstract = models.TextField(blank=True)
    description = models.TextField(blank=True)
    claims = models.TextField(blank=True)
    domain_code = models.CharField(max_length=40, blank=True)
    preferred_attorney_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=choices(sm.APPLICATION_STATUSES),
                              default=sm.DRAFT)
    version = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_on = models.DateField(null=True, blank=True)
    revision_due_on = models.DateField(null=True, blank=True)
    appeal_due_on = models.DateField(null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)
    grant_jurisdiction = models.CharField(max_length=5, blank=True)
    patent_number = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(status__in=sm.APPLICATION_STATUSES),
                                   name="pms_application_status_valid"),
            models.CheckConstraint(condition=Q(status=sm.DRAFT) | ~Q(reference=""),
                                   name="pms_application_reference_when_submitted"),
            models.UniqueConstraint(fields=["reference"], condition=~Q(reference=""),
                                    name="pms_application_reference_unique"),
            models.CheckConstraint(
                condition=~Q(status=sm.GRANTED) | (Q(grant_date__isnull=False)
                                                   & ~Q(patent_number="")),
                name="pms_application_granted_has_grant"),
        ]
        indexes = [
            models.Index(fields=["applicant_user_id", "-created_at"],
                         name="pms_app_applicant_idx"),
            models.Index(fields=["status", "-updated_at"], name="pms_app_status_idx"),
            models.Index(fields=["domain_code", "status"], name="pms_app_domain_status_idx"),
            models.Index(fields=["revision_due_on"], name="pms_app_revision_due_idx",
                         condition=Q(status__in=[sm.NEEDS_REVISION, sm.REJECTED])),
        ]

    def __str__(self):
        return self.reference or f"draft #{self.pk}"


class ApplicationVersion(AppendOnly):
    """The content as submitted, one row per submission (PMS-AFR-071)."""

    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="versions")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=300)
    abstract = models.TextField()
    description = models.TextField()
    claims = models.TextField()
    domain_code = models.CharField(max_length=40)
    created_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["application", "version"],
                                               name="pms_appversion_unique")]


class Inventor(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="inventors")
    user_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, blank=True)
    affiliation = models.CharField(max_length=200, blank=True)
    share_percent = models.DecimalField(max_digits=5, decimal_places=2)
    agreement_completed_at = models.DateTimeField(null=True, blank=True)
    agreement_reference = models.CharField(max_length=200, blank=True)
    consent_recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(share_percent__gt=0) & Q(share_percent__lte=100),
                                   name="pms_inventor_share_range"),
            models.UniqueConstraint(fields=["application", "user_id"],
                                    condition=Q(user_id__isnull=False),
                                    name="pms_inventor_user_once"),
        ]
        indexes = [models.Index(fields=["user_id"], name="pms_inventor_user_idx",
                                condition=Q(user_id__isnull=False))]


REVIEW_STATUSES = ("open", "decided", "reassigned", "closed")
DECISIONS = ("approve", "reject", "needs_revision")


class ReviewCycle(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="review_cycles")
    cycle_no = models.PositiveIntegerField()
    director_user_id = models.IntegerField()
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    assigned_on = models.DateField()
    due_on = models.DateField()
    status = models.CharField(max_length=12, choices=choices(REVIEW_STATUSES), default="open")
    decision = models.CharField(max_length=16, choices=choices(DECISIONS), blank=True)
    justification = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["application"], condition=Q(status="open"),
                                    name="pms_review_one_open"),
            models.UniqueConstraint(fields=["application", "cycle_no"],
                                    name="pms_review_cycle_unique"),
            models.CheckConstraint(
                condition=~Q(status="decided") | (~Q(decision="") & Q(decided_at__isnull=False)),
                name="pms_review_decided_complete"),
        ]
        indexes = [
            models.Index(fields=["director_user_id"], name="pms_review_director_open_idx",
                         condition=Q(status="open")),
            models.Index(fields=["due_on"], name="pms_review_due_idx",
                         condition=Q(status="open")),
            models.Index(fields=["director_user_id", "application"],
                         name="pms_review_director_idx"),
        ]


class RevisionResponse(AppendOnly):
    """The applicant's answer to one piece of feedback (BR-PMS-036)."""

    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="revision_responses")
    version = models.PositiveIntegerField()
    feedback_key = models.CharField(max_length=20)
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


APPEAL_STATUSES = (sm.APPEAL_OPEN, sm.APPEAL_DECIDED)


class Appeal(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="appeals")
    rejected_cycle = models.ForeignKey(ReviewCycle, on_delete=models.PROTECT,
                                       related_name="+")
    director_user_id = models.IntegerField(null=True, blank=True)
    grounds = models.TextField()
    justification = models.TextField()
    status = models.CharField(max_length=10, choices=choices(APPEAL_STATUSES),
                              default=sm.APPEAL_OPEN)
    outcome = models.CharField(max_length=10, choices=choices(ap.OUTCOMES), blank=True)
    modified_decision = models.CharField(max_length=16, choices=choices(ap.MODIFIED_DECISIONS),
                                         blank=True)
    outcome_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["application"], condition=Q(status="open"),
                                    name="pms_appeal_one_open"),
            models.CheckConstraint(condition=~Q(outcome="modify") | ~Q(modified_decision=""),
                                   name="pms_appeal_modify_has_decision"),
        ]
        indexes = [models.Index(fields=["director_user_id"], name="pms_appeal_director_idx",
                                condition=Q(status="open"))]


class Withdrawal(AppendOnly):
    application = models.OneToOneField(Application, on_delete=models.PROTECT,
                                       related_name="withdrawal")
    from_status = models.CharField(max_length=20)
    reason = models.TextField()
    withdrawn_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class WithdrawalConsent(AppendOnly):
    withdrawal = models.ForeignKey(Withdrawal, on_delete=models.PROTECT, related_name="consents")
    inventor = models.ForeignKey(Inventor, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
