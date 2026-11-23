"""The attorney's legal work and prior art (UC-PMS-004, 012, 033)."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import validation as v
from modules.pms.models.applications import Application
from modules.pms.models.base import AppendOnly, choices


class Assessment(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="assessments")
    attorney_user_id = models.IntegerField()
    analysis = models.TextField(blank=True)
    novelty = models.TextField(blank=True)
    non_obviousness = models.TextField(blank=True)
    utility = models.TextField(blank=True)
    recommendation = models.CharField(max_length=20, choices=choices(v.RECOMMENDATIONS),
                                      blank=True)
    status = models.CharField(max_length=8, choices=choices(("draft", "final")),
                              default="draft")
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=~Q(status="final") | (Q(recommendation__in=v.RECOMMENDATIONS)
                                            & Q(finalized_at__isnull=False)),
            name="pms_assessment_final_has_recommendation")]


class LegalRequest(AppendOnly):
    """PMS-AFR-086 / 087: information or extension requested of the applicant."""

    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="legal_requests")
    attorney_user_id = models.IntegerField()
    kind = models.CharField(max_length=12, choices=choices(("information", "extension")))
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class LegalAdvice(AppendOnly):
    """UC-PMS-033: advice at any stage; it changes no status."""

    application = models.ForeignKey(Application, on_delete=models.PROTECT,
                                    related_name="legal_advice")
    attorney_user_id = models.IntegerField()
    stage = models.CharField(max_length=20)
    advice = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class PriorArtSearch(AppendOnly):
    """PMS-AFR-147: every search session, kept for the audit trail."""

    actor_user_id = models.IntegerField()
    application = models.ForeignKey(Application, on_delete=models.PROTECT, null=True,
                                    blank=True, related_name="prior_art_searches")
    query = models.CharField(max_length=500)
    keywords = models.JSONField(default=list)
    classification_codes = models.JSONField(default=list)
    result_reference_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["actor_user_id", "-created_at"],
                                name="pms_search_actor_idx")]


class PriorArtReference(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="prior_art")
    kind = models.CharField(max_length=12, choices=choices(("patent", "publication")))
    title = models.CharField(max_length=500)
    identifier = models.CharField(max_length=120, blank=True)
    url = models.URLField(max_length=500, blank=True)
    source_name = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    added_by_user_id = models.IntegerField()
    search = models.ForeignKey(PriorArtSearch, on_delete=models.SET_NULL, null=True,
                               blank=True, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["application", "identifier"],
                                               condition=~Q(identifier=""),
                                               name="pms_reference_once")]
