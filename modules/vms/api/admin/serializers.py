from rest_framework import serializers

from modules.vms.models import AccessPolicy, BlacklistEntry


class BlacklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = "__all__"
        read_only_fields = ["version"]


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = "__all__"
