from rest_framework import serializers
from modules.phc.models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "message", "entity_type", "entity_id", "created_at", "read_at"]
        read_only_fields = fields
