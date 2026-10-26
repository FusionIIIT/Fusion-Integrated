"""API serializers for Leave Management — write serializers."""
from rest_framework import serializers
from datetime import date
from ...models import (
    LeaveCategory,
    LeaveRequest,
    LeaveBalance,
    LeavePolicy,
    HolidayCalendar,
    SubstituteRequest,
    OfflineLeaveEntry,
)


class LeavePolicyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = [
            "category", "employee_type", "annual_entitlement",
            "carries_forward", "half_day_allowed", "requires_medical_certificate",
            "max_per_request", "effective_from", "effective_to", "is_active",
        ]

    def validate(self, data):
        if data["effective_to"] and data["effective_to"] < data["effective_from"]:
            raise serializers.ValidationError("effective_to must be after effective_from")
        return data


class HolidayCalendarWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["date", "name", "is_restricted", "year", "is_active"]


class LeaveBalanceAdjustSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=LeaveCategory.choices)
    year = serializers.IntegerField()
    adjustment = serializers.DecimalField(max_digits=6, decimal_places=2)
    reason = serializers.CharField(required=False, allow_blank=True)


class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "category", "start_date", "end_date", "half_day", "half_day_session",
            "purpose", "station_leave", "station_leave_address", "substitute_id",
        ]

    def validate(self, data):
        start = data["start_date"]
        end = data["end_date"]

        if end < start:
            raise serializers.ValidationError("end_date must be after or equal to start_date")

        if data.get("half_day") and start != end:
            raise serializers.ValidationError("Half-day leave must have same start and end date")

        if data.get("half_day") and not data.get("half_day_session"):
            raise serializers.ValidationError("half_day_session required for half-day leave")

        if data.get("category") == "RH" and data.get("half_day"):
            raise serializers.ValidationError("RH cannot be half-day")

        return data


class LeaveRequestSubmitSerializer(serializers.Serializer):
    """Empty serializer for submit action."""
    pass


class LeaveRequestModifySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "start_date", "end_date", "half_day", "half_day_session",
            "purpose", "station_leave", "station_leave_address", "substitute_id",
        ]


class LeaveRequestWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class LeaveRequestCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class LeaveRequestExtendSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["end_date", "purpose"]

    def validate_end_date(self, value):
        # Ensure new end_date is after original
        instance = self.instance
        if value <= instance.end_date:
            raise serializers.ValidationError("New end date must be after current end date")
        return value


class LeaveRequestResumeSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()


class SubstituteRequestRespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True)


class UnitHeadReviewSerializer(serializers.Serializer):
    recommend = serializers.BooleanField()
    remark = serializers.CharField(required=False, allow_blank=True)


class EstablishmentReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[("forward", "Forward"), ("return", "Return")])
    remark = serializers.CharField(required=False, allow_blank=True)


class FinalSanctionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remark = serializers.CharField(required=False, allow_blank=True)


class OfflineLeaveEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineLeaveEntry
        fields = [
            "user_id", "category", "start_date", "end_date",
            "total_days", "sanction_order_number", "sanction_order_date",
            "sanctioning_authority", "remarks",
        ]