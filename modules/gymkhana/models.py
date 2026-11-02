from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.gymkhana.storage import GymkhanaFileStorage

_storage = GymkhanaFileStorage()


class Club(TimeStampedModel):
    class Category(models.TextChoices):
        TECHNICAL = "Technical", "Technical"
        SPORTS = "Sports", "Sports"
        CULTURAL = "Cultural", "Cultural"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CONFIRMED = "confirmed", "Confirmed"

    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=16, choices=Category.choices)
    coordinator_user_id = models.IntegerField()
    co_coordinator_user_id = models.IntegerField()
    faculty_councillor_user_id = models.IntegerField()
    description = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)

    class Meta:
        db_table = "gymkhana_club"
        indexes = [models.Index(fields=["status", "name"], name="gym_club_status_name")]

    def __str__(self):
        return self.name


class ClubSession(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="sessions")
    venue = models.CharField(max_length=160)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField()
    poster = models.FileField(storage=_storage, upload_to="sessions/", blank=True)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_session"
        indexes = [models.Index(fields=["venue", "date"], name="gym_session_venue_day")]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="gym_session_time_valid",
            ),
        ]


class ClubEvent(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="events")
    name = models.CharField(max_length=180)
    venue = models.CharField(max_length=160)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField()
    poster = models.FileField(storage=_storage, upload_to="events/", blank=True)
    faculty_user_id = models.IntegerField()
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_event"
        indexes = [models.Index(fields=["venue", "date"], name="gym_event_venue_day")]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="gym_event_time_valid",
            ),
        ]


class BookingLock(models.Model):
    venue = models.CharField(max_length=160)
    date = models.DateField()

    class Meta:
        db_table = "gymkhana_booking_lock"
        constraints = [
            models.UniqueConstraint(fields=["venue", "date"], name="gym_booking_lock_unique"),
        ]

    def __str__(self):
        return f"{self.venue} on {self.date}"


class MembershipApplication(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CONFIRMED = "confirmed", "Confirmed"

    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="applications")
    student_user_id = models.IntegerField()
    description = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    remarks = models.TextField(blank=True)
    approved_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["club", "student_user_id"], name="gym_membership_once_per_club",
            ),
        ]
        indexes = [models.Index(fields=["club", "status"], name="gym_member_club_status")]


class VotingPoll(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="polls")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    created_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gymkhana_poll"
        indexes = [models.Index(fields=["is_active", "expires_at"], name="gym_poll_active_exp")]


class PollTargetGroup(models.Model):
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name="target_groups")
    batch_year = models.PositiveSmallIntegerField()
    discipline = models.CharField(max_length=40)

    class Meta:
        db_table = "gymkhana_poll_group"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "batch_year", "discipline"], name="gym_poll_group_unique",
            ),
        ]

    def __str__(self):
        return f"{self.poll_id}: {self.batch_year}/{self.discipline}"


class PollChoice(models.Model):
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=180)

    class Meta:
        db_table = "gymkhana_poll_choice"
        constraints = [
            models.UniqueConstraint(fields=["poll", "text"], name="gym_poll_choice_unique"),
        ]

    def __str__(self):
        return self.text


class PollVote(TimeStampedModel):
    poll = models.ForeignKey(VotingPoll, on_delete=models.PROTECT, related_name="votes")
    choice = models.ForeignKey(PollChoice, on_delete=models.PROTECT, related_name="votes")
    student_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_poll_vote"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "student_user_id"], name="gym_poll_one_vote",
            ),
        ]


class BudgetRequest(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="budget_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.CharField(max_length=180)
    description = models.TextField()
    supporting_file = models.FileField(storage=_storage, upload_to="budgets/")
    created_by_user_id = models.IntegerField()
    status = models.CharField(max_length=12, default="open", editable=False)

    class Meta:
        db_table = "gymkhana_budget_request"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="gym_budget_nonnegative"),
        ]


class ClubEventReport(TimeStampedModel):
    club = models.ForeignKey(Club, on_delete=models.PROTECT, related_name="reports")
    student_incharge_user_id = models.IntegerField()
    event_name = models.CharField(max_length=180)
    event_at = models.DateTimeField()
    description = models.TextField()
    report_file = models.FileField(storage=_storage, upload_to="reports/")
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "gymkhana_event_report"
        indexes = [models.Index(fields=["club", "-created_at"], name="gym_report_club_date")]


class NotificationOutbox(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    topic = models.CharField(max_length=40)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "gymkhana_notification_outbox"
        indexes = [models.Index(fields=["status", "created_at"], name="gym_outbox_pending")]
