from rest_framework import serializers

from modules.iaa import domain
from modules.iaa.models import ExpenseRequest


class ExpenseRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseRequest
        fields = [
            "id", "creator_user_id", "department", "purpose", "amount", "status",
            "submitted_at", "finance_user_id", "validated_at", "approver_user_id",
            "decision_remarks", "decided_at", "recorded_by_user_id", "recorded_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [f for f in fields if f not in ("department", "purpose", "amount")]


class DecisionSerializer(serializers.Serializer):
    """Remarks may be blank here so IAA-BR-005 is enforced (and cited) by the domain."""

    decision = serializers.ChoiceField(choices=sorted(domain.DECISIONS))
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
