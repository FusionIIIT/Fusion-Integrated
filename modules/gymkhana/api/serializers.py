"""Serializers for Gymkhana module."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from modules.gymkhana.models.booking import VenueBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import (
    Poll,
    PollChoice,
    PollTargetGroup,
)
from modules.gymkhana.models.report import ClubEventReport

EXAMPLE_CLUB = {
    "id": 1,
    "name": "Robotics Club",
    "category": "technical",
    "description": "Builds robots.",
    "coordinator_id": 101,
    "coordinator_name": "Student A",
    "co_coordinator_id": 102,
    "co_coordinator_name": "Student B",
    "faculty_councillor_id": 201,
    "faculty_councillor_name": "Faculty A",
    "status": "open",
    "created_at": "2026-12-01T10:00:00+05:30",
    "updated_at": "2026-12-01T10:00:00+05:30",
}


@extend_schema_field(str)
class NameField(serializers.SerializerMethodField):
    """A person's name, from the batch the view already fetched."""

    def __init__(self, source_id: str):
        self.source_id = source_id
        super().__init__()

    def to_representation(self, value) -> str:
        return self.context.get("names", {}).get(getattr(value, self.source_id), "")


def file_path(segment: str, pk: int, leaf: str, stored) -> str | None:
    """Where the scoped download lives; the storage key itself never leaves the server."""
    return f"/gymkhana/{segment}/{pk}/{leaf}/" if stored else None


class LedClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ("id", "name", "status", "faculty_councillor_id")
        read_only_fields = fields


class AccessSerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.CharField())
    clubs_led = LedClubSerializer(many=True)


class VenueListSerializer(serializers.Serializer):
    venues = serializers.ListField(child=serializers.CharField())


class PollOptionsSerializer(serializers.Serializer):
    batches = serializers.ListField(child=serializers.CharField())
    branches = serializers.ListField(child=serializers.CharField())


class PersonSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField()


class PeopleSerializer(serializers.Serializer):
    results = PersonSerializer(many=True)


@extend_schema_serializer(examples=[OpenApiExample("Club", value=EXAMPLE_CLUB)])
class ClubSerializer(serializers.ModelSerializer):
    coordinator_name = NameField("coordinator_id")
    co_coordinator_name = NameField("co_coordinator_id")
    faculty_councillor_name = NameField("faculty_councillor_id")

    class Meta:
        model = Club
        fields = (
            "id",
            "name",
            "category",
            "description",
            "coordinator_id",
            "coordinator_name",
            "co_coordinator_id",
            "co_coordinator_name",
            "faculty_councillor_id",
            "faculty_councillor_name",
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
    poster_file = serializers.SerializerMethodField()

    def get_poster_file(self, obj) -> str | None:
        return file_path("bookings", obj.pk, "poster", obj.poster_file)

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
    student_name = NameField("student_id")

    class Meta:
        model = ClubMembership
        fields = (
            "id",
            "club_id",
            "club_name",
            "student_id",
            "student_name",
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
    has_voted = serializers.BooleanField(source="voted", read_only=True)

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


class PollGroupInputSerializer(serializers.Serializer):
    batch = serializers.CharField(max_length=20)
    branch = serializers.CharField(max_length=50)


class PollCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    expires_at = serializers.DateTimeField()
    choices = serializers.ListField(
        child=serializers.CharField(max_length=200), min_length=2, max_length=20
    )
    target_groups = PollGroupInputSerializer(many=True, allow_empty=False)


class VoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField()


class BudgetRequestSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    supporting_file = serializers.SerializerMethodField()

    def get_supporting_file(self, obj) -> str | None:
        return file_path("budgets", obj.pk, "file", obj.supporting_file)

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
    student_incharge_name = NameField("student_incharge_id")
    report_file = serializers.SerializerMethodField()

    def get_report_file(self, obj) -> str | None:
        return file_path("reports", obj.pk, "file", obj.report_file)

    class Meta:
        model = ClubEventReport
        fields = (
            "id",
            "club_id",
            "club_name",
            "submitted_by_id",
            "student_incharge_id",
            "student_incharge_name",
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
