from rest_framework import serializers

from modules.vms.models import Alert, VisitLog


class GateCredentialMixin(serializers.Serializer):
    qr_token = serializers.CharField(required=False, allow_blank=True)
    otp = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not (attrs.get("qr_token") or attrs.get("otp")):
            raise serializers.ValidationError("qr_token or otp is required.")
        return attrs

    def credential(self) -> dict:
        d = self.validated_data
        return {"qr_token": d["qr_token"]} if d.get("qr_token") else {"otp": d["otp"]}


class GateValidateSerializer(GateCredentialMixin):
    gate_id = serializers.IntegerField()
    zone_id = serializers.IntegerField(required=False, allow_null=True)
    device_id = serializers.CharField(required=False, allow_blank=True, default="",
                                      max_length=80)


class GateCheckoutSerializer(serializers.Serializer):
    qr_token = serializers.CharField(required=False, allow_blank=True, default="")


class OverrideSerializer(serializers.Serializer):
    denial_log_id = serializers.IntegerField()
    justification = serializers.CharField(max_length=500)


class EscalationCreateSerializer(serializers.Serializer):
    visit_log_id = serializers.IntegerField()
    note = serializers.CharField(max_length=500)


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500)


class ManualEntrySerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    gate_id = serializers.IntegerField()
    event = serializers.ChoiceField(choices=[VisitLog.Event.CHECK_IN, VisitLog.Event.CHECK_OUT])
    reason = serializers.CharField(max_length=200)
    zone_id = serializers.IntegerField(required=False, allow_null=True)


class AlertHandleSerializer(serializers.Serializer):
    outcome = serializers.CharField(max_length=20)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class OfflineEventSerializer(GateCredentialMixin):
    client_event_id = serializers.UUIDField()
    event = serializers.ChoiceField(choices=[VisitLog.Event.CHECK_IN, VisitLog.Event.CHECK_OUT])
    occurred_at = serializers.DateTimeField()
    zone_id = serializers.IntegerField(required=False, allow_null=True)
    device_id = serializers.CharField(required=False, allow_blank=True, default="",
                                      max_length=80)


class SyncSerializer(serializers.Serializer):
    gate_id = serializers.IntegerField()
    events = OfflineEventSerializer(many=True)


class FailureSerializer(serializers.Serializer):
    code = serializers.CharField()
    rule = serializers.CharField()
    message = serializers.CharField()


class DenialSerializer(serializers.ModelSerializer):
    failures = serializers.SerializerMethodField()
    visitor_name = serializers.CharField(source="visit_pass.visit_request.visitor.full_name")
    overridden = serializers.BooleanField(source="is_overridden")
    escalated = serializers.BooleanField(source="is_escalated")

    class Meta:
        model = VisitLog
        fields = ["id", "visit_pass_id", "visitor_name", "gate_id", "zone_id", "device_id",
                  "failures", "overridden", "escalated", "created_at"]

    def get_failures(self, obj):
        detail = obj.detail or {}
        return detail.get("failures") or [c for c in obj.reason.split(",") if c]


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ["id", "kind", "severity", "ref_type", "ref_id", "status",
                  "handled_by_user_id", "handled_at", "detail", "created_at"]
