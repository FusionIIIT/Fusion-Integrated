"""Serializers for Gymkhana module."""

from __future__ import annotations

from rest_framework import serializers

from modules.gymkhana.models.booking import VenueBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import (
    Poll,
    PollChoice,
    PollTargetGroup,
    PollVote,
)
from modules.gymkhana.models.report import ClubEventReport


class ClubSerializer(serializers.ModelSerializer):
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
        )
        read_only_fields = fields


class ClubCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    category = serializers.CharField(max_length=30)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    coordinator_id = serializers.IntegerField()
    co_coordinator_id = serializers.IntegerField()
    faculty_councillor_id = serializers.IntegerField()


class LeadershipChangeSerializer(serializers.Serializer):
    coordinator_id = serializers.IntegerField()
    co_coordinator_id = serializers.IntegerField()


class VenueBookingSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = VenueBooking
        fields = (
            "id",
            "club_id",
            "club_name",
            "booking_type",
            "venue",
            "booking_date",
            "start_time",
            "end_time",
            "name",
            "description",
            "poster_file",
            "faculty_councillor_id",
            "booked_by_id",
            "created_at",
        )
        read_only_fields = fields


class SessionBookingCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    venue = serializers.CharField(max_length=100)
    booking_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    poster_file = serializers.FileField(required=False, allow_null=True, default=None)


class EventBookingCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    venue = serializers.CharField(max_length=100)
    booking_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    faculty_councillor_id = serializers.IntegerField()
    poster_file = serializers.FileField(required=False, allow_null=True, default=None)


class MembershipSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubMembership
        fields = (
            "id",
            "club_id",
            "club_name",
            "student_id",
            "description",
            "status",
            "remarks",
            "applied_at",
            "approved_at",
            "approved_by_id",
        )
        read_only_fields = fields


class MembershipApplySerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, default="")


class MembershipApproveSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PollTargetGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollTargetGroup
        fields = ("batch", "branch")


class PollChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollChoice
        fields = ("id", "choice_text", "vote_count")


class PollSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    choices = PollChoiceSerializer(many=True, read_only=True)
    target_groups = PollTargetGroupSerializer(many=True, read_only=True)
    has_voted = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = (
            "id",
            "club_id",
            "club_name",
            "created_by_id",
            "title",
            "description",
            "expires_at",
            "status",
            "created_at",
            "choices",
            "target_groups",
            "has_voted",
        )
        read_only_fields = fields

    def get_has_voted(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not getattr(request, "principal", None):
            return False
        return PollVote.objects.filter(poll=obj, student_id=request.principal.user_id).exists()


class PollCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    expires_at = serializers.DateTimeField()
    choices = serializers.ListField(child=serializers.CharField(max_length=200), min_length=2)
    target_groups = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


class VoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField()


class BudgetRequestSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubBudgetRequest
        fields = (
            "id",
            "club_id",
            "club_name",
            "submitted_by_id",
            "amount",
            "purpose",
            "description",
            "supporting_file",
            "status",
            "submitted_at",
        )
        read_only_fields = fields


class BudgetRequestCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    purpose = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    supporting_file = serializers.FileField()


class EventReportSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = ClubEventReport
        fields = (
            "id",
            "club_id",
            "club_name",
            "submitted_by_id",
            "student_incharge_id",
            "event_name",
            "event_date",
            "description",
            "report_file",
            "submitted_at",
        )
        read_only_fields = fields


class EventReportCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    student_incharge_id = serializers.IntegerField()
    event_name = serializers.CharField(max_length=150)
    event_date = serializers.DateTimeField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    report_file = serializers.FileField()
