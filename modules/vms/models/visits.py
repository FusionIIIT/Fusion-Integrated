"""VMS Visit and Pass Models.
Institute people referenced by plain user_id integers, never foreign keys.
"""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.vms.models.visitors import Visitor


class Visit(TimeStampedModel):
    VISIT_TYPES = [
        ("pre_registered", "Pre-registered"),
        ("walk_in", "Walk-in"),
        ("vip", "VIP Visit"),
        ("contractor", "Contractor"),
    ]

    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("on_site", "On Site"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name="visits")
    host_user_id = models.IntegerField(db_index=True)
    purpose = models.CharField(max_length=255)
    visit_type = models.CharField(max_length=32, choices=VISIT_TYPES, default="pre_registered")
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="requested", db_index=True
    )

    pass_number = models.CharField(max_length=64, unique=True, db_index=True)
    qr_code_hash = models.CharField(max_length=64, unique=True, db_index=True)

    valid_from = models.DateTimeField(db_index=True)
    valid_to = models.DateTimeField(db_index=True)
    allowed_zones = models.JSONField(default=list)
    is_multi_entry = models.BooleanField(default=False)

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.IntegerField(null=True, blank=True)
    checked_out_by = models.IntegerField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "vms_visit"
        indexes = [
            models.Index(fields=["host_user_id", "status"], name="vms_v_host_stat_idx"),
            models.Index(fields=["status", "valid_to"], name="vms_v_stat_vto_idx"),
            models.Index(fields=["visitor", "status"], name="vms_v_vis_stat_idx"),
        ]

    def __str__(self) -> str:
        return f"Visit {self.pass_number} - {self.visitor.first_name} ({self.status})"
