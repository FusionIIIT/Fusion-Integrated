from django.db import models

from core.db.mixins import TimeStampedModel


class DocumentType(models.TextChoices):
    PROVISIONAL_SPEC = "provisional_spec", "Provisional Patent Specification"
    COMPLETE_SPEC = "complete_spec", "Complete Patent Specification"
    CLAIMS = "claims", "Patent Claims Document"
    DRAWINGS = "drawings", "Formal Patent Drawings"
    INVENTOR_AGREEMENT = "inventor_agreement", "Executed Co-Inventor Agreement"
    FORM_1_APPLICATION = "form_1", "Patent Office Form 1"
    FORM_2_SPECIFICATION = "form_2", "Patent Office Form 2"
    FORM_3_UNDERTAKING = "form_3", "Patent Office Form 3 (Statement & Undertaking)"
    FER_REPLY_LEGAL = "fer_reply", "FER Legal & Technical Response"
    GRANT_CERTIFICATE = "grant_certificate", "Official Letters Patent Certificate"
    LEGAL_ADVICE_MEMO = "legal_advice", "Attorney Legal Advice Memorandum"


class PatentDocumentVersion(TimeStampedModel):
    """Versioned patent documentation linked to verified external Google Drive references."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=32, choices=DocumentType.choices)
    version_number = models.IntegerField(default=1)
    title = models.CharField(max_length=256)
    drive_link = models.URLField(max_length=1024)
    file_size_bytes = models.BigIntegerField(default=0)
    uploaded_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "pms_document_version"
        ordering = ["-version_number"]

    def __str__(self) -> str:
        return f"{self.title} (v{self.version_number})"
