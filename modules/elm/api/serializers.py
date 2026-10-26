"""DRF serializers for ELM API."""
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveAuditTrail,
    LeaveBalance,
    LeaveCancellationRequest,
    LeaveExtensionRequest,
    LeaveResumptionReport,
    LeaveType,
    OfflineSanctionRecord,
)


class LeaveTypeSerializer(ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "code",
            "name",
            "max_days_per_year",
            "is_continuous_count",
            "is_faculty_only",
            "is_non_faculty_only",
            "carries_forward",
            "requires_document",
            "is_active",
        ]


class LeaveBalanceSerializer(ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    available = SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "year",
            "allotted",
            "used",
            "credited_from_vl",
            "available",
        ]

    def get_available(self, obj) -> float:
        return float(obj.allotted - obj.used)


class LeaveAuditTrailSerializer(ModelSerializer):
    class Meta:
        model = LeaveAuditTrail
        fields = [
            "id",
            "actor_id",
            "action",
            "from_status",
            "to_status",
            "remarks",
            "created_at",
        ]


class LeaveApplicationSerializer(ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    audit_trail = LeaveAuditTrailSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "employee_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "start_date",
            "end_date",
            "is_half_day",
            "half_day_period",
            "days",
            "reason",
            "status",
            "is_station_leave",
            "station_destination",
            "station_start_date",
            "station_end_date",
            "station_address",
            "station_contact_no",
            "substitute_id",
            "substitute_status",
            "substitute_declined_reason",
            "substitute_responded_at",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_decided_at",
            "establishment_id",
            "establishment_remarks",
            "establishment_routed_at",
            "sanctioning_authority_id",
            "sanctioning_authority_role",
            "remarks",
            "decided_at",
            "audit_trail",
            "created_at",
            "updated_at",
        ]


class ApplyInputSerializer(serializers.Serializer):
    leave_type = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    is_half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(
        choices=["NONE", "FIRST_HALF", "SECOND_HALF"], default="NONE"
    )
    is_station_leave = serializers.BooleanField(default=False)
    station_destination = serializers.CharField(required=False, allow_blank=True, default="", max_length=256)
    station_start_date = serializers.DateField(required=False, allow_null=True, default=None)
    station_end_date = serializers.DateField(required=False, allow_null=True, default=None)
    station_address = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)
    station_contact_no = serializers.CharField(required=False, allow_blank=True, default="", max_length=32)
    substitute_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    declined_reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)


class SubstituteReplacementSerializer(serializers.Serializer):
    new_substitute_id = serializers.IntegerField()


class UnitHeadDecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["RECOMMENDED", "NOT_RECOMMENDED", "APPROVE", "REJECT"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
    has_establishment_step = serializers.BooleanField(default=False)


class EstablishmentRouteSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class SanctionDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    sanctioning_role = serializers.CharField(default="Dean", max_length=64)
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class DirectorSelfSanctionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class CancellationRequestInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class CancellationDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)
    is_final_authority = serializers.BooleanField(default=False)


class ExtensionRequestInputSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    substitute_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    reason_for_difference = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class ResumptionReviewSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class HolidayCalendarSerializer(ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "date", "name", "is_restricted_holiday", "is_closed_holiday", "is_published"]


class OfflineSanctionInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    leave_type_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    sanction_order_no = serializers.CharField(max_length=128)
    sanction_order_date = serializers.DateField()
    sanctioned_by_role = serializers.CharField(max_length=64)
    remarks = serializers.CharField(required=False, allow_blank=True, default="", max_length=2000)


class YearEndProcessingInputSerializer(serializers.Serializer):
    old_year = serializers.IntegerField()
    new_year = serializers.IntegerField()
    employee_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    faculty_user_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
