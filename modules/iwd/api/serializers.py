from rest_framework import serializers

from modules.iwd.models.audit import DecisionAuditTrail
from modules.iwd.models.complaint import Complaint, RepairAssessment
from modules.iwd.models.completion import (
    ComplaintFeedback,
    FinalBill,
    PhysicalVerification,
)
from modules.iwd.models.estimate import RepairEstimate, ReviewCommitteeOutcome
from modules.iwd.models.inventory import (
    InventoryItem,
    MaterialIssueLedger,
    ProcurementOrder,
)


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            "id",
            "complaint_id",
            "complainant_user_id",
            "category",
            "location",
            "urgency",
            "remarks",
            "status",
            "assigned_engineer_id",
            "is_urgent_escalated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "complaint_id",
            "complainant_user_id",
            "status",
            "assigned_engineer_id",
        ]


class RepairAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairAssessment
        fields = [
            "id",
            "complaint",
            "engineer_id",
            "assessment_details",
            "is_site_visit_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["complaint", "engineer_id"]


class RepairEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairEstimate
        fields = [
            "id",
            "complaint",
            "version",
            "engineer_id",
            "time_estimate_days",
            "materials_cost",
            "labor_cost",
            "other_cost",
            "total_cost",
            "cost_band",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "complaint",
            "version",
            "engineer_id",
            "total_cost",
            "cost_band",
            "status",
        ]


class ReviewCommitteeOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewCommitteeOutcome
        fields = [
            "id",
            "estimate",
            "reviewer_user_id",
            "is_feasible",
            "is_necessary",
            "remarks",
            "reviewed_at",
        ]
        read_only_fields = ["estimate", "reviewer_user_id"]


class DecisionAuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionAuditTrail
        fields = [
            "id",
            "complaint",
            "estimate",
            "actor_user_id",
            "acting_role",
            "action",
            "from_state",
            "to_state",
            "decision_reason",
            "timestamp",
        ]


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "item_code", "name", "category", "unit", "current_stock"]


class MaterialIssueLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialIssueLedger
        fields = ["id", "complaint", "item", "quantity", "issued_by_user_id", "issued_at"]


class ProcurementOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementOrder
        fields = [
            "id",
            "complaint",
            "estimate",
            "procurement_type",
            "vendor_name",
            "vendor_details",
            "quoted_amount",
            "compliance_confirmed",
            "status",
            "created_at",
        ]


class PhysicalVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhysicalVerification
        fields = [
            "id",
            "complaint",
            "verified_by_user_id",
            "is_approved",
            "verification_remarks",
            "rework_notes",
            "verified_at",
        ]
        read_only_fields = ["complaint", "verified_by_user_id"]


class FinalBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalBill
        fields = [
            "id",
            "complaint",
            "engineer_id",
            "invoice_number",
            "claimed_amount",
            "is_audited",
            "auditor_user_id",
            "audit_remarks",
            "audit_timestamp",
            "director_approved",
            "director_user_id",
            "director_approved_at",
            "settlement_status",
            "accounts_reference",
            "settled_at",
        ]
        read_only_fields = [
            "complaint",
            "engineer_id",
            "is_audited",
            "director_approved",
            "settlement_status",
        ]


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = [
            "id",
            "complaint",
            "user_id",
            "rating",
            "feedback_text",
            "post_repair_issue",
            "created_at",
        ]
        read_only_fields = ["complaint", "user_id"]
