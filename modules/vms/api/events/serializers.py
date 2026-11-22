from rest_framework import serializers


class SlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    capacity = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class EventWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    organizer = serializers.CharField(max_length=150, required=False, allow_blank=True)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField()
    zone_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    allow_restricted_zones = serializers.ListField(child=serializers.IntegerField(),
                                                   required=False)
    slots = SlotSerializer(many=True, required=False)
    fast_lane = serializers.BooleanField(required=False)
    walkin_rate_limit = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class ApproveSerializer(serializers.Serializer):
    attendee_ids = serializers.ListField(child=serializers.IntegerField(), required=False,
                                         allow_null=True, default=None)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
