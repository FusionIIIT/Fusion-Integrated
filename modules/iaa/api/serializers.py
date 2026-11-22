from rest_framework import serializers

from modules.iaa.models import (
    Anomaly,
    ApprovalAction,
    AuditObservation,
    ClarificationQuery,
    DepartmentBudget,
    ExpenseItem,
    ExpenseVoucherRequest,
    IAAConfiguration,
    TAClaim,
    TAExpenseItem,
)


class ExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseItem
        fields = ["id", "description", "category", "amount", "receipt_reference", "created_at"]


class ExpenseVoucherRequestSerializer(serializers.ModelSerializer):
    items = ExpenseItemSerializer(many=True, read_only=True)

    class Meta:
        model = ExpenseVoucherRequest
        fields = [
            "id",
            "user_id",
            "department",
            "request_type",
            "title",
            "description",
            "total_amount",
            "status",
            "current_approval_level",
            "required_approval_levels",
            "assigned_approver_role",
            "assigned_approver_id",
            "approval_assigned_at",
            "is_locked",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "status",
            "current_approval_level",
            "required_approval_levels",
            "assigned_approver_role",
            "assigned_approver_id",
            "approval_assigned_at",
            "is_locked",
            "created_at",
            "updated_at",
        ]


class CreateExpenseRequestInputSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=64)
    request_type = serializers.ChoiceField(choices=["expense", "voucher"])
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    items = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class TAExpenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAExpenseItem
        fields = ["id", "expense_type", "amount", "details", "created_at"]


class TAClaimSerializer(serializers.ModelSerializer):
    items = TAExpenseItemSerializer(many=True, read_only=True)

    class Meta:
        model = TAClaim
        fields = [
            "id",
            "user_id",
            "department",
            "purpose",
            "departure_date",
            "arrival_date",
            "source_location",
            "destination_location",
            "claimed_amount",
            "status",
            "is_high_value",
            "assigned_approver_role",
            "assigned_approver_id",
            "approval_assigned_at",
            "is_locked",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "status",
            "is_high_value",
            "assigned_approver_role",
            "assigned_approver_id",
            "approval_assigned_at",
            "is_locked",
            "created_at",
            "updated_at",
        ]


class SubmitTAClaimInputSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=64)
    purpose = serializers.CharField(max_length=255)
    departure_date = serializers.DateField()
    arrival_date = serializers.DateField()
    source_location = serializers.CharField(max_length=128)
    destination_location = serializers.CharField(max_length=128)
    claimed_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    items = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ApprovalActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalAction
        fields = [
            "id",
            "content_type",
            "object_id",
            "actor_id",
            "actor_role",
            "decision",
            "remarks",
            "level",
            "created_at",
        ]


class ApprovalDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(min_length=1, allow_blank=False)


class ClarificationQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClarificationQuery
        fields = [
            "id",
            "content_type",
            "object_id",
            "sender_id",
            "sender_role",
            "query_text",
            "response_text",
            "status",
            "created_at",
            "responded_at",
        ]


class ClarificationQueryInputSerializer(serializers.Serializer):
    query_text = serializers.CharField(min_length=1, allow_blank=False)


class ClarificationResponseInputSerializer(serializers.Serializer):
    response_text = serializers.CharField(min_length=1, allow_blank=False)


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = [
            "id",
            "category",
            "description",
            "reference_type",
            "reference_id",
            "status",
            "flagged_by_id",
            "flagged_by_role",
            "resolver_role",
            "resolved_by_id",
            "resolution_remarks",
            "created_at",
            "resolved_at",
        ]


class CreateAnomalyInputSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=64)
    description = serializers.CharField(min_length=1)
    reference_type = serializers.CharField(max_length=32)
    reference_id = serializers.IntegerField()


class AnomalyResolutionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["resolve", "escalate"])
    remarks = serializers.CharField(min_length=1)


class AuditObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditObservation
        fields = [
            "id",
            "auditor_id",
            "department",
            "reference_type",
            "reference_id",
            "title",
            "description",
            "status",
            "response_text",
            "responded_by_id",
            "responded_at",
            "closure_remarks",
            "created_at",
            "closed_at",
        ]


class RaiseAuditObservationInputSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=64)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(min_length=1)
    reference_type = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default=""
    )
    reference_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class AuditObservationResponseInputSerializer(serializers.Serializer):
    response_text = serializers.CharField(min_length=1)


class AuditObservationClosureInputSerializer(serializers.Serializer):
    is_satisfactory = serializers.BooleanField()
    remarks = serializers.CharField(min_length=1)


class IAAConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAConfiguration
        fields = [
            "id",
            "financial_year",
            "high_value_ta_threshold",
            "approval_timeout_days",
            "is_active",
            "updated_at",
        ]


class DepartmentBudgetSerializer(serializers.ModelSerializer):
    available_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = DepartmentBudget
        fields = [
            "id",
            "department",
            "financial_year",
            "allocated_amount",
            "utilized_amount",
            "available_amount",
        ]
