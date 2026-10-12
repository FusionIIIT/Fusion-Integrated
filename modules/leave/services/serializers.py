"""Leave Management serializers.

Follows placement module pattern: thin serializers in api/serializers.py,
service logic in services/serializers.py.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from rest_framework import serializers


class LeaveCategorySerializer(serializers.ModelSerializer):
    """Leave category serializer."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["code", "label", "description"]
        extra_kwargs = {
            "code": {"required": True},
        }


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Leave balance serializer."""
    class Meta:
        model = None  # Will be set based on use case
        fields = [
            "user_id",
            "kind",
            "category_code",
            "year",
            "available",
            "used",
            "carried_over",
            "entitlement",
            "created_at",
        ]
        extra_kwargs = {
            "available": {"read_only": True},
            "used": {"read_only": True},
            "created_at": {"read_only": True},
        }


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Leave request serializer."""
    class Meta:
        model = None  # Will be set based on use case
        fields = [
            "id",
            "user_id",
            "category_code",
            "category_label",
            "status",
            "request_type",
            "start_date",
            "end_date",
            "duration_days",
            "reason",
            "station_leave",
            "approved_by",
            "approved_at",
            "cancelled_by",
            "cancelled_at",
            "resumed_by",
            "resumed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "start_date": {"required": True},
            "end_date": {"required": True},
            "reason": {"required": True},
            "category_code": {"required": True},
        }


class LeaveRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating a leave request."""
    user_id = serializers.IntegerField(required=True)
    category_code = serializers.CharField(required=True, max_length=2)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    reason = serializers.CharField(required=True)
    station_leave = serializers.BooleanField(default=False)


class LeaveRequestUpdateSerializer(serializers.Serializer):
    """Serializer for updating a leave request (draft only)."""
    reason = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    duration_days = serializers.IntegerField(required=False, min_value=1)


class LeaveBalanceQuerySerializer(serializers.Serializer):
    """Serializer for querying leave balances."""
    user_id = serializers.IntegerField(required=True)
    kind = serializers.ChoiceField(
        choices=[("faculty", "Faculty"), ("staff", "Staff"), ("student", "Student")],
        required=False,
    )
    year = serializers.IntegerField(required=False)


class LeaveRequestQuerySerializer(serializers.Serializer):
    """Serializer for querying leave requests."""
    user_id = serializers.IntegerField(required=False)
    category_code = serializers.CharField(required=False, max_length=2)
    status = serializers.ChoiceField(
        choices=[
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("cancelled", "Cancelled"),
            ("resumed", "Resumed"),
        ],
        required=False,
    )
    request_type = serializers.ChoiceField(
        choices=[
            ("initial", "Initial Request"),
            ("extension", "Extension Request"),
            ("resumption", "Resumption Request"),
        ],
        required=False,
    )


class LeaveSanctionSerializer(serializers.Serializer):
    """Serializer for leave sanction."""
    request_id = serializers.IntegerField(required=True)
    authority = serializers.CharField(required=True)
    authority_type = serializers.CharField(required=True)
    decision = serializers.ChoiceField(
        choices=[("Approved", "Approved"), ("Rejected", "Rejected"), ("Pending", "Pending")],
        required=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class LeavePolicySerializer(serializers.ModelSerializer):
    """Leave policy serializer."""
    class Meta:
        model = None  # Will be set based on use case
        fields = [
            "policy_name",
            "version",
            "effective_from",
            "effective_to",
            "cl_entitlement",
            "rh_entitlement",
            "scl_entitlement",
            "el_carry_forward",
            "is_active",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "effective_from": {"read_only": True},
            "effective_to": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }


class LeaveHolidayCalendarSerializer(serializers.Serializer):
    """Holiday calendar serializer."""
    year = serializers.IntegerField(required=True)
    holidays = serializers.ListField(
        child=serializers.DictField(keys=[("date", serializers.DateField), ("description", serializers.CharField)]),
        required=True,
    )
    published_at = serializers.DateField(required=False)
