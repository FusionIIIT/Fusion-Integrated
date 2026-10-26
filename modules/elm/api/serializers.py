from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType, SubstituteNomination


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "leave_type"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "employee_id", "leave_type", "balance"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "start_date",
            "end_date",
            "station_leave_details",
            "reason",
            "status",
        ]
        read_only_fields = ["status", "applicant_id"]


class SubstituteNominationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteNomination
        fields = [
            "id",
            "leave_application",
            "substitute_id",
            "start_date",
            "end_date",
            "reason",
            "status",
            "decline_reason",
        ]
        read_only_fields = ["status"]


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    decline_reason = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewApplicationSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
