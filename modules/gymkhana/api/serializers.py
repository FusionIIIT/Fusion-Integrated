from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.gymkhana.models.booking import ClubBooking
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.membership import ClubMembership
from modules.gymkhana.models.poll import PollChoice, VotingPoll
from modules.gymkhana.models.report import ClubEventReport


class ClubLeadershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubLeadership
        fields = ["id", "student_id", "role", "is_current", "created_at"]


class ClubSerializer(serializers.ModelSerializer):
    leaderships = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "category",
            "description",
            "faculty_councillor_id",
            "status",
            "leaderships",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(ClubLeadershipSerializer(many=True))
    def get_leaderships(self, obj):
        return ClubLeadershipSerializer(obj.leaderships.filter(is_current=True), many=True).data


class ClubCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    category = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    coordinator_id = serializers.IntegerField()
    co_coordinator_id = serializers.IntegerField()
    faculty_councillor_id = serializers.IntegerField()


class ClubLeadershipChangeSerializer(serializers.Serializer):
    new_coordinator_id = serializers.IntegerField()
    new_co_coordinator_id = serializers.IntegerField()


class ClubBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubBooking
        fields = [
            "id",
            "club_id",
            "booking_type",
            "title",
            "venue",
            "date",
            "start_time",
            "end_time",
            "description",
            "created_by_id",
            "created_at",
        ]


class ClubBookingCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    venue = serializers.CharField(max_length=100)
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField(required=False, allow_blank=True, default="")


class ClubMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubMembership
        fields = [
            "id",
            "club_id",
            "student_id",
            "status",
            "remarks",
            "created_at",
            "confirmed_at",
        ]


class ClubMembershipApplySerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PollChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollChoice
        fields = ["id", "text", "votes_count"]


class VotingPollSerializer(serializers.ModelSerializer):
    choices = PollChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = VotingPoll
        fields = [
            "id",
            "club_id",
            "title",
            "description",
            "target_batches",
            "target_branches",
            "expires_at",
            "choices",
            "created_by_id",
            "created_at",
        ]


class VotingPollCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=250)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    target_batches = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    target_branches = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    expires_at = serializers.DateTimeField()
    choices = serializers.ListField(child=serializers.CharField(), min_length=2)


class PollVoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField()


class PollVoteResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    vote_id = serializers.IntegerField()


class ClubBudgetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubBudgetRequest
        fields = [
            "id",
            "club_id",
            "amount",
            "purpose",
            "description",
            "supporting_file",
            "status",
            "submitted_by_id",
            "created_at",
        ]


class ClubBudgetRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    purpose = serializers.CharField(max_length=250)
    description = serializers.CharField()
    supporting_file = serializers.FileField()


class ClubEventReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubEventReport
        fields = [
            "id",
            "club_id",
            "title",
            "description",
            "report_file",
            "submitted_by_id",
            "created_at",
        ]


class ClubEventReportCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    report_file = serializers.FileField()
