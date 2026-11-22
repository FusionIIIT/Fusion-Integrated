from rest_framework import serializers

from modules.vms.domain import muster_state as ms

STATUS_CHOICES = [ms.ACCOUNTED, ms.EVACUATED]


class TriggerSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class RollCallSerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)


class BulkRollCallSerializer(serializers.Serializer):
    marks = RollCallSerializer(many=True, allow_empty=False)


class CachedMarkSerializer(RollCallSerializer):
    marked_at = serializers.DateTimeField()


class ReconcileSerializer(serializers.Serializer):
    entries = CachedMarkSerializer(many=True, allow_empty=False)


class CloseSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)
    force = serializers.BooleanField(required=False, default=False)


class MusterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    trigger_role = serializers.CharField()
    triggered_by_user_id = serializers.IntegerField()
    triggered_at = serializers.DateTimeField()
    closed_at = serializers.DateTimeField(allow_null=True)


class RosterEntrySerializer(serializers.Serializer):
    pass_id = serializers.IntegerField()
    visitor_name = serializers.CharField()
    visitor_phone = serializers.CharField()
    visitor_email = serializers.CharField()
    last_zone_id = serializers.IntegerField(allow_null=True)
    last_zone_name = serializers.CharField()
    last_seen_at = serializers.DateTimeField(allow_null=True)
    host_user_id = serializers.IntegerField()
    host_name = serializers.CharField()
    status = serializers.CharField()
    marked_by_user_id = serializers.IntegerField(allow_null=True)
    marked_at = serializers.DateTimeField(allow_null=True)
