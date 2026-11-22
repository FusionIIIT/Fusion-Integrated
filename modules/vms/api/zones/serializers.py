from rest_framework import serializers

from modules.vms.models import ZoneElevation


class AccessCheckSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    zone_id = serializers.IntegerField()
    reader_id = serializers.CharField(required=False, allow_blank=True, default="",
                                      max_length=80)
    gate_id = serializers.IntegerField(required=False, allow_null=True)
    at = serializers.DateTimeField(required=False)


class ElevationCreateSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    zone_id = serializers.IntegerField()
    ends_at = serializers.DateTimeField()
    reason = serializers.CharField(max_length=255)


class ElevationSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = ZoneElevation
        fields = ["id", "visit_pass_id", "zone_id", "zone_name", "starts_at", "ends_at",
                  "granted_by_user_id", "reason", "revoked_at"]
