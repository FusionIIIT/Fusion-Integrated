from rest_framework import serializers

from modules.gymkhana.models import (
    Club,
    ClubLeadership,
    ClubMembership,
    VenueBooking,
    VotingPoll,
    PollOption,
    PollVote,
    ClubBudgetRequest,
    ClubEventReport,
)


class ClubLeadershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubLeadership
        fields = [
            "id",
            "club",
            "coordinator_id",
            "co_coordinator_id",
            "faculty_councillor_id",
            "is_active",
            "assigned_at",
        ]
        read_only_fields = ["is_active", "assigned_at"]


class ClubSerializer(serializers.ModelSerializer):
    leaderships = ClubLeadershipSerializer(many=True, read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "category",
            "description",
            "status",
            "created_at",
            "updated_at",
            "leaderships",
        ]
        read_only_fields = ["status", "created_at", "updated_at"]


class ClubCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    category = serializers.CharField(max_length=20)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    coordinator_id = serializers.IntegerField()
    co_coordinator_id = serializers.IntegerField()
    faculty_councillor_id = serializers.IntegerField()


class ChangeLeadershipSerializer(serializers.Serializer):
    new_coordinator_id = serializers.IntegerField()
    new_co_coordinator_id = serializers.IntegerField()


class ClubMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubMembership
        fields = [
            "id",
            "club",
            "student_id",
            "status",
            "applied_at",
            "confirmed_at",
        ]
        read_only_fields = ["status", "applied_at", "confirmed_at", "student_id"]


class VenueBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueBooking
        fields = [
            "id",
            "club",
            "booking_type",
            "venue_name",
            "booking_date",
            "start_time",
            "end_time",
            "description",
            "poster_url",
            "created_by_id",
            "created_at",
        ]
        read_only_fields = ["created_by_id", "created_at"]


class PollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ["id", "option_text"]


class VotingPollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)

    class Meta:
        model = VotingPoll
        fields = [
            "id",
            "club",
            "title",
            "description",
            "target_batch",
            "target_branch",
            "is_active",
            "expires_at",
            "created_by_id",
            "created_at",
            "options",
        ]
        read_only_fields = ["is_active", "created_by_id", "created_at"]


class CreatePollSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    options = serializers.ListField(child=serializers.CharField(max_length=200), min_length=2)
    target_batch = serializers.CharField(max_length=50, default="ALL")
    target_branch = serializers.CharField(max_length=50, default="ALL")
    expires_at = serializers.DateTimeField()


class CastVoteSerializer(serializers.Serializer):
    option_id = serializers.IntegerField()
    student_batch = serializers.CharField(max_length=50, default="ALL")
    student_branch = serializers.CharField(max_length=50, default="ALL")


class PollVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollVote
        fields = [
            "id",
            "poll",
            "option",
            "student_id",
            "voted_at",
        ]
        read_only_fields = ["student_id", "voted_at"]


class ClubBudgetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubBudgetRequest
        fields = [
            "id",
            "club",
            "requested_amount",
            "description",
            "supporting_file",
            "status",
            "submitted_by_id",
            "submitted_at",
        ]
        read_only_fields = ["status", "submitted_by_id", "submitted_at"]


class ClubEventReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubEventReport
        fields = [
            "id",
            "club",
            "event_name",
            "event_date",
            "report_file",
            "submitted_by_id",
            "submitted_at",
        ]
        read_only_fields = ["submitted_by_id", "submitted_at"]
