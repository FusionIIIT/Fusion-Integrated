"""Placement domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


# -- Offers and placement records (PC-UC-005, PC-BR-013/014/015) ---------------
class Offer(TimeStampedModel, UserScopedModel):
    STATUS = [("issued", "Issued"), ("accepted", "Accepted"),
              ("declined", "Declined"), ("revoked", "Revoked"),
              ("superseded", "Superseded"), ("expired", "Expired")]

    application = models.OneToOneField("Application", on_delete=models.PROTECT,
                                       related_name="offer")
    posting = models.ForeignKey("JobPosting", on_delete=models.PROTECT,
                                related_name="offers")
    ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tier_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    is_dream = models.BooleanField(default=False)

    status = models.CharField(max_length=12, choices=STATUS, default="issued")
    respond_by = models.DateTimeField()                # PC-BR-013, always set
    responded_at = models.DateTimeField(null=True, blank=True)

    # Machine-readable justification, so an appeal has a reason.
    policy_decision = models.JSONField(default=dict, blank=True)

    issued_by_user_id = models.IntegerField(null=True, blank=True)
    issued_by_recruiter = models.ForeignKey(
        "RecruiterAccount", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+")
    letter = models.ForeignKey("ProfileDocument", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="+")

    class Meta:
        db_table = "placement_offer"
        indexes = [
            models.Index(fields=["user_id", "status"], name="offer_user_idx"),
            models.Index(fields=["posting", "status"], name="offer_posting_idx"),
            models.Index(fields=["status", "respond_by"], name="offer_expiry_idx"),
        ]

    def __str__(self) -> str:
        return f"offer#{self.pk} u{self.user_id} {self.status}"


class PlacementRecord(TimeStampedModel, UserScopedModel):
    """Written when an offer is accepted (PC-BR-014).

    The partial unique index is the backstop: even bypassing the service, a
    student cannot hold two active placements in one season.
    """

    SOURCE = [("campus", "Through the Placement Cell"),
              ("off_campus", "Off campus (rules 5 and 24)")]

    policy = models.ForeignKey("PlacementPolicy", on_delete=models.PROTECT,
                               related_name="records")
    # Null off-campus: rules 5 and 24 cover placements that had no posting here.
    offer = models.OneToOneField(Offer, on_delete=models.PROTECT,
                                 related_name="record", null=True, blank=True)
    posting = models.ForeignKey("JobPosting", on_delete=models.PROTECT,
                                related_name="records", null=True, blank=True)
    source = models.CharField(max_length=12, choices=SOURCE, default="campus")
    company = models.ForeignKey("Company", on_delete=models.PROTECT,
                                related_name="records")
    ctc_lpa = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    kind = models.CharField(max_length=12, default="fte")
    is_active = models.BooleanField(default=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    # Rule 24: the no-dues certificate is withheld until this is submitted.
    offer_letter = models.ForeignKey("ProfileDocument", on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name="offer_letter_for")
    offer_letter_submitted_at = models.DateTimeField(null=True, blank=True)

    # Rule 22: declaring it does not release the letter obligation.
    not_joining_declared_at = models.DateTimeField(null=True, blank=True)
    not_joining_reason = models.CharField(max_length=300, blank=True)
    not_joining_was_late = models.BooleanField(default=False)

    class Meta:
        db_table = "placement_record"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "policy"], condition=Q(is_active=True),
                name="one_active_placement_per_student_per_season",
            ),
            # Both null on a campus record would make the source field a lie.
            models.CheckConstraint(
                condition=(
                    Q(source="campus", offer__isnull=False, posting__isnull=False)
                    | Q(source="off_campus", offer__isnull=True,
                        posting__isnull=True)
                ),
                name="record_source_matches_its_origin",
            ),
        ]
        indexes = [
            models.Index(fields=["policy", "company"], name="record_season_idx"),
            models.Index(fields=["user_id", "is_active"], name="record_user_idx"),
        ]

    def __str__(self) -> str:
        return f"placed u{self.user_id} @{self.company_id}"
