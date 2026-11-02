from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from modules.gymkhana.models import (
    BudgetRequest,
    Club,
    ClubEvent,
    ClubEventReport,
    ClubSession,
    MembershipApplication,
    PollChoice,
    PollTargetGroup,
    VotingPoll,
)


class ClubSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Club
        fields = [
            "id", "name", "category", "coordinator_user_id",
            "co_coordinator_user_id", "faculty_councillor_user_id",
            "description", "status", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class LeadershipSerializer(serializers.Serializer):
    coordinator_user_id = serializers.IntegerField(min_value=1)
    co_coordinator_user_id = serializers.IntegerField(min_value=1)


class ActivitySerializer(serializers.ModelSerializer):
    poster = serializers.FileField(required=False, allow_empty_file=False, write_only=True)
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = ClubSession
        fields = [
            "id", "venue", "date", "start_time", "end_time",
            "description", "poster", "poster_url", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_venue(self, value):
        if value not in settings.GYMKHANA_VENUES:
            raise serializers.ValidationError("Choose a configured venue.")
        return value

    def validate_poster(self, value):
        if value.size > settings.GYMKHANA_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("Poster exceeds the configured upload limit.")
        return value

    def get_poster_url(self, obj) -> str:
        return f"/api/v1/gymkhana/files/session/{obj.pk}" if obj.poster else ""

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError(
                {"end_time": "The end time must be later than the start time."}
            )
        return attrs


class EventSerializer(serializers.ModelSerializer):
    poster = serializers.FileField(required=False, allow_empty_file=False, write_only=True)
    poster_url = serializers.SerializerMethodField()

    class Meta:
        model = ClubEvent
        fields = [
            "id", "name", "venue", "date", "start_time", "end_time",
            "description", "poster", "poster_url", "faculty_user_id", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_venue(self, value):
        if value not in settings.GYMKHANA_VENUES:
            raise serializers.ValidationError("Choose a configured venue.")
        return value

    def validate_poster(self, value):
        if value.size > settings.GYMKHANA_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("Poster exceeds the configured upload limit.")
        return value

    def get_poster_url(self, obj) -> str:
        return f"/api/v1/gymkhana/files/event/{obj.pk}" if obj.poster else ""

    def validate(self, attrs):
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start is not None and end is not None and start >= end:
            raise serializers.ValidationError(
                {"end_time": "The end time must be later than the start time."}
            )
        return attrs


class MembershipApplicationSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = MembershipApplication
        fields = [
            "id", "club", "student_user_id", "description", "status",
            "remarks", "approved_by_user_id", "created_at",
        ]
        read_only_fields = [
            "id", "club", "student_user_id", "status", "remarks",
            "approved_by_user_id", "created_at",
        ]


class MembershipMineSerializer(MembershipApplicationSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta(MembershipApplicationSerializer.Meta):
        fields = [*MembershipApplicationSerializer.Meta.fields, "club_name"]


class MembershipApprovalSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PollTargetGroupSerializer(serializers.ModelSerializer):
    batch_year = serializers.IntegerField(min_value=1)

    class Meta:
        model = PollTargetGroup
        fields = ["batch_year", "discipline"]

    def validate_discipline(self, value):
        if value != "*" and not value.strip():
            raise serializers.ValidationError("Select a valid branch/discipline.")
        return value.strip() if value != "*" else value


class PollCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    expires_at = serializers.DateTimeField()
    choices = serializers.ListField(
        child=serializers.CharField(max_length=180, trim_whitespace=True),
        min_length=2,
    )
    target_groups = PollTargetGroupSerializer(many=True, allow_empty=False)

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Poll expiry must be in the future.")
        return value

    def validate_choices(self, value):
        normalized = [choice.strip() for choice in value]
        if any(not choice for choice in normalized):
            raise serializers.ValidationError("Poll choices cannot be blank.")
        if len(set(normalized)) != len(normalized):
            raise serializers.ValidationError("Poll choices must be unique.")
        return normalized

    def validate_target_groups(self, value):
        unique = {(row["batch_year"], row["discipline"]) for row in value}
        if len(unique) != len(value):
            raise serializers.ValidationError("Target groups must be unique.")
        return value


class PollChoiceSerializer(serializers.ModelSerializer):
    vote_count = serializers.IntegerField(source="votes.count", read_only=True)

    class Meta:
        model = PollChoice
        fields = ["id", "text", "vote_count"]


class PollSerializer(serializers.ModelSerializer):
    choices = PollChoiceSerializer(many=True, read_only=True)
    has_voted = serializers.SerializerMethodField()

    class Meta:
        model = VotingPoll
        fields = [
            "id", "club", "title", "description", "expires_at",
            "choices", "has_voted", "created_at",
        ]

    def get_has_voted(self, obj) -> bool:
        user_id = self.context.get("user_id")
        return obj.votes.filter(student_user_id=user_id).exists() if user_id else False


class VoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField(min_value=1)


class BudgetRequestSerializer(serializers.ModelSerializer):
    supporting_file = serializers.FileField(write_only=True, allow_empty_file=False)
    download_url = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = BudgetRequest
        fields = [
            "id", "amount", "purpose", "description", "supporting_file",
            "download_url", "status", "created_at",
        ]
        read_only_fields = ["id", "download_url", "status", "created_at"]

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Amount must be zero or greater.")
        return value

    def validate_supporting_file(self, value):
        if value.size > settings.GYMKHANA_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File exceeds the configured upload limit.")
        return value

    def get_download_url(self, obj) -> str:
        return f"/api/v1/gymkhana/files/budget/{obj.pk}"


class EventReportSerializer(serializers.ModelSerializer):
    report_file = serializers.FileField(write_only=True, allow_empty_file=False)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ClubEventReport
        fields = [
            "id", "student_incharge_user_id", "event_name", "event_at",
            "description", "report_file", "download_url", "created_at",
        ]
        read_only_fields = ["id", "download_url", "created_at"]

    def get_download_url(self, obj) -> str:
        return f"/api/v1/gymkhana/files/report/{obj.pk}"

    def validate_report_file(self, value):
        if value.size > settings.GYMKHANA_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File exceeds the configured upload limit.")
        return value


class VenueListSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.CharField())


class PersonSearchResultSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    username = serializers.CharField()
    kind = serializers.ChoiceField(choices=("student", "faculty"))
    batch_year = serializers.IntegerField(allow_null=True)
    discipline = serializers.CharField()


class PeopleSearchSerializer(serializers.Serializer):
    results = PersonSearchResultSerializer(many=True)


class ClubListSerializer(serializers.Serializer):
    results = ClubSerializer(many=True)


class ActivityListSerializer(serializers.Serializer):
    results = ActivitySerializer(many=True)


class EventListSerializer(serializers.Serializer):
    results = EventSerializer(many=True)


class MembershipListSerializer(serializers.Serializer):
    results = MembershipApplicationSerializer(many=True)


class PollListSerializer(serializers.Serializer):
    results = PollSerializer(many=True)


class BudgetListSerializer(serializers.Serializer):
    results = BudgetRequestSerializer(many=True)


class EventReportListSerializer(serializers.Serializer):
    results = EventReportSerializer(many=True)


class AssignedEventReportSerializer(EventReportSerializer):
    club_name = serializers.CharField()

    class Meta(EventReportSerializer.Meta):
        fields = [*EventReportSerializer.Meta.fields, "club_name"]


class AssignedEventReportListSerializer(serializers.Serializer):
    results = AssignedEventReportSerializer(many=True)


class MembershipMineListSerializer(serializers.Serializer):
    results = MembershipMineSerializer(many=True)


class VoteResultSerializer(serializers.Serializer):
    poll_id = serializers.IntegerField()
    choice_id = serializers.IntegerField()
