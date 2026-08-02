"""Wire shapes for the session endpoints.

Declared for the OpenAPI document rather than for validation — these views
build their payloads by hand from the principal, which is not a model.
"""
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class OkSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    csrf_token = serializers.CharField()


class SessionUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField(allow_blank=True)
    kind = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)


class NavItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    to = serializers.CharField()
    icon = serializers.CharField(allow_blank=True)


class NavGroupSerializer(serializers.Serializer):
    """A sidebar section. Already filtered to what the caller was granted —
    the client does none of its own filtering (ADR-0010)."""

    code = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField(allow_blank=True)
    items = NavItemSerializer(many=True)


class SessionSerializer(serializers.Serializer):
    user = SessionUserSerializer()
    active_role = serializers.CharField(allow_null=True)
    roles = serializers.ListField(child=serializers.CharField())
    permissions = serializers.ListField(child=serializers.CharField())
    modules = serializers.ListField(child=serializers.CharField())
    navigation = NavGroupSerializer(many=True)
    csrf_token = serializers.CharField()
