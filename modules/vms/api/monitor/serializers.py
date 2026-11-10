from rest_framework import serializers


class OnSiteSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    visitor_name = serializers.CharField()
    visitor_phone = serializers.CharField()
    visitor_email = serializers.CharField()
    zone_id = serializers.IntegerField(allow_null=True)
    zone_name = serializers.CharField()
    last_seen_at = serializers.DateTimeField(allow_null=True)
    valid_until = serializers.DateTimeField()
    terminated = serializers.BooleanField()
    overstay = serializers.BooleanField()
    host_user_id = serializers.IntegerField()
    host_name = serializers.CharField()
    host_department = serializers.CharField()


class MovementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    pass_id = serializers.IntegerField(source="visit_pass_id")
    event = serializers.CharField()
    zone_id = serializers.IntegerField(allow_null=True)
    zone_name = serializers.CharField(source="zone.name", default="")
    gate_id = serializers.IntegerField(allow_null=True)
    device_id = serializers.CharField()
    reason = serializers.CharField()
    at = serializers.DateTimeField(source="created_at")


class OutOfBoundsSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    visitor_name = serializers.CharField()
    host_user_id = serializers.IntegerField()
    host_name = serializers.CharField()
    zone_id = serializers.IntegerField()
    zone_name = serializers.CharField()
    since = serializers.DateTimeField()
    reason = serializers.CharField()
    detail = serializers.CharField(allow_blank=True)
