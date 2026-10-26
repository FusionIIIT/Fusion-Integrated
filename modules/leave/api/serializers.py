"""DRF serializers for the Leave module."""

from rest_framework import serializers

from modules.leave.models import (
    HolidayCalendar,
    LeaveActionLog,
    LeaveApplication,
    LeaveBalance,
    LeaveTypeConfig,
    VacationPeriod,
)


class LeaveTypeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTypeConfig
        fields = [
            "code",
            "name",
            "annual_entitlement",
            "max_carry_forward",
            "is_continuous_counting",
            "requires_substitute",
            "applies_to",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "leave_type",
            "credited",
            "availed",
            "balance",
            "updated_at",
        ]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = [
            "id",
            "year",
            "date",
            "name",
            "is_restricted_holiday",
            "is_closed_holiday",
            "is_published",
        ]


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = [
            "id",
            "year",
            "name",
            "start_date",
            "end_date",
            "is_published",
        ]


class LeaveActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionLog
        fields = [
            "id",
            "actor_user_id",
            "action",
            "from_status",
            "to_status",
            "remarks",
            "created_at",
        ]


class LeaveApplicationReadSerializer(serializers.ModelSerializer):
    action_logs = LeaveActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_user_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day_type",
            "days_count",
            "reason",
            "status",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "is_station_leave",
            "station_departure_date",
            "station_arrival_date",
            "station_address",
            "contact_number",
            "unit_head_user_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "establishment_remarks",
            "sanctioning_authority_user_id",
            "sanction_decision",
            "sanction_remarks",
            "parent_leave_id",
            "is_cancellation_requested",
            "cancellation_reason",
            "resumption_status",
            "actual_resumption_date",
            "resumption_remarks",
            "resumption_days_adjusted",
            "is_offline",
            "offline_sanction_ref",
            "offline_sanction_date",
            "offline_sanctioned_by",
            "created_at",
            "updated_at",
            "action_logs",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day_type = serializers.CharField(max_length=16, default="FULL", required=False)
    reason = serializers.CharField(required=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    is_station_leave = serializers.BooleanField(required=False, default=False)
    station_departure_date = serializers.DateTimeField(required=False, allow_null=True)
    station_arrival_date = serializers.DateTimeField(required=False, allow_null=True)
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
    contact_number = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionSerializer(serializers.Serializer):
    decision = serializers.CharField(max_length=32)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class RemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteRespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReplaceSubstituteSerializer(serializers.Serializer):
    new_substitute_id = serializers.IntegerField()


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ExtensionRequestSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField()


class OfflineLeaveCreateSerializer(serializers.Serializer):
    applicant_user_id = serializers.IntegerField()
    applicant_kind = serializers.CharField(max_length=16, default="staff")
    leave_type = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    sanction_ref = serializers.CharField(max_length=64)
    sanction_date = serializers.DateField()
    sanctioned_by = serializers.CharField(max_length=100)
    half_day_type = serializers.CharField(max_length=16, default="FULL")


class BalanceAdjustSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField()
    leave_type = serializers.CharField(max_length=8)
    delta = serializers.DecimalField(max_digits=5, decimal_places=1)
    is_credit = serializers.BooleanField(default=True)


class YearEndRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)


class YearEndResponseSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    next_year = serializers.IntegerField()
    employees_processed = serializers.IntegerField()
    total_vl_converted_to_el = serializers.CharField()


class SLAResponseSerializer(serializers.Serializer):
    reminded = serializers.IntegerField()
    escalated = serializers.IntegerField()


class ApplicationListResponseSerializer(serializers.Serializer):
    results = LeaveApplicationReadSerializer(many=True)


class BalanceListResponseSerializer(serializers.Serializer):
    results = LeaveBalanceSerializer(many=True)


class HolidayListResponseSerializer(serializers.Serializer):
    results = HolidayCalendarSerializer(many=True)


class VacationListResponseSerializer(serializers.Serializer):
    results = VacationPeriodSerializer(many=True)
