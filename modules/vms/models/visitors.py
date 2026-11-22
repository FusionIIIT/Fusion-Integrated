"""VMS Visitor and Blacklist Models.
All timestamps UTC, indexed appropriately.
No cross-module foreign keys.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class Visitor(TimeStampedModel):
    ID_TYPES = [
        ("aadhaar", "Aadhaar Card"),
        ("passport", "Passport"),
        ("driving_license", "Driving License"),
        ("voter_id", "Voter ID"),
        ("other", "Other"),
    ]

    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    email = models.EmailField()
    phone = models.CharField(max_length=20, db_index=True)
    id_type = models.CharField(max_length=32, choices=ID_TYPES, default="aadhaar")
    id_number_hash = models.CharField(max_length=64, db_index=True)
    organization = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_visitor"
        indexes = [
            models.Index(fields=["id_number_hash"], name="vms_v_id_hash_idx"),
            models.Index(fields=["phone"], name="vms_v_phone_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.phone})"


class BlacklistEntry(TimeStampedModel):
    id_type = models.CharField(max_length=32, choices=Visitor.ID_TYPES, default="aadhaar")
    id_number_hash = models.CharField(max_length=64, db_index=True)
    full_name = models.CharField(max_length=128)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    reason = models.CharField(max_length=255)
    severity = models.CharField(max_length=32, default="critical")
    is_active = models.BooleanField(default=True)
    added_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_blacklist_entry"
        indexes = [
            models.Index(fields=["id_number_hash", "is_active"], name="vms_bl_hash_act_idx"),
            models.Index(fields=["phone", "is_active"], name="vms_bl_phone_act_idx"),
        ]

    def __str__(self) -> str:
        return f"Blacklist: {self.full_name} ({self.severity}) - {self.reason}"
