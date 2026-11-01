"""Serializers for IWD module."""
from rest_framework import serializers
from modules.iwd.models import (
    Complaint,
    Estimate,
    InventoryItem,
    InventoryMovement,
    ProcurementRequest,
    WorkVerification,
    BillAndSettlement,
    ComplaintFeedback,
)
from modules.iwd.domain.rules import determine_cost_band


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = "__all__"
        read_only_fields = ("status", "assigned_engineer_id", "created_at", "updated_at")


class EstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estimate
        fields = "__all__"
        read_only_fields = ("cost_band", "status", "approved_by", "created_at", "updated_at")

    def create(self, validated_data):
        total = validated_data.get("total_cost", 0)
        cost_band = determine_cost_band(total)
        validated_data["cost_band"] = cost_band
        if cost_band == "LOW":
            validated_data["status"] = "LOW_COST_PENDING"
        elif cost_band == "MID":
            validated_data["status"] = "MID_RANGE_COMMITTEE_PENDING"
        else:
            validated_data["status"] = "DIRECTOR_PENDING"
        return super().create(validated_data)


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"


class InventoryMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryMovement
        fields = "__all__"
        read_only_fields = ("created_at",)


class ProcurementRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementRequest
        fields = "__all__"
        read_only_fields = ("created_at",)


class WorkVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkVerification
        fields = "__all__"
        read_only_fields = ("verified_at",)


class BillAndSettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillAndSettlement
        fields = "__all__"
        read_only_fields = ("auditor_validated", "director_approved", "settlement_status", "created_at", "updated_at")


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = "__all__"
        read_only_fields = ("created_at",)

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

