"""Licensing and technology-transfer requests (UC-PMS-020, 021)."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import licensing as lic
from modules.pms.domain import state_machine as sm
from modules.pms.models.applications import Application
from modules.pms.models.base import AppendOnly, choices

LICENSING_STATUSES = (sm.LICENSING_SUBMITTED, sm.LICENSING_ROUTED, sm.NEGOTIATING,
                      sm.AGREEMENT_RECORDED)


class LicensingRequest(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="licensing_requests")
    applicant_user_id = models.IntegerField()
    kind = models.CharField(max_length=20, choices=choices(lic.KINDS))
    summary = models.TextField()
    status = models.CharField(max_length=20, choices=choices(LICENSING_STATUSES),
                              default=sm.LICENSING_SUBMITTED)
    route_kind = models.CharField(max_length=10, blank=True)
    routed_director_user_id = models.IntegerField(null=True, blank=True)
    committee_name = models.CharField(max_length=200, blank=True)
    routed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=Q(status=sm.LICENSING_SUBMITTED) | ~Q(route_kind=""),
            name="pms_licensing_routed_has_target")]
        indexes = [
            models.Index(fields=["applicant_user_id", "-created_at"],
                         name="pms_licensing_applicant_idx"),
            models.Index(fields=["routed_director_user_id"], name="pms_licensing_director_idx"),
        ]


class NegotiationNote(AppendOnly):
    request = models.ForeignKey(LicensingRequest, on_delete=models.PROTECT,
                                related_name="notes")
    author_user_id = models.IntegerField()
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class LicenseAgreement(AppendOnly):
    request = models.OneToOneField(LicensingRequest, on_delete=models.PROTECT,
                                   related_name="agreement")
    counterparty = models.CharField(max_length=200)
    signed_on = models.DateField()
    terms_summary = models.TextField()
    financial_terms = models.TextField(blank=True)
    financial_sync = models.CharField(max_length=30, default=lic.NOT_SHARED)
    recorded_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
