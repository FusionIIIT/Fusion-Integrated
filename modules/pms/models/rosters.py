"""Directors and panel attorneys PCC_ADMIN maintains, and attorney assignments (UC-PMS-010, 026)."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import state_machine as sm
from modules.pms.models.applications import Application
from modules.pms.models.base import choices


class _Roster(TimeStampedModel):
    """Effective-dated: a change ends the row and adds a new one, so history stays."""

    user_id = models.IntegerField()
    domain_codes = models.JSONField(default=list)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    added_by_user_id = models.IntegerField()
    ended_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        abstract = True


class DirectorProfile(_Roster):
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user_id"],
                                               condition=Q(valid_to__isnull=True),
                                               name="pms_director_one_active")]
        indexes = [models.Index(fields=["user_id", "-valid_from"], name="pms_director_user_idx")]


class PanelAttorney(_Roster):
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user_id"],
                                               condition=Q(valid_to__isnull=True),
                                               name="pms_panel_one_active")]
        indexes = [models.Index(fields=["user_id", "-valid_from"], name="pms_panel_user_idx")]


ASSIGNMENT_STATUSES = (sm.OFFERED, sm.ACCEPTED, sm.DECLINED, sm.CANCELLED)


class AttorneyAssignment(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="attorney_assignments")
    attorney_user_id = models.IntegerField()
    assigned_by_user_id = models.IntegerField()
    is_exception = models.BooleanField(default=False)
    exception_reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=choices(ASSIGNMENT_STATUSES),
                              default=sm.OFFERED)
    responded_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["application"],
                                    condition=Q(status__in=[sm.OFFERED, sm.ACCEPTED]),
                                    name="pms_assignment_one_live"),
            models.CheckConstraint(condition=Q(is_exception=False) | ~Q(exception_reason=""),
                                   name="pms_assignment_exception_has_reason"),
            models.CheckConstraint(condition=Q(status__in=ASSIGNMENT_STATUSES),
                                   name="pms_assignment_status_valid"),
        ]
        indexes = [models.Index(fields=["attorney_user_id"],
                                name="pms_assign_attorney_idx",
                                condition=Q(status__in=[sm.OFFERED, sm.ACCEPTED]))]
