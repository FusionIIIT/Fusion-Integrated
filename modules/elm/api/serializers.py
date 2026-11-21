from rest_framework import serializers

from modules.elm.models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Serializer for the LeaveRequest model."""

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "user_id",
            "start_date",
            "end_date",
            "reason",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
