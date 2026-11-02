from rest_framework import serializers


class GateValidateSerializer(serializers.Serializer):
    """Either credential; the service rejects a request with neither."""
    qr_token = serializers.CharField(required=False, allow_blank=True)
    otp = serializers.CharField(required=False, allow_blank=True)
    zone_id = serializers.IntegerField(required=False, allow_null=True)


class GateCheckoutSerializer(serializers.Serializer):
    qr_token = serializers.CharField(required=False, allow_blank=True, default="")
