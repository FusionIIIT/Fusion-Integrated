"""Serializers. Thin, explicit allow-list."""
from rest_framework import serializers

from modules.leave.models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ("id", "user_id", "category", "start_date", "end_date",
                  "half_day", "purpose", "station_leave", "station_details",
                  "substitute_user_id", "status", "created_at")
        read_only_fields = fields


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                    default="")
    half_day = serializers.BooleanField(default=False)
    station_leave = serializers.BooleanField(default=False)
    station_details = serializers.CharField(max_length=300, required=False,
                                            allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                  default=None)


class LeaveTransitionSerializer(serializers.Serializer):
    to_status = serializers.CharField(max_length=24)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                   default="")
