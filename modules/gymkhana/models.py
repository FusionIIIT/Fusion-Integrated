"""
Gymkhana database models.
Uses integer user references for cross-module decoupling (ADR-0013).
"""

from django.db import models


class Club(models.Model):
    CATEGORY_CHOICES = [
        ("Technical", "Technical"),
        ("Sports", "Sports"),
        ("Cultural", "Cultural"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("confirmed", "Confirmed"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.category}) - {self.status}"


class ClubLeadership(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="leaderships")
    coordinator_id = models.IntegerField(db_index=True)
    co_coordinator_id = models.IntegerField(db_index=True)
    faculty_councillor_id = models.IntegerField(db_index=True)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.club.name} Leadership (Coord: {self.coordinator_id})"


class ClubMembership(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("confirmed", "Confirmed"),
    ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="memberships")
    student_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    applied_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("club", "student_id")

    def __str__(self):
        return f"Member {self.student_id} in {self.club.name} ({self.status})"


class VenueBooking(models.Model):
    BOOKING_TYPE_CHOICES = [
        ("session", "Session"),
        ("event", "Event"),
    ]

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="bookings")
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES)
    venue_name = models.CharField(max_length=100)
    booking_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True)
    poster_url = models.CharField(max_length=255, blank=True)
    created_by_id = models.IntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking_type} at {self.venue_name} on {self.booking_date} ({self.start_time}-{self.end_time})"


class VotingPoll(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="polls")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_batch = models.CharField(max_length=50, blank=True)
    target_branch = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_by_id = models.IntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Poll: {self.title} (Active: {self.is_active})"


class PollOption(models.Model):
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.poll.id} - {self.option_text}"


class PollVote(models.Model):
    poll = models.ForeignKey(VotingPoll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    student_id = models.IntegerField(db_index=True)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("poll", "student_id")

    def __str__(self):
        return f"Vote by {self.student_id} in Poll {self.poll_id}"


class ClubBudgetRequest(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="budget_requests")
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    supporting_file = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="open")
    submitted_by_id = models.IntegerField(db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Budget ₹{self.requested_amount} for {self.club.name}"


class ClubEventReport(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="event_reports")
    event_name = models.CharField(max_length=200)
    event_date = models.DateField()
    report_file = models.CharField(max_length=255)
    submitted_by_id = models.IntegerField(db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report: {self.event_name} ({self.club.name})"
