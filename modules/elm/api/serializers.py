from decimal import Decimal

from rest_framework import serializers

from modules.elm.models import (
    AccountEntry,
    HolidayCalendar,
    LeaveActionLog,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Notification,
)


class LeaveActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionLog
        fields = ["id", "actor_user_id", "actor_role", "action", "remarks", "created_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=9, decimal_places=2, read_only=True)

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


class LeaveRequestSerializer(serializers.ModelSerializer):
    action_logs = LeaveActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "applicant_user_id",
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
            "created_at",
            "updated_at",
            "action_logs",
            "request_kind",
            "original_id",
            "recommendation",
            "current_approver_user_id",
            "evidence_reference",
            "actual_end_date",
            "actual_duration_days",
        ]
        read_only_fields = [
            "id",
            "status",
            "current_approver_role",
            "substitute_status",
            "created_at",
            "updated_at",
        ]


class LeaveCreateSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    duration_days = serializers.DecimalField(
        max_digits=9, decimal_places=2, required=False, min_value=Decimal("0.5")
    )
    reason = serializers.CharField(max_length=4000)
    evidence_reference = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )
    is_half_day = serializers.BooleanField(default=False)
    half_day_session = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(default=False)
    station_leave_address = serializers.CharField(required=False, allow_blank=True, default="")
    out_of_station_from = serializers.DateField(required=False, allow_null=True)
    out_of_station_to = serializers.DateField(required=False, allow_null=True)
    substitute_id = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteDecisionSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ApproverDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    forward_higher = serializers.BooleanField(default=False)


class ReplacementSerializer(serializers.Serializer):
    substitute_id = serializers.RegexField(r"^[1-9][0-9]*$", max_length=64)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=4000)


class FollowupSerializer(ReasonSerializer):
    end_date = serializers.DateField()
    substitute_id = serializers.RegexField(
        r"^[1-9][0-9]*$", required=False, allow_blank=True, default="", max_length=64
    )
    evidence_reference = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=2000
    )


class OfflineSerializer(LeaveCreateSerializer):
    employee_id = serializers.RegexField(r"^[1-9][0-9]*$", max_length=64)
    sanction_reference = serializers.CharField(max_length=2000)
    unavailable_reason = serializers.CharField(max_length=2000)


class FollowupActionSerializer(ReasonSerializer):
    end_date = serializers.DateField(required=False)
    substitute_id = serializers.CharField(required=False)
    evidence_reference = serializers.CharField(required=False)


class MaintenanceSerializer(serializers.Serializer):
    remarks = serializers.CharField(max_length=4000)


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountEntry
        fields = ["id", "year", "leave_type", "action", "amount", "created_at", "request_id"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "event", "message", "created_at", "request_id"]


class CalendarRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "closed_dates", "restricted_dates", "published_at", "created_at"]


class CalendarResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    published_at = serializers.DateTimeField(allow_null=True)
