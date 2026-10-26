from rest_framework import serializers

from modules.elm.models import LeaveRequest

CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["id", "category", "start_date", "end_date", "half_day", "reason",
                  "station_leave_details", "substitute_user_id", "status", "created_at"]
        read_only_fields = fields


class ApplyInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    half_day = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.CharField(required=False, allow_blank=True,
                                                  allow_null=True, default=None)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)
