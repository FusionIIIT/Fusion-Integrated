from rest_framework import serializers

from modules.elm.models import Leave, LeaveCategory


class LeaveSerializer(serializers.ModelSerializer):
    leave_type = serializers.CharField(source="leave_type.name", read_only=True)
    status = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = Leave
        fields = ("id", "user_id", "leave_type", "start_date", "end_date",
                  "reason", "approved_by", "cancelled_by", "resumed_by",
                  "extended_by", "created_at")
        read_only_fields = ["id", "user_id", "created_at"]

class LeaveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCategory
        fields = ("name", "description")

