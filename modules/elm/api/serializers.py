from rest_framework import serializers
from modules.elm.models import LeaveApplication, LeaveBalance


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = ("id", "user_id", "status", "decision_note", "created_at")


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "category", "start_date", "end_date", "part_of_day", "reason",
            "station_leave", "station_destination", "substitute_user_id",
        )

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("End date must be after start date.")
        if data.get("station_leave") and not data.get("station_destination", "").strip():
            raise serializers.ValidationError({"station_destination": "Enter destination."})
        return data


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ("id", "year", "category", "entitled_days", "used_days", "available_days")
