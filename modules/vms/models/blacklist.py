"""Blacklist, watchlist and safe-list models."""

from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class BlacklistEntry(TimeStampedModel):
    """Centralized blacklist / watchlist entry with temporary safe-list capabilities."""

    STATUS_CHOICES = [
        ("ACTIVE", "Active Blacklist"),
        ("SAFE_LISTED", "Temporarily Safe-Listed"),
        ("INACTIVE", "Inactive"),
    ]

    name = models.CharField(max_length=150, db_index=True)
    id_document_type = models.CharField(max_length=30)
    id_document_number = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="ACTIVE", db_index=True
    )
    safe_list_until = models.DateTimeField(null=True, blank=True)
    safe_list_reason = models.TextField(blank=True)
    safe_listed_by_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "id_document_number"]),
            models.Index(fields=["status", "phone"]),
        ]

    def __str__(self) -> str:
        return f"Blacklist: {self.name} ({self.id_document_number}) [{self.status}]"
