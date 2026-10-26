from decimal import Decimal

from rest_framework import serializers

from modules.elm.domain.rules import validate_leave_details
from modules.elm.models import LeaveActionLog, LeaveBalance, LeaveRequest, LeaveType


class LeaveActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionLog
        fields = ["id", "actor_user_id", "actor_role", "action", "remarks", "created_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "year",
            "credited",
            "availed",
            "pending",
            "balance",
        ]
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    action_logs = LeaveActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "applicant_user_id",
            "applicant_role",
            "leave_type",
            "start_date",
            "end_date",
            "duration_days",
            "is_half_day",
            "half_day_session",
            "reason",
            "station_leave",
            "station_leave_address",
            "out_of_station_from",
            "out_of_station_to",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "status",
            "current_approver_role",
            "rejection_reason",
            "unit_head_recommendation",
            "created_at",
            "updated_at",
            "action_logs",
        ]
        read_only_fields = fields


class LeaveCreateSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    duration_days = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=Decimal("0.5")
    )
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)
    is_half_day = serializers.BooleanField(default=False)
    half_day_session = serializers.ChoiceField(
        choices=(("FN", "Forenoon"), ("AN", "Afternoon")),
        required=False,
        allow_blank=True,
        default="",
    )
    station_leave = serializers.BooleanField(default=False)
    station_leave_address = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
    out_of_station_from = serializers.DateField(required=False, allow_null=True)
    out_of_station_to = serializers.DateField(required=False, allow_null=True)
    substitute_id = serializers.RegexField(
        regex=r"^\d+$", required=False, allow_blank=True, max_length=64, default=""
    )

    def validate(self, attrs):
        try:
            validate_leave_details(
                start_date=attrs["start_date"],
                end_date=attrs["end_date"],
                leave_type=attrs["leave_type"],
                duration_days=attrs["duration_days"],
                is_half_day=attrs["is_half_day"],
                half_day_session=attrs["half_day_session"],
                reason=attrs["reason"],
                station_leave=attrs["station_leave"],
                station_leave_address=attrs["station_leave_address"],
                out_of_station_from=attrs.get("out_of_station_from"),
                out_of_station_to=attrs.get("out_of_station_to"),
            )
        except ValueError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return attrs


class SubstituteDecisionSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ApproverDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    forward_higher = serializers.BooleanField(default=False)


class LeaveWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000, default="")


class SubstituteReplacementSerializer(serializers.Serializer):
    substitute_id = serializers.RegexField(
        regex=r"^\d+$",
        max_length=64,
    )
