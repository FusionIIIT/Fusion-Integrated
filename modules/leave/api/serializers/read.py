"""API serializers for Leave Management — read serializers."""
from rest_framework import serializers
from ...models import (
    LeaveRequest,
    LeaveBalance,
    LeavePolicy,
    HolidayCalendar,
    SubstituteRequest,
    OfflineLeaveEntry,
    LeaveRequestTransition,
)


class LeavePolicyReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = [
            "id", "category", "employee_type", "annual_entitlement",
            "carries_forward", "half_day_allowed", "requires_medical_certificate",
            "max_per_request", "effective_from", "effective_to", "is_active",
            "created_at", "updated_at",
        ]


class HolidayCalendarReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "name", "is_restricted", "year", "is_active", "created_at", "updated_at"]


class LeaveBalanceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id", "user_id", "category", "year",
            "opening_balance", "credited", "availed", "lapsed", "closing_balance",
            "created_at", "updated_at",
        ]


class LeaveRequestTransitionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestTransition
        fields = [
            "id", "from_status", "to_status", "actor_user_id",
            "actor_role", "reason", "metadata", "created_at",
        ]


class SubstituteRequestReadSerializer(serializers.ModelSerializer):
    leave_request_category = serializers.CharField(source="leave_request.category", read_only=True)
    leave_request_status = serializers.CharField(source="leave_request.status", read_only=True)
    leave_request_start = serializers.DateField(source="leave_request.start_date", read_only=True)
    leave_request_end = serializers.DateField(source="leave_request.end_date", read_only=True)

    class Meta:
        model = SubstituteRequest
        fields = [
            "id", "leave_request", "leave_request_category", "leave_request_status",
            "leave_request_start", "leave_request_end", "substitute_id",
            "nominated_by", "status", "responded_at", "reason",
            "created_at", "updated_at",
        ]


class LeaveRequestReadSerializer(serializers.ModelSerializer):
    transitions = LeaveRequestTransitionReadSerializer(many=True, read_only=True)
    substitute_requests = SubstituteRequestReadSerializer(many=True, read_only=True)
    extension_of_category = serializers.CharField(source="extension_of.category", read_only=True)
    original_request_category = serializers.CharField(source="original_request.category", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "category", "start_date", "end_date",
            "half_day", "half_day_session", "total_days", "purpose",
            "station_leave", "station_leave_address", "substitute_id",
            "status", "medical_certificate", "unit_head_id", "unit_head_remark",
            "unit_head_action_at", "establishment_id", "establishment_remark",
            "establishment_action_at", "final_authority_id", "final_authority_remark",
            "final_authority_action_at", "applied_at", "approved_at", "rejected_at",
            "extension_of", "extension_of_category", "original_request",
            "original_request_category", "resumption_date",
            "resumption_verified_by", "resumption_verified_at",
            "transitions", "substitute_requests",
            "created_at", "updated_at",
        ]


class OfflineLeaveEntryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineLeaveEntry
        fields = [
            "id", "user_id", "category", "start_date", "end_date",
            "total_days", "sanction_order_number", "sanction_order_date",
            "sanctioning_authority", "remarks", "entered_by",
            "verified", "verified_by", "verified_at",
            "created_at", "updated_at",
        ]


class LeaveRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "category", "start_date", "end_date",
            "half_day", "total_days", "purpose", "station_leave",
            "substitute_id", "status", "applied_at", "approved_at",
            "created_at", "updated_at",
        ]