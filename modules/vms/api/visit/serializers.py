from rest_framework import serializers


class CheckOutSerializer(serializers.Serializer):
    credential = serializers.CharField()
    gate_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class SelfCheckOutSerializer(serializers.Serializer):
    pass_token = serializers.CharField()


class TerminateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
