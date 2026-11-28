"""Polls, their choices, audience and votes (BW-GYM-02)."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.gymkhana.models.clubs import Club


class Poll(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="polls")
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=4000)
    expires_on = models.DateField()
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_poll"
        indexes = [
            models.Index(fields=["club", "expires_on"], name="gym_poll_club_expiry_idx"),
            models.Index(fields=["expires_on"], name="gym_poll_expiry_idx"),
        ]


class PollChoice(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.PROTECT, related_name="choices")
    label = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "gymkhana_poll_choice"
        constraints = [
            models.UniqueConstraint(fields=["poll", "position"],
                                    name="gym_choice_position_unique"),
        ]

    def __str__(self) -> str:
        return self.label

class PollTarget(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.PROTECT, related_name="targets")
    batch_year = models.PositiveSmallIntegerField()
    # Empty means every branch of the batch.
    discipline = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = "gymkhana_poll_target"
        constraints = [
            models.UniqueConstraint(fields=["poll", "batch_year", "discipline"],
                                    name="gym_target_unique"),
        ]
        indexes = [
            models.Index(fields=["batch_year", "discipline"],
                         name="gym_target_cohort_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.batch_year} {self.discipline or 'all branches'}"

class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.PROTECT, related_name="votes")
    choice = models.ForeignKey(PollChoice, on_delete=models.PROTECT, related_name="votes")
    user_id = models.IntegerField()
    cast_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_vote"
        constraints = [
            # BR-GYM-015
            models.UniqueConstraint(fields=["poll", "user_id"],
                                    name="gym_vote_one_per_student"),
        ]
        indexes = [
            models.Index(fields=["choice"], name="gym_vote_choice_idx"),
        ]

    def __str__(self) -> str:
        return f"vote {self.pk} in poll {self.poll_id}"
