from rest_framework import serializers
from ..models import (
    ExpenseRequest,
    TravelAllowanceClaim,
    DepartmentBudget,
    AnomalyRecord,
    AuditObservation,
    ApprovalAction,
)

class ExpenseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseRequest
        fields = "__all__"
        read_only_fields = (
            "id",
            "status",
            "is_locked",
            "current_authority_role",
            "current_authority_user_id",
            "submission_date",
            "created_at",
            "updated_at",
        )

class TravelAllowanceClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelAllowanceClaim
        fields = "__all__"
        read_only_fields = (
            "id",
            "status",
            "is_high_value",
            "is_locked",
            "current_authority_role",
            "current_authority_user_id",
            "created_at",
            "updated_at",
        )

class DepartmentBudgetSerializer(serializers.ModelSerializer):
    available_budget = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = DepartmentBudget
        fields = "__all__"

class AnomalyRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at")

class AuditObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditObservation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

class ApprovalActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalAction
        fields = "__all__"
        read_only_fields = ("id", "created_at")

class ExpenseRequestSubmitSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")

class ClarificationQuerySerializer(serializers.Serializer):
    query = serializers.CharField(required=True)

class ClarificationResponseSerializer(serializers.Serializer):
    response = serializers.CharField(required=True)

class ApprovalDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[("approve", "Approve"), ("reject", "Reject")])
    remarks = serializers.CharField(required=True)
    actor_role = serializers.CharField(required=False, default="hod")

class AnomalyResolutionSerializer(serializers.Serializer):
    resolution = serializers.ChoiceField(choices=[("resolve", "Resolve"), ("escalate", "Escalate")])
    remarks = serializers.CharField(required=True)

class AuditResponseSerializer(serializers.Serializer):
    department_response = serializers.CharField(required=True)

class AuditClosureSerializer(serializers.Serializer):
    closure_remarks = serializers.CharField(required=True)
