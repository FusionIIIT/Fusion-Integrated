"""Leave applications and an append-only transition log."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    KINDS = (("leave", "Leave"), ("extension", "Extension"),
             ("cancellation", "Cancellation"), ("offline", "Offline-sanctioned"))
    CATEGORIES = (("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
                  ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
                  ("COL", "Commuted Leave"), ("VL", "Vacation Leave"))
    HALVES = (("", "Full day"), ("first", "First half"), ("second", "Second half"))
    STATUSES = (
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting substitute response"),
        ("awaiting_unit_head", "Awaiting Unit Head review"),
        ("awaiting_establishment", "Awaiting Establishment routing"),
        ("awaiting_final_sanction", "Awaiting final sanction"),
        ("awaiting_director_self_sanction", "Awaiting Director self-sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancellation_pending", "Cancellation pending"),
        ("cancelled", "Cancelled"),
        ("awaiting_resumption", "Awaiting resumption"),
        ("awaiting_resumption_verification", "Awaiting resumption verification"),
        ("closed", "Closed"),
    )

    kind = models.CharField(max_length=16, choices=KINDS, default="leave")
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="children")
    category = models.CharField(max_length=4, choices=CATEGORIES)
    start_on = models.DateField()
    end_on = models.DateField()
    half = models.CharField(max_length=8, choices=HALVES, blank=True, default="")
    purpose = models.TextField()
    chargeable_days = models.DecimalField(max_digits=8, decimal_places=2)
    station_leave = models.BooleanField(default=False)
    station_details = models.TextField(blank=True)
    medical_evidence = models.BooleanField(default=False)
    medical_note = models.TextField(blank=True)

    status = models.CharField(max_length=40, choices=STATUSES, default="draft",
                              db_index=True)
    unit_code = models.CharField(max_length=80, blank=True, db_index=True)
    applicant_kind = models.CharField(max_length=16, blank=True)
    applicant_is_director = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, blank=True)
    unit_head_recommendation = models.CharField(max_length=24, blank=True)

    offline_reference = models.CharField(max_length=200, blank=True)
    resumption_on = models.DateField(null=True, blank=True)
    resumption_details = models.TextField(blank=True)
    actual_end_on = models.DateField(null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_status"),
            models.Index(fields=["status", "start_on"], name="leave_app_status_start"),
            models.Index(fields=["substitute_user_id", "status"],
                         name="leave_app_substitute"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_on__gte=models.F("start_on")),
                name="leave_application_date_order",
            ),
        ]


class LeaveTransition(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="history")
    frm = models.CharField(max_length=40)
    to = models.CharField(max_length=40)
    event = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_kind = models.CharField(max_length=32, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "leave_transition"
        indexes = [
            models.Index(fields=["application", "created_at"],
                         name="leave_transition_app"),
        ]
