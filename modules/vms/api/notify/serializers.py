from rest_framework import serializers

from modules.vms.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "topic", "subject", "body", "created_at", "read_at"]
        read_only_fields = fields


class OutboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "topic", "channel", "status", "attempts", "last_error",
                  "recipient_user_id", "recipient_visitor_id", "subject",
                  "sent_at", "created_at"]
        read_only_fields = fields


class ArrivalSerializer(serializers.Serializer):
    notification = NotificationSerializer()
    checked_in_at = serializers.DateTimeField()
    request = serializers.DictField(allow_null=True)
