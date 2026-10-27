from rest_framework import serializers

from modules.leave.models import LeaveRequest


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["cl", "rh"])
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    cl_half = serializers.ChoiceField(choices=["full", "first", "second"], default="full")
    reason = serializers.CharField(max_length=500)
    station_leave = serializers.BooleanField(default=False)
    station_leave_details = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "This field cannot be blank."})
        if attrs["station_leave"] and not attrs["station_leave_details"].strip():
            raise serializers.ValidationError(
                {"station_leave_details": "Station Leave details are required."})
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["id", "category", "starts_on", "ends_on", "cl_half", "reason",
                  "station_leave", "station_leave_details", "status", "withdrawn_at",
                  "created_at"]
