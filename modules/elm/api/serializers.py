from rest_framework import serializers
from modules.elm.models import ApprovalTask, LeaveBalance, LeaveCalendarDay, LeavePolicy, LeaveRequest, ResumptionRecord


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ("id", "user_id", "category", "start_date", "end_date", "duration_days", "half_day", "half_day_period", "station_leave_required", "station_leave_from", "station_leave_until", "substitute_user_id", "substitute_consent", "reason", "status", "current_approver_user_id", "submitted_at", "decided_at", "related_request_id", "source", "external_reference", "created_at", "updated_at")
        read_only_fields = ("id", "user_id", "substitute_consent", "status", "current_approver_user_id", "submitted_at", "decided_at", "source", "external_reference", "created_at", "updated_at")


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ("category", "start_date", "end_date", "duration_days", "half_day", "half_day_period", "station_leave_required", "station_leave_from", "station_leave_until", "substitute_user_id", "reason")


class TaskSerializer(serializers.ModelSerializer):
    request = LeaveRequestSerializer(read_only=True)
    class Meta:
        model = ApprovalTask
        fields = ("id", "request", "stage", "approver_user_id", "status", "decision_note", "acted_at", "due_at", "created_at")
        read_only_fields = fields


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "category", "leave_year", "opening", "credited", "consumed", "adjusted", "available")
        read_only_fields = fields


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id", "category", "annual_entitlement", "carry_forward_limit", "applies_to", "requires_substitute", "counts_closed_days", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendarDay
        fields = ("id", "date", "title", "day_type", "is_published")


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRecord
        fields = ("id", "request", "reported_on", "remarks", "status", "verified_by_user_id", "verified_at", "created_at")
        read_only_fields = ("id", "status", "verified_by_user_id", "verified_at", "created_at")
