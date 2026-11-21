"""Gymkhana module models.

Entities:
- Club (UC-GYM-001, UC-GYM-011): clubs with category, leadership, faculty councillor, status lifecycle.
- ClubMembership (UC-GYM-004, UC-GYM-005): student membership applications with open/confirmed status.
- ClubSession (UC-GYM-002): venue-booked club sessions with cross-type conflict detection.
- ClubEvent (UC-GYM-003): venue-booked club events with cross-type conflict detection.
- VotingPoll + PollChoice + PollVote (UC-GYM-006, UC-GYM-007): polls with targeting, min-2-choices, one-vote-per-student.
- ClubBudgetRequest (UC-GYM-009): budget requests with non-negative amount and file.
- ClubEventReport (UC-GYM-010, UC-GYM-012): event reports with required file, faculty review.
- GymkhanaWorkflowHistory: audit log for all state transitions.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


# ---------------------------------------------------------------------------
# Club
# ---------------------------------------------------------------------------

class Club(models.Model):
    """A student club governed by Gymkhana (BR-GYM-001 to BR-GYM-004)."""

    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('sports', 'Sports'),
        ('cultural', 'Cultural'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('confirmed', 'Confirmed'),
    ]

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    # Coordinator and co-coordinator must be valid students (BR-GYM-001)
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='coordinated_clubs',
    )
    co_coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='co_coordinated_clubs',
    )
    # Faculty councillor must be valid faculty (BR-GYM-002)
    faculty_councillor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='councillor_clubs',
    )
    # BR-GYM-004: new club is open; Student Admin approval → confirmed
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.status})"

    def confirm(self):
        """UC-GYM-011 / BW-GYM-03: Student Admin approves an open club → confirmed."""
        if self.status != 'open':
            raise ValidationError("Only open clubs can be confirmed.")
        self.status = 'confirmed'
        self.save()

    def is_head(self, user):
        """Return True if user is coordinator or co-coordinator (BR-GYM-010)."""
        return user.pk in (self.coordinator_id, self.co_coordinator_id)


# ---------------------------------------------------------------------------
# Club Membership
# ---------------------------------------------------------------------------

class ClubMembership(models.Model):
    """Student membership application for a confirmed club (BW-GYM-01)."""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('confirmed', 'Confirmed'),
    ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='memberships')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_memberships',
    )
    achievements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # BR-GYM-009: No duplicate same-club application
        unique_together = [('club', 'student')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student} → {self.club} ({self.status})"

    def clean(self):
        # BR-GYM-007: only confirmed clubs accept applications
        if self.club_id and self.club.status != 'confirmed':
            raise ValidationError("Membership applications are only allowed for confirmed clubs.")


# ---------------------------------------------------------------------------
# Venue (configurable venues for bookings - BR-GYM-020)
# ---------------------------------------------------------------------------

class Venue(models.Model):
    """Venues configured for Gymkhana session/event booking (BR-GYM-020)."""
    name = models.CharField(max_length=200, unique=True)
    capacity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Club Session
# ---------------------------------------------------------------------------

class ClubSession(models.Model):
    """A session booked in a venue by a Club Head (UC-GYM-002)."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='sessions')
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name='sessions')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)
    poster = models.FileField(upload_to='gymkhana/session_posters/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sessions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.club} session @ {self.venue} on {self.date}"

    def clean(self):
        # BR-GYM-005: start_time must be before end_time
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(
                "Session start time must be before end time."
            )
        # BR-GYM-006: cross-type conflict detection
        if self.venue_id and self.date and self.start_time and self.end_time:
            _check_venue_conflict(
                venue_id=self.venue_id,
                date=self.date,
                start_time=self.start_time,
                end_time=self.end_time,
                exclude_session_pk=self.pk,
            )


# ---------------------------------------------------------------------------
# Club Event
# ---------------------------------------------------------------------------

class ClubEvent(models.Model):
    """An event booked in a venue by a Club Head (UC-GYM-003)."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=200)
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name='events')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)
    poster = models.FileField(upload_to='gymkhana/event_posters/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_events',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.name} @ {self.venue} on {self.date}"

    def clean(self):
        # BR-GYM-005: start_time must be before end_time
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Event start time must be before end time.")
        # BR-GYM-006: cross-type conflict detection
        if self.venue_id and self.date and self.start_time and self.end_time:
            _check_venue_conflict(
                venue_id=self.venue_id,
                date=self.date,
                start_time=self.start_time,
                end_time=self.end_time,
                exclude_event_pk=self.pk,
            )


# ---------------------------------------------------------------------------
# Cross-type venue conflict helper (BR-GYM-006)
# ---------------------------------------------------------------------------

def _check_venue_conflict(
    venue_id, date, start_time, end_time,
    exclude_session_pk=None, exclude_event_pk=None,
):
    """Raise ValidationError if a session-session, event-event, or session-event
    overlap exists for the same venue on the same date.
    """
    from django.db.models import Q

    overlap = Q(start_time__lt=end_time, end_time__gt=start_time)

    session_qs = ClubSession.objects.filter(venue_id=venue_id, date=date).filter(overlap)
    if exclude_session_pk is not None:
        session_qs = session_qs.exclude(pk=exclude_session_pk)
    if session_qs.exists():
        raise ValidationError(
            "This time slot conflicts with an existing session at the same venue on the same date."
        )

    event_qs = ClubEvent.objects.filter(venue_id=venue_id, date=date).filter(overlap)
    if exclude_event_pk is not None:
        event_qs = event_qs.exclude(pk=exclude_event_pk)
    if event_qs.exists():
        raise ValidationError(
            "This time slot conflicts with an existing event at the same venue on the same date."
        )


# ---------------------------------------------------------------------------
# Voting Poll
# ---------------------------------------------------------------------------

class VotingPoll(models.Model):
    """A targeted poll created by a Club Head (UC-GYM-006)."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='polls')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    expiry_date = models.DateField()
    # Target audience: JSON list of {batch, branch} dicts (BR-GYM-013)
    target_batches = models.JSONField(default=list, blank=True)
    target_branches = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_polls',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        from django.utils import timezone
        import datetime
        today = timezone.now().date() if timezone.is_aware(timezone.now()) else datetime.date.today()
        return today <= self.expiry_date


class PollChoice(models.Model):
    """A choice in a voting poll (BR-GYM-012: minimum 2 choices)."""
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    vote_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.poll} — {self.text}"


class PollVote(models.Model):
    """One vote per student per poll (BR-GYM-015)."""
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name='votes')
    choice = models.ForeignKey(PollChoice, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='poll_votes',
    )
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('poll', 'voter')]  # BR-GYM-015

    def __str__(self):
        return f"{self.voter} voted in {self.poll}"


# ---------------------------------------------------------------------------
# Club Budget Request
# ---------------------------------------------------------------------------

class ClubBudgetRequest(models.Model):
    """Budget request submitted by Club Head for tracking (UC-GYM-009)."""

    STATUS_CHOICES = [
        ('open', 'Open'),
    ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='budget_requests')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='budget_requests',
    )
    purpose = models.CharField(max_length=300)
    # BR-GYM-017: non-negative; DecimalField (never FloatField)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    # BR-GYM-018: required supporting file
    supporting_file = models.FileField(upload_to='gymkhana/budget_docs/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.club} budget — {self.purpose} ({self.amount})"

    def clean(self):
        # BR-GYM-017: amount must be non-negative
        if self.amount is not None and self.amount < Decimal('0'):
            raise ValidationError({'amount': "Budget amount must be zero or greater."})


# ---------------------------------------------------------------------------
# Club Event Report
# ---------------------------------------------------------------------------

class ClubEventReport(models.Model):
    """Event report submitted by Club Head; reviewed by Faculty Councillor (UC-GYM-010, UC-GYM-012)."""

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='event_reports')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_event_reports',
    )
    student_incharge = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incharge_event_reports',
    )
    event_name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    event_date = models.DateField()
    # BR-GYM-019: required report file
    report_file = models.FileField(upload_to='gymkhana/event_reports/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.club} — {self.event_name} on {self.event_date}"


# ---------------------------------------------------------------------------
# Gymkhana Workflow History (audit log for state transitions)
# ---------------------------------------------------------------------------

class GymkhanaWorkflowHistory(models.Model):
    """Captures all state transitions across Gymkhana entities."""

    ENTITY_CHOICES = [
        ('club', 'Club'),
        ('membership', 'Club Membership'),
        ('session', 'Club Session'),
        ('event', 'Club Event'),
        ('poll', 'Voting Poll'),
        ('budget_request', 'Budget Request'),
        ('event_report', 'Event Report'),
    ]

    entity_type = models.CharField(max_length=30, choices=ENTITY_CHOICES)
    entity_id = models.PositiveIntegerField()
    from_state = models.CharField(max_length=50)
    to_state = models.CharField(max_length=50)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gymkhana_workflow_actions',
    )
    action_taken = models.CharField(max_length=100)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f"{self.entity_type}#{self.entity_id}: "
            f"{self.from_state} → {self.to_state} [{self.action_taken}]"
        )
