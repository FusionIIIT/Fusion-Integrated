from rest_framework import serializers

from modules.elm.models import HolidayCalendar, LeaveApplication, LeaveBalance


class LeaveApplicationReadSerializer(serializers.ModelSerializer):
    leave_category_display = serializers.CharField(
        source="get_leave_category_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_category",
            "leave_category_display",
            "start_date",
            "end_date",
            "chargeable_days",
            "reason",
            "half_day",
            "half_day_type",
            "station_leave",
            "station_start_date",
            "station_end_date",
            "station_address",
            "station_emergency_contact",
            "substitute_required",
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "status",
            "status_display",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_acted_at",
            "sanctioning_authority_id",
            "sanction_role",
            "sanction_decision",
            "sanction_remarks",
            "sanction_acted_at",
            "original_application_id",
            "resumption_date",
            "resumption_reason",
            "resumption_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_category = serializers.ChoiceField(choices=LeaveApplication.LEAVE_CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    half_day = serializers.BooleanField(default=False)
    half_day_type = serializers.ChoiceField(
        choices=LeaveApplication.HALF_DAY_CHOICES, allow_blank=True, default=""
    )
    station_leave = serializers.BooleanField(default=False)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    station_address = serializers.CharField(max_length=500, allow_blank=True, default="")
    station_emergency_contact = serializers.CharField(max_length=32, allow_blank=True, default="")
    substitute_required = serializers.BooleanField(default=False)
    substitute_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    category_display = serializers.CharField(source="get_leave_category_display", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "leave_category",
            "category_display",
            "credited",
            "used",
            "available",
        ]
        read_only_fields = fields


class SubstituteActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "declined"])
    remarks = serializers.CharField(max_length=500, allow_blank=True, default="")


class ReplacementSubstituteSerializer(serializers.Serializer):
    substitute_id = serializers.IntegerField()


class UnitHeadReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    remarks = serializers.CharField(max_length=1000, allow_blank=True, default="")


class EstablishmentRouteSerializer(serializers.Serializer):
    remarks = serializers.CharField(max_length=1000, allow_blank=True, default="")


class SanctionActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(max_length=1000, allow_blank=True, default="")


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, allow_blank=True, default="")


class ExtensionRequestSerializer(serializers.Serializer):
    extended_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=1000)
    substitute_id = serializers.IntegerField(required=False, allow_null=True)


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    resumption_reason = serializers.CharField(max_length=1000, allow_blank=True, default="")


class ResumptionReviewSerializer(serializers.Serializer):
    remarks = serializers.CharField(max_length=1000, allow_blank=True, default="")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "name", "date", "is_rh", "is_closed", "year", "is_published"]
        read_only_fields = fields
