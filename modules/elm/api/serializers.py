from __future__ import annotations

from rest_framework import serializers

from modules.elm.models import LeaveBalance, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "days_requested",
            "half_day",
            "reason",
            "substitute_user_id",
            "status",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs

    def create(self, validated_data):
        principal = self.context["request"].principal
        validated_data["user_id"] = principal.user_id
        return super().create(validated_data)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "year",
            "entitled_days",
            "used_days",
            "remaining_days",
        ]
        read_only_fields = fields
