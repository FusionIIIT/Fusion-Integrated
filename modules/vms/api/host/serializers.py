from rest_framework import serializers

from modules.vms.models import PreAuthorization, VisitPass, VisitRequest, Zone


class HostRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name")
    requested_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitRequest
        fields = ["id", "visitor_name", "host_user_id", "purpose", "scheduled_start",
                  "scheduled_end", "status", "source", "is_urgent", "requested_zones",
                  "decision_note", "decided_at", "expires_at", "created_at"]


class VisitPassSerializer(serializers.ModelSerializer):
    allowed_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitPass
        fields = ["id", "visit_request", "pass_type", "valid_from", "valid_until",
                  "is_active", "allowed_zones"]


class WindowSerializer(serializers.Serializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    zones = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=Zone.objects.all())
    window = WindowSerializer(required=False)


class BulkDecisionSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1,
                                max_length=100)
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class UrgentDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class PreAuthorizationSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name", read_only=True)
    zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = PreAuthorization
        fields = ["id", "visitor_name", "zones", "valid_from", "valid_until",
                  "max_visits", "used_visits", "revoked_at"]


class PreAuthorizationCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    id_doc_type = serializers.CharField(max_length=30)
    id_doc_number = serializers.CharField(max_length=60)
    zones = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=Zone.objects.all())
    valid_from = serializers.DateTimeField(required=False)
    valid_until = serializers.DateTimeField()
    max_visits = serializers.IntegerField(min_value=1, required=False, default=1)
