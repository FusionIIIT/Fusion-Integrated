"""Serializers for the Gymkhana module.

Thin serializers with explicit allow-lists. fields = "__all__" is never used.
Read and write models are kept strictly separated to prevent mass-assignment.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.gymkhana.models import (
    Booking,
    Club,
    ClubBudgetRequest,
    ClubEventReport,
    ClubLeadershipHistory,
    ClubMembership,
    Poll,
    PollChoice,
    PollTarget,
    PollVote,
)


# ---------------------------------------------------------------------------
# Clubs & Leadership
# ---------------------------------------------------------------------------


class ClubSummarySerializer(serializers.ModelSerializer):
    """Public/student club summary representation."""

    class Meta:
        model = Club
        fields = (
            "id",
            "name",
            "category",
            "status",
            "coordinator_id",
            "co_coordinator_id",
            "faculty_councillor_id",
            "created_at",
        )
        read_only_fields = fields


class ClubLeadershipHistorySerializer(serializers.ModelSerializer):
    """Historical record of club coordinators."""

    class Meta:
        model = ClubLeadershipHistory
        fields = (
            "id",
            "coordinator_id",
            "co_coordinator_id",
            "effective_from",
            "effective_to",
            "changed_by_user_id",
        )
        read_only_fields = fields


class ClubDetailSerializer(serializers.ModelSerializer):
    """Detailed club representation including active status and leadership history."""

    leadership_history = ClubLeadershipHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Club
        fields = (
            "id",
            "name",
            "category",
            "description",
            "coordinator_id",
            "co_coordinator_id",
            "faculty_councillor_id",
            "status",
            "created_at",
            "updated_at",
            "leadership_history",
        )
        read_only_fields = fields


class ClubCreateWriteSerializer(serializers.Serializer):
    """Input validation for creating a new club (UC-GYM-001)."""

    name = serializers.CharField(max_length=100)
    category = serializers.ChoiceField(choices=["Technical", "Sports", "Cultural"])
    description = serializers.CharField()
    coordinator_id = serializers.IntegerField()
    co_coordinator_id = serializers.IntegerField()
    faculty_councillor_id = serializers.IntegerField()


class ClubLeadershipWriteSerializer(serializers.Serializer):
    """Input validation for changing club leadership (UC-GYM-008)."""

    new_coordinator_id = serializers.IntegerField()
    new_co_coordinator_id = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Memberships
# ---------------------------------------------------------------------------


class MembershipSerializer(serializers.ModelSerializer):
    """Representation of student club membership applications."""

    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubMembership
        fields = (
            "id",
            "club_id",
            "club_name",
            "student_id",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MembershipApplyWriteSerializer(serializers.Serializer):
    """Input validation for applying for club membership (UC-GYM-004)."""

    club_id = serializers.IntegerField()


class MembershipApproveWriteSerializer(serializers.Serializer):
    """Input validation for approving club membership (UC-GYM-005)."""

    remarks = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Bookings (Sessions & Events)
# ---------------------------------------------------------------------------


class BookingSerializer(serializers.ModelSerializer):
    """Representation of booked sessions and events on the calendar."""

    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "booking_type",
            "club_id",
            "club_name",
            "venue",
            "date",
            "start_time",
            "end_time",
            "name",
            "description",
            "poster_url",
            "poster_file_id",
            "faculty_councillor_id",
            "created_at",
        )
        read_only_fields = fields


class SessionBookingWriteSerializer(serializers.Serializer):
    """Input validation for booking a club session (UC-GYM-002)."""

    club_id = serializers.IntegerField()
    venue = serializers.CharField(max_length=60)
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    description = serializers.CharField()
    poster_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class EventBookingWriteSerializer(serializers.Serializer):
    """Input validation for booking a club event (UC-GYM-003)."""

    club_id = serializers.IntegerField()
    faculty_councillor_id = serializers.IntegerField(required=False, allow_null=True)
    venue = serializers.CharField(max_length=60)
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    name = serializers.CharField(max_length=150)
    description = serializers.CharField()
    poster_url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Polls & Voting
# ---------------------------------------------------------------------------


class PollChoiceSerializer(serializers.ModelSerializer):
    """Representation of an individual poll choice with dynamic tally."""

    tally = serializers.SerializerMethodField()

    class Meta:
        model = PollChoice
        fields = ("id", "text", "tally")
        read_only_fields = fields

    def get_tally(self, obj: PollChoice) -> int:
        annotated = getattr(obj, "tally", None)
        if annotated is not None:
            return int(annotated)
        return obj.votes.count()


class PollTargetSerializer(serializers.ModelSerializer):
    """Representation of an audience group targeted by a poll."""

    class Meta:
        model = PollTarget
        fields = ("id", "batch_year", "discipline")
        read_only_fields = fields


class PollSummarySerializer(serializers.ModelSerializer):
    """Brief poll summary for public listings."""

    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Poll
        fields = (
            "id",
            "club_id",
            "club_name",
            "title",
            "description",
            "expires_at",
            "status",
            "created_at",
        )
        read_only_fields = fields


class PollDetailSerializer(serializers.ModelSerializer):
    """Detailed poll view with choices, dynamic tallies, and caller voting state."""

    club_name = serializers.CharField(source="club.name", read_only=True)
    choices = PollChoiceSerializer(many=True, read_only=True)
    targets = PollTargetSerializer(many=True, read_only=True)
    has_voted = serializers.SerializerMethodField()
    selected_choice_id = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = (
            "id",
            "club_id",
            "club_name",
            "title",
            "description",
            "expires_at",
            "status",
            "choices",
            "targets",
            "has_voted",
            "selected_choice_id",
            "created_by_user_id",
            "created_at",
        )
        read_only_fields = fields

    def get_has_voted(self, obj: Poll) -> bool:
        actor = self.context.get("actor")
        if not actor or not hasattr(actor, "user_id"):
            return False
        return obj.votes.filter(student_id=actor.user_id).exists()

    def get_selected_choice_id(self, obj: Poll) -> int | None:
        actor = self.context.get("actor")
        if not actor or not hasattr(actor, "user_id"):
            return None
        vote = obj.votes.filter(student_id=actor.user_id).first()
        return vote.choice_id if vote else None


class PollTargetItemSerializer(serializers.Serializer):
    """Single target group in poll creation payload."""

    batch_year = serializers.IntegerField()
    discipline = serializers.CharField(required=False, allow_blank=True, default="all")


class PollCreateWriteSerializer(serializers.Serializer):
    """Input validation for creating a voting poll (UC-GYM-006)."""

    club_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    expires_at = serializers.DateTimeField()
    choices = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=2,
    )
    targets = serializers.ListField(
        child=PollTargetItemSerializer(),
        min_length=1,
    )


class PollVoteWriteSerializer(serializers.Serializer):
    """Input validation for casting a vote in a poll (UC-GYM-007)."""

    choice_id = serializers.IntegerField()


class PollVoteResultSerializer(serializers.ModelSerializer):
    """Result of casting a vote."""

    class Meta:
        model = PollVote
        fields = ("id", "poll_id", "choice_id", "student_id", "created_at")
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------


class BudgetRequestSerializer(serializers.ModelSerializer):
    """Representation of submitted club budget requests."""

    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubBudgetRequest
        fields = (
            "id",
            "club_id",
            "club_name",
            "amount",
            "purpose",
            "description",
            "supporting_file_url",
            "supporting_file_id",
            "status",
            "submitted_by_user_id",
            "created_at",
        )
        read_only_fields = fields


class BudgetRequestWriteSerializer(serializers.Serializer):
    """Input validation for submitting a club budget request (UC-GYM-009)."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    purpose = serializers.CharField(max_length=200)
    description = serializers.CharField()
    supporting_file_url = serializers.CharField(max_length=500)


# ---------------------------------------------------------------------------
# Event Reports
# ---------------------------------------------------------------------------


class EventReportSerializer(serializers.ModelSerializer):
    """Representation of submitted club event reports."""

    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubEventReport
        fields = (
            "id",
            "club_id",
            "club_name",
            "student_incharge_id",
            "event_name",
            "event_date",
            "event_time",
            "description",
            "report_file_url",
            "report_file_id",
            "submitted_by_user_id",
            "created_at",
        )
        read_only_fields = fields


class EventReportWriteSerializer(serializers.Serializer):
    """Input validation for submitting a club event report (UC-GYM-010)."""

    student_incharge_id = serializers.IntegerField()
    event_name = serializers.CharField(max_length=150)
    event_date = serializers.DateField()
    event_time = serializers.TimeField()
    description = serializers.CharField()
    report_file_url = serializers.CharField(max_length=500)


class EventReportDetailSerializer(serializers.ModelSerializer):
    """Detailed event report representation for faculty review (UC-GYM-012)."""

    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubEventReport
        fields = (
            "id",
            "club_id",
            "club_name",
            "student_incharge_id",
            "event_name",
            "event_date",
            "event_time",
            "description",
            "report_file_url",
            "report_file_id",
            "submitted_by_user_id",
            "created_at",
        )
        read_only_fields = fields
