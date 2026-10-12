"""Leave Management API serializers.

Follows placement module pattern: thin serializers in api/serializers.py,
service logic in services/serializers.py.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from rest_framework import serializers

from modules.leave.services import serializers as sv


class LeaveCategorySerializer(sv.LeaveCategorySerializer):
    """Leave category serializer for API."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["id", "code", "label", "description"]
        extra_kwargs = {
            "code": {"required": True},
        }


class LeaveBalanceSerializer(sv.LeaveBalanceSerializer):
    """Leave balance serializer for API."""
    class Meta:
        model = None  # Will be set based on use case
        fields = [
            "id",
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


class LeaveRequestSerializer(sv.LeaveRequestSerializer):
    """Leave request serializer for API."""
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


class LeaveRequestCreateSerializer(sv.LeaveRequestCreateSerializer):
    """Serializer for creating a leave request."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["user_id", "category_code", "start_date", "end_date", "reason", "station_leave"]


class LeaveRequestUpdateSerializer(sv.LeaveRequestUpdateSerializer):
    """Serializer for updating a leave request (draft only)."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["reason", "start_date", "end_date", "duration_days"]


class LeaveBalanceQuerySerializer(sv.LeaveBalanceQuerySerializer):
    """Serializer for querying leave balances."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["user_id", "kind", "year"]


class LeaveRequestQuerySerializer(sv.LeaveRequestQuerySerializer):
    """Serializer for querying leave requests."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["user_id", "category_code", "status", "request_type"]


class LeaveSanctionSerializer(sv.LeaveSanctionSerializer):
    """Serializer for leave sanction."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["request_id", "authority", "authority_type", "decision", "notes"]


class LeavePolicySerializer(sv.LeavePolicySerializer):
    """Leave policy serializer for API."""
    class Meta:
        model = None  # Will be set based on use case
        fields = [
            "id",
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


class LeaveHolidayCalendarSerializer(sv.LeaveHolidayCalendarSerializer):
    """Holiday calendar serializer for API."""
    class Meta:
        model = None  # Will be set based on use case
        fields = ["year", "holidays", "published_at"]
