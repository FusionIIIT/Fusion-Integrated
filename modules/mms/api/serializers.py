"""Serializers for Mess Management System (MMS) API."""

from rest_framework import serializers

from modules.mms.domain.constants import (
    DayOfWeek,
    FeedbackCategory,
    MealTime,
    MessRole,
)
from modules.mms.models import (
    DailyMenuItem,
    MessFeedback,
    MessRegistration,
    MessRoleAssignment,
    RebateRequest,
    RegistrationWindow,
)


class MessRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRoleAssignment
        fields = [
            "id",
            "employee_id",
            "role",
            "start_date",
            "end_date",
            "is_active",
            "assigned_by_id",
            "remarks",
            "created_at",
        ]


class AssignRoleInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=[r.value for r in MessRole])
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class RegistrationWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationWindow
        fields = [
            "id",
            "name",
            "mess_name",
            "start_date",
            "end_date",
            "is_open",
            "opened_by_id",
            "created_at",
        ]


class OpenWindowInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    mess_name = serializers.CharField(max_length=50, default="Central Mess")
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class MessRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessRegistration
        fields = [
            "id",
            "student_id",
            "window_id",
            "mess_name",
            "start_date",
            "end_date",
            "status",
            "remarks",
            "reviewed_by_id",
            "deregistration_date",
            "deregistration_reason",
            "created_at",
        ]


class SubmitRegistrationInputSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    mess_name = serializers.CharField(max_length=50, default="Central Mess")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewRegistrationInputSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubmitDeregistrationInputSerializer(serializers.Serializer):
    reason = serializers.CharField()


class DailyMenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMenuItem
        fields = [
            "id",
            "mess_name",
            "day_of_week",
            "meal_time",
            "items",
            "is_active",
            "updated_by_id",
            "updated_at",
        ]


class UpdateMenuItemInputSerializer(serializers.Serializer):
    day_of_week = serializers.ChoiceField(choices=[d.value for d in DayOfWeek])
    meal_time = serializers.ChoiceField(choices=[m.value for m in MealTime])
    items = serializers.CharField()
    mess_name = serializers.CharField(max_length=50, default="Central Mess")


class RebateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RebateRequest
        fields = [
            "id",
            "student_id",
            "mess_name",
            "start_date",
            "end_date",
            "duration_days",
            "reason",
            "status",
            "approved_start_date",
            "approved_end_date",
            "reviewed_by_id",
            "decision_remarks",
            "created_at",
        ]


class SubmitRebateInputSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    mess_name = serializers.CharField(max_length=50, default="Central Mess")


class ReviewRebateInputSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    approved_start_date = serializers.DateField(required=False, allow_null=True)
    approved_end_date = serializers.DateField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class MessFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessFeedback
        fields = [
            "id",
            "student_id",
            "mess_name",
            "rating",
            "category",
            "comments",
            "is_resolved",
            "resolution_notes",
            "created_at",
        ]


class SubmitFeedbackInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    category = serializers.ChoiceField(
        choices=[c.value for c in FeedbackCategory], default="GENERAL"
    )
    comments = serializers.CharField()
    mess_name = serializers.CharField(max_length=50, default="Central Mess")
