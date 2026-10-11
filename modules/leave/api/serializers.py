from rest_framework import serializers

from modules.leave.models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee_id",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason"]

    def validate(self, attrs):
        start_date = attrs["start_date"]
        end_date = attrs["end_date"]
        if end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after the start date."}
            )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return LeaveRequest.objects.create(
            employee_id=request.principal.user_id,
            **validated_data,
        )
