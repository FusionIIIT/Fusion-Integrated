"""Voting poll models for Gymkhana."""

from __future__ import annotations

from django.db import models
from django.db.models import UniqueConstraint

from modules.gymkhana.domain.constants import (
    POLL_STATUS_ACTIVE,
)
from modules.gymkhana.models.club import Club


class Poll(models.Model):
    """Voting poll entity."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="polls")
    created_by_id = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, default=POLL_STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_poll"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"


class PollTargetGroup(models.Model):
    """Target audience batch and branch for poll eligibility."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="target_groups")
    batch = models.CharField(max_length=20)
    branch = models.CharField(max_length=50)

    class Meta:
        db_table = "gymkhana_poll_target_group"
        constraints = [
            UniqueConstraint(
                fields=["poll", "batch", "branch"],
                name="unique_poll_target_group",
            ),
        ]

    def __str__(self) -> str:
        return f"Target(poll_id={self.poll_id}, batch={self.batch}, branch={self.branch})"


class PollChoice(models.Model):
    """Choice in a voting poll."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="choices")
    choice_text = models.CharField(max_length=200)
    vote_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "gymkhana_poll_choice"
        constraints = [
            UniqueConstraint(
                fields=["poll", "choice_text"],
                name="unique_choice_per_poll",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.choice_text} ({self.vote_count} votes)"


class PollVote(models.Model):
    """Record of a student casting a vote in a poll (one vote per student)."""

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    student_id = models.IntegerField()
    choice = models.ForeignKey(PollChoice, on_delete=models.CASCADE, related_name="cast_votes")
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_poll_vote"
        constraints = [
            UniqueConstraint(
                fields=["poll", "student_id"],
                name="unique_student_vote_per_poll",
            ),
        ]

    def __str__(self) -> str:
        return f"Vote(poll_id={self.poll_id}, student_id={self.student_id})"
