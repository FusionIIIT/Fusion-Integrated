"""HR-EIS API Serializers."""
from rest_framework import serializers

from modules.hreis.models import (
    AppraisalSubmission,
    CpdaRequest,
    EmployeeServiceRecord,
    HrAuditLog,
    HrNotification,
    LeaveRequest,
    LtcRequest,
    WorkflowConfiguration,
)


class EmployeeServiceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeServiceRecord
        fields = [
            "id",
            "user_id",
            "employee_id",
            "department",
            "designation",
            "category",
            "appointment_date",
            "retirement_date",
            "retirement_status",
            "service_history",
            "leave_balances",
            "cpda_balance",
            "ltc_eligible_block",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "duration_days",
            "justification",
            "status",
            "current_authority_role",
            "approval_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "status",
            "current_authority_role",
            "approval_history",
            "created_at",
            "updated_at",
        ]


class LeaveDecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "rejected", "forwarded"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class AppraisalSubmissionSerializer(serializers.ModelSerializer):
    content = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = AppraisalSubmission
        fields = [
            "id",
            "user_id",
            "academic_year",
            "status",
            "content",
            "assigned_reviewers",
            "reviews",
            "final_score",
            "final_remarks",
            "finalized_at",
            "is_immutable",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "status",
            "assigned_reviewers",
            "reviews",
            "final_score",
            "final_remarks",
            "finalized_at",
            "is_immutable",
            "created_at",
            "updated_at",
        ]


class AssignReviewersSerializer(serializers.Serializer):
    reviewer_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class AppraisalReviewSerializer(serializers.Serializer):
    score = serializers.FloatField(min_value=0.0, max_value=100.0)
    comments = serializers.CharField(required=True)


class AppraisalFinalizeSerializer(serializers.Serializer):
    final_score = serializers.FloatField(min_value=0.0, max_value=100.0)
    final_remarks = serializers.CharField(required=True)


class LtcRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LtcRequest
        fields = [
            "id",
            "user_id",
            "request_type",
            "block_year",
            "travel_from",
            "travel_to",
            "travel_start_date",
            "travel_end_date",
            "estimated_amount",
            "claimed_amount",
            "passed_amount",
            "supporting_documents",
            "verification_status",
            "verification_remarks",
            "status",
            "current_authority_role",
            "approval_history",
            "payment_status",
            "payment_reference",
            "settlement_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "verification_status",
            "verification_remarks",
            "status",
            "current_authority_role",
            "approval_history",
            "payment_status",
            "payment_reference",
            "settlement_details",
            "passed_amount",
            "created_at",
            "updated_at",
        ]


class ClaimVerificationSerializer(serializers.Serializer):
    verdict = serializers.ChoiceField(choices=["verified", "returned", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ClaimDecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "rejected", "forwarded"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LtcSettlementSerializer(serializers.Serializer):
    passed_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reference_id = serializers.CharField(max_length=128)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CpdaRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CpdaRequest
        fields = [
            "id",
            "user_id",
            "request_type",
            "purpose",
            "amount",
            "passed_amount",
            "supporting_documents",
            "verification_status",
            "verification_remarks",
            "status",
            "current_authority_role",
            "approval_history",
            "disbursement_status",
            "disbursement_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "verification_status",
            "verification_remarks",
            "status",
            "current_authority_role",
            "approval_history",
            "disbursement_status",
            "disbursement_details",
            "passed_amount",
            "created_at",
            "updated_at",
        ]


class CpdaSettlementSerializer(serializers.Serializer):
    passed_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    voucher_no = serializers.CharField(max_length=128)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class WorkflowConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowConfiguration
        fields = ["setting_key", "setting_value", "description", "updated_at"]
        read_only_fields = ["updated_at"]


class HrAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrAuditLog
        fields = [
            "id",
            "actor_id",
            "actor_username",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "details",
            "ip_address",
            "timestamp",
        ]


class HrNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HrNotification
        fields = ["id", "user_id", "title", "message", "category", "link", "is_read", "created_at"]


class DashboardStatsSerializer(serializers.Serializer):
    leave_balances = serializers.DictField(child=serializers.FloatField(), required=False)
    cpda_balance = serializers.FloatField(required=False)
    ltc_eligible_block = serializers.CharField(required=False)
    pending_leaves_count = serializers.IntegerField(default=0)
    pending_ltc_count = serializers.IntegerField(default=0)
    pending_cpda_count = serializers.IntegerField(default=0)
    pending_reviews_count = serializers.IntegerField(default=0)

