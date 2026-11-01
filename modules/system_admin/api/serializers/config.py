"""System configuration serializers for System Admin module."""
from rest_framework import serializers

from modules.system_admin.domain import (
    validate_permitted_system_configuration,
)


class UpdateSystemConfigurationSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    value = serializers.JSONField()
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_key(self, value):
        validate_permitted_system_configuration([value])
        return value
