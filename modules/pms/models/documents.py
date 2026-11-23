"""Application documents and their versions (UC-PMS-019)."""
from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.pms.domain import documents as d
from modules.pms.models.applications import Application
from modules.pms.models.base import choices


class Document(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="documents")
    kind = models.CharField(max_length=20, choices=choices(d.KINDS))
    title = models.CharField(max_length=200)
    sensitivity = models.CharField(max_length=20, choices=choices(d.SENSITIVITIES))
    created_by_user_id = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(sensitivity__in=d.SENSITIVITIES),
                                   name="pms_document_sensitivity_valid"),
            models.CheckConstraint(condition=Q(kind__in=d.KINDS), name="pms_document_kind_valid"),
        ]


class DocumentVersion(models.Model):
    """The file bytes live under PMS_UPLOAD_ROOT; only a clean scan reaches this table."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=64, unique=True)
    original_name = models.CharField(max_length=120)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    scanner = models.CharField(max_length=60)
    uploaded_by_user_id = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["document", "number"],
                                    name="pms_docversion_number_unique"),
            models.UniqueConstraint(fields=["document"], condition=Q(is_current=True),
                                    name="pms_docversion_one_current"),
            models.CheckConstraint(condition=Q(size_bytes__gt=0) & Q(size_bytes__lt=d.MAX_BYTES),
                                   name="pms_docversion_size_range"),
        ]

    def __str__(self):
        return f"{self.document_id} v{self.number}"
