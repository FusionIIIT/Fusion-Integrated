from rest_framework import serializers

from modules.iaa.models import (
    Anomaly, ApprovalDecision, AuditObservation, ExpenseVoucherRequest, TAClaim,
)


class ExpenseVoucherRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseVoucherRequest
        fields = ["id", "creator_id", "request_type", "amount", "department",
                  "description", "status", "approval_level",
                  "approval_levels_required", "current_approver_id",
                  "query_text", "created_at", "updated_at"]
        read_only_fields = ["id", "creator_id", "status", "approval_level",
                            "current_approver_id", "query_text",
                            "created_at", "updated_at"]


class ExpenseCreateSerializer(serializers.Serializer):
    request_type = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    department = serializers.CharField(max_length=100)
    description = serializers.CharField(allow_blank=True, required=False, default="")


class TAClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = TAClaim
        fields = ["id", "employee_id", "trip_start", "trip_end", "purpose",
                  "claimed_amount", "status", "is_high_value", "approval_level",
                  "approval_levels_required", "current_approver_id",
                  "query_text", "created_at", "updated_at"]
        read_only_fields = ["id", "employee_id", "status", "is_high_value",
                            "approval_level", "current_approver_id",
                            "query_text", "created_at", "updated_at"]


class TAClaimCreateSerializer(serializers.Serializer):
    trip_start = serializers.DateField()
    trip_end = serializers.DateField()
    purpose = serializers.CharField()
    claimed_amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate(self, attrs):
        if attrs["trip_end"] < attrs["trip_start"]:
            raise serializers.ValidationError("trip_end cannot be before trip_start.")
        return attrs


class DecisionInputSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    remarks = serializers.CharField()


class ReviewInputSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    available_budget = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, default=None)
    query_text = serializers.CharField(allow_blank=True, required=False, default="")


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalDecision
        fields = ["id", "expense_request", "ta_claim", "approver_id",
                  "decision", "remarks", "level", "created_at"]
        read_only_fields = fields


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = ["id", "expense_request", "ta_claim", "category", "description",
                  "status", "resolver_id", "resolution_notes", "created_at"]
        read_only_fields = ["id", "status", "resolver_id", "resolution_notes", "created_at"]


class AnomalyFlagSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=50)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    expense_request_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    ta_claim_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class AnomalyResolveSerializer(serializers.Serializer):
    escalate = serializers.BooleanField()
    notes = serializers.CharField(allow_blank=True, required=False, default="")


class AuditObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditObservation
        fields = ["id", "expense_request", "ta_claim", "auditor_id", "description",
                  "status", "response_text", "created_at"]
        read_only_fields = ["id", "status", "response_text", "created_at"]


class AuditRaiseSerializer(serializers.Serializer):
    description = serializers.CharField()
    expense_request_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    ta_claim_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class AuditRespondSerializer(serializers.Serializer):
    response_text = serializers.CharField()


class AuditReviewCloseSerializer(serializers.Serializer):
    satisfactory = serializers.BooleanField()
