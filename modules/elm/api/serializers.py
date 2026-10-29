from rest_framework import serializers

from modules.elm.models import LeaveApplication


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id", "category", "start_date", "end_date", "reason",
            "status", "applied_at",
        )
        read_only_fields = ("id", "status", "applied_at")


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ("category", "start_date", "end_date", "reason")