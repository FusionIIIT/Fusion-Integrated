"""Wire shapes for ELM's endpoints."""
from __future__ import annotations

from rest_framework import serializers

from modules.elm.models import Category, HalfDay


class LeaveRequestSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    applicant_user_id = serializers.IntegerField(read_only=True)
    category = serializers.ChoiceField(choices=Category.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=HalfDay.choices, default=HalfDay.NONE)
    station_leave = serializers.BooleanField(default=False)
    station_leave_details = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(read_only=True)
    unit_head_user_id = serializers.IntegerField()
    unit_head_remarks = serializers.CharField(read_only=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    substitute_consent = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class DecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
