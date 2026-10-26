from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_user_id",
            "leave_code",
            "start_date",
            "end_date",
            "half_day",
            "purpose",
            "station_leave_required",
            "station_leave_details",
            "medical_evidence_reference",
            "substitute_user_id",
            "responsibility_start",
            "responsibility_end",
            "status",
            "current_assignee_user_id",
            "current_assignee_role",
            "submitted_at",
            "final_decision_at",
            "final_decision_by_user_id",
            "final_decision_reason",
        ]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_code",
            "leave_year",
            "opening_balance",
            "credited",
            "consumed",
            "adjusted",
            "available",
        ]
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "leave_code",
            "start_date",
            "end_date",
            "half_day",
            "purpose",
            "station_leave_required",
            "station_leave_details",
            "medical_evidence_reference",
            "substitute_user_id",
            "responsibility_start",
            "responsibility_end",
        ]


class LeaveSubstituteResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=("accept", "decline"))
