"""Placement domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database. Recruiters are the exception:
they are local rows, scoped to one company.
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


# -- Interviews (PC-UC-009, PC-BR-011, PC-BR-012) ------------------------------
class InterviewRound(TimeStampedModel):
    """PC-BR-011: date, time slot and mode are all required."""

    KIND = [("test", "Written / online test"), ("gd", "Group discussion"),
            ("tech", "Technical interview"), ("hr", "HR interview"),
            ("other", "Other")]
    MODE = [("online", "Online"), ("offline", "Offline")]

    posting = models.ForeignKey("JobPosting", on_delete=models.CASCADE,
                                related_name="rounds")
    seq = models.PositiveSmallIntegerField(default=1)
    kind = models.CharField(max_length=12, choices=KIND, default="tech")
    mode = models.CharField(max_length=8, choices=MODE)          # required
    starts_at = models.DateTimeField()                           # date + time slot
    ends_at = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    meeting_url = models.URLField(blank=True)
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    instructions = models.TextField(blank=True)

    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    scheduled_by_recruiter = models.ForeignKey(
        "RecruiterAccount", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+")

    class Meta:
        db_table = "placement_interview_round"
        constraints = [
            models.UniqueConstraint(fields=["posting", "seq"],
                                    name="round_unique_seq_per_posting"),
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True)
                | Q(ends_at__gt=models.F("starts_at")),
                name="round_time_valid",
            ),
            # Online needs a link, offline needs a venue.
            models.CheckConstraint(
                condition=(Q(mode="online") & ~Q(meeting_url=""))
                | (Q(mode="offline") & ~Q(venue="")),
                name="round_has_a_location",
            ),
        ]
        indexes = [models.Index(fields=["posting", "seq"], name="round_posting_idx"),
                   models.Index(fields=["starts_at"], name="round_when_idx")]

    def __str__(self) -> str:
        return f"{self.posting_id} round {self.seq} ({self.kind})"


class RoundParticipation(TimeStampedModel):
    OUTCOME = [("pending", "Pending"), ("attended", "Attended"),
               ("absent", "Absent"), ("passed", "Passed"), ("failed", "Failed")]

    round = models.ForeignKey(InterviewRound, on_delete=models.CASCADE,
                              related_name="participants")
    application = models.ForeignKey("Application", on_delete=models.CASCADE,
                                    related_name="participations")
    outcome = models.CharField(max_length=12, choices=OUTCOME, default="pending")
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "placement_round_participation"
        constraints = [
            models.UniqueConstraint(fields=["round", "application"],
                                    name="participation_unique"),
        ]
        indexes = [models.Index(fields=["round", "outcome"],
                                name="participation_round_idx")]

    def __str__(self) -> str:
        return f"r{self.round_id} app{self.application_id} {self.outcome}"
