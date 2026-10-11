"""
DRF Serializers for Leave Management.
Implements serialization/deserialization for LeaveApplication, LeaveBalance, and LeaveActionHistory.
Includes input serializers for application creation and decision recording.
"""

from typing import Any, Dict, List, Optional
from rest_framework import serializers
from django.db.models import QuerySet

from modules.directory.serializers import UserRefSerializer
from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveActionHistory,
    LeaveCategory,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Serializer for LeaveBalance model."""

    class Meta:
        model = LeaveBalance
        fields = ["id", "category", "year", "available_days", "used_days"]
        read_only_fields = ["id", "year"]


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    """Serializer for LeaveActionHistory model."""

    class Meta:
        model = LeaveActionHistory
        fields = [
            "id",
            "application_id",
            "actor_id",
            "action_type",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeaveApplicationDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed LeaveApplication view."""

    category_display = serializers.CharField(source="category", read_only=True)
    status_display = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "category",
            "requested_from",
            "requested_to",
            "purpose",
            "station_leave_details",
            "nominated_substitute_id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "category",
            "status",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationListSerializer(serializers.ModelSerializer):
    """Serializer for list of LeaveApplications (pagination-ready)."""

    category_display = serializers.CharField(source="category", read_only=True)
    status_display = serializers.CharField(source="status", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "category",
            "requested_from",
            "requested_to",
            "purpose",
            "status",
            "created_at",
        ]


class ApplyLeaveSerializer(serializers.Serializer):
    """Input serializer for creating a new leave application."""

    category = serializers.ChoiceField(
        choices=LeaveCategory.choices,
        required=True,
    )
    requested_from = serializers.DateField(required=True)
    requested_to = serializers.DateField(required=True)
    purpose = serializers.CharField(required=True, max_length=500)
    station_leave_details = serializers.JSONField(required=False, allow_null=True)
    nominated_substitute_id = serializers.IntegerField(required=False, allow_null=True)


class RespondToSubstituteRequestSerializer(serializers.Serializer):
    """Input serializer for responding to a substitute request."""

    accept = serializers.BooleanField(required=True)


class NominateReplacementSubstituteSerializer(serializers.Serializer):
    """Input serializer for nominating a replacement substitute."""

    new_substitute_id = serializers.IntegerField(required=True)


class UnitHeadReviewDecisionSerializer(serializers.Serializer):
    """Input serializer for Unit Head review decision (CL/RH)."""

    decision = serializers.ChoiceField(
        choices=["approve", "reject"],
        required=True,
    )


class UnitHeadRecommendationSerializer(serializers.Serializer):
    """Input serializer for Unit Head recommendation (SCL/EL/COL/VL)."""

    decision = serializers.ChoiceField(
        choices=["recommended", "not_recommended"],
        required=True,
    )


class EstablishmentVerifyAndRouteSerializer(serializers.Serializer):
    """Input serializer for establishment verification and routing."""

    pass  # No additional data needed, uses application context


class FinalSanctionDecisionSerializer(serializers.Serializer):
    """Input serializer for final sanctioning decision."""

    decision = serializers.ChoiceField(
        choices=["approve", "reject"],
        required=True,
    )


class RequestWithdrawalSerializer(serializers.Serializer):
    """Input serializer for withdrawing a pending request."""

    pass  # No additional data needed


class RequestCancellationSerializer(serializers.Serializer):
    """Input serializer for requesting cancellation of an approved leave."""

    pass  # No additional data needed


class RequestExtensionSerializer(serializers.Serializer):
    """Input serializer for requesting an extension of ongoing leave."""

    extension_from = serializers.DateField(required=True)
    extension_to = serializers.DateField(required=True)
    purpose = serializers.CharField(required=True, max_length=500)
    station_leave_details = serializers.JSONField(required=False, allow_null=True)
    nominated_substitute_id = serializers.IntegerField(required=False, allow_null=True)


class SubmitResumptionSerializer(serializers.Serializer):
    """Input serializer for submitting actual resumption of duty information."""

    actual_resumption_date = serializers.DateField(required=True)


class ReviewResumptionSerializer(serializers.Serializer):
    """Input serializer for reviewing the submitted resumption."""

    actual_resumption_date = serializers.DateField(required=True)
