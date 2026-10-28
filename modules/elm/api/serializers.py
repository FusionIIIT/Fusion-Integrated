from rest_framework import serializers
from modules.elm.models import LeaveApplication


class LeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = ["applicant_id", "employee", "status", "approver_id"]

    def validate(self, data):
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("End date cannot be before start date.")
        return data