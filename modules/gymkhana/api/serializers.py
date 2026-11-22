"""Request and response shapes. Every server-owned field is read-only."""
from rest_framework import serializers

from modules.gymkhana.models import (
    Booking,
    BudgetRequest,
    Club,
    EventReport,
    Membership,
    Poll,
)


class GymkhanaClubSerializer(serializers.ModelSerializer):
    category = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    leaders = serializers.SerializerMethodField()
    leader_names = serializers.SerializerMethodField()
    councillor_name = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = ["id", "name", "category", "description", "status",
                  "faculty_councillor_user_id", "councillor_name", "approved_at",
                  "created_at", "leaders", "leader_names", "my_membership"]
        read_only_fields = fields

    def get_leaders(self, obj) -> dict:
        return self.context.get("leaders", {}).get(obj.pk, {})

    def get_leader_names(self, obj) -> dict:
        names = self.context.get("names", {})
        return {role: names.get(uid, "") for role, uid in self.get_leaders(obj).items()}

    def get_councillor_name(self, obj) -> str:
        return self.context.get("names", {}).get(obj.faculty_councillor_user_id, "")

    def get_my_membership(self, obj) -> str | None:
        return self.context.get("own_status", {}).get(obj.pk)


class GymkhanaClubCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, allow_blank=True)
    category = serializers.CharField(max_length=16, allow_blank=True)
    description = serializers.CharField(max_length=4000, allow_blank=True)
    coordinator_user_id = serializers.IntegerField()
    co_coordinator_user_id = serializers.IntegerField()
    faculty_councillor_user_id = serializers.IntegerField()


class GymkhanaLeadershipSerializer(serializers.Serializer):
    coordinator_user_id = serializers.IntegerField()
    co_coordinator_user_id = serializers.IntegerField()


class GymkhanaLeadersOutSerializer(serializers.Serializer):
    coordinator = serializers.IntegerField()
    co_coordinator = serializers.IntegerField()


class GymkhanaMyClubsSerializer(serializers.Serializer):
    leading = GymkhanaClubSerializer(many=True)
    member_of = GymkhanaClubSerializer(many=True)


class GymkhanaMembershipSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["id", "club", "club_name", "user_id", "applicant_name", "description",
                  "status", "remarks", "approved_at", "created_at"]
        read_only_fields = fields

    def get_applicant_name(self, obj) -> str:
        return self.context.get("names", {}).get(obj.user_id, "")


class GymkhanaApplySerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    description = serializers.CharField(max_length=4000, allow_blank=True)


class GymkhanaApproveSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), max_length=100)
    remarks = serializers.CharField(max_length=1000, allow_blank=True, required=False,
                                    default="")


class GymkhanaApprovalOutcomeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    outcome = serializers.CharField()
    code = serializers.CharField()
    message = serializers.CharField()


class GymkhanaBookingSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "club", "club_name", "kind", "venue_name", "date", "start_time",
                  "end_time", "description", "poster_link", "event_name",
                  "faculty_user_id", "created_at"]
        read_only_fields = fields


class GymkhanaSessionCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    venue = serializers.CharField(max_length=120)
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField(max_length=4000, allow_blank=True)
    poster_url = serializers.CharField(max_length=500, allow_blank=True, required=False,
                                       default="")


class GymkhanaEventCreateSerializer(GymkhanaSessionCreateSerializer):
    event_name = serializers.CharField(max_length=200, allow_blank=True)
    poster_url = serializers.CharField(max_length=500, allow_blank=True)


class GymkhanaVenueListSerializer(serializers.Serializer):
    venues = serializers.ListField(child=serializers.CharField())


class GymkhanaChoiceOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    votes = serializers.IntegerField(required=False)


class GymkhanaTargetSerializer(serializers.Serializer):
    batch_year = serializers.IntegerField()
    discipline = serializers.CharField(max_length=40, allow_blank=True, required=False,
                                       default="")


class GymkhanaPollSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    choices = serializers.SerializerMethodField()
    my_choice_id = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ["id", "club", "club_name", "title", "description", "expires_on",
                  "created_at", "choices", "my_choice_id"]
        read_only_fields = fields

    def get_choices(self, obj) -> list[dict]:
        return [{"id": c.id, "label": c.label} for c in obj.choices.all()]

    def get_my_choice_id(self, obj) -> int | None:
        return self.context.get("own_votes", {}).get(obj.pk)


class GymkhanaManagedPollSerializer(GymkhanaPollSerializer):
    targets = serializers.SerializerMethodField()
    total_votes = serializers.SerializerMethodField()

    class Meta(GymkhanaPollSerializer.Meta):
        fields = ["id", "club", "club_name", "title", "description", "expires_on",
                  "created_at", "choices", "targets", "total_votes"]
        read_only_fields = fields

    def get_choices(self, obj) -> list[dict]:
        counts = self.context.get("tallies", {}).get(obj.pk, {})
        return [{"id": c.id, "label": c.label, "votes": counts.get(c.id, 0)}
                for c in obj.choices.all()]

    def get_targets(self, obj) -> list[dict]:
        return [{"batch_year": t.batch_year, "discipline": t.discipline}
                for t in obj.targets.all()]

    def get_total_votes(self, obj) -> int:
        return sum(self.context.get("tallies", {}).get(obj.pk, {}).values())


class GymkhanaPollCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200, allow_blank=True)
    description = serializers.CharField(max_length=4000, allow_blank=True)
    expires_on = serializers.DateField()
    choices = serializers.ListField(child=serializers.CharField(max_length=200,
                                                                allow_blank=True),
                                    max_length=50)
    targets = GymkhanaTargetSerializer(many=True)


class GymkhanaVoteSerializer(serializers.Serializer):
    choice_id = serializers.IntegerField()


class GymkhanaBudgetRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = BudgetRequest
        fields = ["id", "club", "club_name", "purpose", "description", "amount",
                  "document_link", "status", "submitted_by_user_id", "created_at"]
        read_only_fields = fields


class GymkhanaBudgetCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=200, allow_blank=True)
    description = serializers.CharField(max_length=4000, allow_blank=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    document_url = serializers.CharField(max_length=500, allow_blank=True)


class GymkhanaEventReportSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    student_incharge_name = serializers.SerializerMethodField()

    class Meta:
        model = EventReport
        fields = ["id", "club", "club_name", "student_incharge_user_id",
                  "student_incharge_name", "event_name", "event_at", "description",
                  "report_link", "submitted_by_user_id", "created_at"]
        read_only_fields = fields

    def get_student_incharge_name(self, obj) -> str:
        return self.context.get("names", {}).get(obj.student_incharge_user_id, "")


class GymkhanaEventReportCreateSerializer(serializers.Serializer):
    club_id = serializers.IntegerField()
    student_incharge_user_id = serializers.IntegerField()
    event_name = serializers.CharField(max_length=200, allow_blank=True)
    event_at = serializers.DateTimeField()
    description = serializers.CharField(max_length=4000, allow_blank=True)
    report_url = serializers.CharField(max_length=500, allow_blank=True)


class GymkhanaPersonSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    kind = serializers.CharField()
