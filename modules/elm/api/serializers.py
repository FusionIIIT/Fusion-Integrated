from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveHistory


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "employee_id",
            "is_faculty",
            "year",
            "leave_type",
            "total_allocated",
            "carried_forward",
            "used_days",
            "lapsed_days",
            "converted_days",
            "remaining_days",
        ]


class LeaveHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveHistory
        fields = [
            "id",
            "actor_id",
            "from_status",
            "to_status",
            "action",
            "remarks",
            "timestamp",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    history = LeaveHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "is_faculty",
            "is_director",
            "leave_type",
            "start_date",
            "end_date",
            "total_days",
            "is_half_day",
            "reason",
            "requires_station_leave",
            "station_leave_address",
            "station_departure_datetime",
            "station_arrival_datetime",
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "substitute_responded_at",
            "status",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_reviewed_at",
            "sanctioner_id",
            "sanction_decision",
            "sanction_remarks",
            "sanctioned_at",
            "is_extension",
            "parent_leave",
            "actual_resumption_date",
            "actual_days_availed",
            "resumption_verified_by",
            "resumption_verified_at",
            "is_offline_record",
            "offline_sanction_ref",
            "offline_sanction_date",
            "created_at",
            "updated_at",
            "history",
        ]
        read_only_fields = [
            "id",
            "applicant_id",
            "total_days",
            "status",
            "substitute_status",
            "unit_head_recommendation",
            "sanction_decision",
            "is_extension",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "VL", "COL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_half_day = serializers.BooleanField(default=False)
    reason = serializers.CharField(max_length=1000)
    requires_station_leave = serializers.BooleanField(default=False)
    station_leave_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_departure_datetime = serializers.DateTimeField(required=False, allow_null=True)
    station_arrival_datetime = serializers.DateTimeField(required=False, allow_null=True)
    substitute_id = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReplaceSubstituteSerializer(serializers.Serializer):
    new_substitute_id = serializers.CharField(required=False, allow_blank=True, default="")


class UnitHeadReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "recommend", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveExtensionSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class OfflineLeaveSerializer(serializers.Serializer):
    employee_id = serializers.CharField(max_length=64)
    is_faculty = serializers.BooleanField(default=False)
    leave_type = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "VL", "COL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    offline_sanction_ref = serializers.CharField(max_length=128)
    offline_sanction_date = serializers.DateField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, default="Offline paper sanction")


class YearEndProcessSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2020, max_value=2100)
