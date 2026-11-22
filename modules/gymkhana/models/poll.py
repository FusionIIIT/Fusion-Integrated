from django.db import models
from django.db.models import Q

from modules.gymkhana.models.club import Club


class Poll(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
    ]

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="polls",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_by_user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_poll"
        indexes = [
            models.Index(fields=["club", "status"], name="gymkhana_poll_club_stat_idx"),
            models.Index(fields=["status", "expires_at"], name="gymkhana_poll_stat_exp_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["active", "expired"]),
                name="gymkhana_poll_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Poll: {self.title} ({self.status})"


class PollChoice(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=200)

    class Meta:
        db_table = "gymkhana_poll_choice"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "text"],
                name="gymkhana_poll_choice_text_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.poll.title} - {self.text}"


class PollTarget(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="targets",
    )
    batch_year = models.IntegerField()
    discipline = models.CharField(max_length=50, blank=True, default="all")

    class Meta:
        db_table = "gymkhana_poll_target"
        indexes = [
            models.Index(fields=["poll", "batch_year"], name="gymkhana_polltarget_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "batch_year", "discipline"],
                name="gymkhana_polltarget_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"Target: batch {self.batch_year}, discipline {self.discipline}"


class PollVote(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    choice = models.ForeignKey(
        PollChoice,
        on_delete=models.PROTECT,
        related_name="votes",
    )
    student_id = models.BigIntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gymkhana_poll_vote"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "student_id"],
                name="gymkhana_pollvote_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"Vote: Poll {self.poll_id} by Student {self.student_id}"
