from django.db import models
from django.db.models import Index, UniqueConstraint

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.club import Club


class VotingPoll(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="polls")
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    target_batches = models.JSONField(default=list)
    target_branches = models.JSONField(default=list)
    expires_at = models.DateTimeField(db_index=True)
    created_by_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "gymkhana_poll"
        indexes = [
            Index(fields=["club", "expires_at"], name="gym_poll_club_exp_idx"),
        ]


class PollChoice(TimeStampedModel):
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=200)
    votes_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "gymkhana_poll_choice"
        indexes = [
            Index(fields=["poll"], name="gym_choice_poll_idx"),
        ]


class PollVote(TimeStampedModel):
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name="votes")
    choice = models.ForeignKey(PollChoice, on_delete=models.CASCADE, related_name="votes")
    student_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "gymkhana_poll_vote"
        constraints = [
            UniqueConstraint(
                fields=["poll", "student_id"],
                name="gymkhana_unique_student_poll_vote",
            ),
        ]
