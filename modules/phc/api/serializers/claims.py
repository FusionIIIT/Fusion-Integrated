from rest_framework import serializers
from modules.phc.models import ReimbursementClaim, ReimbursementPayment

class ReimbursementClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementClaim
        fields = [
            "id", "claimant_user_id", "prescription", "expense_date",
            "claimed_amount", "description", "status", "submitted_at", "updated_at"
        ]
        read_only_fields = ["id", "claimant_user_id", "status", "submitted_at", "updated_at"]

class ClaimActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)

class ClaimDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)

class ReimbursementPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementPayment
        fields = ["paid_on", "reference"]
