from rest_framework import serializers

from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    SubstituteNomination,
)


class LeaveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCategory
        fields = [
            "code",
            "label",
            "annual_entitlement",
            "carry_forward",
            "continuous_day_counting",
            "applicable_to",
            "supports_half_day",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_category_code = serializers.SlugRelatedField(
        source="leave_category",
        slug_field="code",
        queryset=LeaveCategory.objects.all(),
    )
    leave_category_label = serializers.CharField(source="leave_category.label", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "pk",
            "employee_user_id",
            "leave_category_code",
            "leave_category_label",
            "requested_start",
            "requested_end",
            "day_part",
            "purpose_reason",
            "station_leave",
            "station_details",
            "status",
            "submitted_at",
            "nominated_substitute_user_id",
            "substitute_accepted",
            "substitute_decline_reason",
            "cancellation_status",
        ]
        read_only_fields = [
            "pk",
            "employee_user_id",
            "submitted_at",
            "status",
            "nominated_substitute_user_id",
            "substitute_accepted",
            "substitute_decline_reason",
            "cancellation_status",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_category_code = serializers.CharField(source="leave_category.code", read_only=True)
    category_label = serializers.CharField(source="leave_category.label", read_only=True)
    available_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = [
            "leave_category_code",
            "category_label",
            "entitlement_per_year",
            "used_per_year",
            "carried_forward_from_previous",
            "year",
            "available_days",
        ]

    def get_available_days(self, obj):
        return obj.available()


class SubstituteNominationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteNomination
        fields = [
            "pk",
            "leave_application",
            "nominee_user_id",
            "nominated_at",
            "status",
            "decline_reason",
        ]
        read_only_fields = ["pk", "nominated_at"]
