"""DRF Serializers for Leave Management."""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.models import (
    HolidayCalendar,
    LeaveActionHistory,
    LeaveApplication,
    LeaveBalance,
    LeaveLedgerEntry,
    SubstituteRequest,
    VacationPeriod,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "is_faculty",
            "cl_balance",
            "rh_balance",
            "scl_balance",
            "el_balance",
            "vl_balance",
            "col_balance",
        ]


class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = [
            "id",
            "category",
            "entry_type",
            "change_amount",
            "balance_after",
            "reference_id",
            "remarks",
            "created_at",
        ]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "name", "date", "kind", "year", "is_published"]


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "name", "start_date", "end_date", "year", "is_active"]


class SubstituteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteRequest
        fields = [
            "id",
            "application_id",
            "substitute_user_id",
            "status",
            "responsibilities",
            "response_remarks",
            "responded_at",
            "is_current",
            "created_at",
        ]


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = [
            "id",
            "actor_user_id",
            "actor_role",
            "action",
            "remarks",
            "created_at",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    substitute_requests = SubstituteRequestSerializer(many=True, read_only=True)
    actions = LeaveActionHistorySerializer(many=True, read_only=True)
    parent_leave_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "category",
            "parent_leave_id",
            "start_date",
            "end_date",
            "half_day_type",
            "days_count",
            "purpose",
            "address_during_leave",
            "is_station_leave",
            "station_departure_date",
            "station_arrival_date",
            "station_destination",
            "status",
            "unit_head_user_id",
            "unit_head_recommended",
            "unit_head_remarks",
            "unit_head_reviewed_at",
            "establishment_user_id",
            "establishment_remarks",
            "establishment_reviewed_at",
            "sanctioning_authority_user_id",
            "sanctioning_remarks",
            "cancellation_reason",
            "resumption_date",
            "resumption_reviewed_at",
            "resumption_outcome",
            "actual_days_count",
            "is_offline_sanctioned",
            "offline_reference_no",
            "substitute_requests",
            "actions",
            "created_at",
            "updated_at",
        ]


class ApplyLeaveSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "VL", "COL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=1000)
    half_day_type = serializers.ChoiceField(choices=["full", "first_half", "second_half"], default="full")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    responsibilities = serializers.CharField(required=False, allow_blank=True, default="")
    is_station_leave = serializers.BooleanField(default=False)
    station_departure_date = serializers.DateField(required=False, allow_null=True)
    station_arrival_date = serializers.DateField(required=False, allow_null=True)
    station_destination = serializers.CharField(required=False, allow_blank=True, default="")
    address_during_leave = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "declined"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReNominateSubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()
    responsibilities = serializers.CharField(required=False, allow_blank=True, default="")


class UnitHeadReviewSerializer(serializers.Serializer):
    recommended = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class ExtensionRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=1000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    responsibilities = serializers.CharField(required=False, allow_blank=True, default="")


class AdminConfigSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=80)
    value = serializers.JSONField()
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class HolidayCalendarEntrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=["closed", "restricted"])


class HolidayCalendarImportSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    entries = HolidayCalendarEntrySerializer(many=True)


class VacationPeriodEntrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class VacationPeriodsSyncSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    periods = VacationPeriodEntrySerializer(many=True)


class ResumptionSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class OfflineLeaveSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "VL", "COL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days_count = serializers.DecimalField(max_digits=5, decimal_places=1)
    offline_reference_no = serializers.CharField(max_length=120)
    offline_sanction_date = serializers.DateField()
    purpose = serializers.CharField(max_length=500)


class LeaveRecordCorrectionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    purpose = serializers.CharField(max_length=1000, required=False)
    address_during_leave = serializers.CharField(required=False, allow_blank=True)
    is_station_leave = serializers.BooleanField(required=False)
    station_departure_date = serializers.DateField(required=False, allow_null=True)
    station_arrival_date = serializers.DateField(required=False, allow_null=True)
    station_destination = serializers.CharField(max_length=255, required=False, allow_blank=True)
