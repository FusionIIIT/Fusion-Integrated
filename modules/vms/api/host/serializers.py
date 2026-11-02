from rest_framework import serializers

from modules.vms.models import VisitPass, VisitRequest


class HostRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name")
    requested_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitRequest
        fields = ["id", "visitor_name", "host_user_id", "purpose", "scheduled_start",
                  "scheduled_end", "status", "requested_zones", "decision_note",
                  "decided_at", "created_at"]


class VisitPassSerializer(serializers.ModelSerializer):
    allowed_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitPass
        fields = ["id", "visit_request", "pass_type", "qr_token", "otp",
                  "valid_from", "valid_until", "is_active", "allowed_zones"]


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
