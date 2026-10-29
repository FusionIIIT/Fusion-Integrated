from rest_framework import serializers

from modules.elm.domain.state_machine import LeaveCategory
from modules.elm.models import LeaveApplication


class LeaveApplicationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "category",
            "category_display",
            "start_date",
            "end_date",
            "reason",
            "status",
            "status_display",
            "reviewed_by_user_id",
            "reviewed_at",
            "remarks",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "category_display",
            "status",
            "status_display",
            "reviewed_by_user_id",
            "reviewed_at",
            "created_at",
            "updated_at",
        )


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ("category", "start_date", "end_date", "reason")

    def validate_category(self, value):
        valid = [c.value for c in LeaveCategory]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid category '{value}'. Must be one of: {', '.join(valid)}."
            )
        return value

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be earlier than start date."}
            )
        return attrs


class LeaveApplicationReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
