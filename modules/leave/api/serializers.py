"""Serializers for Employee Leave Management endpoints."""
from rest_framework import serializers


class LeaveHealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    module = serializers.CharField()


class LeaveActionResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
