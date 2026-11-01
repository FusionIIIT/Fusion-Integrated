"""Serializers for IWD complaints API."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from modules.iwd.models import Complaint, ComplaintTransition, Estimate


class ComplaintCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=[("civil", "Civil"), ("electrical", "Electrical")],
        required=True,
    )
    location = serializers.CharField(max_length=255, required=True, allow_blank=False)
    urgency = serializers.ChoiceField(
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("emergency", "Emergency")],
        default="low",
        required=False,
    )
    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ComplaintAssessmentSerializer(serializers.Serializer):
    """Input serializer for technical assessment findings (UC-IWD-015)."""

    assessment_details = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Detailed assessment of issue and repairs required.",
    )


class EstimateCreateSerializer(serializers.Serializer):
    """Input serializer for initial estimate submission (UC-IWD-021)."""

    estimated_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=True,
        help_text="Estimated total repair cost in INR.",
    )
    estimated_time = serializers.CharField(
        max_length=120,
        required=True,
        allow_blank=False,
        help_text="Estimated time to complete repair work.",
    )
    materials_summary = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Required materials and estimated quantities.",
    )
    supporting_details = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional remarks or justification.",
    )


class EstimateDetailSerializer(serializers.ModelSerializer):
    """Output serializer for estimate records."""

    class Meta:
        model = Estimate
        fields = [
            "id",
            "complaint_id",
            "engineer_id",
            "cost_band",
            "estimated_cost",
            "estimated_time",
            "materials_summary",
            "supporting_details",
            "submitted_at",
            "created_at",
        ]


class EstimateReviewActionSerializer(serializers.Serializer):
    """Input serializer for estimate review decisions across all cost bands."""

    action = serializers.ChoiceField(
        choices=[
            ("approve", "Approve"),
            ("reject", "Reject"),
            ("forward_to_director", "Forward to Director"),
            ("approve_bidding", "Approve for Bidding"),
            ("reject_bidding", "Reject Bidding"),
            ("record_committee_review", "Record Committee Review"),
        ],
        required=True,
    )
    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Rejection reason, committee findings, or optional approval remarks.",
    )


class ComplaintTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintTransition
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "actor_label",
            "reason",
            "created_at",
        ]


class ComplaintDetailSerializer(serializers.ModelSerializer):
    transitions = ComplaintTransitionSerializer(many=True, read_only=True)
    estimates = EstimateDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id",
            "user_id",
            "category",
            "location",
            "urgency",
            "remarks",
            "status",
            "assigned_engineer_id",
            "assigned_at",
            "assessment_details",
            "assessed_at",
            "created_at",
            "updated_at",
            "transitions",
            "estimates",
        ]


class ComplaintListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            "id",
            "user_id",
            "category",
            "location",
            "urgency",
            "status",
            "assigned_engineer_id",
            "created_at",
            "updated_at",
        ]

