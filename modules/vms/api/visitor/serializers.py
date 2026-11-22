from rest_framework import serializers

from modules.vms.models import VisitPass, VisitRequest, Zone
from modules.vms.selectors import passes as pass_selectors
from modules.vms.selectors import requests as request_selectors


class OtpRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OtpVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=12)


class PreRegistrationSerializer(serializers.Serializer):
    """Shape only. Mandatory-field and document rules live in the service so
    BR-037 / BR-186 / BR-187 hold for every caller."""
    full_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    id_doc_type = serializers.CharField(max_length=30, allow_blank=True, required=False)
    id_doc_number = serializers.CharField(max_length=60, allow_blank=True, required=False)
    host_user_id = serializers.IntegerField(required=False, allow_null=True)
    purpose = serializers.CharField(max_length=255, allow_blank=True, required=False)
    scheduled_start = serializers.DateTimeField(required=False, allow_null=True)
    scheduled_end = serializers.DateTimeField(required=False, allow_null=True)
    requested_zones = serializers.PrimaryKeyRelatedField(
        many=True, required=False, queryset=Zone.objects.all())


class VisitRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name")
    requested_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    pass_summary = serializers.SerializerMethodField()

    class Meta:
        model = VisitRequest
        fields = ["id", "visitor_name", "host_user_id", "purpose", "scheduled_start",
                  "scheduled_end", "status", "source", "is_urgent", "requested_zones",
                  "decision_note", "decided_at", "expires_at", "created_at",
                  "pass_summary"]

    def get_pass_summary(self, obj):
        return pass_selectors.pass_summary(obj)


class VisitRequestDetailSerializer(VisitRequestSerializer):
    history = serializers.SerializerMethodField()

    class Meta(VisitRequestSerializer.Meta):
        fields = [*VisitRequestSerializer.Meta.fields, "history"]

    def get_history(self, obj):
        return [{"action": h["action"], "at": h["created_at"],
                 "note": (h["detail"] or {}).get("note", "")}
                for h in request_selectors.history(obj)]


class PassSerializer(serializers.ModelSerializer):
    """QR payload and OTP for the visitor's own active pass (UC-012)."""
    allowed_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    request_id = serializers.IntegerField(source="visit_request_id")

    class Meta:
        model = VisitPass
        fields = ["id", "request_id", "pass_type", "qr_token", "otp", "valid_from",
                  "valid_until", "allowed_zones"]
