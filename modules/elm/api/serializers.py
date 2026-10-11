"""ELM serializers."""
from __future__ import annotations

from rest_framework import serializers

from modules.elm.models import CATEGORY_CHOICES, HolidayCalendar, LeaveApplication, LeaveBalance


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=["full", "first", "second"],
                                   required=False, default="full")
    purpose = serializers.CharField(required=False, allow_blank=True,
                                    max_length=2000)
    station_leave = serializers.JSONField(required=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ["id", "user_id", "category", "start_date", "end_date", "half",
                  "purpose", "station_leave", "substitute_user_id",
                  "substitute_status", "status", "chargeable_days",
                  "decided_by_user_id", "decided_at", "decision_note",
                  "created_at", "updated_at"]


class SubstituteRespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class DecideSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True,
                                 max_length=2000)


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
