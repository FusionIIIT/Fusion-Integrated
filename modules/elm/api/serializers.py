from rest_framework import serializers

from ..models import HolidayCalendar, LeaveApplication, LeavePolicy, RoleBasedUnit


class RoleBasedUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleBasedUnit
        fields = ("id", "code", "name", "description")
        read_only_fields = fields


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = (
            "id",
            "employee_type",
            "leave_type",
            "annual_quota",
            "carry_forward_days",
            "encashment_allowed",
            "min_service_days",
            "effective_from",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = (
            "id",
            "holiday_name",
            "holiday_date",
            "is_recurring",
            "is_optional",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeaveApplicationStatusChoices(serializers.ChoiceField):
    CHOICES = [
        ("pending", "Pending"),
        ("withdrawn", "Withdrawn"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    unit = RoleBasedUnitSerializer(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    leave_type_display = serializers.CharField(
        source="get_leave_type_display",
        read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "employee_user_id",
            "employee_name",
            "leave_type",
            "leave_type_display",
            "start_date",
            "end_date",
            "duration_days",
            "reason",
            "is_half_day",
            "status",
            "status_display",
            "unit",
            "unit_head_id",
            "substitute_id",
            "comments",
            "created_by",
            "last_action_by",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeaveApplicationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "employee_user_id",
            "employee_name",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "is_half_day",
            "status",
            "unit",
            "unit_head_id",
            "substitute_id",
            "comments",
        )
