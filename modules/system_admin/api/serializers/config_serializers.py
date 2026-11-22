"""Serializers for permitted system parameters."""
from __future__ import annotations

from rest_framework import serializers


class SystemParametersSerializer(serializers.Serializer):
    parameters = serializers.DictField(child=serializers.CharField())
