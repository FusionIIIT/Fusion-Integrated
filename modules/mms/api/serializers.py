from rest_framework import serializers

from modules.mms.models import (
    Announcement,
    Feedback,
    MenuItem,
    RebateRequest,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodRequest,
    StudentRegistration,
    VacationResponse,
    VacationSurvey,
)


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSRoleAssignmentSchema"
        model = RoleAssignment
        fields = ["id", "role", "user_id", "starts_at", "ends_at"]
        read_only_fields = ["id"]


class RoleAssignmentInputSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["caretaker", "warden"])
    user_id = serializers.IntegerField(min_value=1)
    ends_at = serializers.DateTimeField()


class WindowSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSWindowSchema"
        model = RegistrationWindow
        fields = ["id", "cycle", "opens_at", "closes_at"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["closes_at"] <= attrs["opens_at"]:
            raise serializers.ValidationError("Closing time must follow opening time.")
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSRegistrationSchema"
        model = StudentRegistration
        fields = [
            "id",
            "user_id",
            "cycle",
            "request_type",
            "status",
            "submitted_at",
            "decided_at",
            "effective_date",
        ]
        read_only_fields = fields


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSMenuItemSchema"
        model = MenuItem
        fields = ["id", "week_start", "day", "meal", "item"]
        read_only_fields = ["id"]


class RebateSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSRebateSchema"
        model = RebateRequest
        fields = [
            "id",
            "user_id",
            "reason",
            "explanation",
            "start_date",
            "end_date",
            "status",
            "submitted_at",
            "decided_at",
        ]
        read_only_fields = ["id", "user_id", "status", "submitted_at", "decided_at"]


class VacationSurveySerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSVacationSurveySchema"
        model = VacationSurvey
        fields = [
            "id",
            "title",
            "vacation_start",
            "vacation_end",
            "response_deadline",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VacationResponseSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSVacationResponseSchema"
        model = VacationResponse
        fields = ["id", "survey", "response"]
        read_only_fields = ["id", "survey"]


class SpecialFoodSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSSpecialFoodSchema"
        model = SpecialFoodRequest
        fields = [
            "id",
            "user_id",
            "requested_date",
            "description",
            "charge",
            "status",
            "submitted_at",
        ]
        read_only_fields = ["id", "user_id", "status", "submitted_at", "charge"]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSFeedbackSchema"
        model = Feedback
        fields = ["id", "text", "created_at"]
        read_only_fields = ["id", "created_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        ref_name = "MMSAnnouncementSchema"
        model = Announcement
        fields = ["id", "owner_role", "title", "body", "created_at"]
        read_only_fields = ["id", "created_at"]


class _StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class _CycleStatusCountSerializer(_StatusCountSerializer):
    cycle = serializers.CharField()


class ReportSummarySerializer(serializers.Serializer):
    registrations = _CycleStatusCountSerializer(many=True)
    rebates = _StatusCountSerializer(many=True)
    special_food = _StatusCountSerializer(many=True)
