# Competitive tender management and bid evaluation records (CFR-PSM-007, BR-PSM-023, PSM-UC-022).
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.psm.domain import state_machine as sm


class Tender(TimeStampedModel):
    STATUS = [(s, s.replace("_", " ").title()) for s in sm.TENDER_STATES]

    tender_number = models.CharField(max_length=32, unique=True)
    indent = models.ForeignKey("Indent", on_delete=models.PROTECT, related_name="tenders")
    title = models.CharField(max_length=200)
    scope = models.TextField()
    evaluation_criteria = models.TextField()
    submission_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS, default=sm.TENDER_DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    committee_members = models.JSONField(default=list, blank=True)
    committee_minutes = models.TextField(blank=True)
    awarded_vendor = models.ForeignKey(
        "Vendor", on_delete=models.PROTECT, null=True, blank=True, related_name="awarded_tenders"
    )
    awarded_by_user_id = models.IntegerField(null=True, blank=True)
    awarded_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "psm_tender"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="psm_tender_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.tender_number} ({self.status})"


class TenderBid(TimeStampedModel):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="bids")
    vendor = models.ForeignKey("Vendor", on_delete=models.PROTECT, related_name="bids")
    quoted_amount = models.DecimalField(max_digits=14, decimal_places=2)
    technical_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    financial_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    evaluation_notes = models.TextField(blank=True)
    is_selected = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "psm_tender_bid"
        ordering = ["quoted_amount", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tender", "vendor"], name="psm_tender_bid_unique_vendor"
            ),
            models.CheckConstraint(
                condition=Q(quoted_amount__gt=0), name="psm_tender_bid_amount_positive"
            ),
        ]
