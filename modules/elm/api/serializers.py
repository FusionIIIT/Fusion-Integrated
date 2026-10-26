"""ELM serializers."""
from __future__ import annotations

from rest_framework import serializers

from modules.elm.models import (
    CATEGORY_CHOICES,
    HALF_CHOICES,
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    VacationCalendar,
)


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=HALF_CHOICES,
                                   required=False, default="full")
    purpose = serializers.CharField(required=False, allow_blank=True,
                                    max_length=2000)
    department = serializers.CharField(required=False, allow_blank=True,
                                       max_length=64, default="")
    station_leave = serializers.JSONField(required=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ["id", "user_id", "department", "category", "start_date", "end_date", "half",
                  "purpose", "station_leave", "substitute_user_id",
                  "substitute_status", "status", "chargeable_days",
                  "recommended_by_user_id", "recommended_at", "recommendation",
                  "recommendation_note", "decided_by_user_id", "decided_at",
                  "decision_note", "actual_resumption_date", "resumption_note",
                  "is_offline_record", "offline_sanction_reference",
                  "created_at", "updated_at"]


class SubstituteRespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class RenominateSubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class RecommendSerializer(serializers.Serializer):
    recommended = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class DecideSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True,
                                 max_length=2000)


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ReviewResumptionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=HALF_CHOICES,
                                   required=False, default="full")
    purpose = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    sanction_reference = serializers.CharField(max_length=200)
    department = serializers.CharField(required=False, allow_blank=True, max_length=64, default="")


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=7, decimal_places=1,
                                         read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["category", "entitled", "used", "available"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "kind", "label", "is_published"]


class VacationCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationCalendar
        fields = ["id", "name", "start_date", "end_date", "is_active"]
