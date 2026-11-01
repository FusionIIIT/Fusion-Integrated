"""Serializers for Employee Leave Management (ELM) API."""
from rest_framework import serializers
from modules.leave.domain.constants import HalfDayOption, LeaveCategory, UnitHeadDecision
from modules.leave.models import (
    HolidayCalendar,
    LeaveActionLog,
    LeaveBalance,
    LeavePolicyConfig,
    LeaveRequest,
    SLAConfig,
    VacationPeriod,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "year", "category", "credited", "availed", "balance"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "name", "is_restricted", "year", "published"]


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "name", "start_date", "end_date", "year"]


class LeaveActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionLog
        fields = ["id", "leave_request_id", "actor_user_id", "action", "from_status", "to_status", "remarks", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    action_logs = LeaveActionLogSerializer(many=True, read_only=True, source="leaveactionlog_set")

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "computed_days",
            "reason",
            "status",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "station_leave",
            "station_address",
            "station_contact",
            "station_start_date",
            "station_end_date",
            "medical_certificate_url",
            "unit_head_user_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "sanctioning_authority_user_id",
            "sanction_remarks",
            "offline_entry",
            "offline_reference",
            "cancellation_reason",
            "extension_base_request_id",
            "extension_days",
            "resumption_date",
            "resumption_remarks",
            "resumption_status",
            "created_at",
            "updated_at",
            "action_logs",
        ]


class ApplyLeaveInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[c.value for c in LeaveCategory])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=[h.value for h in HalfDayOption], required=False, default="NONE")
    reason = serializers.CharField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_contact = serializers.CharField(required=False, allow_blank=True, default="")
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    medical_certificate_url = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseInputSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReplaceSubstituteInputSerializer(serializers.Serializer):
    new_substitute_user_id = serializers.IntegerField()


class UnitHeadReviewInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[d.value for d in UnitHeadDecision])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionInputSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CancelRequestInputSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField()


class ExtensionRequestInputSerializer(serializers.Serializer):
    extended_end_date = serializers.DateField()
    reason = serializers.CharField()


class ResumptionInputSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewResumptionInputSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class OfflineLeaveInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[c.value for c in LeaveCategory])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    offline_reference = serializers.CharField()


class YearEndProcessingInputSerializer(serializers.Serializer):
    year = serializers.IntegerField()
