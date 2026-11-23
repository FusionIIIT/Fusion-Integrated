"""Filings, patent-office communications, office actions and maintenance cycles."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import state_machine as sm
from modules.pms.models.applications import Application
from modules.pms.models.base import AppendOnly, choices


class Filing(AppendOnly):
    """PMS-AFR-104: recorded only with the office's id, date and confirmation."""

    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="filings")
    jurisdiction = models.CharField(max_length=5)
    office_name = models.CharField(max_length=120)
    international_justification = models.TextField(blank=True)
    external_filing_id = models.CharField(max_length=64)
    filing_date = models.DateField()
    confirmation_reference = models.CharField(max_length=200)
    format_validation = models.CharField(max_length=30)
    filed_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(jurisdiction="IN") | ~Q(international_justification=""),
                name="pms_filing_international_justified"),
            models.UniqueConstraint(fields=["jurisdiction", "external_filing_id"],
                                    name="pms_filing_external_id"),
            models.CheckConstraint(condition=~Q(confirmation_reference=""),
                                   name="pms_filing_confirmed"),
        ]


COMMUNICATION_KINDS = ("office_action", "grant", "refusal", "other")


class Communication(AppendOnly):
    """PMS-AFR-106: official patent-office communication, as received."""

    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="communications")
    kind = models.CharField(max_length=16, choices=choices(COMMUNICATION_KINDS))
    received_on = models.DateField()
    reference = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


OA_STATUSES = (sm.RECORDED, sm.AWAITING_APPLICANT, sm.APPLICANT_APPROVED, sm.RESPONSE_READY,
               sm.RESPONSE_SUBMITTED)


class OfficeAction(TimeStampedModel):
    communication = models.OneToOneField(Communication, on_delete=models.PROTECT,
                                         related_name="office_action")
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="office_actions")
    response_due_on = models.DateField(null=True, blank=True)
    requires_applicant_review = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=choices(OA_STATUSES), default=sm.RECORDED)
    draft_response = models.TextField(blank=True)
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    submitted_on = models.DateField(null=True, blank=True)
    submission_reference = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(status=sm.RESPONSE_SUBMITTED) | (Q(submitted_on__isnull=False)
                                                             & ~Q(submission_reference="")),
                name="pms_oa_submitted_complete"),
            models.CheckConstraint(condition=Q(status__in=OA_STATUSES),
                                   name="pms_oa_status_valid"),
        ]
        indexes = [models.Index(fields=["response_due_on"], name="pms_oa_due_idx",
                                condition=~Q(status=sm.RESPONSE_SUBMITTED))]


class OfficeActionExtension(AppendOnly):
    office_action = models.ForeignKey(OfficeAction, on_delete=models.PROTECT,
                                      related_name="extensions")
    previous_due_on = models.DateField(null=True, blank=True)
    new_due_on = models.DateField()
    reason = models.TextField()
    recorded_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


CYCLE_STATUSES = (sm.SCHEDULED, sm.DECISION_REQUESTED, sm.RENEW_APPROVED, sm.DO_NOT_RENEW,
                  sm.RENEWED)


class MaintenanceCycle(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="maintenance_cycles")
    seq = models.PositiveIntegerField()
    due_on = models.DateField()
    source = models.CharField(max_length=10, choices=choices(("schedule", "manual")))
    status = models.CharField(max_length=20, choices=choices(CYCLE_STATUSES),
                              default=sm.SCHEDULED)
    deciding_director_user_id = models.IntegerField(null=True, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    action_reference = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actioned_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["application", "seq"], name="pms_cycle_seq_unique"),
            models.UniqueConstraint(fields=["application"],
                                    condition=Q(status__in=sorted(sm.LIVE_CYCLE)),
                                    name="pms_maintenance_one_live"),
            models.CheckConstraint(
                condition=~Q(status=sm.RENEWED) | (~Q(action_reference="")
                                                   & Q(actioned_on__isnull=False)),
                name="pms_cycle_renewed_complete"),
        ]
        indexes = [
            models.Index(fields=["due_on"], name="pms_cycle_due_idx",
                         condition=Q(status__in=sorted(sm.LIVE_CYCLE))),
            models.Index(fields=["deciding_director_user_id"], name="pms_cycle_director_idx",
                         condition=Q(status=sm.DECISION_REQUESTED)),
        ]
