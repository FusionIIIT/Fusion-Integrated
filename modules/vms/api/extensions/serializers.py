from rest_framework import serializers

from modules.vms.models import ExtensionRequest


class ExtensionCreateSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    new_end = serializers.DateTimeField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class ExtensionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class ExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtensionRequest
        fields = ["id", "visit_request", "requested_end", "reason", "status",
                  "decided_by_user_id", "decided_at", "created_at"]
        read_only_fields = fields
