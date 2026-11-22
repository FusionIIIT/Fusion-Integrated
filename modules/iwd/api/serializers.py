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
        fields = "__all__"
        read_only_fields = ["complaint_id", "complainant_user_id", "status", "assigned_engineer_id"]


class RepairAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairAssessment
        fields = "__all__"
        read_only_fields = ["complaint", "engineer_id"]


class RepairEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairEstimate
        fields = "__all__"
        read_only_fields = ["complaint", "version", "engineer_id", "total_cost", "cost_band", "status"]


class ReviewCommitteeOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewCommitteeOutcome
        fields = "__all__"
        read_only_fields = ["estimate", "reviewer_user_id"]


class DecisionAuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionAuditTrail
        fields = "__all__"


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"


class MaterialIssueLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialIssueLedger
        fields = "__all__"


class ProcurementOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementOrder
        fields = "__all__"


class PhysicalVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhysicalVerification
        fields = "__all__"
        read_only_fields = ["complaint", "verified_by_user_id"]


class FinalBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalBill
        fields = "__all__"
        read_only_fields = ["complaint", "engineer_id", "is_audited", "director_approved", "settlement_status"]


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = "__all__"
        read_only_fields = ["complaint", "user_id"]
