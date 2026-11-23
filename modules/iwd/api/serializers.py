"""DRF serializers for the IWD module."""

from rest_framework import serializers

from modules.iwd.models import (
    Complaint,
    ComplaintFeedback,
    DecisionAuditTrail,
    Estimate,
    FinalBill,
    InventoryItem,
    MaterialIssue,
    VerificationRecord,
)


class DecisionAuditTrailSerializer(serializers.ModelSerializer):
    """Serializer for immutable workflow audit trails."""

    class Meta:
        """Model serializer configuration."""

        model = DecisionAuditTrail
        fields = [
            "id",
            "actor_user_id",
            "actor_role",
            "action",
            "previous_state",
            "new_state",
            "remarks",
            "timestamp",
        ]
        read_only_fields = fields


class ComplaintSerializer(serializers.ModelSerializer):
    """Serializer for maintenance complaints."""

    audit_trails = DecisionAuditTrailSerializer(many=True, read_only=True)

    class Meta:
        """Model serializer configuration."""

        model = Complaint
        fields = [
            "id",
            "requester_user_id",
            "category",
            "location",
            "urgency",
            "remarks",
            "assigned_engineer_id",
            "status",
            "assessment_details",
            "assessment_date",
            "is_urgent_escalated",
            "urgent_remarks",
            "is_resolved",
            "resolved_at",
            "rework_count",
            "created_at",
            "updated_at",
            "audit_trails",
        ]
        read_only_fields = [
            "id",
            "requester_user_id",
            "assigned_engineer_id",
            "status",
            "assessment_date",
            "is_resolved",
            "resolved_at",
            "rework_count",
            "created_at",
            "updated_at",
        ]


class EstimateSerializer(serializers.ModelSerializer):
    """Serializer for repair estimates."""

    class Meta:
        """Model serializer configuration."""

        model = Estimate
        fields = [
            "id",
            "complaint",
            "engineer_user_id",
            "estimated_time_days",
            "materials_details",
            "total_cost",
            "cost_band",
            "committee_outcome",
            "committee_approved",
            "dept_head_decision",
            "dept_head_remarks",
            "director_decision",
            "director_remarks",
            "rejection_reason",
            "resubmission_count",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "engineer_user_id",
            "cost_band",
            "resubmission_count",
            "status",
            "created_at",
            "updated_at",
        ]


class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for inventory items."""

    class Meta:
        """Model serializer configuration."""

        model = InventoryItem
        fields = ["id", "name", "category", "stock_quantity", "unit", "unit_price"]


class MaterialIssueSerializer(serializers.ModelSerializer):
    """Serializer for material issue records."""

    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        """Model serializer configuration."""

        model = MaterialIssue
        fields = [
            "id",
            "complaint",
            "item",
            "item_name",
            "quantity",
            "issued_by_user_id",
            "issued_at",
            "remarks",
        ]
        read_only_fields = ["id", "issued_by_user_id", "issued_at"]


class VerificationRecordSerializer(serializers.ModelSerializer):
    """Serializer for physical verification records."""

    class Meta:
        """Model serializer configuration."""

        model = VerificationRecord
        fields = [
            "id",
            "complaint",
            "verifier_user_id",
            "outcome",
            "remarks",
            "verified_at",
            "traversal_number",
        ]
        read_only_fields = ["id", "verifier_user_id", "verified_at", "traversal_number"]


class FinalBillSerializer(serializers.ModelSerializer):
    """Serializer for final bills and audit records."""

    class Meta:
        """Model serializer configuration."""

        model = FinalBill
        fields = [
            "id",
            "complaint",
            "engineer_user_id",
            "total_amount",
            "auditor_status",
            "auditor_remarks",
            "audited_at",
            "director_approved",
            "director_approved_at",
            "settled",
            "settled_at",
            "settlement_reference",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "engineer_user_id",
            "auditor_status",
            "auditor_remarks",
            "audited_at",
            "director_approved",
            "director_approved_at",
            "settled",
            "settled_at",
            "created_at",
        ]


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for complaint feedback."""

    class Meta:
        """Model serializer configuration."""

        model = ComplaintFeedback
        fields = [
            "id",
            "complaint",
            "employee_user_id",
            "rating",
            "comments",
            "post_repair_issue",
            "post_repair_remarks",
            "submitted_at",
        ]
        read_only_fields = ["id", "employee_user_id", "submitted_at"]
