from rest_framework import serializers
from modules.phc.models import ReimbursementClaim, AuditEvent

class ReimbursementClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReimbursementClaim
        fields = [
            "id", "claimant_user_id", "prescription", "expense_date",
            "claimed_amount", "status", "submitted_at", "updated_at"
        ]
        read_only_fields = ["id", "claimant_user_id", "status", "submitted_at", "updated_at"]

class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            "entity_type", "entity_id", "action", "from_status", "to_status",
            "actor_user_id", "note", "at"
        ]
