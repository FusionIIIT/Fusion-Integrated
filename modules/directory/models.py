"""A local projection of IAM's directory.

Kept for joins (you cannot ORDER BY a field that lives behind an HTTP call)
and for resilience while IAM is briefly down. A cache with a table, never a
source of truth — nothing here is edited by hand.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class UserRef(TimeStampedModel):
    KIND_CHOICES = [
        ("student", "Student"), ("faculty", "Faculty"),
        ("staff", "Staff"), ("operator", "Operator"),
    ]

    user_id = models.IntegerField(primary_key=True)     # IAM's id
    username = models.CharField(max_length=64, db_index=True)
    display_name = models.CharField(max_length=150)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, db_index=True)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=80, blank=True)
    programme = models.CharField(max_length=40, blank=True)
    discipline = models.CharField(max_length=40, blank=True, db_index=True)
    batch_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "directory_user_ref"
        indexes = [
            models.Index(fields=["kind", "discipline"], name="userref_kind_disc_idx"),
            models.Index(fields=["batch_year"], name="userref_batch_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} <{self.username}>"
