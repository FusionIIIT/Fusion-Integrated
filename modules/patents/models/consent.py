from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import CoInventor


class CoInventorConsentToken(TimeStampedModel):
    """One-time consent token sent by email to an external co-inventor (R1 decision).

    Only the SHA-256 hash of the token is stored. The raw token is sent to the co-inventor's
    email address and is never shown to the applicant.
    """

    co_inventor = models.ForeignKey(
        CoInventor,
        on_delete=models.CASCADE,
        related_name="consent_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "patents_coinventor_consent_token"
