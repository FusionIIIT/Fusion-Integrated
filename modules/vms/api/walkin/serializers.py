from rest_framework import serializers


class WalkinRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    id_doc_type = serializers.CharField(max_length=30)
    id_doc_number = serializers.CharField(max_length=60)
    purpose = serializers.CharField(max_length=255)
    host_user_id = serializers.IntegerField(min_value=1)
    host_available = serializers.BooleanField(required=False, default=True)
    gate_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    event_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    zone_ids = serializers.ListField(child=serializers.IntegerField(), required=False,
                                     default=list)


class WalkinDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")


def request_payload(vr, vp=None) -> dict:
    out = {"id": vr.pk, "status": vr.status, "source": vr.source,
           "visitor_name": vr.visitor.full_name, "host_user_id": vr.host_user_id,
           "purpose": vr.purpose, "scheduled_start": vr.scheduled_start,
           "scheduled_end": vr.scheduled_end,
           "contingency_requested_at": vr.contingency_requested_at}
    if vp is not None:
        out["pass"] = {"id": vp.pk, "pass_type": vp.pass_type, "qr_token": vp.qr_token,
                       "otp": vp.otp, "valid_from": vp.valid_from,
                       "valid_until": vp.valid_until}
    return out
